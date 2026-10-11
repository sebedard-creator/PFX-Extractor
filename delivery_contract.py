"""Test V3 delivery contract, also embedded in the standalone Colab notebook."""
import hashlib
import json
import re
import struct
import uuid
from pathlib import Path

DELIVERY_MANIFEST = 'PFX_delivery.json'
RENDER_UMID_PREFIX = bytes.fromhex('060a2b340101010501010f1013000000')


def wave_chunk_extent(path, wanted):
    """Locate one RIFF chunk with bounds checks; no audio decoding or mutation."""
    with Path(path).open('rb') as handle:
        header = handle.read(12)
        if len(header) != 12 or header[:4] != b'RIFF' or header[8:] != b'WAVE':
            raise ValueError(f'WAV RIFF invalide : {Path(path).name}')
        end = struct.unpack_from('<I', header, 4)[0] + 8
        handle.seek(0, 2)
        if end > handle.tell():
            raise ValueError('WAV tronqué.')
        handle.seek(12)
        matches = []
        while handle.tell() + 8 <= end:
            tag, size = struct.unpack('<4sI', handle.read(8))
            start = handle.tell()
            if start + size > end:
                raise ValueError('Chunk WAV tronqué.')
            if tag == wanted:
                matches.append((start, size))
            handle.seek(start + size + size % 2)
        if len(matches) != 1:
            raise ValueError(f'Chunk {wanted!r} absent ou dupliqué : {Path(path).name}')
        return matches[0]


def read_wave_umid(path):
    offset, size = wave_chunk_extent(path, b'bext')
    if size < 412:
        raise ValueError(f'UMID BWF absent : {Path(path).name}')
    with Path(path).open('rb') as handle:
        handle.seek(offset + 348)
        umid = handle.read(64)
    if not any(umid[:32]):
        raise ValueError(f'UMID BWF vide : {Path(path).name}')
    return umid.hex()


def wave_audio_sha256(path):
    offset, size = wave_chunk_extent(path, b'data')
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        handle.seek(offset)
        while size:
            block = handle.read(min(size, 1024 * 1024))
            if not block:
                raise ValueError('Audio tronqué.')
            digest.update(block)
            size -= len(block)
    return digest.hexdigest()


def assign_render_umid(path, forbidden=()):
    """Only for newly rendered staging WAVs. Fresh native-compatible basic UMID.

    Keep the observed native label/zero instance and use a UUID4 material number.
    Write bytes directly AFTER FFmpeg; never stringify via signed strtoll in FFmpeg.
    """
    forbidden_basic = {value[:64].lower() for value in forbidden}
    for _ in range(10):
        umid = RENDER_UMID_PREFIX + uuid.uuid4().bytes + bytes(32)
        if umid[:32].hex() not in forbidden_basic:
            break
    else:
        raise RuntimeError('Impossible de générer un UMID distinct; livraison refusée.')
    offset, size = wave_chunk_extent(path, b'bext')
    if size < 412:
        raise ValueError('BWF trop court pour écrire un UMID.')
    before = wave_audio_sha256(path)
    with Path(path).open('r+b') as handle:
        handle.seek(offset + 348)
        handle.write(umid)
    if read_wave_umid(path) != umid.hex() or wave_audio_sha256(path) != before:
        raise RuntimeError('Échec de vérification UMID/audio; livraison refusée.')
    return umid.hex()


def verify_unique_wave_umids(paths, forbidden=()):
    seen = {value[:64].lower(): 'source' for value in forbidden}
    for path in paths:
        basic = read_wave_umid(path)[:64]
        if basic in seen:
            raise ValueError(f'UMID dupliqué : {Path(path).name} et {seen[basic]}. '
                             'Import Pro Tools dangereux; livraison refusée. Refaire avec le backend corrigé.')
        seen[basic] = Path(path).name


def safe_audio_name(name):
    if (not isinstance(name, str) or not name or name in ('.', '..')
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or name.endswith((' ', '.'))
            or name.split('.')[0].upper() in {'CON', 'PRN', 'AUX', 'NUL',
                *(f'COM{i}' for i in range(1, 10)), *(f'LPT{i}' for i in range(1, 10))}
            or not name.lower().endswith('.wav')):
        raise ValueError(f'Nom WAV non compatible Windows : {name!r}')
    return name


