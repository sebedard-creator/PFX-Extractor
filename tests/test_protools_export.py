import tempfile
import struct
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import protools_export
from tests.wav_fixtures import wave_bytes


class ApiResolutionTests(unittest.TestCase):
    def module(self, version):
        return SimpleNamespace(__version__=version, __file__='installed/pt_api.py',
                               build_audio_session=Mock())

    def test_installed_release_is_used_and_logged(self):
        module = self.module('1.6.2')
        with patch.dict(protools_export.os.environ, {}, clear=True), \
             patch.object(protools_export.importlib, 'import_module', return_value=module), \
             self.assertLogs('pfx_extractor', level='INFO') as logs:
            self.assertIs(protools_export.resolve_pt_api_builder(), module.build_audio_session)
        self.assertIn('pt_api 1.6.2', logs.output[0])
        self.assertIn('installed/pt_api.py', logs.output[0])

    def test_old_installed_api_does_not_silently_fall_back(self):
        with patch.dict(protools_export.os.environ, {}, clear=True), \
             patch.object(protools_export.importlib, 'import_module', return_value=self.module('1.6.1')), \
             patch.object(protools_export, '_load_pt_api_from_file') as fallback:
            with self.assertRaisesRegex(RuntimeError, '1.6.2.*1.6.1'):
                protools_export.resolve_pt_api_builder()
            fallback.assert_not_called()

    def test_explicit_local_override_must_also_meet_version_requirement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'pt_api.py'
            path.write_text("__version__ = '1.6.1'\ndef build_audio_session(*args): pass\n")
            with patch.dict(protools_export.os.environ, {'PT_API_PATH': str(path)}):
                with self.assertRaisesRegex(RuntimeError, '1.6.2.*1.6.1'):
                    protools_export.resolve_pt_api_builder()

    def test_missing_version_and_builder_are_explicit_errors(self):
        with self.assertRaisesRegex(RuntimeError, 'inconnue'):
            protools_export._validated_pt_api_builder(self.module(None))
        module = self.module('1.6.2')
        module.build_audio_session = None
        with self.assertRaisesRegex(RuntimeError, 'build_audio_session'):
            protools_export._validated_pt_api_builder(module)

    def test_later_stable_releases_are_accepted_and_older_ones_rejected(self):
        for version in ('1.6.2', '1.6.3', '1.7.0', '2.0.0'):
            with self.subTest(version=version):
                module = self.module(version)
                self.assertIs(protools_export._validated_pt_api_builder(module), module.build_audio_session)
        for version in ('1.3.8', '1.6.0', '1.6.1'):
            with self.subTest(version=version), self.assertRaisesRegex(RuntimeError, '1.6.2.*requis'):
                protools_export._validated_pt_api_builder(self.module(version))


class ApiRealIntegrationTests(unittest.TestCase):
    @unittest.skipUnless(protools_export.DEFAULT_TEMPLATE_PATH.is_file(), 'local PTX template required')
    def test_131_alphabetical_inputs_have_chronological_serialized_events(self):
        try:
            builder = protools_export.resolve_pt_api_builder()
        except RuntimeError as exc:
            self.skipTest(str(exc))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            processed = root / 'processed'
            processed.mkdir()
            for sequence in range(1, 132):
                name = f'Scene_Boom-Gain_{sequence:02d}_PFX_Ready.wav'
                (processed / name).write_bytes(wave_bytes(
                    n=4800, tc=1728000000 + (sequence - 1) * 4800, identity=name))
            result = protools_export.create_protools_delivery(
                processed, root / 'exports', session_name='Chronological_131', builder=builder)
            session = builder.__globals__['ProToolsSession'](result['session_path'])
            block_type = builder.__globals__['PTBlock']
            clips = session.get_timeline_clips(include_fades=False)
            self.assertEqual(len(clips), 131)
            self.assertEqual(max(c['end_samples'] for c in clips), 1728000000 + 131 * 4800)
            count = 0
            for playlist, _, _ in session._validated_main_playlists():
                starts = []
                for event in playlist.items:
                    if isinstance(event, block_type) and event.content_type == 0x1050:
                        payload = next(b for b in event.items
                                       if isinstance(b, block_type) and b.content_type == 0x104f)
                        starts.append(struct.unpack_from('<Q', payload.items[0], 7)[0])
                self.assertEqual(starts, sorted(starts))
                count += len(starts)
            self.assertEqual(count, 131)


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
                (processed / name).write_bytes(wave_bytes(identity=name))

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
            (processed / "A144_Boom-Gain_01_PFX_Ready.wav").write_bytes(wave_bytes())

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
            source.write_bytes(wave_bytes())
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
