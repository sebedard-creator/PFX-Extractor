import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import drive_auth
from tests.wav_fixtures import wave_bytes


class ExplosiveProgress:
    """Reproduit le comportement Gradio qui a causé l'IndexError."""

    def __init__(self):
        self.calls = []

    def __len__(self):
        raise IndexError("list index out of range")

    def __call__(self, value, *, desc):
        self.calls.append((value, desc))


class FakeDriveService:
    def files(self):
        return self

    def get_media(self, fileId):
        return fileId


class FakeDownload:
    def __init__(self, handle, request):
        self.handle = handle
        self.request = request
        self.done = False

    def next_chunk(self):
        if not self.done:
            self.handle.write(wave_bytes())
            self.done = True
        return None, True


class DriveProgressTests(unittest.TestCase):
    def test_resumable_upload_reports_chunks_and_completed_file_count(self):
        progress = ExplosiveProgress()
        service = Mock()
        first = Mock()
        first.next_chunk.side_effect = [
            (Mock(progress=lambda: .25), None),
            (Mock(progress=lambda: .75), None),
            (None, {'id': 'first-upload'}),
        ]
        second = Mock()
        second.next_chunk.return_value = (None, {'id': 'second-upload'})
        service.files.return_value.create.side_effect = [first, second]
        with tempfile.TemporaryDirectory() as directory:
            paths = [Path(directory) / name for name in ('BOOM_01.wav', 'BOOM_02.wav')]
            for path in paths:
                path.write_bytes(wave_bytes())
            with patch.object(drive_auth, 'authenticate_drive', return_value=service), \
                 patch.object(drive_auth, 'get_pfx_folders', return_value=('parent', 'raw', 'out')):
                result = drive_auth.upload_files(paths, progress=progress)
            self.assertEqual(result, {'count': 2, 'names': [p.name for p in paths], 'failed': []})
            self.assertEqual([value for value, _ in progress.calls], [0, .125, .375, .5, .5, 1, 1])
            self.assertIn('25%', progress.calls[1][1])
            self.assertIn('1/2', progress.calls[3][1])
            self.assertIn('2/2', progress.calls[-1][1])
            self.assertEqual(first.next_chunk.call_count, 3)
            first.next_chunk.assert_called_with(num_retries=3)
            first.execute.assert_not_called()
            for call in service.files.return_value.create.call_args_list:
                media = call.kwargs['media_body']
                self.assertEqual(media.chunksize(), 8 * 1024 * 1024)
                self.assertTrue(media.stream().closed)

    def test_upload_failure_does_not_count_as_sent_or_stop_remaining_files(self):
        progress = ExplosiveProgress()
        service = Mock()
        failed = Mock()
        failed.next_chunk.side_effect = RuntimeError('connection failed')
        succeeded = Mock()
        succeeded.next_chunk.return_value = (None, {'id': 'uploaded'})
        service.files.return_value.create.side_effect = [failed, succeeded]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = [root / name for name in ('BOOM_01.wav', 'missing.wav', 'BOOM_02.wav')]
            paths[0].write_bytes(wave_bytes())
            paths[2].write_bytes(wave_bytes())
            with patch.object(drive_auth, 'authenticate_drive', return_value=service), \
                 patch.object(drive_auth, 'get_pfx_folders', return_value=('parent', 'raw', 'out')):
                result = drive_auth.upload_files(paths, progress=progress)
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['names'], ['BOOM_02.wav'])
        self.assertEqual(len(result['failed']), 2)
        self.assertIn('1/3', progress.calls[-1][1])
        self.assertIn('2 échec', progress.calls[-1][1])
        fractions = [value for value, _ in progress.calls]
        self.assertEqual(fractions, sorted(fractions))

    def test_progress_helper_never_uses_truthiness(self):
        progress = ExplosiveProgress()
        drive_auth._report_progress(progress, 0.5, "Test")
        self.assertEqual(progress.calls, [(0.5, "Test")])
        drive_auth._report_progress(None, 1.0, "Ignored")

    def test_download_accepts_gradio_like_progress_object(self):
        progress = ExplosiveProgress()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / "processed"
            processed.mkdir()
            with (
                patch.object(drive_auth, "WORK_DIR", root),
                patch.object(drive_auth, "PROCESSED_DIR", processed),
                patch.object(drive_auth, "ensure_work_dirs"),
                patch.object(drive_auth, "authenticate_drive", return_value=FakeDriveService()),
                patch.object(drive_auth, "get_pfx_folders", return_value=("parent", "raw", "processed")),
                patch.object(
                    drive_auth,
                    "_list_files_in_folder",
                    return_value=[{"id": "media-1", "name": "A144_Boom-Gain_01_PFX_Ready.wav"}],
                ),
                patch.object(drive_auth, "MediaIoBaseDownload", FakeDownload),
            ):
                paths, result = drive_auth.download_processed_files(progress=progress)

            self.assertEqual(result["count"], 1)
            self.assertEqual(paths[0].read_bytes(), wave_bytes())
            self.assertEqual(
                progress.calls,
                [
                    (0.0, "Download 1/1: A144_Boom-Gain_01_PFX_Ready.wav"),
                    (1.0, "Fichiers traites telecharges"),
                ],
            )

    def test_no_progress_truthiness_checks_remain(self):
        source = Path(drive_auth.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        checks = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Name)
            and node.test.id == "progress"
        ]
        self.assertEqual(checks, [])


