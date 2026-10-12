"""Cumulative Bandit finishing, temporal behavior and actual BWF delivery."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import numpy as np
import soundfile as sf

import delivery_contract as contract
from tests.test_backend_v330 import notebook, scope
from tests.wav_fixtures import wave_bytes

ROOT = Path(__file__).resolve().parents[1]


class V4Tests(unittest.TestCase):
    def environment(self):
        env = scope('test_V4')
        env.update(sf=sf, validate_bandit_audio=lambda x, sr: x)
        return env

    def finish(self, env, audio, raw, residual):
        first = env['apply_v4_raw_masks'](audio, 100, {'frames': raw})
        return env['apply_v4_residual_and_bodytalk'](first, 100, {'frames': raw}, {'frames': residual})

    def test_standalone_notebook_and_unchanged_bandit_settings(self):
        old, new = notebook('test_V3'), notebook('test_V4')
        for i in (2, 4, 5, 8):
            self.assertEqual(old['cells'][i]['source'], new['cells'][i]['source'])
        before, after = scope('test_V3'), scope('test_V4')
        for key in before:
            if key.startswith(('DUCK_DEPTH_', 'GAIN_', 'YAMNET_', 'PROFIL_RESPIRATOIRE_')) or key in (
                    'NIVEAU_DENOISE_POURCENTAGE', 'DENOISE_ADAPTATIF', 'PROTECTION_PFX'):
                if not callable(before[key]):
                    self.assertEqual(before[key], after[key], key)
        for i, cell in enumerate(new['cells']):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), f'cell{i}', 'exec')
                self.assertEqual(cell['outputs'], [])
        engine = ''.join(new['cells'][6]['source'])
        for path in ('delivery_contract.py', 'backend_test/v4_processing.py'):
            self.assertIn((ROOT / path).read_text(encoding='utf-8').strip(), engine)
        self.assertEqual(''.join(new['cells'][7]['source']).strip(),
                         (ROOT / 'backend_test/v4_workflow.py').read_text(encoding='utf-8').strip())
        for term in ('initial_mic_alignment', 'snowball_merge'):
            self.assertNotIn(term, engine)

    def test_cumulative_95_then_90_gives_minus_46_db(self):
        env = self.environment()
        audio = np.full((1000, 1), .1, np.float32)
        out = self.finish(env, audio, {'soft_human': [1]}, {'residual': [1]})
        np.testing.assert_allclose(out, .0005, atol=1e-8)
        np.testing.assert_array_equal(audio, np.full((1000, 1), .1, np.float32))
        v3 = scope('test_V3')
        control = v3['apply_v3_masks'](audio, 100, {'frames': {'soft_human': [1]}},
                                      {'frames': {'residual': [1]}})
        np.testing.assert_allclose(control, .005, atol=1e-7)

    def test_first_masks_maximum_not_sum_and_pfx_does_not_veto_breaths(self):
        env = self.environment()
        audio = np.full((1000, 1), .1, np.float32)
        out = self.finish(env, audio, {'human': [1], 'soft_human': [1], 'mouth': [1], 'pfx': [1]}, {})
        np.testing.assert_allclose(out, .005, atol=1e-7)

    def test_residual_detector_receives_attenuated_audio_and_raw_path(self):
        env = self.environment()
        with tempfile.TemporaryDirectory() as d:
            stem, dest = Path(d) / 'bandit.wav', Path(d) / 'final.wav'
            sf.write(stem, np.full(48001, .1), 48000, subtype='FLOAT')
            observations = []
            def raw(path):
                observations.append(path)
                return {'frames': {'soft_human': [1]}}
            def residual(audio, sr):
                np.testing.assert_allclose(audio, .005, atol=1e-7)
                self.assertEqual(sr, 48000)
                return {'frames': {'residual': [1]}}
            env.update(analyze_yamnet=raw, _analyze_residual_audio=residual)
            env['finish_v4'](str(stem), str(dest), 'original_snapshot.wav')
            self.assertEqual(observations, ['original_snapshot.wav'])
            result, sr = sf.read(dest)
            self.assertEqual((len(result), sr), (48001, 48000))
            np.testing.assert_allclose(result, .0005, atol=1e-8)

    def test_disabled_residual_skips_detector_keeps_first_attenuation(self):
        env = self.environment()
        env.update(DUCK_DEPTH_RESIDUS=0,
                   analyze_yamnet=lambda p: {'frames': {'soft_human': [1]}},
                   _analyze_residual_audio=lambda *a: self.fail('Residual analysis must be skipped'))
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / 'sfx.wav', Path(d) / 'out.wav'
            sf.write(src, np.full(48000, .1), 48000, subtype='FLOAT')
            env['finish_v4'](str(src), str(dst), 'raw.wav')
            np.testing.assert_allclose(sf.read(dst)[0], .005, atol=1e-7)

    def test_bodytalk_applied_once_and_human_impact_veto_preserved(self):
        env = self.environment()
        audio = np.full((1000, 1), .1, np.float32)
        out = self.finish(env, audio, {'bodytalk': [1]}, {})
        np.testing.assert_allclose(out, .1 * 10 ** (4 / 20), atol=1e-7)
        for mask in ('soft_human', 'mouth', 'crying', 'human_guard', 'impact_guard'):
            out = self.finish(env, audio, {'bodytalk': [1], mask: [1]}, {})
            self.assertLessEqual(float(out.max()), .100001)
        out = self.finish(env, audio, {'bodytalk': [1]}, {'human_guard': [1]})
        np.testing.assert_allclose(out, .1, atol=1e-7)
        audio[0] = .99
        out = self.finish(env, audio, {'bodytalk': [1]}, {})
        self.assertEqual(out[0, 0], audio[0, 0])
        self.assertAlmostEqual(float(out[-1, 0]), .1 * 10 ** (4 / 20), places=6)

    def test_temporal_masks_do_not_attenuate_entire_scene(self):
        env = self.environment()
        audio = np.full((1000, 1), .1, np.float32)
        out = self.finish(env, audio, {'soft_human': [0, 0, 1, 1, 0, 0]}, {'residual': [0, 0, 1, 1, 0, 0]})
        self.assertAlmostEqual(float(out[0, 0]), .1, places=6)
        self.assertLess(float(out[145, 0]), .001)
        self.assertAlmostEqual(float(out[-1, 0]), .1, places=6)
        self.assertEqual(out.shape, audio.shape)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_actual_workflow_bwf_uses_shared_frontend_contract_and_fails_closed(self):
        for failure in (False, True):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as d:
                env = self.environment()
                env.update(vars(contract))
                env.update(shutil=shutil, subprocess=subprocess, RUN_ID='v4synthetic',
                           REMPLACER_RUN_INTERROMPU=False, BANDIT_COMMIT='synthetic', BANDIT_CHECKPOINT_MD5='synthetic')
                for key in ('FOLDER_IN', 'FOLDER_OUT', 'FOLDER_MERGED', 'FOLDER_DENOISED', 'FOLDER_AI_STEMS', 'FOLDER_TC_READY'):
                    path = Path(d) / key
                    path.mkdir()
                    env[key] = str(path)
                raw = Path(env['FOLDER_IN']) / 'scene_BOOM_1.wav'
                raw.write_bytes(wave_bytes(90001, 1823255434, level=.1))
                old = Path(env['FOLDER_OUT']) / 'run_v352_old'
                old.mkdir()
                (old / 'retained.txt').write_text('previous run')
                contract.write_delivery_manifest(Path(env['FOLDER_OUT']) / contract.DELIVERY_MANIFEST,
                                                 {'status': 'complete', 'backend': 'V3.5.2', 'run_id': 'v352_old'})
                observations = []
                def analyze(path):
                    observations.append(Path(path))
                    return {'frames': {'soft_human': [1]}}
                def residual(audio, sr):
                    np.testing.assert_allclose(audio, .005, atol=1e-7)
                    if failure:
                        raise RuntimeError('detector failed')
                    return {'frames': {'residual': [1]}}
                env.update(preflight_models=lambda: None, analyze_yamnet=analyze,
                           _analyze_residual_audio=residual,
                           prep_denoise_batch=lambda files,masks: None)
                def bandit(files):
                    for name in files:
                        # Mock separation only; actual finishing, FFmpeg and contract below.
                        shutil.copy2(Path(env['FOLDER_MERGED']) / name,
                                     Path(env['FOLDER_AI_STEMS']) / (Path(name).stem + '_Bandit.wav'))
                env['process_bandit_batch'] = bandit
                workflow = ''.join(notebook('test_V4')['cells'][7]['source'])
                if failure:
                    with self.assertRaisesRegex(RuntimeError, 'detector failed'):
                        exec(compile(workflow, '<v4workflow>', 'exec'), env)
                else:
                    exec(compile(workflow, '<v4workflow>', 'exec'), env)
                manifest = json.loads((Path(env['FOLDER_OUT']) / contract.DELIVERY_MANIFEST).read_text())
                self.assertEqual(manifest['backend'], 'Bandit_V4')
                self.assertEqual(manifest['status'], 'failed' if failure else 'complete')
                self.assertEqual(env['WORKFLOW_COMPLETE'], not failure)
                self.assertEqual(observations, [Path(env['FOLDER_MERGED']) / raw.name] * 2)
                self.assertEqual((old / 'retained.txt').read_text(), 'previous run')
                if not failure:
                    contract.validate_delivery_manifest(manifest)
                    entry = manifest['outputs'][0]
                    output = Path(env['FOLDER_OUT']) / manifest['run_folder'] / entry['name']
                    contract.verify_delivery_file(output, entry)
                    self.assertEqual((entry['frames'], entry['time_reference']), (90001, 1823255434))
                    self.assertNotEqual(entry['umid'], contract.read_wave_umid(raw))
                    np.testing.assert_allclose(sf.read(output)[0], .0005, atol=1e-8)
                else:
                    with self.assertRaises(ValueError):
                        contract.validate_delivery_manifest(manifest)


if __name__ == '__main__':
    unittest.main()
