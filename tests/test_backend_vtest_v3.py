import ast
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf
from scipy import signal

import delivery_contract as contract
import drive_auth
import protools_export
from tests.test_backend_v330 import scope, notebook
from tests.wav_fixtures import wave_bytes

ROOT = Path(__file__).resolve().parents[1]


def manifest_for(data, name='scene BOOM libre_PFX_Ready.wav'):
    return {'protocol': 1, 'status': 'complete', 'run_id': 'test1', 'run_folder': 'run_test1',
            'outputs': [{'name': name, 'role': 'BOOM', 'sha256': hashlib.sha256(data).hexdigest(),
                         'frames': 48000, 'sample_rate': 48000, 'time_reference': 172800000}]}


class V3Tests(unittest.TestCase):
    def test_compile_and_embedded_sources(self):
        nb = notebook('test_V3')
        for i, cell in enumerate(nb['cells']):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), f'cell{i}', 'exec')
                self.assertEqual(cell['outputs'], [])
        code = ''.join(nb['cells'][6]['source'])
        for path in ('delivery_contract.py', 'backend_test/v3_processing.py'):
            self.assertIn((ROOT / path).read_text(encoding='utf-8').strip(), code)
        self.assertEqual(''.join(nb['cells'][7]['source']).strip(),
                         (ROOT / 'backend_test/v3_workflow.py').read_text(encoding='utf-8').strip())
        self.assertNotIn('initial_mic_alignment', code)
        self.assertNotIn('snowball_merge', code)
        env = scope('test_V3')
        self.assertEqual(env['NIVEAU_DENOISE_POURCENTAGE'], 40)
        self.assertEqual(env['GAIN_BODYTALK_DB'], 4)

    def test_raw_and_residual_attenuation_do_not_multiply(self):
        env = scope('test_V3')
        x = np.full((1000, 1), .1, np.float32)
        out = env['apply_v3_masks'](x, 100, {'frames': {'soft_human': [1]}},
                                    {'frames': {'residual': [1]}})
        np.testing.assert_allclose(out, .005, atol=1e-7)  # -26 dB, not -46 dB
        np.testing.assert_array_equal(x, np.full((1000, 1), .1, np.float32))

    def test_finishing_analyzes_sfx_before_any_attenuation(self):
        env = scope('test_V3')
        with tempfile.TemporaryDirectory() as d:
            source, dest = Path(d) / 'sfx.wav', Path(d) / 'out.wav'
            sf.write(source, np.full(48000, .1), 48000, subtype='FLOAT')
            def residual(x, sr):
                np.testing.assert_allclose(x, .1, atol=1e-7)
                return {'frames': {'residual': [1]}}
            env.update(sf=sf, validate_bandit_audio=lambda x, sr: x,
                       analyze_yamnet=lambda p: {'frames': {'soft_human': [1]}},
                       _analyze_residual_audio=residual)
            env['finish_v3'](source, dest)
            np.testing.assert_allclose(sf.read(dest)[0], .005, atol=1e-7)

    def test_bodytalk_local_margin_and_impact_veto(self):
        env = scope('test_V3')
        x = np.full((1000, 1), .1, np.float32)
        x[0] = .99
        out = env['apply_v3_masks'](x, 100, {'frames': {'bodytalk': [1]}}, {'frames': {}})
        self.assertEqual(out[0, 0], x[0, 0])
        self.assertAlmostEqual(float(out[-1, 0]), .1 * 10 ** (4 / 20), places=6)
        for mask in ('impact_guard', 'human_guard', 'crying', 'mouth'):
            out = env['apply_v3_masks'](x, 100, {'frames': {'bodytalk': [1], mask: [1]}}, {'frames': {}})
            self.assertLessEqual(float(out[-1, 0]), .100001)

    def test_scene_delivery_exact_lengths_timecodes_and_failure_state(self):
        code = (ROOT / 'backend_test/v3_workflow.py').read_text(encoding='utf-8')
        for fail in (False, True):
            with self.subTest(fail=fail), tempfile.TemporaryDirectory() as d:
                env = scope('test_V3')
                env.update(vars(contract))
                env.update(sf=sf, shutil=shutil, Path=Path, json=json,
                           REMPLACER_RUN_INTERROMPU=False, RUN_ID='synthetic',
                           BANDIT_COMMIT='test', BANDIT_CHECKPOINT_MD5='test', print=lambda *a: None)
                for key in ('FOLDER_IN', 'FOLDER_OUT', 'FOLDER_MERGED', 'FOLDER_DENOISED', 'FOLDER_AI_STEMS', 'FOLDER_TC_READY'):
                    path = Path(d) / key
                    path.mkdir()
                    env[key] = str(path)
                names = ['scene BOOM court.wav', 'autre BOOM longue.wav']
                for name, n, tc in zip(names, (4800, 90001), (172800000, 182800000)):
                    (Path(env['FOLDER_IN']) / name).write_bytes(wave_bytes(n, tc))
                # The contract snapshots both scenes; mock ML only, keep actual delivery checks.
                env['preflight_models'] = lambda: None
                env['analyze_yamnet'] = lambda path: {'frames': {}}
                def pre(files, masks):
                    self.assertEqual(len(files), 1)
                    shutil.copy2(Path(env['FOLDER_MERGED']) / files[0], Path(env['FOLDER_DENOISED']) / files[0])
                env['prep_denoise_batch'] = pre
                def separate(files):
                    for name in files:
                        shutil.copy2(Path(env['FOLDER_DENOISED']) / name,
                                     Path(env['FOLDER_AI_STEMS']) / (Path(name).stem + '_Bandit.wav'))
                env['process_bandit_batch'] = separate
                def finish(src, dst):
                    if fail:
                        raise RuntimeError('synthetic failure')
                    shutil.copy2(src, dst)
                env['finish_v3'] = finish
                def inject(original, processed, final):
                    shutil.copy2(processed, final)
                    contract.assign_render_umid(final, forbidden=[contract.read_wave_umid(original)])
                env['inject_timecode'] = inject
                if fail:
                    with self.assertRaisesRegex(RuntimeError, 'synthetic failure'):
                        exec(compile(code, '<workflow>', 'exec'), env)
                else:
                    exec(compile(code, '<workflow>', 'exec'), env)
                manifest = json.loads((Path(env['FOLDER_OUT']) / contract.DELIVERY_MANIFEST).read_text())
                self.assertEqual(manifest['status'], 'failed' if fail else 'complete')
                self.assertEqual(env['WORKFLOW_COMPLETE'], not fail)
                if not fail:
                    self.assertEqual(len(manifest['outputs']), 2)
                    for entry in manifest['outputs']:
                        contract.verify_delivery_file(Path(env['FOLDER_OUT']) / 'run_synthetic' / entry['name'], entry)
                    self.assertEqual(sorted(e['frames'] for e in manifest['outputs']), [4800, 90001])

    def test_input_preflight_rejects_missing_bwf_before_models(self):
        env = scope('test_V3')
        env.update(vars(contract))
        with tempfile.TemporaryDirectory() as d:
            env['FOLDER_IN'] = d
            sf.write(Path(d) / 'BOOM.wav', np.zeros(48000), 48000)
            with self.assertRaisesRegex(ValueError, 'timecode BWF'):
                env['preflight_v3_inputs']()

    def test_contract_rejects_unsafe_names_and_bad_geometry(self):
        for name in ('../BOOM.wav', 'BOOM:LAV.wav', 'CON.wav', 'BOOM_LAV.wav', 'unknown.wav'):
            with self.assertRaises(ValueError):
                contract.microphone_role(name)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'BOOM.wav'
            path.write_bytes(wave_bytes(100))
            with self.assertRaisesRegex(ValueError, 'Durée hors'):
                contract.inspect_delivery_wave(path)

    def test_input_preflight_rejects_wrong_pair_counts(self):
        env = scope('test_V3')
        env.update(vars(contract))
        with tempfile.TemporaryDirectory() as d:
            env['FOLDER_IN'] = d
            for name in ('a BOOM.wav', 'b BOOM.wav', 'c LAV.wav'):
                (Path(d) / name).write_bytes(wave_bytes())
            with self.assertRaisesRegex(ValueError, 'Comptes BOOM/LAV'):
                env['preflight_v3_inputs']()

    def test_contract_rejects_absent_umid_and_mismatched_fact(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'BOOM.wav'
            data = bytearray(wave_bytes())
            bext = data.index(b'bext') + 8
            data[bext + 348:bext + 380] = bytes(32)
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'UMID'):
                contract.inspect_delivery_wave(path)
            data = bytearray(wave_bytes())
            struct.pack_into('<I', data, data.index(b'fact') + 8, 100)
            path.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'fact'):
                contract.inspect_delivery_wave(path, for_export=True)

    @unittest.skipUnless((ROOT / 'template.ptx').is_file(), 'local proprietary template needed')
    def test_real_pt_api_build_and_readback(self):
        try:
            builder = protools_export.resolve_pt_api_builder()
        except RuntimeError as exc:
            self.skipTest(str(exc))
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); processed = root / 'processed'; processed.mkdir()
            data = wave_bytes(); manifest = manifest_for(data)
            manifest['outputs'].append(dict(manifest['outputs'][0],
                name='scene autre LAV libre_PFX_Ready.wav', role='LAV'))
            for entry in manifest['outputs']:
                audio = wave_bytes(identity=entry['name'])
                (processed / entry['name']).write_bytes(audio)
                entry['sha256'] = hashlib.sha256(audio).hexdigest()
            contract.write_delivery_manifest(processed / contract.DELIVERY_MANIFEST, manifest)
            result = protools_export.create_protools_delivery(processed, root / 'exports',
                session_name='V3_synthetic_contract', builder=builder)
            session = builder.__globals__['ProToolsSession'](result['session_path'])
            clips = session.get_timeline_clips(include_fades=False)
            self.assertEqual(len(clips), 2)
            self.assertEqual({c['track'] for c in clips}, {'PFX 01', 'PFX 02'})
            for clip in clips:
                self.assertEqual(clip['length_samples'], 48000)
                self.assertEqual(clip['start_samples'], 172800000)
                self.assertEqual(clip['src_offset_samples'], 0)

    @unittest.skipUnless(shutil.which('ffmpeg'), 'ffmpeg needed')
    def test_real_ffmpeg_preserves_exact_non_frame_aligned_length_and_bwf(self):
        env = scope('test_V3')
        env.update(vars(contract))
        env.update(sf=sf, subprocess=subprocess)
        with tempfile.TemporaryDirectory() as d:
            raw, mix, final = [Path(d) / name for name in ('raw.wav', 'mix.wav', 'final.wav')]
            raw.write_bytes(wave_bytes(1483482, 1823255434))
            sf.write(mix, np.full(1483482, .001, np.float32), 48000, subtype='FLOAT')
            env['inject_timecode'](str(raw), str(mix), str(final))
            geometry = contract.inspect_delivery_wave(final, for_export=True)
            self.assertEqual(geometry, {'frames': 1483482, 'sample_rate': 48000,
                                        'time_reference': 1823255434})
            np.testing.assert_array_equal(sf.read(final, dtype='float32')[0],
                                          sf.read(mix, dtype='float32')[0])
            self.assertNotEqual(contract.read_wave_umid(raw), contract.read_wave_umid(final))
            digest = contract.sha256_file(final)
            contract.ensure_export_extensible(final)
            self.assertEqual(contract.sha256_file(final), digest)

    def test_verified_mapping_ignores_scene_prefixes(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            data = wave_bytes()
            manifest = manifest_for(data)
            for name in ('different BOOM scene_PFX_Ready.wav', 'another LAV name_PFX_Ready.wav'):
                item = dict(manifest['outputs'][0], name=name, role=contract.microphone_role(name))
                manifest['outputs'].append(item)
            for entry in manifest['outputs']:
                (root / entry['name']).write_bytes(data)
            contract.write_delivery_manifest(root / contract.DELIVERY_MANIFEST, manifest)
            descriptors, families = protools_export.collect_processed_manifest(root)
            self.assertEqual([f['family'] for f in families], ['BOOM', 'LAV'])
            self.assertEqual([f['count'] for f in families], [2, 1])
            (root / manifest['outputs'][0]['name']).write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'Empreinte'):
                protools_export.collect_processed_manifest(root)


