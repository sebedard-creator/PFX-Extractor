"""Regression of signed-64-bit UMID collisions, using synthetic BWF only."""
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import Mock, patch

import delivery_contract as contract
import protools_export
from tests.wav_fixtures import wave_bytes


class UmidTests(unittest.TestCase):
    def test_signed_overflow_collision_is_repaired_without_touching_audio_or_tc(self):
        native = [contract.RENDER_UMID_PREFIX + bytes.fromhex(value) + bytes(32)
                  for value in ('94aaaaaaaaaaaaaaadbbbbbbbbbbbbbb', '95ccccccccccccccbedddddddddddddd')]
        def signed_ffmpeg_bug(value):
            return b''.join(min(int.from_bytes(value[i:i+8], 'big'), 0x7fffffffffffffff)
                            .to_bytes(8, 'big') for i in range(0, 64, 8))
        self.assertNotEqual(native[0], native[1])
        self.assertEqual(signed_ffmpeg_bug(native[0]), signed_ffmpeg_bug(native[1]))
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            before = {}
            for i in range(2):
                path = Path(directory) / f'BOOM_{i}.wav'
                path.write_bytes(wave_bytes(48000 + i * 2002))
                offset, _ = contract.wave_chunk_extent(path, b'bext')
                data = bytearray(path.read_bytes())
                data[offset+348:offset+412] = signed_ffmpeg_bug(native[i])
                path.write_bytes(data)
                before[path] = (bytes(data), offset, contract.wave_audio_sha256(path), contract.inspect_delivery_wave(path))
                paths.append(path)
            with self.assertRaisesRegex(ValueError, 'UMID dupliqué'):
                contract.verify_unique_wave_umids(paths)
            used = [value.hex() for value in native]
            for path in paths:
                new = contract.assign_render_umid(path, forbidden=used)
                used.append(new)
                old, offset, audio_hash, geometry = before[path]
                actual = path.read_bytes()
                self.assertEqual(actual[:offset+348], old[:offset+348])
                self.assertEqual(actual[offset+412:], old[offset+412:])
                self.assertEqual(contract.wave_audio_sha256(path), audio_hash)
                self.assertEqual(contract.inspect_delivery_wave(path), geometry)
            contract.verify_unique_wave_umids(paths, forbidden=[v.hex() for v in native])

    def test_retry_regenerates_identity_even_for_same_audio(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'BOOM.wav'
            path.write_bytes(wave_bytes())
            first = contract.assign_render_umid(path)
            second = contract.assign_render_umid(path, forbidden=[first])
            self.assertNotEqual(first, second)

    def test_rng_collision_exhaustion_fails_without_rewriting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'BOOM.wav'
            path.write_bytes(wave_bytes())
            before = path.read_bytes()
            material = bytes(range(16))
            existing = (contract.RENDER_UMID_PREFIX + material + bytes(32)).hex()
            with patch.object(contract.uuid, 'uuid4', return_value=Mock(bytes=material)):
                with self.assertRaisesRegex(RuntimeError, 'Impossible'):
                    contract.assign_render_umid(path, forbidden=[existing])
            self.assertEqual(path.read_bytes(), before)

    def test_protocol2_identity_required_and_matches_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'BOOM_PFX_Ready.wav'
            path.write_bytes(wave_bytes())
            entry = dict(contract.inspect_delivery_wave(path), name=path.name, role='BOOM',
                         umid=contract.assign_render_umid(path), sha256=contract.sha256_file(path))
            manifest = dict(protocol=2, status='complete', run_id='test', run_folder='run_test', outputs=[entry])
            contract.validate_delivery_manifest(manifest)
            contract.verify_delivery_file(path, entry)
            manifest['outputs'].append(dict(entry, name='other_BOOM_PFX_Ready.wav'))
            with self.assertRaisesRegex(ValueError, 'UMID dupliqué'):
                contract.validate_delivery_manifest(manifest)
            manifest['outputs'].pop()
            manifest['inputs'] = [{'umid': entry['umid']}]
            with self.assertRaisesRegex(ValueError, 'réutilisé'):
                contract.validate_delivery_manifest(manifest)
            manifest['inputs'] = []
            wrong = dict(entry, umid=entry['umid'][:32] + '1' * 32 + '0' * 64)
            with self.assertRaisesRegex(ValueError, 'UMID différent'):
                contract.verify_delivery_file(path, wrong)
            del entry['umid']
            with self.assertRaisesRegex(ValueError, 'UMID de rendu invalide'):
                contract.validate_delivery_manifest(manifest)

    def test_legacy_delivery_collision_stops_before_api(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for n in (1, 2):
                (root / f'A_Boom-Gain_{n}_PFX_Ready.wav').write_bytes(wave_bytes())
            builder = Mock(side_effect=AssertionError('API must not run'))
            with self.assertRaisesRegex(ValueError, 'UMID dupliqué'):
                protools_export.create_protools_delivery(root, root / 'exports', builder=builder)
            builder.assert_not_called()


if __name__ == '__main__':
    unittest.main()
