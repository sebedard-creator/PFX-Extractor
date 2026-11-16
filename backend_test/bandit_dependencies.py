"""Standalone Colab dependency checks; no installation or torch import here."""
import re
from packaging.version import InvalidVersion, Version


def check_bandit_torch_pair(torch_version, audio_version, cuda_version,
                            installed_torch=None, installed_audio=None):
    """Keep matched legacy pairs and allow the documented TorchAudio 2.11 ABI.

    https://docs.pytorch.org/audio/stable/installation.html
    Only the documented 2.11 family is forward-compatible here; do not assume
    that every future TorchAudio release has the same minimum PyTorch version.
    """
    try:
        torch_v, audio_v = Version(torch_version), Version(audio_version)
        for name, loaded, installed in (
                ('torch', torch_v, installed_torch),
                ('torchaudio', audio_v, installed_audio)):
            if installed is not None and loaded != Version(installed):
                raise RuntimeError(
                    f'{name} chargé ({loaded}) différent du paquet installé ({installed}). '
                    "Redémarrez l'environnement Colab pour recharger les paquets, sans les réinstaller.")
    except (InvalidVersion, TypeError) as exc:
        raise RuntimeError('Versions torch/torchaudio illisibles; arrêt de sécurité.') from exc
    exact = torch_v.public == audio_v.public
    stable_abi = (audio_v.release[:2] == (2, 11)
                  and not audio_v.is_prerelease and not audio_v.is_devrelease
                  and not torch_v.is_prerelease and not torch_v.is_devrelease
                  and torch_v >= Version('2.11.0'))
    if not (exact or stable_abi):
        raise RuntimeError(
            f'Paire non prise en charge : torch {torch_version}, torchaudio {audio_version}. '
            'TorchAudio 2.11 accepte PyTorch >=2.11; les anciennes paires doivent correspondre. '
            'Ne pas réinstaller automatiquement : vérifier la matrice de compatibilité.')
    if not cuda_version:
        raise RuntimeError('Build torch sans CUDA; sélectionnez un environnement Colab GPU.')
    match = re.fullmatch(r'(\d+)\.(\d+)', str(cuda_version))
    if match is None:
        raise RuntimeError(f'Version CUDA illisible : {cuda_version!r}.')
    expected = 'cu' + ''.join(match.groups())
    for name, value in (('torch', torch_v), ('torchaudio', audio_v)):
        tag = value.local
        # A missing build suffix isn't evidence of an incompatible binary.
        # Explicit CPU/ROCm or a different CUDA suffix, however, must stop.
        if tag and (tag.startswith(('cpu', 'rocm'))
                    or (tag.startswith('cu') and tag != expected)):
            raise RuntimeError(f'Build {name} {value} incompatible avec CUDA {cuda_version}.')
    return 'ABI stable TorchAudio 2.11' if stable_abi and not exact else 'versions correspondantes'
