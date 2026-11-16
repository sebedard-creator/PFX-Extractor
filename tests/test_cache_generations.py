"""In-memory Drive only: no real cloud deletion, including for safety cases."""
import hashlib
import json
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import drive_auth
from tests.test_drive_auth import ExplosiveProgress


FOLDER = 'application/vnd.google-apps.folder'


class MemoryDrive:
    def __init__(self):
        self.items, self.media, self.deleted = {}, {}, []
        self.fail = set()
        self.list_hook = None
        self.add('raw', '1_Bruts_vers_Colab', 'parent', FOLDER)
        self.add('out', '2_Environnements_IA', 'parent', FOLDER)

    def add(self, ident, name, parent, mime='audio/wav', data=None):
        self.items[ident] = dict(id=ident, name=name, parents=[parent], mimeType=mime)
        if data is not None:
            raw = json.dumps(data).encode()
            self.media[ident] = raw
            self.items[ident].update(size=str(len(raw)), md5Checksum=hashlib.md5(raw).hexdigest())

    def manifest(self, ident, parent, run_id='test', status='complete'):
        self.add(ident, drive_auth.DELIVERY_MANIFEST, parent, 'application/json',
                 dict(status=status, run_id=run_id, run_folder='run_'+run_id))

    def files(self):
        return self

    def list(self, **kwargs):
        parent = re.search(r"'([^']+)' in parents", kwargs['q']).group(1)
        def execute():
            if self.list_hook:
                self.list_hook(parent)
            rows = [dict(item) for item in self.items.values() if parent in item['parents']]
            if "mimeType!='application/vnd.google-apps.folder'" in kwargs['q']:
                rows = [item for item in rows if item['mimeType'] != FOLDER]
            return {'files': rows}
        return SimpleNamespace(execute=execute)

    def get_media(self, fileId):
        return SimpleNamespace(execute=lambda: self.media[fileId])

    def delete(self, fileId, **kwargs):
        def execute():
            if fileId in self.fail:
                raise RuntimeError('injected delete failure')
            assert not any(fileId in item['parents'] for item in self.items.values()), 'Nonempty folder deletion forbidden'
            self.deleted.append(fileId)
            del self.items[fileId]
        return SimpleNamespace(execute=execute)