def microphone_role(name):
    safe_audio_name(name)
    roles = [role for role in ('BOOM', 'LAV') if role.casefold() in name.casefold()]
    if len(roles) != 1:
        raise ValueError(f'Nom ambigu : un seul identifiant BOOM ou LAV requis : {name}')
    return roles[0]


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def inspect_delivery_wave(path, for_export=False):
    """Read RIFF geometry/BWF time reference, not audio; reject unsupported inputs early."""
    path = Path(path)
    chunks = {}
    with path.open('rb') as handle:
        size = path.stat().st_size
        header = handle.read(12)
        if len(header) != 12 or header[:4] != b'RIFF' or header[8:] != b'WAVE':
            raise ValueError(f'WAV RIFF requis (RF64 non pris en charge) : {path.name}')
        riff_end = struct.unpack_from('<I', header, 4)[0] + 8
        if riff_end > size:
            raise ValueError(f'WAV tronqué : {path.name}')
        while handle.tell() + 8 <= riff_end:
            tag, length = struct.unpack('<4sI', handle.read(8))
            offset = handle.tell()
            if offset + length > riff_end:
                raise ValueError(f'Chunk WAV tronqué : {path.name}')
            if tag in (b'fmt ', b'data', b'bext', b'fact'):
                if tag in chunks:
                    raise ValueError(f'Chunk WAV dupliqué : {path.name}')
                chunks[tag] = (length, handle.read(min(length, 412)) if tag != b'data' else b'')
            handle.seek(offset + length + length % 2)
    if not all(k in chunks for k in (b'fmt ', b'data', b'bext')):
        raise ValueError(f'WAV sans format, audio ou timecode BWF : {path.name}')
    fmt = chunks[b'fmt '][1]
    if len(fmt) < 16 or chunks[b'bext'][0] < 412:
        raise ValueError(f'Entête WAV/BWF invalide : {path.name}')
    code, channels, rate, byte_rate, align, bits = struct.unpack_from('<HHIIHH', fmt)
    if code == 0xfffe and len(fmt) >= 40:
        if fmt[28:40] != bytes.fromhex('00001000800000aa00389b71'):
            raise ValueError(f'Sous-format WAV inconnu : {path.name}')
        code = struct.unpack_from('<I', fmt, 24)[0]
    if (channels != 1 or rate != 48000 or code not in (1, 3)
            or bits not in ((16, 24, 32) if code == 1 else (32,))
            or align != bits // 8 or byte_rate != rate * align
            or chunks[b'data'][0] % align):
        raise ValueError(f'WAV mono PCM/float 48 kHz à échantillons complets requis : {path.name}')
    frames = chunks[b'data'][0] // align
    # Current pt_api template builder geometry; do not silently pad or truncate.
    if not 1024 <= frames <= 0xffffff:
        raise ValueError(f'Durée hors profil export PTX (1024–16777215 samples) : {path.name}')
    time_reference = struct.unpack_from('<Q', chunks[b'bext'][1], 338)[0]
    if (time_reference > 0xffffffff or not any(chunks[b'bext'][1][348:380])
            or struct.unpack_from('<H', chunks[b'bext'][1], 346)[0] not in (1, 2)):
        raise ValueError(f'Timecode hors profil UInt32 ou UMID BWF absent : {path.name}')
    if for_export:
        fact = chunks.get(b'fact', (0, b''))[1]
        if (len(fmt) < 40 or struct.unpack_from('<H', fmt)[0] != 0xfffe
                or code != 3 or bits != 32 or struct.unpack_from('<H', fmt, 16)[0] < 22
                or struct.unpack_from('<H', fmt, 18)[0] != 32
                or len(fact) < 4 or struct.unpack_from('<I', fact)[0] != frames):
            raise ValueError(f'Export PTX : float32 extensible/fact correct requis : {path.name}')
    return {'frames': frames, 'sample_rate': rate, 'time_reference': time_reference}


