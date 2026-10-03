"""Gain réservé au classificateur et fusion des observations résiduelles."""
import unittest
from types import SimpleNamespace
import numpy as np
from scipy import signal
from tests.test_backend_v330 import scope


class BackendV350Tests(unittest.TestCase):
    def setUp(self):
        self.env = scope()
        self.env['signal'] = signal

    def test_current_default_bodytalk_gain_applied_once(self):
        self.env['yamnet_model'] = lambda w: (SimpleNamespace(numpy=lambda: np.zeros((1,521),np.float32)),None,None)
        self.env['GAIN_ANALYSE_RESIDUS_DB'] = 0
        audio = np.full((15600,1),.1,np.float32)
        out = self.env['_apply_yamnet_masks_inplace'](audio,16000,{'frames':{'bodytalk':[1]}},'test')
        np.testing.assert_allclose(out, .1 * 10**(3.5/20), atol=1e-7)

    def test_zero_gain_uses_only_native_scores(self):
        scores = np.random.default_rng(350).uniform(0,.4,(5,521)).astype(np.float32)
        calls = []
        def model(w):
            calls.append(w.copy())
            return SimpleNamespace(numpy=lambda: scores), None, None
        self.env['yamnet_model'] = model
        self.env['GAIN_ANALYSE_RESIDUS_DB'] = 0
        audio = np.full((48000,1), .01, np.float32)
        expected = self.env['_residual_frames'](scores)
        b = self.env['_analyze_residual_audio'](audio, 48000)
        self.assertEqual(len(calls), 1)
        for key in expected:
            np.testing.assert_array_equal(expected[key], b['frames'][key])
        np.testing.assert_array_equal(audio, np.full_like(audio,.01))

    def test_gain_fuses_maximum_without_mutating_source_or_scores(self):
        base = np.zeros((2,521), np.float32)
        base[:,23] = .6
        extra = np.zeros((1,521), np.float32)
        extra[:,36] = .8
        calls = []
        def model(w):
            calls.append(w.copy())
            return SimpleNamespace(numpy=lambda: extra), None, None
        self.env['yamnet_model'] = model
        wave = np.full(23000,.01,np.float32)
        result = self.env['_residual_scores_with_gain'](wave,base,18)
        self.assertEqual(len(calls),2)
        for w in calls:
            self.assertEqual(len(w),15600)
            self.assertAlmostEqual(float(w[0]),.01*10**(.9),places=6)
        np.testing.assert_array_equal(result[:,23],base[:,23])
        np.testing.assert_allclose(result[:,36],.8)
        self.assertEqual(float(base[:,36].max()),0)
        np.testing.assert_array_equal(wave,np.full_like(wave,.01))

    def test_peak_limit_silence_and_tail(self):
        calls=[]
        def model(w):
            calls.append(w.copy())
            return SimpleNamespace(numpy=lambda: np.zeros((1,521),np.float32)),None,None
        self.env['yamnet_model']=model
        fn=self.env['_residual_scores_with_gain']
        base=np.zeros((1,521),np.float32)
        fn(np.full(1000,.5,np.float32),base,18)
        self.assertLessEqual(float(np.max(calls[0])),.900001)
        self.assertTrue(np.all(calls[0][1000:]==0))
        calls.clear()
        for wave in (np.zeros(15600,np.float32),np.full(15600,.95,np.float32)):
            np.testing.assert_array_equal(fn(wave,base,18),base)
        self.assertEqual(len(calls),0)

    def test_frames_remain_at_their_time_positions(self):
        # Une seule activité au dernier sample de la deuxième fenêtre.
        wave=np.zeros(23280,np.float32);wave[-1]=.01
        extra=np.zeros((1,521),np.float32);extra[0,36]=1
        self.env['yamnet_model']=lambda w:(SimpleNamespace(numpy=lambda:extra),None,None)
        result=self.env['_residual_scores_with_gain'](wave,np.zeros((2,521),np.float32),18)
        self.assertEqual(result[0,36],0)
        self.assertEqual(result[1,36],1)

    def test_disabled_residual_skips_all_inference(self):
        self.env['DUCK_DEPTH_RESIDUS'] = 0
        self.env['yamnet_model'] = lambda w: self.fail('Analyse désactivée mais appelée')
        data = {'frames': {'human': [1], 'bodytalk': [1]}}
        audio = np.full((16000,1), .01, np.float32)
        b = self.env['_apply_yamnet_masks_inplace'](audio.copy(),16000,data,'test')
        np.testing.assert_allclose(b,.0025,atol=1e-8)

    def test_detector_gain_does_not_amplify_output(self):
        calls = []
        def model(w):
            calls.append(w.copy())
            return SimpleNamespace(numpy=lambda: np.zeros((1,521),np.float32)),None,None
        self.env['yamnet_model'] = model
        self.env['GAIN_BODYTALK_DB'] = 0
        audio = np.full((15600,1),.01,np.float32)
        out = self.env['_apply_yamnet_masks_inplace'](audio.copy(),16000,{'frames':{}},'test')
        self.assertEqual(len(calls),2)
        self.assertGreater(float(calls[1].max()),float(calls[0].max()))
        np.testing.assert_array_equal(out,audio)

    def test_unexpected_output_or_invalid_gain_fails(self):
        self.env['yamnet_model']=lambda w:(SimpleNamespace(numpy=lambda:np.zeros((2,521))),None,None)
        with self.assertRaises(RuntimeError):
            self.env['_residual_scores_with_gain'](np.full(15600,.01),np.zeros((1,521)),18)
        for gain in (-1,25,float('nan')):
            with self.assertRaises(ValueError):
                self.env['_residual_scores_with_gain'](np.zeros(1),np.zeros((1,521)),gain)


if __name__ == '__main__':
    unittest.main()
