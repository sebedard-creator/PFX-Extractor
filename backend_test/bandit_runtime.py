"""Runtime embedded verbatim in Vtest: official Bandit v2, local inference only.

No audio is passed to a network operation. Upstream sources and model weights
are downloaded once, verified, and cached. This is NOT DnR-nonverbal or MVSEP.
"""
from pathlib import Path
import hashlib
import importlib
import sys
import time

import numpy as np

BANDIT_COMMIT = 'd5563d9031e95fdaa3e5a73d5020b9a0df61adb6'
BANDIT_CHECKPOINT_URL = 'https://zenodo.org/api/records/12701995/files/checkpoint-multi.ckpt/content'
BANDIT_CHECKPOINT_MD5 = 'fea2868787551b0cff36cfcf7c3622a3'
BANDIT_CHECKPOINT_SIZE = 446680129
BANDIT_RATE = 48000
BANDIT_STEMS = ['speech', 'music', 'sfx']
BANDIT_SOURCES = {
    'LICENSE': '261eeb9e9f8b2b4b0d119366dda99c6fd7d35c64',
    'configs/models/bandit-mus64.yaml': 'c68a3ad1756908bc23726c46e2eb7206c4ee2572',
    'src/models/base.py': '49fd4191102d9e4880d50e6f42dc1030c32086e5',
    'src/models/bandit/bandit.py': '02e0768766f979ffdd79bc280a757d9716abd22f',
    'src/models/bandit/bandsplit.py': '6bf8d4437248391caf9f741abc59fbdd1ebcfda3',
    'src/models/bandit/film.py': 'e30795332ea0e06865ea3d883767db17bb02353c',
    'src/models/bandit/maskestim.py': '8677ea6130407f54dde0265b21227c7f03bfb320',
    'src/models/bandit/tfmodel.py': '21aef03d1f0e814c20db05fe7d14f8019f07713b',
    'src/models/bandit/utils.py': 'ad4eab5d8c5b5396ed717f5b9c365a6900eddd2f',
}


def _file_digest(path, algorithm, git_blob=False):
    digest = hashlib.new(algorithm)
    if git_blob:
        digest.update(f'blob {path.stat().st_size}\0'.encode('ascii'))
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _verified_download(url, path, expected, algorithm, size=None, git_blob=False):
    """GET only; no audio path, body, API key or user information is sent."""
    import requests
    path = Path(path)
    def valid(candidate):
        return (candidate.is_file()
                and (size is None or candidate.stat().st_size == size)
                and _file_digest(candidate, algorithm, git_blob) == expected)
    if valid(path):
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_name(path.name + '.part')
    for attempt in range(1, 4):
        try:
            print(f'Téléchargement public : {path.name} ({attempt}/3)')
            with requests.get(url, stream=True, timeout=(20, 120)) as response:
                response.raise_for_status()
                with part.open('wb') as handle:
                    for block in response.iter_content(1024 * 1024):
                        handle.write(block)
            if not valid(part):
                raise RuntimeError(f'Intégrité incorrecte : {path.name}')
            part.replace(path)
            return path
        except Exception:
            part.unlink(missing_ok=True)
            if attempt == 3:
                raise
            time.sleep(3 * attempt)


def prepare_bandit_assets(cache_dir):
    cache = Path(cache_dir)
    package_name = 'pfx_bandit_' + BANDIT_COMMIT[:12]
    source_root = cache / package_name
    for relative, blob in BANDIT_SOURCES.items():
        _verified_download(
            f'https://raw.githubusercontent.com/kwatcharasupat/bandit-v2/{BANDIT_COMMIT}/{relative}',
            source_root / relative, blob, 'sha1', git_blob=True,
        )
    checkpoint = _verified_download(
        BANDIT_CHECKPOINT_URL, cache / 'checkpoint-multi.ckpt',
        BANDIT_CHECKPOINT_MD5, 'md5', BANDIT_CHECKPOINT_SIZE,
    )
    return source_root, checkpoint


def bandit_model_state(checkpoint):
    """Extract only the model from the original Lightning training checkpoint."""
    state = checkpoint.get('state_dict')
    if not isinstance(state, dict):
        raise RuntimeError('Checkpoint Bandit sans state_dict attendu.')
    result = {key[len('model.'):]: value for key, value in state.items()
              if key.startswith('model.')}
    if not result:
        raise RuntimeError('Checkpoint Bandit sans paramètres model.*.')
    return result


