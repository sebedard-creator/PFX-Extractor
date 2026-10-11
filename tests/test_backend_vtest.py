"""Offline contract tests; no confidential audio or model downloads."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

from backend_test.bandit_runtime import (
    BANDIT_RATE, bandit_model_state, bandit_overlap_add,
    validate_bandit_audio, _file_digest, _verified_download,
)

ROOT = Path(__file__).resolve().parents[1]


def read_notebook(name):
    return json.loads((ROOT / name).read_text(encoding='utf-8'))


class BanditRuntimeTests(unittest.TestCase):
    def test_identity_overlap_add_edges_and_short_clips(self):
        rng = np.random.default_rng(42)
        for n in (1, 2, 5, 19, 20, 21, 40, 101):
            for hop in (1, 5, 7, 10):
                with self.subTest(n=n, hop=hop):
                    audio = rng.normal(0, .1, (n, 1)).astype(np.float32)
                    result = bandit_overlap_add(audio, lambda x: x, 20, hop)
                    self.assertEqual(result.shape, audio.shape)
                    np.testing.assert_allclose(result, audio, atol=5e-8)

    def test_impulses_have_no_shift_or_edge_fade(self):
        audio = np.zeros((101, 1), np.float32)
        audio[[0, 50, 100], 0] = [0.3, -0.5, 0.7]
        result = bandit_overlap_add(audio, lambda x: x * .25, 20, 5)
        np.testing.assert_allclose(result, audio * .25, atol=1e-7)

    def test_source_not_mutated_and_no_normalization(self):
        audio = np.full((101, 1), .001, np.float32)
        original = audio.copy()
        result = bandit_overlap_add(audio, lambda x: x, 20, 5)
        np.testing.assert_array_equal(audio, original)
        np.testing.assert_allclose(result, .001, atol=1e-9)

    def test_invalid_prediction_fails_not_bypass(self):
        audio = np.ones((31, 1), np.float32)
        for pred in (lambda x: np.zeros(19), lambda x: x * np.nan):
            with self.assertRaises(RuntimeError):
                bandit_overlap_add(audio, pred, 20, 5)
        with self.assertRaisesRegex(ValueError, 'model failed'):
            def fail(x):
                raise ValueError('model failed')
            bandit_overlap_add(audio, fail, 20, 5)

    def test_reject_invalid_audio(self):
        for x, sr in [(np.zeros((3, 2)), 48000), (np.zeros((0, 1)), 48000),
                      (np.zeros((3, 1)), 44100), (np.full((3, 1), np.nan), 48000),
                      (np.full((3, 1), np.inf), 48000)]:
            with self.assertRaises(ValueError):
                validate_bandit_audio(x, sr)

    def test_checkpoint_prefix_and_excluded_training_state(self):
        self.assertEqual(bandit_model_state({'state_dict': {
            'model.mask_estim.sfx.weight': 1, 'loss_handler.foo': 2}}),
            {'mask_estim.sfx.weight': 1})
        for value in ({}, {'state_dict': {}}, {'state_dict': {'unrelated': 1}}):
            with self.assertRaises(RuntimeError):
                bandit_model_state(value)

    def test_verified_cache_does_not_access_network(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'asset'
            path.write_bytes(b'asset')
            digest = hashlib.md5(b'asset').hexdigest()
            with patch('requests.get', side_effect=AssertionError('Network forbidden')):
                self.assertEqual(_verified_download('https://example.invalid', path,
                    digest, 'md5', 5), path)

    def test_git_blob_checksum(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'asset'
            path.write_bytes(b'abc')
            self.assertEqual(_file_digest(path, 'sha1', True),
                             hashlib.sha1(b'blob 3\0abc').hexdigest())


class VtestNotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb = read_notebook('Colab_Backend_PFX_Vtest.ipynb')
        cls.reference = read_notebook('Colab_Backend_PFX_V3_5_1.ipynb')

    def test_original_unchanged(self):
        self.assertEqual(hashlib.sha256((ROOT / 'Colab_Backend_PFX_V3_5_1.ipynb').read_bytes()).hexdigest(),
                         'faf3695fbb4621acf2852037992f6888c436ca8e962a5cc4c6b655e419973a7a')

    def test_all_cells_compile_and_have_no_stale_output(self):
        for index, cell in enumerate(self.nb['cells']):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), f'cell{index}', 'exec')
                self.assertEqual(cell['outputs'], [])
                self.assertIsNone(cell['execution_count'])

    def test_embedded_runtime_is_identical(self):
        runtime = (ROOT / 'backend_test/bandit_runtime.py').read_text(encoding='utf-8').strip()
        self.assertIn(runtime, ''.join(self.nb['cells'][4]['source']))

    def test_yamnet_and_finishing_functions_identical(self):
        def functions(nb, index):
            return {n.name: ast.dump(n, include_attributes=False)
                    for n in ast.parse(''.join(nb['cells'][index]['source'])).body
                    if isinstance(n, ast.FunctionDef)}
        new_yamnet, old_yamnet = functions(self.nb, 5), functions(self.reference, 5)
        for name in old_yamnet.keys() - {'_residual_frames', 'analyze_yamnet'}:
            self.assertEqual(new_yamnet[name], old_yamnet[name], name)
        test, reference = functions(self.nb, 6), functions(self.reference, 6)
        for name in ('initial_mic_alignment', 'snowball_merge', 'prep_denoise_batch',
                     'iter_split_merged_audio'):
            self.assertEqual(test[name], reference[name], name)

    def test_same_relevant_control_defaults(self):
        def constants(nb):
            values = {}
            for n in ast.parse(''.join(nb['cells'][1]['source'])).body:
                if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name):
                    values[n.targets[0].id] = ast.literal_eval(n.value)
            return values
        old, new = constants(self.reference), constants(self.nb)
        self.assertEqual(new.pop('DUCK_DEPTH_PLEURS'), 95)
        self.assertEqual(new.pop('GAIN_BODYTALK_DB'), 4.0)
        self.assertEqual(old.pop('GAIN_BODYTALK_DB'), 3.5)
        self.assertEqual(new, {k: v for k, v in old.items()
                               if k not in ('RATIO_ROFORMER', 'AI_OVERLAP')})

    def test_only_bandit_called_and_preflight_before_audio(self):
        code = ''.join(self.nb['cells'][7]['source'])
        self.assertNotIn('process_batch(', code)
        self.assertNotIn('auto_align_and_mix(', code)
        self.assertIn('process_bandit_batch(merged_files_list)', code)
        self.assertLess(code.index('preflight_models()'), code.index('initial_mic_alignment('))
        self.assertIn('raise RuntimeError', code)

    def test_network_calls_only_downloads_no_upload_or_remote_logger(self):
        runtime = ast.parse((ROOT / 'backend_test/bandit_runtime.py').read_text(encoding='utf-8'))
        requests_calls = [n for n in ast.walk(runtime) if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
                          and n.func.value.id == 'requests']
        self.assertEqual([n.func.attr for n in requests_calls], ['get'])
        all_code = '\n'.join(''.join(c['source']) for c in self.nb['cells'] if c['cell_type'] == 'code')
        for forbidden in ('requests.post', 'api.mvsep', 'api_key', 'wandb.init', 'pl.Trainer('):
            self.assertNotIn(forbidden, all_code)

    def test_standard_output_and_failure_no_disconnect(self):
        code = ''.join(self.nb['cells'][3]['source'])
        self.assertIn('FOLDER_OUT = os.path.join(DRIVE_BASE, "2_Environnements_IA")', code)
        self.assertNotIn('3_Comparatifs_Vtest', code)
        workflow = ''.join(self.nb['cells'][7]['source'])
        self.assertNotIn('zipfile', workflow)
        self.assertNotIn('if os.listdir(FOLDER_OUT)', workflow)
        self.assertIn("if globals().get('WORKFLOW_COMPLETE', False):", ''.join(self.nb['cells'][8]['source']))

    def test_crying_classes_trigger_raw_and_residual_masks(self):
        from tests.test_backend_v330 import scope
        env = scope('test')
        for index in (19, 20, 21, 22):
            scores = np.zeros((9, 521), np.float32)
            scores[4, index] = .4
            self.assertGreater(env['_crying_frames'](scores)[4], .99)
            self.assertGreater(env['_residual_frames'](scores)['residual'][4], .99)
        for index in (13, 48, 354, 372, 470, 473, 481):
            scores = np.zeros((9, 521), np.float32)
            scores[4, index] = 1
            np.testing.assert_array_equal(env['_crying_frames'](scores), 0)

    def test_crying_slider_zero_restores_old_residual_mask(self):
        from tests.test_backend_v330 import scope
        new, old = scope('test'), scope()
        new['DUCK_DEPTH_PLEURS'] = 0
        scores = np.random.default_rng(5).uniform(0, .15, (21, 521)).astype(np.float32)
        np.testing.assert_array_equal(new['_crying_frames'](scores), 0)
        for key, expected in old['_residual_frames'](scores).items():
            np.testing.assert_array_equal(new['_residual_frames'](scores)[key], expected)

    def test_crying_priority_blocks_bodytalk_and_pfx_restoration(self):
        from tests.test_backend_v330 import scope
        env = scope('test')
        env['DUCK_DEPTH_RESIDUS'] = 0
        audio = np.full((200, 1), .1, np.float32)
        masks = {'frames': {'crying': [1], 'pfx': [1], 'bodytalk': [1]}}
        result = env['_apply_yamnet_masks_inplace'](audio, 100, masks, 'test.wav')
        np.testing.assert_allclose(result, .005, atol=1e-7)

    def test_bodytalk_extra_half_db_once_with_or_without_residual_pass(self):
        from tests.test_backend_v330 import scope
        masks = {'frames': {'bodytalk': [1]}}
        for residual_depth in (0, 90):
            env = scope('test')
            env['DUCK_DEPTH_RESIDUS'] = residual_depth
            env['_analyze_residual_audio'] = lambda *a: {'frames': {}}
            outputs = []
            for gain in (3.5, 4.0):
                env['GAIN_BODYTALK_DB'] = gain
                result = env['_apply_yamnet_masks_inplace'](
                    np.full((200, 1), .1, np.float32), 100, masks, 'test.wav')
                self.assertEqual(result.shape, (200, 1))
                np.testing.assert_allclose(result, .1 * 10 ** (gain / 20), atol=1e-7)
                outputs.append(result)
            np.testing.assert_allclose(20 * np.log10(outputs[1] / outputs[0]), .5, atol=1e-5)

    def test_bodytalk_four_db_preserves_peak_headroom(self):
        from tests.test_backend_v330 import scope
        env = scope('test')
        env['_analyze_residual_audio'] = lambda *a: {'frames': {}}
        result = env['_apply_yamnet_masks_inplace'](
            np.full((200, 1), .9, np.float32), 100,
            {'frames': {'bodytalk': [1]}}, 'test.wav')
        np.testing.assert_allclose(result, .98, atol=1e-7)

    def test_three_snowball_clips_keep_exact_lengths_even_with_long_model_tail(self):
        from tests.test_backend_v330 import scope
        import re
        env = scope('test')
        env.update(sf=sf, re=re, MIN_SAFE_DURATION=5.0, MIN_EXPORT_SAMPLES=1024)
        with tempfile.TemporaryDirectory() as temp:
            env['FOLDER_ALIGNED'] = str(Path(temp) / 'aligned')
            env['FOLDER_MERGED'] = str(Path(temp) / 'merged')
            Path(env['FOLDER_ALIGNED']).mkdir()
            Path(env['FOLDER_MERGED']).mkdir()
            lengths = [30001, 45123, 60007]
            files = [f'A_Boom-Gain_{i}.wav' for i in range(3)]
            for index, (filename, n) in enumerate(zip(files, lengths)):
                sf.write(Path(env['FOLDER_ALIGNED']) / filename,
                         np.full(n, (index + 1) / 10), 48000, subtype='FLOAT')
            merged, groups = env['snowball_merge'](files)
            self.assertEqual(len(merged), 1)
            path = Path(env['FOLDER_MERGED']) / merged[0]
            audio, sr = sf.read(path, always_2d=True)
            # Even an unexpected 1/4-second tail must not enter the source cuts.
            sf.write(path, np.pad(audio, ((0, 12000), (0, 0))), sr, subtype='FLOAT')
            parts = list(env['iter_split_merged_audio'](path, groups[merged[0]]))
            self.assertEqual([len(p[1]) for p in parts], lengths)
            for index, (filename, audio, sr) in enumerate(parts):
                self.assertEqual(filename, files[index])
                np.testing.assert_allclose(audio, (index + 1) / 10, atol=1e-7)

    def test_two_runs_replace_wavs_in_frontend_folder_without_extra_files(self):
        """Execute delivery orchestration twice, mocking ML only (no network)."""
        from backend_test.bandit_runtime import BANDIT_COMMIT, BANDIT_CHECKPOINT_MD5
        code = ''.join(self.nb['cells'][7]['source'])
        filename = 'A01_Boom-Gain_1.wav'
        output_name = 'A01_Boom-Gain_1_PFX_Ready.wav'
        with tempfile.TemporaryDirectory() as temp:
            env = {'os': os, 'Path': Path, 'sf': sf, 'shutil': shutil,
                   'BANDIT_RATE': BANDIT_RATE, 'BANDIT_COMMIT': BANDIT_COMMIT,
                   'BANDIT_CHECKPOINT_MD5': BANDIT_CHECKPOINT_MD5,
                   '_file_digest': _file_digest, 'print': lambda *a, **k: None}
            for key in ('FOLDER_IN', 'FOLDER_OUT', 'FOLDER_MERGED', 'FOLDER_TC_READY',
                        'FOLDER_AI_STEMS', 'FOLDER_MODEL_CACHE'):
                path = Path(temp) / ('2_Environnements_IA' if key == 'FOLDER_OUT' else key)
                path.mkdir()
                env[key] = str(path)
            source = Path(env['FOLDER_IN']) / filename
            sf.write(source, np.full((4800, 1), .01), 48000, subtype='FLOAT')
            destination = Path(env['FOLDER_OUT']) / output_name
            sf.write(destination, np.full((4800, 1), .9), 48000, subtype='FLOAT')
            env.update({
                'natural_sort_key': str,
                'preflight_models': lambda: None,
                'initial_mic_alignment': lambda files: files,
                'snowball_merge': lambda files: (files, {f: {} for f in files}),
                'analyze_yamnet': lambda path: {},
                'prep_denoise_batch': lambda *args: None,
                'process_bandit_batch': lambda files: None,
                'finish_bandit': lambda stem, mix, masks: sf.write(
                    mix, np.full((4800, 1), env['test_level']), 48000, subtype='FLOAT'),
                'iter_split_merged_audio': lambda mix, info: [(filename,
                    sf.read(mix, always_2d=True)[0], 48000)],
                'inject_timecode': lambda original, processed, final: shutil.copy2(processed, final),
            })
            for run, level in (('first', .1), ('second', .2)):
                env.update(RUN_ID=run, test_level=level)
                with patch('importlib.metadata.version', return_value='test'):
                    exec(compile(code, '<Vtest workflow>', 'exec'), env)
                self.assertTrue(env['WORKFLOW_COMPLETE'])
                self.assertEqual(sorted(p.name for p in destination.parent.iterdir()), [output_name])
                np.testing.assert_allclose(sf.read(destination)[0], level, atol=1e-7)
                self.assertTrue((Path(env['FOLDER_MODEL_CACHE']) / 'manifests' / (run + '.json')).is_file())

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'ffmpeg needed')
    def test_real_bwf_mono_timecode_and_duration(self):
        tree = ast.parse(''.join(self.nb['cells'][6]['source']))
        scope = {'sf': sf, 'subprocess': subprocess}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in ('get_sample_rate', 'inject_timecode'):
                exec(compile(ast.Module(body=[node], type_ignores=[]), '<bwf>', 'exec'), scope)
        with tempfile.TemporaryDirectory() as temp:
            raw, source, processed, final = [str(Path(temp) / (name + '.wav'))
                                           for name in ('raw', 'source', 'processed', 'final')]
            sf.write(raw, np.zeros(48000, np.float32), 48000, subtype='FLOAT')
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', raw, '-write_bext', '1',
                            '-metadata', 'time_reference=172972800', source], check=True)
            sf.write(processed, np.full(48000, .01, np.float32), 48000, subtype='FLOAT')
            scope['inject_timecode'](source, processed, final)
            info = sf.info(final)
            self.assertEqual((info.samplerate, info.channels, info.frames), (48000, 1, 48000))
            tc = subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
                'format_tags=time_reference', '-of', 'default=nw=1:nk=1', final]).decode().strip()
            self.assertEqual(tc, '172972800')


if __name__ == '__main__':
    unittest.main()
