"""Tests DSP hors GPU des fonctions réelles des notebooks, sans importer TensorFlow."""
import ast
import json
import os
from pathlib import Path
from types import SimpleNamespace
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def notebook(version):
    return json.loads((ROOT / f'Colab_Backend_PFX_V{version}.ipynb').read_text(encoding='utf-8'))


def scope(version):
    nb = notebook(version)
    env = {'np': np, 'os': os, 'print': lambda *args, **kwargs: None}
    # N'exécuter que fonctions et constantes pures : aucun téléchargement / modèle / audio.
    for index in (1, 5, 6):
        tree = ast.parse(''.join(nb['cells'][index]['source']))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                exec(compile(ast.Module(body=[node], type_ignores=[]), '<functions>', 'exec'), env)
            elif isinstance(node, ast.Assign):
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        env[target.id] = value
    # Exécuter les ensembles et indices exacts, ainsi que leurs assertions d'audit.
    tree = ast.parse(''.join(nb['cells'][5]['source']))
    start = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'HUMAN_CLASS_SET' for t in n.targets))
    stop = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'YAMNET_FRAME_HOP_S' for t in n.targets))
    exec(compile(ast.Module(body=tree.body[start:stop], type_ignores=[]), '<taxonomy>', 'exec'), env)
    return env


