"""Generic source sets: real naming example, synthetic BWFs, no cloud/model calls."""
import copy
from pathlib import Path
import re
import shutil
import tempfile
import unittest

import delivery_contract as contract
import protools_export
from tests.test_backend_v330 import scope
from tests.wav_fixtures import wave_bytes


class AudioSetTests(unittest.TestCase):
    def test_final_index_only_and_processed_name_stability(self):
        for name, role in (
                ('Pr_Rep_1-Gain_01.wav', 'Pr_Rep_1'),
                ('Pr_Rep_2-Gain_45.wav', 'Pr_Rep_2'),
                ('Scene_2026_Mic_A_124.wav', 'Scene_2026_Mic_A'),
                ('Plant-002.WAV', 'Plant'),
                ('A153_Boom-Gain_99.wav', 'BOOM'),
                ('autre_LAV_004.wav', 'LAV')):
            with self.subTest(name=name):
                self.assertEqual(contract.microphone_role(name), role)
                output = name[:-4] + '_PFX_Ready.wav'
                self.assertEqual(contract.microphone_role(output), role)

    def test_counts_ambiguities_duplicates_and_one_set(self):
        names = [f'Pr_Rep_{group}-Gain_{i:02d}.wav'
                 for group in (1, 2) for i in range(1, 46)]
        roles = contract.audio_set_roles(names)
        self.assertEqual(list(roles.values()).count('Pr_Rep_1'), 45)
        self.assertEqual(list(roles.values()).count('Pr_Rep_2'), 45)
        self.assertEqual(len(contract.audio_set_roles(names[:45])), 45)
        for invalid in (names[:-1], names + ['Third_01.wav'],
                        ['unknown.wav'], ['BOOM_LAV_01.wav'],
                        ['Mic_01.wav', 'mic_01.WAV'], ['../Mic_01.wav']):
            with self.subTest(invalid=invalid[-1]), self.assertRaises(ValueError):
                contract.audio_set_roles(invalid)
        # Case variants cannot accidentally become extra tracks.
        self.assertEqual(set(contract.audio_set_roles(['Mic_01.wav', 'mic_02.wav']).values()), {'Mic'})

    def test_generic_preflight_in_every_supported_notebook_before_models(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            source.mkdir()
            for group in (1, 2):
                for i in (1, 2):
                    name = f'Pr_Rep_{group}-Gain_{i:02d}.wav'
                    (source / name).write_bytes(wave_bytes(n=4800+i, tc=1728000000+i*9600,
                                                         identity=name))
            for version in ('test_V4', 'bandit_4_1', 'bandit_4_2', '3_5_2'):
                with self.subTest(version=version):
                    env = scope(version)
                    env.update(vars(contract))
                    env['FOLDER_IN'] = str(source)
                    if version == '3_5_2':
                        output = root / version
                        output.mkdir()
                        delivery = env['begin_v352_delivery'](source, output, {})
                        self.assertFalse(delivery['manifest']['alignment'])
                        entries = delivery['manifest']['inputs']
                    else:
                        entries = env['preflight_v4_inputs']()
                    self.assertEqual([entry['role'] for entry in entries],
                                     ['Pr_Rep_1', 'Pr_Rep_1', 'Pr_Rep_2', 'Pr_Rep_2'])
                    self.assertEqual([entry['frames'] for entry in entries], [4801,4802,4801,4802])

    def test_mdx_does_not_guess_alignment_reference_from_generic_set_names(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, aligned = root / 'in', root / 'aligned'
            source.mkdir()
            aligned.mkdir()
            names = ['Pr_Rep_1-Gain_01.wav', 'Pr_Rep_2-Gain_01.wav']
            for name in names:
                (source / name).write_bytes(wave_bytes(identity=name))
            env = scope('3_5_2')
            env.update(re=re, shutil=shutil, FOLDER_IN=str(source), FOLDER_ALIGNED=str(aligned))
            self.assertEqual(env['initial_mic_alignment'](names), names)
            for name in names:
                self.assertEqual((source / name).read_bytes(), (aligned / name).read_bytes())

    @unittest.skipUnless(protools_export.DEFAULT_TEMPLATE_PATH.is_file(), 'local PTX template required')
    def test_real_90_clip_two_set_delivery_preserves_geometry_and_tracks(self):
        builder = protools_export.resolve_pt_api_builder()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / 'processed'
            processed.mkdir()
            manifest = dict(protocol=2, status='complete', run_id='generic_sets',
                            run_folder='run_generic_sets', inputs=[], outputs=[])
            expected = {}
            for group in (1,2):
                for i in range(1,46):
                    name = f'Pr_Rep_{group}-Gain_{i:02d}_PFX_Ready.wav'
                    path = processed / name
                    n, tc = 4800+i, 1728000000+i*9600
                    path.write_bytes(wave_bytes(n=n, tc=tc, identity=name))
                    contract.assign_render_umid(path)
                    entry = dict(contract.inspect_delivery_wave(path, for_export=True),
                                 name=name, role=f'Pr_Rep_{group}',
                                 sha256=contract.sha256_file(path), umid=contract.read_wave_umid(path))
                    manifest['outputs'].append(entry)
                    expected[name[:-4]] = (n, tc, f'PFX 0{group}')
            contract.validate_delivery_manifest(manifest)
            bad = copy.deepcopy(manifest)
            bad['outputs'][0]['role'] = 'Pr_Rep_2'
            with self.assertRaisesRegex(ValueError, 'Ensemble'):
                contract.validate_delivery_manifest(bad)
            contract.write_delivery_manifest(processed / contract.DELIVERY_MANIFEST, manifest)
            descriptors, families = protools_export.collect_processed_manifest(processed)
            self.assertEqual(len(descriptors), 90)
            self.assertEqual(families, [dict(family=f'Pr_Rep_{g}', track=f'PFX 0{g}', count=45)
                                       for g in (1,2)])
            result = protools_export.create_protools_delivery(processed, root / 'exports',
                session_name='Generic_sets_90', builder=builder)
            session = builder.__globals__['ProToolsSession'](result['session_path'])
            clips = session.get_timeline_clips(include_fades=False)
            self.assertEqual(len(clips), 90)
            actual = sorted((c['length_samples'], c['start_samples'], c['track']) for c in clips)
            self.assertEqual(actual, sorted(expected.values()))


if __name__ == '__main__':
    unittest.main()