def validate_delivery_manifest(manifest):
    if (not isinstance(manifest, dict) or manifest.get('protocol') not in (1, 2)
            or manifest.get('status') != 'complete'):
        raise ValueError('Traitement incomplet ou manifeste incompatible; téléchargement refusé.')
    run_id = manifest.get('run_id', '')
    if not isinstance(run_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]+', run_id):
        raise ValueError('Identifiant de traitement invalide.')
    if manifest.get('run_folder') != 'run_' + run_id:
        raise ValueError('Dossier de traitement invalide.')
    outputs = manifest.get('outputs')
    if not isinstance(outputs, list) or not outputs:
        raise ValueError('Manifeste sans WAV.')
    names = set()
    identities = set()
    source_identities = {e['umid'][:64] for e in manifest.get('inputs', []) if 'umid' in e}
    for item in outputs:
        name = safe_audio_name(item['name'])
        if name.casefold() in names:
            raise ValueError('WAV dupliqué dans le manifeste.')
        names.add(name.casefold())
        if item.get('role') != microphone_role(name):
            raise ValueError('Rôle BOOM/LAV incohérent dans le manifeste.')
        if not re.fullmatch(r'[0-9a-f]{64}', item.get('sha256', '')):
            raise ValueError('Empreinte WAV invalide.')
        if (type(item.get('frames')) is not int or not 1024 <= item['frames'] <= 0xffffff
                or item.get('sample_rate') != 48000
                or type(item.get('time_reference')) is not int or item['time_reference'] < 0):
            raise ValueError('Géométrie WAV invalide dans le manifeste.')
        if manifest['protocol'] == 2:
            umid = item.get('umid', '')
            if (not isinstance(umid, str) or not re.fullmatch(r'[0-9a-f]{128}', umid)
                    or not umid.startswith(RENDER_UMID_PREFIX.hex()) or umid[64:] != '0' * 64):
                raise ValueError('UMID de rendu invalide dans le manifeste.')
            if umid[:64] in identities or umid[:64] in source_identities:
                raise ValueError('UMID dupliqué ou réutilisé depuis le brut; livraison refusée.')
            identities.add(umid[:64])
    return outputs


def verify_delivery_file(path, entry):
    if sha256_file(path) != entry['sha256']:
        raise ValueError(f'Empreinte incorrecte, WAV incomplet ou mauvais lot : {entry["name"]}')
    info = inspect_delivery_wave(path, for_export=True)
    if any(info[k] != entry[k] for k in ('frames', 'sample_rate', 'time_reference')):
        raise ValueError(f'Durée/timecode incorrect : {entry["name"]}')
    if 'umid' in entry and read_wave_umid(path) != entry['umid']:
        raise ValueError(f'UMID différent du manifeste : {entry["name"]}')


def ensure_export_extensible(path):
    """Normalize a plain IEEE-float fmt header only; never touch data/BWF payloads.

    Some FFmpeg versions emit fmt=3 (18 bytes) for mono, others extensible (40).
    pt_api requires the latter. Only our newly rendered staging WAV is rewritten.
    """
    path = Path(path)
    before = inspect_delivery_wave(path)
    data = path.read_bytes()
    pos = 12
    while pos + 8 <= len(data):
        tag, size = struct.unpack_from('<4sI', data, pos)
        end = pos + 8 + size + size % 2
        if tag == b'fmt ':
            fmt = data[pos + 8:pos + 8 + size]
            code = struct.unpack_from('<H', fmt)[0]
            if code == 0xfffe:
                inspect_delivery_wave(path, for_export=True)
                return
            if code != 3 or struct.unpack_from('<H', fmt, 14)[0] != 32:
                raise ValueError('Seul un rendu float32 peut être normalisé pour PTX.')
            replacement = struct.pack('<HHIIHHHHI', 0xfffe, 1, 48000, 192000, 4, 32, 22, 32, 4)
            replacement += bytes.fromhex('0300000000001000800000aa00389b71')
            normalized = bytearray(data[:pos] + b'fmt ' + struct.pack('<I', 40) + replacement + data[end:])
            struct.pack_into('<I', normalized, 4, len(normalized) - 8)
            pending = path.with_name(path.name + '.extensible.part')
            pending.write_bytes(normalized)
            if inspect_delivery_wave(pending, for_export=True) != before:
                raise ValueError('Géométrie modifiée pendant la normalisation WAV.')
            pending.replace(path)
            return
        pos = end
    raise ValueError('Chunk fmt absent.')


def write_delivery_manifest(path, manifest):
    path = Path(path)
    pending = path.with_name(path.name + '.part')
    pending.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
    pending.replace(path)
