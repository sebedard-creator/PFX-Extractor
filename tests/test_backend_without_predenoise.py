"""Offline checks for the single-variable pre-denoise comparison."""
import ast
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import numpy as np
import soundfile as sf

from tests import test_backend_vtest as reference_tests


class WithoutPredenoiseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.nb = reference_tests.read_notebook('Colab_Backend_PFX_Vtest_sans_prenettoyage.ipynb')
        cls.reference = reference_tests.read_notebook('Colab_Backend_PFX_Vtest.ipynb')

    def test_compile_and_clean_outputs(self):
        reference_tests.VtestNotebookTests.test_all_cells_compile_and_have_no_stale_output(self)

    def test_embedded_runtime_identical(self):
        reference_tests.VtestNotebookTests.test_embedded_runtime_is_identical(self)

    def test_only_predenoise_processing_changes(self):
        for index in (2, 3, 5, 8):
            self.assertEqual(self.nb['cells'][index], self.reference['cells'][index])
        def functions(nb, index):
            return {n.name: ast.dump(n, include_attributes=False)
                    for n in ast.parse(''.join(nb['cells'][index]['source'])).body
                    if isinstance(n, ast.FunctionDef)}
        original = functions(self.reference, 6)
        original.pop('prep_denoise_batch')
        self.assertEqual(functions(self.nb, 6), original)
        old = ''.join(self.reference['cells'][4]['source'])
        self.assertEqual(''.join(self.nb['cells'][4]['source']), old.replace(
            'sf.read(os.path.join(FOLDER_DENOISED, filename)',
            'sf.read(os.path.join(FOLDER_MERGED, filename)'))
        def constants(nb):
            return {n.targets[0].id: ast.literal_eval(n.value)
                    for n in ast.parse(''.join(nb['cells'][1]['source'])).body
                    if isinstance(n, ast.Assign)}
        before, after = constants(self.reference), constants(self.nb)
        before.update(NIVEAU_DENOISE_POURCENTAGE=0, DENOISE_ADAPTATIF=False)
        self.assertEqual(after, before)
        self.assertEqual(after['GAIN_BODYTALK_DB'], 4.0)
        code = '\n'.join(''.join(c['source']) for c in self.nb['cells'])
        self.assertNotIn('nr.reduce_noise(', code)
        self.assertNotIn('prep_denoise_batch(', code)

    def test_bandit_receives_exact_merged_samples_without_denoised_files(self):
        tree = ast.parse(''.join(self.nb['cells'][4]['source']))
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'process_bandit_batch')
        with tempfile.TemporaryDirectory() as temp:
            merged, stems = Path(temp) / 'merged', Path(temp) / 'stems'
            merged.mkdir()
            stems.mkdir()
            audio = np.random.default_rng(8).normal(0, .02, (48001, 1)).astype(np.float32)
            sf.write(merged / 'Boom.wav', audio, 48000, subtype='FLOAT')
            observed = []
            def separate(model, samples, sr):
                observed.append((samples.copy(), sr))
                return samples
            env = dict(os=os, sf=sf, _bandit_model=object(),
                       FOLDER_MERGED=str(merged), FOLDER_AI_STEMS=str(stems),
                       bandit_separate_audio=separate, print=lambda *a: None,
                       gc=SimpleNamespace(collect=lambda: None),
                       torch=SimpleNamespace(cuda=SimpleNamespace(empty_cache=lambda: None)))
            exec(compile(ast.Module(body=[node], type_ignores=[]), '<batch>', 'exec'), env)
            env['process_bandit_batch'](['Boom.wav'])
            np.testing.assert_array_equal(observed[0][0], audio)
            self.assertEqual(observed[0][1], 48000)
            np.testing.assert_array_equal(sf.read(stems / 'Boom_Bandit.wav',
                                                 dtype='float32', always_2d=True)[0], audio)

    def test_standard_delivery_two_runs(self):
        reference_tests.VtestNotebookTests.test_two_runs_replace_wavs_in_frontend_folder_without_extra_files(self)

    def test_real_bwf_export(self):
        reference_tests.VtestNotebookTests.test_real_bwf_mono_timecode_and_duration(self)


if __name__ == '__main__':
    unittest.main()