class CacheGenerationTests(unittest.TestCase):
    def run_cleanup(self, service, progress=None, all_caches=False):
        with patch.object(drive_auth, 'authenticate_drive', return_value=service), \
                patch.object(drive_auth, 'get_pfx_folders', return_value=('parent', 'raw', 'out')):
            if all_caches:
                return drive_auth.clear_all_cache(progress=progress)
            return drive_auth.clear_drive_cache(progress=progress)

    def populated(self, status='complete', root_pointer=True):
        service = MemoryDrive()
        service.add('raw1', 'source.wav', 'raw')
        service.add('run', 'run_test', 'out', FOLDER)
        service.manifest('run-manifest', 'run', status=status)
        service.add('wav1', 'scene_01_PFX_Ready.wav', 'run')
        service.add('wav2', 'scene_02_PFX_Ready.wav', 'run')
        if root_pointer:
            service.manifest('pointer', 'out', status=status)
        return service

    def test_deletes_generated_files_and_empty_run_preserves_roots_models_and_unrelated(self):
        service = self.populated()
        service.add('models', '0_Model_Cache', 'parent', FOLDER)
        service.add('model', 'weights.ckpt', 'models')
        service.add('notebook', 'backend.ipynb', 'parent')
        service.add('other', 'user_archive', 'out', FOLDER)
        service.add('keep', 'keep.wav', 'other')
        progress = ExplosiveProgress()
        result = self.run_cleanup(service, progress)
        self.assertEqual(result, dict(deleted=5, folders_deleted=1, failed=[]))
        self.assertEqual(set(service.deleted), {'raw1','run-manifest','wav1','wav2','run','pointer'})
        self.assertTrue({'raw','out','models','model','notebook','other','keep'}.issubset(service.items))
        self.assertLess(service.deleted.index('wav2'), service.deleted.index('run-manifest'))
        self.assertLess(service.deleted.index('run'), service.deleted.index('pointer'))
        fractions = [value for value, _ in progress.calls]
        self.assertEqual(fractions, sorted(fractions))
        self.assertEqual(fractions[-1], 1)
        self.assertTrue(any('run_test' in desc for _, desc in progress.calls))

    def test_running_root_or_generation_blocks_all_deletes_and_local_cleanup(self):
        for pointer in (True, False):
            with self.subTest(pointer=pointer):
                service = self.populated(status='running', root_pointer=pointer)
                with patch.object(drive_auth, 'clear_local_cache') as local:
                    with self.assertRaisesRegex(RuntimeError, 'running'):
                        self.run_cleanup(service, all_caches=True)
                    local.assert_not_called()
                self.assertEqual(service.deleted, [])

    def test_corrupt_unknown_or_mismatched_manifest_fails_before_any_deletion(self):
        for fault in ('corrupt', 'unknown', 'mismatch'):
            with self.subTest(fault=fault):
                service = self.populated(root_pointer=False)
                if fault == 'corrupt':
                    service.media['run-manifest'] = b'not json'
                else:
                    data = dict(status='unknown' if fault=='unknown' else 'complete',
                                run_id='other' if fault=='mismatch' else 'test', run_folder='run_test')
                    service.manifest('run-manifest', 'run')
                    service.media['run-manifest'] = json.dumps(data).encode()
                with self.assertRaises(RuntimeError):
                    self.run_cleanup(service)
                self.assertEqual(service.deleted, [])

    def test_new_run_or_changed_pointer_detected_before_deleting_inputs(self):
        for fault in ('pointer', 'new-run'):
            with self.subTest(fault=fault):
                service = self.populated()
                visits = []
                def change(parent):
                    if parent == 'out':
                        visits.append(parent)
                        if len(visits) == 2:
                            if fault == 'pointer':
                                service.manifest('pointer','out',run_id='new',status='running')
                            else:
                                service.add('new-run','run_new','out',FOLDER)
                service.list_hook = change
                with self.assertRaisesRegex(RuntimeError, 'changé'):
                    self.run_cleanup(service)
                self.assertEqual(service.deleted, [])

    def test_failed_wav_retains_manifest_and_folder_then_retry_succeeds(self):
        service = self.populated(root_pointer=False)
        service.fail.add('wav1')
        result = self.run_cleanup(service)
        self.assertEqual(result['folders_deleted'], 0)
        self.assertEqual(len(result['failed']), 1)
        self.assertTrue({'run', 'run-manifest', 'wav1'}.issubset(service.items))
        self.assertNotIn('wav2', service.items)
        service.fail.clear()
        retry = self.run_cleanup(service)
        self.assertEqual(retry, dict(deleted=2, folders_deleted=1, failed=[]))

    def test_unexpected_subfolder_or_file_not_followed_or_recursively_deleted(self):
        service = self.populated(root_pointer=False)
        service.add('nested', 'unrelated', 'run', FOLDER)
        service.add('private', 'keep.wav', 'nested')
        service.add('notes', 'keep.txt', 'run')
        result = self.run_cleanup(service)
        self.assertEqual(result['folders_deleted'], 0)
        self.assertTrue(result['failed'])
        self.assertTrue({'run','run-manifest','nested','private','notes'}.issubset(service.items))

    def test_missing_manifest_generation_is_reported_preserved(self):
        service = MemoryDrive()
        service.add('run', 'run_unidentified', 'out', FOLDER)
        service.add('wav', 'keep.wav', 'run')
        result = self.run_cleanup(service)
        self.assertEqual(result['deleted'], 0)
        self.assertIn('conservé', result['failed'][0])
        self.assertEqual(service.deleted, [])

    def test_empty_and_explicitly_failed_generations_can_be_removed(self):
        service = self.populated(status='failed', root_pointer=False)
        service.add('empty', 'run_empty', 'out', FOLDER)
        result = self.run_cleanup(service)
        self.assertEqual(result['folders_deleted'], 2)
        self.assertEqual(result['failed'], [])

    def test_inventory_paginates_including_folders(self):
        from unittest.mock import Mock
        service = Mock()
        service.files.return_value.list.return_value.execute.side_effect = [
            {'files':[dict(id='one')], 'nextPageToken':'next'}, {'files':[dict(id='two')]}]
        result = drive_auth._list_cache_children(service, 'out')
        self.assertEqual(result, [dict(id='one'), dict(id='two')])
        calls = service.files.return_value.list.call_args_list
        self.assertEqual(calls[1].kwargs['pageToken'], 'next')
        self.assertNotIn("mimeType!=", calls[0].kwargs['q'])


if __name__ == '__main__':
    unittest.main()