def load_bandit(cache_dir, device='cuda'):
    import torch
    import yaml
    source_root, checkpoint_path = prepare_bandit_assets(cache_dir)
    cache_parent = str(source_root.parent.resolve())
    if cache_parent not in sys.path:
        sys.path.insert(0, cache_parent)
    module = importlib.import_module(source_root.name + '.src.models.bandit.bandit')
    config = yaml.safe_load((source_root / 'configs/models/bandit-mus64.yaml').read_text())
    model = module.Bandit(fs=BANDIT_RATE, stems=list(BANDIT_STEMS), **config['kwargs'])
    checkpoint = torch.load(checkpoint_path, map_location='cpu', weights_only=True)
    # No strict=False: an incompatible checkpoint must stop before any real batch.
    model.load_state_dict(bandit_model_state(checkpoint), strict=True)
    del checkpoint
    return model.eval().to(device)


def validate_bandit_audio(audio, sample_rate):
    audio = np.asarray(audio, dtype=np.float32)
    if sample_rate != BANDIT_RATE:
        raise ValueError(f'Vtest attend du 48000 Hz, reçu {sample_rate}.')
    if audio.ndim != 2 or audio.shape[1] != 1 or not len(audio):
        raise ValueError('Vtest attend un WAV mono non vide (N, 1).')
    if not np.isfinite(audio).all():
        raise ValueError('Audio contenant NaN ou Inf.')
    return audio


def bandit_overlap_add(audio, predict, chunk_samples=384000, hop_samples=48000):
    """Bounded GPU input, CPU overlap-add; preserve sample count and gain.

    Eight-second windows / one-second hop, as in the upstream inference config.
    Symmetric reflected context and actual window-sum normalization prevent edge
    fades, including for very short clips. Only the SFX stem is retained.
    """
    audio = validate_bandit_audio(audio, BANDIT_RATE)
    if not 0 < hop_samples <= chunk_samples or chunk_samples < 2:
        raise ValueError('Fenêtre/pas Bandit invalides.')
    n = len(audio)
    pad = chunk_samples
    padded = np.pad(audio[:, 0], (pad, pad), mode='reflect' if n > 1 else 'edge')
    window = np.hanning(chunk_samples + 1)[:-1].astype(np.float32)
    result = np.zeros(len(padded), dtype=np.float32)
    weight = np.zeros(len(padded), dtype=np.float32)
    starts = range(0, len(padded) - chunk_samples + 1, hop_samples)
    total = len(starts)
    for index, start in enumerate(starts):
        # Windows wholly outside the retained region cannot contribute.
        end = start + chunk_samples
        if end <= pad or start >= pad + n:
            continue
        chunk = np.ascontiguousarray(padded[start:end])
        estimate = np.asarray(predict(chunk), dtype=np.float32)
        if estimate.shape != (chunk_samples,) or not np.isfinite(estimate).all():
            raise RuntimeError('Sortie SFX Bandit invalide (forme/NaN/Inf). Aucun bypass.')
        result[start:end] += estimate * window
        weight[start:end] += window
        if index % 30 == 0:
            print(f'   Bandit : fenêtre {index + 1}/{total}')
    result, weight = result[pad:pad + n], weight[pad:pad + n]
    if np.any(weight <= 0):
        raise RuntimeError('Trou dans la reconstruction Bandit.')
    return (result / weight).reshape(-1, 1)


def predict_bandit_sfx(model, chunk):
    import torch
    device = next(model.parameters()).device
    tensor = torch.from_numpy(np.ascontiguousarray(chunk)).reshape(1, 1, -1).to(device)
    with torch.inference_mode():
        output = model({'mixture': {'audio': tensor}})
        estimate = output['estimates']['sfx']['audio']
        if tuple(estimate.shape) != (1, 1, len(chunk)):
            raise RuntimeError(f'Forme SFX inattendue : {tuple(estimate.shape)}')
        return estimate[0, 0].detach().float().cpu().numpy().copy()


def bandit_separate_audio(model, audio, sample_rate):
    audio = validate_bandit_audio(audio, sample_rate)
    return bandit_overlap_add(audio, lambda chunk: predict_bandit_sfx(model, chunk))
