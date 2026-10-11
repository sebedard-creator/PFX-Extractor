"""UMID-only backport: actual FFmpeg export and unchanged legacy DSP."""
import ast
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

import soundfile as sf

import delivery_contract as contract
from tests.test_backend_v330 import notebook, scope
from tests.wav_fixtures import wave_bytes


class BackendV352Tests(unittest.TestCase):
    def environment(self):
        env = scope('3_5_2')
        env.update(hashlib=hashlib, struct=struct, uuid=uuid, tempfile=tempfile,
                   Path=Path, subprocess=subprocess, sf=sf,
                   RENDER_UMID_PREFIX=contract.RENDER_UMID_PREFIX)
        return env

    def test_unchanged_dsp_and_settings(self):
        old, new = notebook('3_5_1'), notebook('3_5_2')
        for i in (2, 3, 4, 5):
            self.assertEqual(old['cells'][i]['source'], new['cells'][i]['source'])
        expected_settings = ''.join(old['cells'][1]['source']).replace(
            'NIVEAU_DENOISE_POURCENTAGE = 58', 'NIVEAU_DENOISE_POURCENTAGE = 40')
        self.assertTrue(''.join(new['cells'][1]['source']).startswith(expected_settings))
        self.assertEqual(scope('3_5_2')['NIVEAU_DENOISE_POURCENTAGE'], 40)
        self.assertEqual(scope('3_5_1')['NIVEAU_DENOISE_POURCENTAGE'], 58)
        self.assertTrue(''.join(new['cells'][8]['source']).endswith(''.join(old['cells'][8]['source'])))
        def functions(nb):
            tree = ast.parse(''.join(nb['cells'][6]['source']))
            return {n.name: ast.dump(n) for n in tree.body if isinstance(n, ast.FunctionDef)}
        before, after = functions(old), functions(new)
        for name in before:
            if name != 'inject_timecode':
                self.assertEqual(before[name], after[name], name)
        for i, cell in enumerate(new['cells']):
            if cell['cell_type'] == 'code':
                code = ''.join(l for l in cell['source'] if not l.lstrip().startswith(('!', '%')))
                compile(code, f'cell{i}', 'exec')
                self.assertEqual(cell['outputs'], [])
        workflow = ''.join(new['cells'][7]['source'])
        self.assertLess(workflow.index('begin_v352_delivery('), workflow.index('preflight_models()'))
        self.assertIn('forbidden=render_umids', workflow)
        self.assertIn('complete_v352_delivery(delivery)', workflow)
        self.assertIn('fail_v352_delivery(delivery)', workflow)
        self.assertIn("str(delivery['run_path']", workflow)
        code = ''.join(new['cells'][6]['source'])
        root = Path(__file__).resolve().parents[1]
        for name in ('delivery_contract.py', 'backend_test/v352_delivery.py'):
            self.assertIn((root / name).read_text(encoding='utf-8').strip(), code)

    def test_embedded_umid_helpers_match_verified_contract(self):
        env = self.environment()
        import inspect
        tree = ast.parse(''.join(notebook('3_5_2')['cells'][6]['source']))
        nodes = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
        for name in ('wave_chunk_extent', 'read_wave_umid', 'wave_audio_sha256',
                     'assign_render_umid', 'verify_unique_wave_umids'):
            reference = ast.parse(inspect.getsource(getattr(contract, name))).body[0]
            self.assertEqual(ast.dump(nodes[name]), ast.dump(reference))

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'), 'FFmpeg required')
    def test_real_exports_preserve_samples_tc_and_use_distinct_umids(self):
        env = self.environment()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, processed = root / 'BOOM.wav', root / 'mix.wav'
            source.write_bytes(wave_bytes(1483482, 1823255434))
            # Source material with both unsigned words above signed-64 maximum.
            offset, _ = contract.wave_chunk_extent(source, b'bext')
            with source.open('r+b') as handle:
                handle.seek(offset + 348)
                handle.write(contract.RENDER_UMID_PREFIX + bytes.fromhex('94aaaaaaaaaaaaaaadbbbbbbbbbbbbbb') + bytes(32))
            source_hash = contract.sha256_file(source)
            audio, sr = sf.read(source, dtype='float32')
            sf.write(processed, audio, sr, subtype='FLOAT')
            used = [contract.read_wave_umid(source)]
            outputs = []
            for i in range(2):
                output = root / f'BOOM_{i}_PFX_Ready.wav'
                env['inject_timecode'](str(source), str(processed), str(output), forbidden=used)
                info = sf.info(output)
                self.assertEqual((info.frames, info.samplerate), (1483482, 48000))
                self.assertEqual(contract.wave_audio_sha256(output), contract.wave_audio_sha256(processed))
                offset, _ = contract.wave_chunk_extent(output, b'bext')
                with output.open('rb') as handle:
                    handle.seek(offset + 338)
                    self.assertEqual(struct.unpack('<Q', handle.read(8))[0], 1823255434)
                identity = contract.read_wave_umid(output)
                self.assertNotIn(identity, used)
                used.append(identity)
                outputs.append(output)
            contract.verify_unique_wave_umids(outputs, forbidden=[contract.read_wave_umid(source)])
            self.assertEqual(contract.sha256_file(source), source_hash)

    def test_failed_ffmpeg_keeps_previous_output(self):
        env = self.environment()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, output = root / 'BOOM.wav', root / 'out.wav'
            source.write_bytes(wave_bytes())
            output.write_bytes(b'previous-delivery')
            env['get_sample_rate'] = lambda path: 48000
            with patch.object(subprocess, 'check_output', return_value=b'172800000'), \
                 patch.object(subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'ffmpeg')):
                with self.assertRaises(subprocess.CalledProcessError):
                    env['inject_timecode'](str(source), 'mix.wav', str(output))
            self.assertEqual(output.read_bytes(), b'previous-delivery')
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['BOOM.wav', 'out.wav'])

    def test_switch_both_directions_preserves_generations_and_blocks_failures(self):
        env = self.environment()
        env.update(vars(contract))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for key in ('FOLDER_IN', 'FOLDER_OUT', 'FOLDER_ALIGNED', 'FOLDER_MERGED',
                        'FOLDER_DENOISED', 'FOLDER_AI_STEMS', 'FOLDER_TC_READY'):
                folder = root / key
                folder.mkdir()
                env[key] = str(folder)
            raw = Path(env['FOLDER_IN']) / 'scene_BOOM_01.wav'
            raw.write_bytes(wave_bytes(48000, 172800000))
            pointer = Path(env['FOLDER_OUT']) / contract.DELIVERY_MANIFEST
            previous = pointer.parent / 'run_previous'
            previous.mkdir()
            (previous / 'keep.txt').write_text('old delivery')
            contract.write_delivery_manifest(pointer, dict(status='complete', backend='Vtest_V3', run_id='previous'))
            env.update(REMPLACER_RUN_INTERROMPU=False, MIN_EXPORT_SAMPLES=1024, preflight_models=lambda: None,
                       analyze_yamnet=lambda p: {}, prep_denoise_batch=lambda *a: None,
                       initial_mic_alignment=lambda files: files,
                       snowball_merge=lambda files: (files, {files[0]: {'segments': [files[0]]}}),
                       iter_split_merged_audio=lambda *a: [(raw.name, sf.read(raw, dtype='float32')[0], 48000)],
                       auto_align_and_mix=lambda a,b,d,**kw: shutil.copy2(raw,d),
                       MODEL_MDX23C='mdx', MODEL_ROFORMER='rof', MDXC_PARAMS={}, ROFORMER_PARAMS={})
            def separate(model, suffix, params, files):
                for name in files:
                    shutil.copy2(raw, Path(env['FOLDER_AI_STEMS']) / (Path(name).stem + suffix))
            env['process_batch'] = separate
            workflow = ''.join(notebook('3_5_2')['cells'][7]['source'])
            exec(compile(workflow, '<workflow352>', 'exec'), env)
            first = json.loads(pointer.read_text())
            contract.validate_delivery_manifest(first)
            self.assertEqual(first['backend'], 'V3.5.2')
            self.assertTrue(env['WORKFLOW_COMPLETE'])
            first_wav = pointer.parent / first['run_folder'] / first['outputs'][0]['name']
            first_hash = contract.sha256_file(first_wav)
            # Run the real Test V3 orchestration, replacing only expensive audio models.
            v3 = scope('test_V3')
            v3.update(vars(contract))
            v3.update({k:v for k,v in env.items() if k.startswith('FOLDER_')})
            v3.update(sf=sf, shutil=shutil, RUN_ID='back_to_test_v3',
                      REMPLACER_RUN_INTERROMPU=False, BANDIT_COMMIT='synthetic', BANDIT_CHECKPOINT_MD5='synthetic',
                      preflight_models=lambda:None, analyze_yamnet=lambda p:{}, prep_denoise_batch=lambda *a:None,
                      process_bandit_batch=lambda files: separate('bandit','_Bandit.wav',{},files),
                      finish_v3=lambda src,dst: shutil.copy2(src,dst))
            def inject(src,mix,dst):
                env['inject_timecode'](src,mix,dst)
                contract.ensure_export_extensible(dst)
            v3['inject_timecode'] = inject
            exec(compile(''.join(notebook('test_V3')['cells'][7]['source']), '<workflowV3>', 'exec'), v3)
            second = json.loads(pointer.read_text())
            contract.validate_delivery_manifest(second)
            self.assertEqual(second['backend'], 'Vtest_V3')
            # Back again to 3.5.2, with a model failure: no old lot may be delivered.
            env['preflight_models'] = lambda: (_ for _ in ()).throw(RuntimeError('model failed'))
            with self.assertRaisesRegex(RuntimeError, 'model failed'):
                exec(compile(workflow, '<workflow352>', 'exec'), env)
            failed = json.loads(pointer.read_text())
            self.assertEqual(failed['status'], 'failed')
            with self.assertRaises(ValueError):
                contract.validate_delivery_manifest(failed)
            self.assertEqual(contract.sha256_file(first_wav), first_hash)
            self.assertTrue((pointer.parent / second['run_folder']).exists())
            self.assertEqual((previous / 'keep.txt').read_text(), 'old delivery')

    def test_partial_and_concurrent_generations_never_publish(self):
        env = self.environment()
        env.update(vars(contract))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, outputs = root / 'in', root / 'out'
            inputs.mkdir()
            outputs.mkdir()
            (inputs / 'scene_BOOM.wav').write_bytes(wave_bytes())
            delivery = env['begin_v352_delivery'](inputs, outputs, {})
            with self.assertRaisesRegex(RuntimeError, 'cours ou interrompu'):
                env['begin_v352_delivery'](inputs, outputs, {})
            with self.assertRaisesRegex(RuntimeError, 'incomplet'):
                env['complete_v352_delivery'](delivery)
            other = dict(run_id='other', status='running')
            contract.write_delivery_manifest(delivery['pointer'], other)
            env['fail_v352_delivery'](delivery)
            self.assertEqual(json.loads(delivery['pointer'].read_text()), other)


if __name__ == '__main__':
    unittest.main()
