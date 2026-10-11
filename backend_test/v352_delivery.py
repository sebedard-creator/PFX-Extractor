"""Generation delivery for the unchanged V3.5.1 audio processing chain."""


def begin_v352_delivery(input_folder, output_folder, settings, replace_interrupted=False):
    from datetime import datetime, timezone
    pointer = Path(output_folder) / DELIVERY_MANIFEST
    if pointer.exists():
        previous = json.loads(pointer.read_text(encoding='utf-8'))
        if previous.get('status') == 'running' and not replace_interrupted:
            raise RuntimeError('Un traitement est en cours ou interrompu. Confirmez son arrêt avant de relancer avec REMPLACER_RUN_INTERROMPU.')
    inputs = []
    names = set()
    for path in sorted(Path(input_folder).iterdir()):
        if not path.is_file() or path.suffix.lower() != '.wav' or path.name.startswith('._'):
            continue
        role = microphone_role(path.name)
        name = safe_audio_name(path.stem + '_PFX_Ready.wav')
        if name.casefold() in names:
            raise ValueError('Noms de sorties dupliqués.')
        names.add(name.casefold())
        inputs.append(dict(inspect_delivery_wave(path), name=path.name, output_name=name,
                           role=role, sha256=sha256_file(path), umid=read_wave_umid(path)))
    if not inputs:
        raise ValueError('Aucun WAV source.')
    counts = {role: sum(e['role'] == role for e in inputs) for role in ('BOOM', 'LAV')}
    if all(counts.values()) and counts['BOOM'] != counts['LAV']:
        raise ValueError('Comptes BOOM/LAV différents.')
    run_id = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '_' + uuid.uuid4().hex[:12]
    run_path = Path(output_folder) / ('run_' + run_id)
    run_path.mkdir(exist_ok=False)
    manifest = dict(protocol=2, backend='V3.5.2', revision='2026-10-06-v352-generations',
                    run_id=run_id, run_folder=run_path.name, status='running',
                    inputs=inputs, outputs=[], settings=settings, alignment=True, scene_merge=True)
    write_delivery_manifest(run_path / DELIVERY_MANIFEST, manifest)
    write_delivery_manifest(pointer, manifest)
    return dict(pointer=pointer, run_path=run_path, manifest=manifest, input_folder=Path(input_folder))


def record_v352_output(delivery, source_name, output_path):
    manifest = delivery['manifest']
    source = next(e for e in manifest['inputs'] if e['name'] == source_name)
    if Path(output_path).name != source['output_name']:
        raise ValueError('Nom de sortie inattendu.')
    if any(e['name'] == source['output_name'] for e in manifest['outputs']):
        raise ValueError('Sortie produite deux fois.')
    # Header compatibility only: no audio, UMID or timecode change.
    before = wave_audio_sha256(output_path)
    ensure_export_extensible(output_path)
    if wave_audio_sha256(output_path) != before:
        raise RuntimeError('Données audio modifiées pendant la normalisation du format WAV.')
    geometry = inspect_delivery_wave(output_path, for_export=True)
    if any(geometry[k] != source[k] for k in ('frames', 'sample_rate', 'time_reference')):
        raise ValueError(f'Durée/timecode modifiés : {source_name}; lot non publié.')
    entry = dict(geometry, name=source['output_name'], role=source['role'],
                 sha256=sha256_file(output_path), umid=read_wave_umid(output_path))
    verify_delivery_file(output_path, entry)
    manifest['outputs'].append(entry)


def complete_v352_delivery(delivery):
    manifest, run_path, pointer = (delivery[k] for k in ('manifest', 'run_path', 'pointer'))
    if {e['name'] for e in manifest['outputs']} != {e['output_name'] for e in manifest['inputs']}:
        raise RuntimeError('Lot incomplet; aucune livraison publiée.')
    if {p.name for p in run_path.glob('*.wav')} != {e['name'] for e in manifest['outputs']}:
        raise RuntimeError('Fichiers inattendus dans le lot.')
    for source in manifest['inputs']:
        if sha256_file(delivery['input_folder'] / source['name']) != source['sha256']:
            raise RuntimeError('Source modifiée pendant le traitement; lot non publié.')
    for output in manifest['outputs']:
        verify_delivery_file(run_path / output['name'], output)
    verify_unique_wave_umids([run_path / e['name'] for e in manifest['outputs']],
                             forbidden=[e['umid'] for e in manifest['inputs']])
    if json.loads(pointer.read_text(encoding='utf-8')).get('run_id') != manifest['run_id']:
        raise RuntimeError('Un autre traitement a remplacé le pointeur; publication refusée.')
    manifest['status'] = 'complete'
    validate_delivery_manifest(manifest)
    write_delivery_manifest(run_path / DELIVERY_MANIFEST, manifest)
    write_delivery_manifest(pointer, manifest)


def fail_v352_delivery(delivery):
    manifest = delivery['manifest']
    manifest['status'] = 'failed'
    write_delivery_manifest(delivery['run_path'] / DELIVERY_MANIFEST, manifest)
    pointer = delivery['pointer']
    if json.loads(pointer.read_text(encoding='utf-8')).get('run_id') == manifest['run_id']:
        write_delivery_manifest(pointer, manifest)
