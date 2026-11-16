"""V4.2 dependency policy and standalone notebook; no installs or GPU needed."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import soundfile as sf

from backend_test.bandit_dependencies import check_bandit_torch_pair
import delivery_contract as contract
from tests.test_backend_v330 import notebook, scope
from tests.wav_fixtures import wave_bytes

ROOT = Path(__file__).resolve().parents[1]


class BanditV42Tests(unittest.TestCase):
    def test_user_pair_uses_documented_stable_abi(self):
        self.assertIn('ABI stable', check_bandit_torch_pair(
            '2.14.1+cu130','2.11.0+cu130','13.0',
            '2.14.1+cu130','2.11.0+cu130'))

    def test_matched_pairs_still_work(self):
        for version, cuda in (('2.6.0+cu124','12.4'),('2.9.1+cu128','12.8'),
                              ('2.11.0+cu130','13.0')):
            with self.subTest(version=version):
                self.assertEqual(check_bandit_torch_pair(version,version,cuda),
                                 'versions correspondantes')

    def test_invalid_or_unsupported_pairs_do_not_get_a_blanket_bypass(self):
        for torch_v, audio_v in (
                ('2.14.1','2.9.1'), ('2.10.0','2.11.0'),
                ('2.14.1','2.12.0'), ('2.14.1','2.11.0rc1'),
                ('2.14.1.dev1','2.11.0'), ('unknown','2.11.0')):
            with self.subTest(torch=torch_v,audio=audio_v), self.assertRaises(RuntimeError):
                check_bandit_torch_pair(torch_v,audio_v,'13.0')

    def test_explicit_build_mismatch_and_missing_cuda_are_rejected(self):
        for torch_v,audio_v,cuda in (
                ('2.14.1+cu130','2.11.0+cu128','13.0'),
                ('2.14.1+cu128','2.11.0+cu130','13.0'),
                ('2.14.1+cu130','2.11.0+cpu','13.0'),
                ('2.14.1+cu130','2.11.0+rocm6.4','13.0'),
                ('2.14.1','2.11.0',None)):
            with self.subTest(torch=torch_v,audio=audio_v), self.assertRaises(RuntimeError):
                check_bandit_torch_pair(torch_v,audio_v,cuda)

    def test_loaded_and_installed_versions_must_agree(self):
        for installed in (('2.13.0+cu130','2.11.0+cu130'),
                          ('2.14.1+cu130','2.10.0+cu130'),
                          ('2.14.1+cu128','2.11.0+cu130')):
            with self.subTest(installed=installed), self.assertRaisesRegex(RuntimeError,'chargé'):
                check_bandit_torch_pair('2.14.1+cu130','2.11.0+cu130','13.0',*installed)

    def test_notebook_is_new_copy_with_exact_same_audio_code_and_controls(self):
        old, new = notebook('bandit_4_1'), notebook('bandit_4_2')
        for index in (1,4,5,6,8):
            self.assertEqual(new['cells'][index],old['cells'][index],index)
        setup = ''.join(new['cells'][3]['source']).replace('pfx_bandit_v4_2','pfx_bandit_v4_1').replace('Bandit V4.2','Bandit V4.1')
        self.assertEqual(setup,''.join(old['cells'][3]['source']))
        workflow = ''.join(new['cells'][7]['source']).replace('Bandit_V4_2','Bandit_V4_1').replace(
            '2026-11-16-bandit-v4-2-torch-abi','2026-10-28-bandit-v4-1-sets').replace('Bandit V4.2 terminé','Bandit V4.1 terminé')
        self.assertEqual(workflow,''.join(old['cells'][7]['source']))
        self.assertIn((ROOT/'backend_test/bandit_dependencies.py').read_text(encoding='utf-8').strip(),
                      ''.join(new['cells'][2]['source']))
        for index,cell in enumerate(new['cells']):
            if cell['cell_type']=='code':
                compile(''.join(cell['source']),f'cell{index}','exec')
                self.assertEqual(cell['outputs'],[])
                self.assertIsNone(cell['execution_count'])

    def dependency_cell(self, gpu=True, audio_version='2.11.0+cu130', mutate=False, calls=None):
        versions={'torch':'2.14.1+cu130','torchaudio':audio_version,
                  'pytorch-lightning':'2.5.1','noisereduce':'3.0.3'}
        torch=SimpleNamespace(__version__=versions['torch'],version=SimpleNamespace(cuda='13.0'),
                              cuda=SimpleNamespace(is_available=lambda:gpu,get_device_name=lambda i:'synthetic GPU'))
        audio=SimpleNamespace(__version__=audio_version)
        calls=[] if calls is None else calls
        def install(command):
            constraint_file=Path(command[command.index('-c')+1])
            calls.append((command,constraint_file.read_text()))
            if mutate:
                versions['torchaudio']='2.10.0+cu130'
        with patch.dict(sys.modules,{'torch':torch,'torchaudio':audio}), \
                patch('importlib.metadata.version',side_effect=lambda name:versions[name]), \
                patch('subprocess.check_call',side_effect=install), \
                patch.dict('os.environ',{},clear=False):
            env={'print':lambda *a:None}
            exec(compile(''.join(notebook('bandit_4_2')['cells'][2]['source']),'<dependencies42>','exec'),env)
        return calls

    def test_installation_retains_pair_and_original_auxiliary_dependency_list(self):
        calls=self.dependency_cell()
        self.assertEqual(len(calls),1)
        command,constraints=calls[0]
        self.assertEqual(constraints,'torch==2.14.1+cu130\ntorchaudio==2.11.0+cu130\n')
        self.assertEqual(command[command.index('-c')+2:],[
            'pytorch-lightning==2.5.1','librosa==0.11.0','soundfile==0.13.1',
            'noisereduce==3.0.3','scipy','PyYAML==6.0.2','requests','tensorflow-hub==0.16.1'])
        self.assertFalse(any(arg.startswith(('torch==','torchaudio==')) for arg in command))

    def test_missing_gpu_or_incompatible_pair_stops_before_install(self):
        for kwargs in (dict(gpu=False),dict(audio_version='2.9.1+cu130')):
            with self.subTest(kwargs=kwargs):
                calls=[]
                with self.assertRaises(RuntimeError):
                    self.dependency_cell(**kwargs,calls=calls)
                self.assertEqual(calls,[])

    def test_post_install_loaded_package_mismatch_is_detected(self):
        calls=[]
        with self.assertRaisesRegex(RuntimeError,'chargé'):
            self.dependency_cell(mutate=True,calls=calls)
        self.assertEqual(len(calls),1)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg required')
    def test_new_backend_label_publishes_exact_bwf_with_generic_set(self):
        env=scope('bandit_4_2')
        env.update(vars(contract))
        env.update(np=np,sf=sf,shutil=shutil,subprocess=subprocess,RUN_ID='bandit42synthetic',
                   REMPLACER_RUN_INTERROMPU=False,BANDIT_COMMIT='synthetic',BANDIT_CHECKPOINT_MD5='synthetic',
                   validate_bandit_audio=lambda x,sr:x,preflight_models=lambda:None,
                   analyze_yamnet=lambda p:{'frames':{}},_analyze_residual_audio=lambda *a:{'frames':{}},
                   prep_denoise_batch=lambda *a:None)
        with tempfile.TemporaryDirectory() as directory:
            for key in ('FOLDER_IN','FOLDER_OUT','FOLDER_MERGED','FOLDER_DENOISED','FOLDER_AI_STEMS','FOLDER_TC_READY'):
                path=Path(directory)/key
                path.mkdir()
                env[key]=str(path)
            raw=Path(env['FOLDER_IN'])/'Pr_Rep_1-Gain_01.wav'
            raw.write_bytes(wave_bytes(90001,1823255434,level=.1))
            def bandit(files):
                for name in files:
                    shutil.copy2(Path(env['FOLDER_MERGED'])/name,
                                 Path(env['FOLDER_AI_STEMS'])/(Path(name).stem+'_Bandit.wav'))
            env['process_bandit_batch']=bandit
            exec(compile(''.join(notebook('bandit_4_2')['cells'][7]['source']),'<workflow42>','exec'),env)
            manifest=json.loads((Path(env['FOLDER_OUT'])/contract.DELIVERY_MANIFEST).read_text())
            contract.validate_delivery_manifest(manifest)
            self.assertEqual(manifest['backend'],'Bandit_V4_2')
            entry=manifest['outputs'][0]
            self.assertEqual((entry['frames'],entry['time_reference'],entry['role']),(90001,1823255434,'Pr_Rep_1'))
            output=Path(env['FOLDER_OUT'])/manifest['run_folder']/entry['name']
            contract.verify_delivery_file(output,entry)
            self.assertNotEqual(entry['umid'],contract.read_wave_umid(raw))
            np.testing.assert_allclose(sf.read(output)[0],.1,atol=4e-7)


if __name__=='__main__':
    unittest.main()
