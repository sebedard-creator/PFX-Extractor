import tempfile
import unittest
import zipfile
from pathlib import Path

import protools_export


class ProcessedManifestTests(unittest.TestCase):
    def test_alphabetical_order_and_family_track_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            names = [
                "A144_Lav-Gain_02_PFX_Ready.wav",
                "A144_Boom-Gain_02_PFX_Ready.wav",
                "A144_Boom-Gain_01_PFX_Ready.wav",
                "A144_Lav-Gain_01_PFX_Ready.wav",
            ]
            for name in names:
                (root / name).write_bytes(b"wav")

            descriptors, families = protools_export.collect_processed_manifest(root)
            self.assertEqual(
                [item["audio_path"].name for item in descriptors],
                sorted(names, key=lambda name: (name.casefold(), name)),
            )
            self.assertEqual(
                families,
                [
                    {"family": "A144_Boom", "track": "PFX 01", "count": 2},
                    {"family": "A144_Lav", "track": "PFX 02", "count": 2},
                ],
            )
            self.assertEqual(
                [item["track_name"] for item in descriptors],
                ["PFX 01", "PFX 01", "PFX 02", "PFX 02"],
            )

    def test_malformed_filename_and_third_family_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "unexpected.wav").write_bytes(b"wav")
            with self.assertRaisesRegex(ValueError, "Filename traité non reconnu"):
                protools_export.collect_processed_manifest(root)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for family in ("Boom", "Lav", "Plant"):
                (root / f"A144_{family}-Gain_01_PFX_Ready.wav").write_bytes(b"wav")
            with self.assertRaisesRegex(ValueError, "3 familles"):
                protools_export.collect_processed_manifest(root)

    def test_session_name_suggestion_and_validation(self):
        families = [{"family": "A144_Boom", "track": "PFX 01", "count": 62}]
        self.assertEqual(protools_export.suggest_session_name(families), "A144_PFX")
        self.assertEqual(
            protools_export.sanitize_session_name("Scene_001.ptx"),
            "Scene_001",
        )
        with self.assertRaises(ValueError):
            protools_export.sanitize_session_name("../unsafe")
        with self.assertRaises(TypeError):
            protools_export.sanitize_session_name(144)


class ProToolsDeliveryTests(unittest.TestCase):
    def test_delivery_contains_ptx_and_audio_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / "processed"
            exports = root / "exports"
            processed.mkdir()
            template = root / "template.ptx"
            template.write_bytes(b"template")
            source_names = [
                "A144_Boom-Gain_01_PFX_Ready.wav",
                "A144_Boom-Gain_02_PFX_Ready.wav",
            ]
            for name in source_names:
                (processed / name).write_bytes(name.encode("utf-8"))

            def fake_builder(template_path, descriptors, output_dir, session_name=None):
                self.assertEqual(Path(template_path), template)
                output_dir = Path(output_dir)
                audio_dir = output_dir / "Audio Files"
                audio_dir.mkdir(parents=True)
                session_path = output_dir / f"{session_name}.ptx"
                session_path.write_bytes(b"ptx")
                clips = []
                for descriptor in descriptors:
                    source = Path(descriptor["audio_path"])
                    (audio_dir / source.name).write_bytes(source.read_bytes())
                    clips.append({"physical_filename": source.name})
                return {
                    "session_path": str(session_path),
                    "audio_files_directory": str(audio_dir),
                    "track_count": 1,
                    "tracks": ["PFX 01"],
                    "clips": clips,
                }

            result = protools_export.create_protools_delivery(
                processed,
                exports,
                template,
                "A144_PFX",
                builder=fake_builder,
            )
            self.assertEqual(result["processed_count"], 2)
            archive_path = Path(result["archive_path"])
            self.assertTrue(archive_path.is_file())
            with zipfile.ZipFile(archive_path) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {
                        "A144_PFX/A144_PFX.ptx",
                        "A144_PFX/Audio Files/A144_Boom-Gain_01_PFX_Ready.wav",
                        "A144_PFX/Audio Files/A144_Boom-Gain_02_PFX_Ready.wav",
                    },
                )

    def test_builder_failure_removes_partial_delivery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / "processed"
            exports = root / "exports"
            processed.mkdir()
            template = root / "template.ptx"
            template.write_bytes(b"template")
            (processed / "A144_Boom-Gain_01_PFX_Ready.wav").write_bytes(b"wav")

            def failing_builder(template_path, descriptors, output_dir, session_name=None):
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True)
                (output_dir / "partial.ptx").write_bytes(b"partial")
                raise RuntimeError("builder failed")

            with self.assertRaisesRegex(RuntimeError, "builder failed"):
                protools_export.create_protools_delivery(
                    processed,
                    exports,
                    template,
                    "A144_PFX",
                    builder=failing_builder,
                )
            self.assertFalse((exports / "A144_PFX").exists())
            self.assertFalse((exports / "A144_PFX.zip").exists())

    def test_existing_archive_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / "processed"
            exports = root / "exports"
            processed.mkdir()
            exports.mkdir()
            template = root / "template.ptx"
            template.write_bytes(b"template")
            source = processed / "A144_Boom-Gain_01_PFX_Ready.wav"
            source.write_bytes(b"wav")
            original_archive = exports / "A144_PFX.zip"
            original_archive.write_bytes(b"existing")

            def fake_builder(template_path, descriptors, output_dir, session_name=None):
                output_dir = Path(output_dir)
                audio_dir = output_dir / "Audio Files"
                audio_dir.mkdir(parents=True)
                (audio_dir / source.name).write_bytes(source.read_bytes())
                session_path = output_dir / f"{session_name}.ptx"
                session_path.write_bytes(b"ptx")
                return {
                    "session_path": str(session_path),
                    "audio_files_directory": str(audio_dir),
                    "track_count": 1,
                    "tracks": ["PFX 01"],
                    "clips": [{"physical_filename": source.name}],
                }

            result = protools_export.create_protools_delivery(
                processed,
                exports,
                template,
                "A144_PFX",
                builder=fake_builder,
            )
            self.assertEqual(
                Path(result["session_directory"]).name,
                "A144_PFX_001",
            )
            self.assertEqual(original_archive.read_bytes(), b"existing")
            self.assertTrue((exports / "A144_PFX_001.zip").is_file())


if __name__ == "__main__":
    unittest.main()
