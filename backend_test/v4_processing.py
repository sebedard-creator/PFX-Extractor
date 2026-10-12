"""Bandit V4: SFX with successive raw-mask and residual attenuation."""


def finish_v4(stem_path, output_path, original_path):
    audio, sr = sf.read(stem_path, dtype='float32', always_2d=True)
    audio = validate_bandit_audio(audio, sr)
    # Like V3.5.2, the first decisions come from the original recording.
    raw_masks = analyze_yamnet(original_path)
    first = apply_v4_raw_masks(audio, sr, raw_masks)
    # Residual detector sees the ALREADY attenuated SFX, with the same +18 dB option.
    residual = _analyze_residual_audio(first, sr) if DUCK_DEPTH_RESIDUS > 0 else {'frames': {}}
    result = apply_v4_residual_and_bodytalk(first, sr, raw_masks, residual)
    if result.shape != audio.shape or not np.isfinite(result).all():
        raise RuntimeError('Finition V4 invalide; aucune publication.')
    sf.write(output_path, result, sr, subtype='FLOAT')


def apply_v4_raw_masks(audio, sr, masks):
    """First attenuation: maximum within raw-derived masks, before residual analysis."""
    result = audio.copy()
    block_size = max(1, int(round(sr * YAMNET_MASK_BLOCK_S)))
    depths = {'human': DUCK_DEPTH_HUMAIN / 100.0,
              'soft_human': DUCK_DEPTH_SOUFFLES / 100.0,
              'crying': DUCK_DEPTH_PLEURS / 100.0,
              'mouth': DUCK_DEPTH_BOUCHE / 100.0,
              'ambience': DUCK_DEPTH_AMBIANCE / 100.0,
              'outside_pfx': DUCK_DEPTH_HORS_PFX / 100.0}
    for start in range(0, len(result), block_size):
        end = min(len(result), start + block_size)
        values = {k: yamnet_mask_block(masks, k, start, end, sr) for k in depths}
        pfx = yamnet_mask_block(masks, 'pfx', start, end, sr) * PROTECTION_PFX / 100.0
        values['human'] *= 1 - .35 * pfx
        values['ambience'] *= 1 - .85 * pfx
        values['outside_pfx'] *= 1 - .55 * pfx
        reduction = np.maximum.reduce([values[k] * depths[k] for k in depths])
        result[start:end] *= np.clip(1 - reduction, .03, 1).reshape(-1, 1)
    return result


def apply_v4_residual_and_bodytalk(audio, sr, masks, residual):
    """Second attenuation multiplies the first; retain V3 local bodytalk controls."""
    from scipy.ndimage import maximum_filter1d, uniform_filter1d
    result = audio.copy()
    n = len(result)
    weight = np.zeros(n, np.float32)
    block_size = max(1, int(round(sr * YAMNET_MASK_BLOCK_S)))
    depth = np.clip(DUCK_DEPTH_RESIDUS / 100.0, 0, .95)
    for start in range(0, n, block_size):
        end = min(n, start + block_size)
        values = {k: yamnet_mask_block(masks, k, start, end, sr)
                  for k in ('human', 'soft_human', 'crying', 'mouth', 'ambience',
                            'outside_pfx', 'human_guard', 'impact_guard', 'bodytalk')}
        res = yamnet_mask_block(residual, 'residual', start, end, sr)
        guard = yamnet_mask_block(residual, 'human_guard', start, end, sr)
        veto = np.maximum.reduce([values[k] for k in values if k != 'bodytalk'] + [res, guard])
        weight[start:end] = values['bodytalk'] * np.square(np.clip(1 - veto, 0, 1))
        result[start:end] *= np.clip(1 - depth * res, .05, 1).reshape(-1, 1)
    # The bodytalk gain is applied once, after both attenuations, with V3 peak margin.
    radius = max(1, int(round(.25 * sr)))
    local_peak = maximum_filter1d(np.max(np.abs(result), axis=1), size=2 * radius + 1, mode='nearest')
    headroom = np.maximum(0, 20 * np.log10(.98 / np.maximum(local_peak, 1e-12)))
    requested = np.clip(float(GAIN_BODYTALK_DB), 0, 4) * weight
    available = np.minimum(headroom, 4.0)
    available = np.minimum(available, uniform_filter1d(available, size=2 * radius + 1, mode='nearest'))
    gain_db = np.minimum(requested, available)
    result *= np.power(10.0, gain_db / 20.0).astype(np.float32).reshape(-1, 1)
    print(f'      V4 : masques bruts puis résidus, retrait cumulatif; bodytalk effectif max +{float(np.max(gain_db)):.2f} dB')
    return result


def preflight_v4_inputs():
    files = sorted([p for p in Path(FOLDER_IN).iterdir()
                    if p.is_file() and p.suffix.lower() == '.wav' and not p.name.startswith('._')],
                   key=lambda p: natural_sort_key(p.name))
    if not files:
        raise ValueError('Aucun WAV source.')
    seen = set()
    entries = []
    for path in files:
        role = microphone_role(path.name)
        output_name = path.stem + '_PFX_Ready.wav'
        safe_audio_name(output_name)
        if output_name.casefold() in seen:
            raise ValueError('Noms de sorties dupliqués sans tenir compte de la casse.')
        seen.add(output_name.casefold())
        info = inspect_delivery_wave(path)
        entries.append(dict(info, name=path.name, output_name=output_name,
                            role=role, sha256=sha256_file(path), umid=read_wave_umid(path)))
    counts = {role: sum(e['role'] == role for e in entries) for role in ('BOOM', 'LAV')}
    if all(counts.values()) and counts['BOOM'] != counts['LAV']:
        raise ValueError(f'Comptes BOOM/LAV différents : {counts}. Aucun appariement ni décalage appliqué.')
    return entries
