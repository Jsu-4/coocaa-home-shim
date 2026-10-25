import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile


SPEC = importlib.util.spec_from_file_location('tv_backup', Path(__file__).resolve().parents[1] / 'tools/tv_backup.py')
backup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(backup)


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'config.json').write_text('{"wallpaper": true}')

    def bundle(self, additions=None):
        files = {'layout/config.json': b'{"wallpaper": true}', 'launcher.apk': b'test-apk'}
        files.update(additions or {})
        path = self.root / 'backup.zip'
        with zipfile.ZipFile(path, 'w') as archive:
            for name, data in files.items():
                archive.writestr(name, data)
        data = path.read_bytes()
        profile = {'bytes': len(data), 'sha256': backup.digest(data), 'config': 'config.json',
                   'members': {name: backup.digest(data) for name, data in files.items()}}
        return path, profile

    def test_verified_bundle_can_be_prepared_without_adb(self):
        path, profile = self.bundle()
        files = backup.verify_archive(path, profile, self.root)
        destination = backup.prepare(files, self.root / 'prepared')
        self.assertEqual((destination / 'launcher.apk').read_bytes(), b'test-apk')

    def test_archive_tampering_is_rejected(self):
        path, profile = self.bundle()
        path.write_bytes(path.read_bytes() + b'tampered')
        with self.assertRaisesRegex(ValueError, 'SHA-256'):
            backup.verify_archive(path, profile, self.root)

    def test_member_digest_mismatch_is_rejected(self):
        path, profile = self.bundle()
        profile['members']['launcher.apk'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'member SHA-256'):
            backup.verify_archive(path, profile, self.root)

    def test_traversal_is_rejected_even_with_matching_hashes(self):
        path, profile = self.bundle({'../escape': b'bad'})
        with self.assertRaisesRegex(ValueError, 'Unsafe ZIP'):
            backup.verify_archive(path, profile, self.root)
        self.assertFalse((self.root.parent / 'escape').exists())

    def test_config_mismatch_is_rejected(self):
        path, profile = self.bundle()
        (self.root / 'config.json').write_text('{"wallpaper": false}')
        with self.assertRaisesRegex(ValueError, 'tracked profile'):
            backup.verify_archive(path, profile, self.root)

    def test_existing_destination_is_preserved(self):
        target = self.root / 'prepared'
        target.mkdir()
        (target / 'user-file').write_text('keep')
        with self.assertRaises(FileExistsError):
            backup.prepare({'launcher.apk': b'new'}, target)
        self.assertEqual((target / 'user-file').read_text(), 'keep')

    def test_unknown_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Unknown profile'):
            backup.get_profile({'profiles': []}, 'unknown')

    def test_catalog_has_four_profiles_and_valid_recommendation(self):
        catalog = backup.load_catalog()
        self.assertEqual(len(catalog['profiles']), 4)
        selected = backup.get_profile(catalog, catalog['recommended_profile'])
        self.assertTrue(selected['recommended'])


if __name__ == '__main__':
    unittest.main()
