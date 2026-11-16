"""Targeted scream routing and BWF delivery; synthetic scores/audio, no cloud calls."""
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


class BanditV41Tests(unittest.TestCase):
    def environment(self):
        env = scope('bandit_4_1')
        env.update(sf=sf, validate_bandit_audio=lambda audio, sr: audio)
        return env

    def test_notebook_compiles_and_embedded_sources_match(self):
        old, new = notebook('test_V4'), notebook('bandit_4_1')
        for i in (2, 4, 8):
            self.assertEqual(old['cells'][i]['source'], new['cells'][i]['source'])
        before, after = scope('test_V4'), scope('bandit_4_1')
        for name in before:
            if name.startswith(('DUCK_DEPTH_', 'GAIN_', 'PROFIL_')) or name in (
                    'NIVEAU_DENOISE_POURCENTAGE', 'DENOISE_ADAPTATIF', 'PROTECTION_PFX'):
                self.assertEqual(before[name], after[name], name)
        self.assertEqual(after['DUCK_DEPTH_CRIS'], 95)
        self.assertEqual(after['SCREAM_CLASS_IDX'], [6,7,8,9,10,11])
        for index, cell in enumerate(new['cells']):
            if cell['cell_type'] == 'code':
                compile(''.join(cell['source']), f'cell{index}', 'exec')
                self.assertEqual(cell['outputs'], [])
        for path, index in [('backend_test/v41_yamnet.py',5),
                            ('backend_test/v41_processing.py',6), ('delivery_contract.py',6)]:
            self.assertIn((ROOT/path).read_text(encoding='utf-8').strip(), ''.join(new['cells'][index]['source']))
        self.assertEqual((ROOT/'backend_test/v41_workflow.py').read_text(encoding='utf-8').strip(),
                         ''.join(new['cells'][7]['source']).strip())
        self.assertEqual({i:after['YAMNET_SENTINEL_NAMES'][i] for i in after['SCREAM_CLASS_IDX']},
                         {6:'Shout',7:'Bellow',8:'Whoop',9:'Yell',10:'Children shouting',11:'Screaming'})

    def test_each_scream_class_activates_raw_and_residual_masks(self):
        env, old = self.environment(), scope('test_V4')
        for index in env['SCREAM_CLASS_IDX']:
            with self.subTest(index=index):
                scores=np.zeros((8,521),np.float32)
                scores[:,index]=1
                self.assertGreater(env['_screaming_frames'](scores).max(), .99)
                self.assertGreater(env['_residual_frames'](scores)['residual'].max(), .99)
                self.assertEqual(old['_residual_frames'](scores)['residual'].max(), 0)

    def test_non_scream_residual_behavior_is_unchanged(self):
        env, old = self.environment(), scope('test_V4')
        scores=np.random.default_rng(41).random((20,521),dtype=np.float32)*.4
        scores[:,env['SCREAM_CLASS_IDX']]=0
        for key,value in old['_residual_frames'](scores).items():
            np.testing.assert_array_equal(env['_residual_frames'](scores)[key], value)
        for index in (48,353,413,461,470,473,481,485):
            scores=np.zeros((8,521),np.float32)
            scores[:,index]=1
            self.assertEqual(env['_screaming_frames'](scores).max(),0)
            self.assertEqual(env['_residual_frames'](scores)['residual'].max(),0)

    def test_scream_priority_bypasses_pfx_and_cumulates_without_bodytalk_boost(self):
        env=self.environment()
        audio=np.full((1000,1),.1,np.float32)
        masks={'frames':{'screaming':[1], 'pfx':[1], 'bodytalk':[1]}}
        first=env['apply_v4_raw_masks'](audio,100,masks)
        np.testing.assert_allclose(first,.005,atol=1e-7)
        out=env['apply_v4_residual_and_bodytalk'](first,100,masks,{'frames':{'residual':[1]}})
        np.testing.assert_allclose(out,.0005,atol=1e-8)
        self.assertEqual(out.shape,audio.shape)
        np.testing.assert_array_equal(audio,np.full((1000,1),.1,np.float32))

    def test_zero_scream_control_disables_both_additions_but_not_general_human_removal(self):
        env=self.environment()
        env['DUCK_DEPTH_CRIS']=0
        scores=np.zeros((8,521),np.float32)
        scores[:,11]=1
        self.assertEqual(env['_screaming_frames'](scores).max(),0)
        self.assertEqual(env['_residual_frames'](scores)['residual'].max(),0)
        out=env['apply_v4_raw_masks'](np.full((1000,1),.1,np.float32),100,
                                      {'frames':{'human':[1],'screaming':[0]}})
        np.testing.assert_allclose(out,.025,atol=1e-7)

    def test_scream_mask_is_temporal_and_does_not_duck_whole_scene(self):
        env=self.environment()
        scores=np.zeros((24,521),np.float32)
        scores[5,6]=1
        masks={'frames':{'screaming':env['_screaming_frames'](scores)}}
        audio=np.full((1200,1),.1,np.float32)
        out=env['apply_v4_raw_masks'](audio,100,masks)
        self.assertAlmostEqual(float(out[0,0]),.1,places=6)
        self.assertLess(float(out[288,0]),.01)
        self.assertAlmostEqual(float(out[-1,0]),.1,places=5)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
    def test_new_workflow_cumulative_scream_delivery_preserves_geometry_and_umid(self):
        env=self.environment()
        env.update(vars(contract))
        env.update(shutil=shutil,subprocess=subprocess,RUN_ID='bandit41synthetic',
                   REMPLACER_RUN_INTERROMPU=False,BANDIT_COMMIT='synthetic',BANDIT_CHECKPOINT_MD5='synthetic')
        with tempfile.TemporaryDirectory() as directory:
            for key in ('FOLDER_IN','FOLDER_OUT','FOLDER_MERGED','FOLDER_DENOISED','FOLDER_AI_STEMS','FOLDER_TC_READY'):
                path=Path(directory)/key
                path.mkdir()
                env[key]=str(path)
            raw=Path(env['FOLDER_IN'])/'scene_BOOM_01.wav'
            raw.write_bytes(wave_bytes(90001,1823255434,level=.1))
            def analyze(path):
                return {'frames':{'screaming':[1]}}
            def residual(audio,sr):
                np.testing.assert_allclose(audio,.005,atol=1e-7)
                scores=np.zeros((1,521),np.float32)
                scores[:,11]=1
                return {'frames':env['_residual_frames'](scores)}
            def bandit(files):
                for name in files:
                    shutil.copy2(Path(env['FOLDER_MERGED'])/name,
                                 Path(env['FOLDER_AI_STEMS'])/(Path(name).stem+'_Bandit.wav'))
            env.update(preflight_models=lambda:None,analyze_yamnet=analyze,
                       prep_denoise_batch=lambda *a:None,process_bandit_batch=bandit,
                       _analyze_residual_audio=residual)
            exec(compile(''.join(notebook('bandit_4_1')['cells'][7]['source']),'<workflow41>','exec'),env)
            manifest=json.loads((Path(env['FOLDER_OUT'])/contract.DELIVERY_MANIFEST).read_text())
            self.assertEqual(manifest['backend'],'Bandit_V4_1')
            self.assertEqual(manifest['settings']['DUCK_DEPTH_CRIS'],95)
            contract.validate_delivery_manifest(manifest)
            entry=manifest['outputs'][0]
            output=Path(env['FOLDER_OUT'])/manifest['run_folder']/entry['name']
            contract.verify_delivery_file(output,entry)
            self.assertEqual((entry['frames'],entry['time_reference']),(90001,1823255434))
            self.assertNotEqual(entry['umid'],contract.read_wave_umid(raw))
            np.testing.assert_allclose(sf.read(output)[0],.0005,atol=4e-7)


if __name__=='__main__':
    unittest.main()
