import ast
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import drive_auth


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
            self.handle.write(b"WAV")
            self.done = True
        return None, True


class DriveProgressTests(unittest.TestCase):
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
            self.assertEqual(paths[0].read_bytes(), b"WAV")
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


if __name__ == "__main__":
    unittest.main()
