"""Régressions des masques respiratoires et de la passe humaine résiduelle."""
import unittest
from types import SimpleNamespace

import numpy as np
from scipy import signal

from tests.test_backend_v330 import scope


class BackendV340Tests(unittest.TestCase):
    def setUp(self):
        self.env = scope()
        self.env['signal'] = signal
        self.env['GAIN_ANALYSE_RESIDUS_DB'] = 0
        self.env['GAIN_BODYTALK_DB'] = 2

    def test_residual_targets_explicit_oral_classes(self):
        for index in (49, 50, 51):
            scores = np.zeros((20,521),np.float32)
            scores[10,index] = .4
            mask = self.env['_residual_frames'](scores)['residual']
            self.assertGreater(mask[10], .9)
            self.assertEqual(mask[0], 0)

    def test_disabled_profile_and_residual_pass(self):
        rng = np.random.default_rng(340)
        scores = rng.uniform(0, .3, (160, 521)).astype(np.float32)
        legacy = self.env['_attack_release_frames'](
            self.env['_soft_threshold'](self.env['_max_class_score'](scores, [12, 23, 36]), .10, .30), .08, .60
        )
        np.testing.assert_array_equal(self.env['_respiratory_frames'](scores, False), legacy)
        frames = {'human': [1], 'bodytalk': [1]}
        audio = np.full((6400,2), .1, np.float32)
        self.env['DUCK_DEPTH_RESIDUS'] = 0
        self.env['yamnet_model'] = lambda x: self.fail('Seconde analyse désactivée mais appelée')
        b = self.env['_apply_yamnet_masks_inplace'](audio.copy(), 100, {'frames': frames}, 'test.wav')
        np.testing.assert_allclose(b, .025, atol=1e-7)

    def test_sniff_and_related_classes_have_priority(self):
        for k in (12, 23, 36, 39, 40, 41, 45):
            scores = np.zeros((50, 521), np.float32)
            scores[20, k] = .139
            m = self.env['_respiratory_frames'](scores, True)
            self.assertGreater(m[20], .8)
            self.assertEqual(m[0], 0)
            self.assertLess(m[-1], 1e-6)

    def test_residual_ignores_generic_pfx_and_music(self):
        for k in (48, 132, 428, 461, 470, 473, 481, 485):
            scores = np.zeros((5, 521), np.float32)
            scores[:, k] = 1
            self.assertEqual(self.env['_residual_frames'](scores)['residual'].max(), 0)

    def test_residual_attenuation_and_bodytalk_veto(self):
        audio = np.full((500, 2), .1, np.float32)
        original = {'frames': {'bodytalk': [1], 'pfx': [1]}}
        residual = {'frames': {'residual': [1], 'human_guard': [1]}}
        out = self.env['_apply_residual_and_bodytalk_inplace'](audio, 100, original, residual, 2, 'test.wav')
        np.testing.assert_allclose(out, .01, atol=1e-7)
        self.assertEqual(out.shape, (500, 2))

    def test_second_analysis_receives_attenuated_audio_before_boost(self):
        received = []
        scores = np.zeros((2, 521), np.float32)
        scores[:, 36] = 1
        def model(wave):
            received.append(wave.copy())
            return SimpleNamespace(numpy=lambda: scores), None, None
        self.env['yamnet_model'] = model
        audio = np.full((16000, 1), .1, np.float32)
        frames = {'human': [1], 'bodytalk': [1]}
        out = self.env['_apply_yamnet_masks_inplace'](audio, 16000, {'frames': frames}, 'test.wav')
        self.assertEqual(len(received), 1)
        np.testing.assert_allclose(received[0], .025, atol=1e-7)
        np.testing.assert_allclose(out, .0025, atol=3e-6)

    def test_no_residual_allows_bodytalk_once_with_headroom(self):
        scores = np.zeros((2, 521), np.float32)
        self.env['yamnet_model'] = lambda w: (SimpleNamespace(numpy=lambda: scores), None, None)
        for peak in (.1, .9, 1.1):
            audio = np.full((16000, 1), peak, np.float32)
            out = self.env['_apply_yamnet_masks_inplace'](audio, 16000, {'frames': {'bodytalk': [1]}}, 'test.wav')
            expected = min(peak * 10**(.1), .98) if peak < .98 else peak
            np.testing.assert_allclose(out, expected, atol=1e-6)

    def test_empty_silence_and_inference_failure(self):
        def broken(w):
            raise RuntimeError('model failure')
        self.env['yamnet_model'] = broken
        for shape in ((0, 1), (16000, 1)):
            data = np.zeros(shape, np.float32)
            out = self.env['_apply_yamnet_masks_inplace'](data, 16000, {'frames': {}}, 'test.wav')
            np.testing.assert_array_equal(out, data)
        with self.assertRaisesRegex(RuntimeError, 'model failure'):
            self.env['_apply_yamnet_masks_inplace'](np.ones((16000, 1), np.float32), 16000, {'frames': {}}, 'test.wav')


if __name__ == '__main__':
    unittest.main()