class VerifiedDownloadTests(unittest.TestCase):
    def exercise(self, fault=None):
        data = wave_bytes()
        manifest = manifest_for(data)
        if fault == 'running':
            manifest['status'] = 'running'
        if fault == 'geometry':
            manifest['outputs'][0]['frames'] += 18018
        if fault == 'umid':
            manifest['outputs'].append(dict(manifest['outputs'][0], name='another_BOOM_PFX_Ready.wav'))
        raw = json.dumps(manifest).encode()
        class Service:
            reads = 0
            def files(self): return self
            def get_media(self, fileId):
                if fileId == 'pointer':
                    self.reads += 1
                    value = raw if self.reads == 1 or fault != 'changed' else b'{}'
                else:
                    value = data if fault != 'corrupt' else b'bad'
                return SimpleNamespace(execute=lambda: value)
            def list(self, **kw):
                return SimpleNamespace(execute=lambda: {'files': [{'id': 'run'}]})
        class Download:
            def __init__(self, handle, request): self.handle, self.request = handle, request
            def next_chunk(self):
                self.handle.write(self.request.execute())
                return None, True
        def files(service, folder):
            if folder == 'parent': return [{'name': contract.DELIVERY_MANIFEST, 'id': 'pointer'}]
            entries = [{'name': manifest['outputs'][0]['name'], 'id': 'wav'}]
            if fault == 'umid':
                entries.append({'name': manifest['outputs'][1]['name'], 'id': 'wav2'})
            if fault == 'extra': entries.append({'name': 'old_BOOM.wav', 'id': 'old'})
            return entries
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            processed = root / 'processed'; processed.mkdir()
            (processed / 'previous.wav').write_bytes(b'keep')
            with (patch.object(drive_auth, 'WORK_DIR', root),
                  patch.object(drive_auth, 'PROCESSED_DIR', processed),
                  patch.object(drive_auth, '_list_files_in_folder', side_effect=files),
                  patch.object(drive_auth, 'MediaIoBaseDownload', Download)):
                run = lambda: drive_auth._download_verified_generation(Service(), 'parent', {'id': 'pointer'})
                if fault:
                    with self.assertRaises(ValueError): run()
                    self.assertEqual((processed / 'previous.wav').read_bytes(), b'keep')
                else:
                    paths, result = run()
                    self.assertTrue(result['verified'])
                    self.assertEqual(paths[0].read_bytes(), data)
                    self.assertFalse((processed / 'previous.wav').exists())
                    self.assertEqual(next(root.glob('processed_previous_*/processed/previous.wav')).read_bytes(), b'keep')

    def test_complete_lot_preserves_previous_locally(self): self.exercise()

    def test_incomplete_corrupt_mixed_changed_lots_refused(self):
        for fault in ('running', 'corrupt', 'geometry', 'extra', 'changed', 'umid'):
            with self.subTest(fault=fault): self.exercise(fault)


if __name__ == '__main__':
    unittest.main()
