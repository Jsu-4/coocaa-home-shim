#!/usr/bin/env python3
"""List, verify and prepare TV backup files locally; never executes ADB."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import tempfile
import urllib.request
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEVICE = ROOT / 'devices' / 'skyworth-9s61-g650'
MAX_ARCHIVE = 64 * 1024 * 1024
MAX_MEMBER = 16 * 1024 * 1024


def digest(data):
    return hashlib.sha256(data).hexdigest()


def load_catalog():
    catalog = json.loads((DEVICE / 'backups.json').read_text(encoding='utf-8'))
    if catalog['schema_version'] != 1:
        raise ValueError('Unsupported backup catalog schema')
    return catalog


def get_profile(catalog, profile_id):
    for profile in catalog['profiles']:
        if profile['id'] == profile_id:
            return profile
    raise ValueError('Unknown profile: ' + profile_id)


def safe_member(info):
    path = PurePosixPath(info.filename)
    return (not path.is_absolute() and '..' not in path.parts
            and '\\' not in info.filename and not info.is_dir()
            and path.as_posix() == info.filename
            and stat.S_IFMT(info.external_attr >> 16) != stat.S_IFLNK
            and info.file_size <= MAX_MEMBER)


def verify_archive(archive, profile, device_dir=DEVICE):
    archive = Path(archive)
    if archive.stat().st_size > MAX_ARCHIVE:
        raise ValueError('Archive exceeds local preparation limit')
    data = archive.read_bytes()
    if len(data) != profile['bytes'] or digest(data) != profile['sha256']:
        raise ValueError('Archive size or SHA-256 does not match the Git catalog')
    with zipfile.ZipFile(archive) as bundle:
        entries = bundle.infolist()
        names = [entry.filename for entry in entries]
        if len(set(names)) != len(names):
            raise ValueError('Duplicate ZIP members')
        if set(names) != set(profile['members']):
            raise ValueError('ZIP member list does not match the Git catalog')
        if sum(entry.file_size for entry in entries) > MAX_ARCHIVE:
            raise ValueError('Expanded backup exceeds local preparation limit')
        if not all(safe_member(entry) for entry in entries):
            raise ValueError('Unsafe ZIP path, link or member size')
        files = {name: bundle.read(name) for name in names}
    for name, expected in profile['members'].items():
        if digest(files[name]) != expected:
            raise ValueError('ZIP member SHA-256 mismatch: ' + name)
    config = json.loads(files['layout/config.json'])
    expected_config = json.loads((device_dir / profile['config']).read_text(encoding='utf-8'))
    if config != expected_config:
        raise ValueError('Layout config does not match the tracked profile')
    if not files.get('launcher.apk'):
        raise ValueError('Missing launcher APK')
    return files


def download(profile, cache_dir):
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    destination = cache_dir / profile['asset_name']
    if destination.exists():
        return destination  # verify_archive checks it before use; never overwrite a bad cached file.
    prefix = 'https://github.com/Jsu-4/coocaa-home-shim/releases/download/'
    if not profile['download_url'].startswith(prefix):
        raise ValueError('Unexpected download origin')
    request = urllib.request.Request(profile['download_url'], headers={'User-Agent': 'coocaa-tv-backup'})
    temporary = None
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            with tempfile.NamedTemporaryFile(dir=cache_dir, suffix='.part', delete=False) as output:
                temporary = Path(output.name)
                size = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_ARCHIVE:
                        raise ValueError('Download exceeds local preparation limit')
                    output.write(chunk)
        if temporary.stat().st_size != profile['bytes'] or digest(temporary.read_bytes()) != profile['sha256']:
            raise ValueError('Downloaded archive does not match the Git catalog')
        if destination.exists():
            raise ValueError('Cache destination appeared during download; retry verification')
        temporary.rename(destination)
        temporary = None
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def prepare(files, output):
    output = Path(output)
    # No reuse of an existing destination: preserve prior prepared files and user edits.
    output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
    return output.resolve()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['list', 'verify', 'prepare'])
    parser.add_argument('profile', nargs='?')
    parser.add_argument('--archive', type=Path, help='Use a local ZIP instead of downloading')
    parser.add_argument('--output', type=Path, help='New extraction directory (prepare only)')
    args = parser.parse_args(argv)
    catalog = load_catalog()
    if args.command == 'list':
        for profile in catalog['profiles']:
            marker = ' [recommended]' if profile['id'] == catalog['recommended_profile'] else ''
            print(profile['id'] + marker + ': ' + profile['title'])
        return 0
    if not args.profile:
        parser.error('verify and prepare require a profile ID')
    if args.output and args.command != 'prepare':
        parser.error('--output is only valid with prepare')
    profile = get_profile(catalog, args.profile)
    archive = args.archive or download(profile, ROOT / '.local' / 'tv-backups')
    files = verify_archive(archive, profile)
    print('Verified: ' + profile['id'] + ' (' + profile['sha256'] + ')')
    if args.command == 'prepare':
        if args.output:
            output = args.output
        else:
            parent = ROOT / '.local' / 'prepared'
            parent.mkdir(parents=True, exist_ok=True)
            # Reserve a unique name; prepare itself creates the directory exclusively.
            with tempfile.TemporaryDirectory(prefix=profile['id'] + '-', dir=parent) as reserved:
                output = Path(reserved)
        print('Prepared: ' + str(prepare(files, output)))
        print('No TV was modified. Follow devices/skyworth-9s61-g650/README.md to restore.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (ValueError, OSError, KeyError, zipfile.BadZipFile) as error:
        print('ERROR: ' + str(error), file=sys.stderr)
        sys.exit(1)
