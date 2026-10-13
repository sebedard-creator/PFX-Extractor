import unittest
import warnings
from pathlib import Path
from unittest.mock import ANY, patch

warnings.filterwarnings(
    "ignore",
    message="Please use `import python_multipart` instead.",
    category=PendingDeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r"(?s).*on_event is deprecated.*",
    category=DeprecationWarning,
)

import app_local


class UploadProgressTests(unittest.TestCase):
    def test_upload_callback_forwards_gradio_progress(self):
        from tests.test_drive_auth import ExplosiveProgress
        progress = ExplosiveProgress()
        paths = [Path('BOOM_01.wav'), Path('BOOM_02.wav')]
        with patch.object(app_local.drive_auth, 'stage_uploaded_files', return_value=paths), \
             patch.object(app_local.drive_auth, 'upload_files', return_value={
                 'count': 2, 'names': [p.name for p in paths], 'failed': []}) as upload:
            status, cleared_files = app_local.upload_raw_files(['uploaded1', 'uploaded2'], progress=progress)
        upload.assert_called_once_with(paths, progress=progress)
        self.assertEqual(len(progress.calls), 2)
        self.assertIn('Préparation', progress.calls[0][1])
        self.assertIn('Connexion', progress.calls[1][1])
        self.assertIn('2 fichiers', status)
        self.assertIsNone(cleared_files)


class CacheProgressTests(unittest.TestCase):
    def test_cleanup_callback_forwards_progress_and_displays_partial_results(self):
        from tests.test_drive_auth import ExplosiveProgress
        progress=ExplosiveProgress()
        with patch.object(app_local.drive_auth,'clear_all_cache',return_value={
                'local_deleted':5,'drive_deleted':10,
                'local_failed':['locked.zip'],'drive_failed':['BOOM_03.wav']}) as clear:
            status,files,archive,confirmation=app_local.clear_cache(progress=progress)
        clear.assert_called_once_with(include_runtime=True,progress=progress)
        self.assertIn('terminé avec des erreurs',status)
        self.assertIn('locked.zip',status)
        self.assertIn('BOOM_03.wav',status)
        self.assertIn('5',status)
        self.assertIn('10',status)
        self.assertIsNone(files)
        self.assertIsNone(archive)


class CombinedDownloadTests(unittest.TestCase):
    @patch("app_local.protools_export.create_protools_delivery")
    @patch("app_local.drive_auth.download_processed_files")
    def test_download_builds_and_returns_protools_delivery(
        self,
        download_processed_files,
        create_protools_delivery,
    ):
        download_processed_files.return_value = (
            [Path("Boom_01.wav"), Path("Boom_02.wav")],
            {"count": 2, "names": ["Boom_01.wav", "Boom_02.wav"]},
        )
        create_protools_delivery.return_value = {
            "processed_count": 2,
            "track_count": 1,
            "families": [
                {"family": "A144_Boom", "track": "PFX 01", "count": 2}
            ],
            "session_path": r"Y:\exports\A144_PFX\A144_PFX.ptx",
            "archive_path": r"Y:\exports\A144_PFX.zip",
        }

        status, archive_path = app_local.download_processed_zip(
            None,
            "A144_PFX",
        )

        download_processed_files.assert_called_once_with(progress=ANY)
        create_protools_delivery.assert_called_once_with(
            processed_dir=app_local.drive_auth.PROCESSED_DIR,
            exports_dir=app_local.drive_auth.EXPORTS_DIR,
            template_path=None,
            session_name="A144_PFX",
        )
        self.assertEqual(archive_path, r"Y:\exports\A144_PFX.zip")
        self.assertIn("2 fichiers", status)
        self.assertIn("Session Pro Tools créée", status)
        self.assertIn("A144_Boom → PFX 01", status)

    @patch("app_local.protools_export.create_protools_delivery")
    @patch("app_local.drive_auth.download_processed_files")
    def test_empty_drive_does_not_call_builder(
        self,
        download_processed_files,
        create_protools_delivery,
    ):
        download_processed_files.return_value = (
            [],
            {"count": 0, "names": []},
        )

        with self.assertRaises(app_local.gr.Error):
            app_local.download_processed_zip(None, "")

        create_protools_delivery.assert_not_called()

    @patch("app_local.protools_export.create_protools_delivery")
    @patch("app_local.drive_auth.download_processed_files")
    def test_builder_error_keeps_downloaded_wav_message(
        self,
        download_processed_files,
        create_protools_delivery,
    ):
        download_processed_files.return_value = (
            [Path("Boom_01.wav")],
            {"count": 1, "names": ["Boom_01.wav"]},
        )
        create_protools_delivery.side_effect = RuntimeError("template incompatible")

        status, archive_path = app_local.download_processed_zip(None, "")

        self.assertIsNone(archive_path)
        self.assertIn("template incompatible", status)
        self.assertIn("WAV déjà téléchargés restent", status)
        self.assertIn("Aucune livraison Pro Tools incomplète", status)


if __name__ == "__main__":
    unittest.main()