class BackendV330Tests(unittest.TestCase):
    def setUp(self):
        self.env = scope('3_3_0')

    def apply(self, frames, audio=None, **settings):
        self.env.update(settings)
        if audio is None:
            audio = np.full((200, 1), 0.1, dtype=np.float32)
        data = None if frames is None else {'frames': frames}
        return self.env['_apply_yamnet_masks_inplace'](audio.copy(), 100, data, 'test.wav')

    def test_notebook_compile_and_unchanged_pipeline(self):
        old, new = notebook('3_2_0'), notebook('3_3_0')
        for i in (2, 3, 4, 7, 8):
            self.assertEqual(old['cells'][i], new['cells'][i])
        for i, cell in enumerate(new['cells']):
            if cell['cell_type'] == 'code':
                source = ''.join(line for line in cell['source'] if not line.lstrip().startswith(('!', '%')))
                compile(source, f'cell_{i}', 'exec')
        # Alignement, séparation, mono, redécoupage, timecode restent identiques.
        def funcs(nb):
            return {n.name: ast.dump(n) for n in ast.parse(''.join(nb['cells'][6]['source'])).body
                    if isinstance(n, ast.FunctionDef) and n.name != '_apply_yamnet_masks_inplace'}
        self.assertEqual(funcs(old), funcs(new))

    def test_disabled_exact_v320(self):
        old = scope('3_2_0')
        rng = np.random.default_rng(330)
        frames = {k: rng.random(180).astype(np.float32) for k in
                  ('human', 'soft_human', 'pfx', 'ambience', 'outside_pfx', 'mouth', 'bodytalk', 'human_guard')}
        audio = rng.normal(0, 0.1, (6501, 2)).astype(np.float32)
        expected = old['_apply_yamnet_masks_inplace'](audio.copy(), 100, {'frames': frames}, 'test.wav')
        actual = self.apply(frames, audio, DUCK_DEPTH_BOUCHE=0, GAIN_BODYTALK_DB=0)
        np.testing.assert_array_equal(actual, expected)

    def test_mouth_priority_over_bodytalk_and_pfx(self):
        out = self.apply({'mouth': [1], 'bodytalk': [1], 'pfx': [1]})
        np.testing.assert_allclose(out, 0.005, atol=1e-7)

    def test_bodytalk_two_db(self):
        out = self.apply({'bodytalk': [1]})
        np.testing.assert_allclose(out, 0.1 * 10 ** (2 / 20), rtol=1e-6)

    def test_human_and_ambience_veto_independent_of_sliders(self):
        for mask in ('human_guard', 'human', 'soft_human', 'mouth', 'ambience', 'outside_pfx'):
            with self.subTest(mask=mask):
                out = self.apply({'bodytalk': [1], mask: [1]}, DUCK_DEPTH_HUMAIN=0,
                                 DUCK_DEPTH_SOUFFLES=0, DUCK_DEPTH_BOUCHE=0,
                                 DUCK_DEPTH_AMBIANCE=0, DUCK_DEPTH_HORS_PFX=0)
                np.testing.assert_array_equal(out, np.full((200, 1), .1, np.float32))

    def test_no_extra_saturation_or_normalization(self):
        for peak in (0.9, 0.99, 1.1):
            audio = np.full((200, 2), peak, np.float32)
            out = self.apply({'bodytalk': [1]}, audio, GAIN_BODYTALK_DB=4)
            if peak < .98:
                self.assertLessEqual(float(np.max(out)), .980001)
            else:
                np.testing.assert_array_equal(out, audio)
            self.assertEqual(out.shape, audio.shape)

    def test_empty_missing_and_silence(self):
        for frames in (None, {}, {'bodytalk': []}):
            out = self.apply(frames)
            np.testing.assert_array_equal(out, np.full((200, 1), .1, np.float32))
        for audio in (np.zeros((0, 1), np.float32), np.zeros((200, 1), np.float32)):
            np.testing.assert_array_equal(self.apply({'bodytalk': [1]}, audio), audio)
        result = self.env['_mouth_bodytalk_frames'](np.zeros((0, 521), np.float32))
        self.assertTrue(all(v.size == 0 for v in result.values()))

    def test_ambiguous_click_requires_nearby_human(self):
        build = self.env['_mouth_bodytalk_frames']
        for index in self.env['MOUTH_TRANSIENT_CLASS_IDX']:
            scores = np.zeros((100, 521), np.float32)
            scores[50, index] = 1
            self.assertEqual(float(build(scores)['mouth'].max()), 0)
            scores[51, 0] = .3  # Voix une frame après : amorce de phrase.
            frames = build(scores)
            self.assertGreater(frames['mouth'][49], .99)
            self.assertEqual(float(frames['mouth'][:48].max()), 0)
            self.assertLess(float(frames['mouth'][70:].max()), 1e-6)
            scores[51, 0] = 0
            scores[60, 0] = 1  # Voix distante : ne valide pas ce clic.
            self.assertEqual(float(build(scores)['mouth'].max()), 0)

    def test_direct_mouth_and_bodytalk_classes(self):
        build = self.env['_mouth_bodytalk_frames']
        for index in self.env['MOUTH_CLASS_IDX']:
            scores = np.zeros((3, 521), np.float32)
            scores[1, index] = .25
            self.assertGreater(build(scores)['mouth'].max(), .99)
        for index in self.env['BODYTALK_CLASS_IDX']:
            scores = np.zeros((3, 521), np.float32)
            scores[1, index] = .4
            frames = build(scores)
            self.assertGreater(frames['bodytalk'].max(), .9)
            self.assertEqual(frames['mouth'].max(), 0)
        scores = np.zeros((3, 521), np.float32)
        scores[:, 48] = 1  # Footsteps seuls ne déclenchent pas de gain.
        self.assertEqual(build(scores)['bodytalk'].max(), 0)

    def test_analysis_wires_new_masks_into_cache(self):
        scores = np.zeros((10, 521), np.float32)
        scores[3, 49] = .8
        scores[7, 481] = .8
        self.env['sf'] = SimpleNamespace(read=lambda *a, **k: (np.zeros((48000, 1)), 48000))
        self.env['signal'] = SimpleNamespace(resample_poly=lambda a, **k: a[::3])
        self.env['yamnet_model'] = lambda a: (SimpleNamespace(numpy=lambda: scores), None, None)
        self.env['class_names'] = [str(i) for i in range(521)]
        result = self.env['analyze_yamnet']('synthetic.wav')
        self.assertEqual(result['source_length'], 48000)
        for name in ('mouth', 'bodytalk', 'human_guard'):
            self.assertEqual(len(result['frames'][name]), 10)
            self.assertGreater(result['frames'][name].max(), .9)
        for empty in (True, False):
            if empty:
                self.env['sf'] = SimpleNamespace(read=lambda *a, **k: (np.zeros((0, 1)), 48000))
            else:
                self.env['sf'] = SimpleNamespace(read=lambda *a, **k: (np.zeros((3, 1)), 48000))
                self.env['yamnet_model'] = lambda a: (SimpleNamespace(numpy=lambda: np.zeros((0, 521))), None, None)
            result = self.env['analyze_yamnet']('synthetic.wav')
            self.assertTrue(all(result['frames'][key].size == 0 for key in ('mouth', 'bodytalk', 'human_guard')))

    def test_block_interpolation_continuity(self):
        data = {'frames': {'bodytalk': np.array([0, 1, 0, .5], np.float32)}}
        f = self.env['yamnet_mask_block']
        whole = f(data, 'bodytalk', 0, 2000, 100)
        chunks = np.concatenate([f(data, 'bodytalk', 0, 99, 100), f(data, 'bodytalk', 99, 2000, 100)])
        np.testing.assert_array_equal(whole, chunks)


if __name__ == '__main__':
    unittest.main()
