"""Standalone cell 7 source, executed in the Colab namespace."""
WORKFLOW_COMPLETE = False
pointer = Path(FOLDER_OUT) / DELIVERY_MANIFEST
if pointer.exists():
    previous = json.loads(pointer.read_text(encoding='utf-8'))
    if previous.get('status') == 'running' and not REMPLACER_RUN_INTERROMPU:
        raise RuntimeError('Un run est en cours ou interrompu. Vérifiez son arrêt, puis activez REMPLACER_RUN_INTERROMPU pour relancer.')
inputs_manifest = preflight_v4_inputs()  # Names, mono/48k, exact duration and BWF before models.
run_folder = 'run_' + RUN_ID
run_path = Path(FOLDER_OUT) / run_folder
run_path.mkdir(exist_ok=False)
manifest = {'protocol': 2, 'backend': 'Vtest_V4', 'revision': '2026-10-06-test-v4-cumulative',
            'run_id': RUN_ID, 'run_folder': run_folder, 'status': 'running',
            'inputs': inputs_manifest,
            'settings': {k: v for k, v in list(globals().items())
                         if k.startswith(('DUCK_DEPTH_', 'GAIN_', 'PROFIL_RESPIRATOIRE_'))
                         or k in ('NIVEAU_DENOISE_POURCENTAGE', 'DENOISE_ADAPTATIF', 'PROTECTION_PFX')},
            'upstream_commit': BANDIT_COMMIT, 'checkpoint_md5': BANDIT_CHECKPOINT_MD5,
            'alignment': False, 'scene_merge': False,
            'human_finishing': 'raw_then_residual_cumulative', 'outputs': []}
write_delivery_manifest(pointer, manifest)
try:
    # Snapshot each source without shifting it or borrowing another scene's context.
    for entry in inputs_manifest:
        local = Path(FOLDER_MERGED) / entry['name']
        shutil.copy2(Path(FOLDER_IN) / entry['name'], local)
        if sha256_file(local) != entry['sha256']:
            raise RuntimeError(f"Source modifiée pendant la copie : {entry['name']}")
    preflight_models()
    names = [entry['name'] for entry in inputs_manifest]
    raw_masks = {}
    for entry in inputs_manifest:
        name = entry['name']
        raw_masks[Path(name).stem] = analyze_yamnet(str(Path(FOLDER_MERGED) / name))
        prep_denoise_batch([name], raw_masks)
        raw_masks.clear()  # Reanalyzed one scene at a time during finishing; no full-project mask cache.
    process_bandit_batch(names)
    for entry in inputs_manifest:
        base = Path(entry['name']).stem
        stem = Path(FOLDER_AI_STEMS) / (base + '_Bandit.wav')
        mix = Path(FOLDER_TC_READY) / (base + '_Mix_Temp.wav')
        finish_v4(str(stem), str(mix), str(Path(FOLDER_MERGED) / entry['name']))
        info = sf.info(mix)
        if info.frames != entry['frames'] or info.samplerate != 48000 or info.channels != 1:
            raise RuntimeError(f"Durée/canaux modifiés : {entry['name']}")
        pending = Path(FOLDER_TC_READY) / entry['output_name']
        inject_timecode(str(Path(FOLDER_MERGED) / entry['name']), str(mix), str(pending))
        geom = inspect_delivery_wave(pending)
        if any(geom[k] != entry[k] for k in ('frames', 'sample_rate', 'time_reference')):
            raise RuntimeError(f"Géométrie/timecode modifiés : {entry['name']}")
        output = dict(geom, name=entry['output_name'], role=entry['role'],
                      sha256=sha256_file(pending), umid=read_wave_umid(pending))
        dest = run_path / output['name']
        shutil.copy2(pending, dest)
        verify_delivery_file(dest, output)
        manifest['outputs'].append(output)
        print(f"✅ Scène indépendante : {output['name']}")
    # Assert all outputs before publishing the single complete generation pointer.
    if len(manifest['outputs']) != len(inputs_manifest):
        raise RuntimeError('Lot incomplet.')
    verify_unique_wave_umids([run_path / e['name'] for e in manifest['outputs']],
                             forbidden=[e['umid'] for e in inputs_manifest])
    manifest['status'] = 'complete'
    validate_delivery_manifest(manifest)
    write_delivery_manifest(run_path / DELIVERY_MANIFEST, manifest)
    # Do not overwrite another run that started while this one was running.
    current = json.loads(pointer.read_text(encoding='utf-8'))
    if current.get('run_id') != RUN_ID:
        raise RuntimeError('Un autre traitement a remplacé le pointeur; publication refusée.')
    write_delivery_manifest(pointer, manifest)
    WORKFLOW_COMPLETE = True
    print('🎉 Test V4 terminé. Téléchargez avec le bouton ZIP/PTX du frontend MIS À JOUR.')
except Exception:
    manifest['status'] = 'failed'
    current = json.loads(pointer.read_text(encoding='utf-8'))
    if current.get('run_id') == RUN_ID:
        write_delivery_manifest(pointer, manifest)
    raise