class CacheProgressTests(unittest.TestCase):
    def test_drive_reports_names_successes_failures_and_empty_folder(self):
        progress = ExplosiveProgress()
        service = Mock()
        service.files.return_value.delete.return_value.execute.side_effect = [None, RuntimeError('locked')]
        with patch.object(drive_auth, 'authenticate_drive', return_value=service), \
             patch.object(drive_auth, 'get_pfx_folders', return_value=('parent','raw','out')), \
             patch.object(drive_auth, '_list_files_in_folder', side_effect=[
                 [{'id':'one','name':'BOOM_01.wav'}, {'id':'two','name':'BOOM_02.wav'}], []]):
            result = drive_auth.clear_drive_cache(progress=progress)
        self.assertEqual(result['deleted'], 1)
        self.assertEqual(len(result['failed']), 1)
        self.assertIn('BOOM_02.wav', result['failed'][0])
        descriptions = [desc for _,desc in progress.calls]
        self.assertTrue(any('BOOM_01.wav' in desc and 'supprimé' in desc for desc in descriptions))
        self.assertTrue(any('BOOM_02.wav' in desc and 'non supprimé' in desc for desc in descriptions))
        self.assertTrue(any('aucun fichier' in desc for desc in descriptions))
        self.assertEqual(progress.calls[-1][0], 1)
        service.files.return_value.delete.assert_any_call(fileId='one',supportsAllDrives=True)

    def test_local_nested_cleanup_reports_each_item_and_retains_cache_root(self):
        progress = ExplosiveProgress()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root / 'processed'
            audio = cache / 'Audio Files'
            audio.mkdir(parents=True)
            for path in (audio/'BOOM_01.wav', audio/'BOOM_02.wav', cache/'manifest.json'):
                path.write_bytes(b'test')
            with patch.object(drive_auth,'WORK_DIR',root), patch.object(drive_auth,'ensure_work_dirs'):
                count = drive_auth._clear_directory_contents(cache,progress=progress)
            self.assertEqual(count, 4)
            self.assertTrue(cache.is_dir())
            self.assertEqual(list(cache.iterdir()), [])
            messages = [desc for _,desc in progress.calls]
            self.assertTrue(any('BOOM_01.wav' in desc for desc in messages))
            self.assertTrue(any('BOOM_02.wav' in desc for desc in messages))
            fractions=[value for value,_ in progress.calls]
            self.assertEqual(fractions,sorted(fractions))
            self.assertEqual(fractions[-1],1)

    def test_locked_local_file_is_reported_and_other_files_are_deleted(self):
        progress, failed = ExplosiveProgress(), []
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cache = root/'exports'
            cache.mkdir()
            locked, other = cache/'locked.zip', cache/'other.zip'
            locked.write_bytes(b'keep')
            other.write_bytes(b'delete')
            unlink = Path.unlink
            def lock_one(path, *args, **kwargs):
                if path == locked:
                    raise PermissionError('file in use')
                return unlink(path, *args, **kwargs)
            with patch.object(drive_auth,'WORK_DIR',root), patch.object(drive_auth,'ensure_work_dirs'), \
                 patch.object(Path,'unlink',lock_one):
                count=drive_auth._clear_directory_contents(cache,progress=progress,failed=failed)
            self.assertEqual(count,1)
            self.assertEqual(locked.read_bytes(),b'keep')
            self.assertFalse(other.exists())
            self.assertEqual(len(failed),1)
            self.assertTrue(any('non supprimé' in desc for _,desc in progress.calls))

    def test_cleanup_refuses_work_root_and_paths_outside_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            work=root/'work'
            outside=root/'outside'
            work.mkdir()
            outside.mkdir()
            protected=outside/'keep.txt'
            protected.write_text('keep')
            with patch.object(drive_auth,'WORK_DIR',work), patch.object(drive_auth,'ensure_work_dirs'):
                for path in (work,outside):
                    with self.assertRaisesRegex(RuntimeError,'Refus'):
                        drive_auth._clear_directory_contents(path)
            self.assertEqual(protected.read_text(),'keep')

    def test_nested_link_is_removed_without_touching_its_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            work=root/'work'
            cache=work/'exports'
            cache.mkdir(parents=True)
            outside=root/'outside'
            outside.mkdir()
            protected=outside/'keep.txt'
            protected.write_text('keep')
            link=cache/'linked_folder'
            try:
                link.symlink_to(outside,target_is_directory=True)
            except OSError as exc:
                self.skipTest(f'Symlink creation unavailable: {exc}')
            with patch.object(drive_auth,'WORK_DIR',work), patch.object(drive_auth,'ensure_work_dirs'):
                count=drive_auth._clear_directory_contents(cache)
            self.assertEqual(count,1)
            self.assertFalse(link.exists())
            self.assertEqual(protected.read_text(),'keep')

    def test_aggregate_progress_covers_drive_then_local_and_keeps_failures(self):
        progress=ExplosiveProgress()
        def drive(*,progress):
            progress(0,desc='Drive start')
            progress(1,desc='Drive done')
            return {'deleted':2,'failed':[]}
        def local(*,include_runtime,progress,failed):
            self.assertTrue(include_runtime)
            progress(0,desc='Local start')
            failed.append('locked local file')
            progress(1,desc='Local done')
            return 3
        with patch.object(drive_auth,'clear_drive_cache',side_effect=drive), \
             patch.object(drive_auth,'clear_local_cache',side_effect=local):
            result=drive_auth.clear_all_cache(progress=progress,include_runtime=True)
        self.assertEqual(result,{'drive_deleted':2,'drive_failed':[],
                                 'local_deleted':3,'local_failed':['locked local file']})
        self.assertEqual([v for v,_ in progress.calls],[0,.75,.75,1,1])
        self.assertIn('1 erreur',progress.calls[-1][1])


if __name__ == "__main__":
    unittest.main()
