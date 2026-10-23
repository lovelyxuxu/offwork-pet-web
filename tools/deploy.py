"""Deploy the committed portal through SSH; password arrives only on stdin.

The existing desktop service, its database and signed downloads are untouched.
Each source release has its own virtual environment. Content is persistent.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import uuid

import paramiko

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='106.54.27.8')
    parser.add_argument('--username', default='ubuntu')
    parser.add_argument('--packs', type=Path, required=True)
    args = parser.parse_args()
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], cwd=ROOT).strip():
        raise RuntimeError('Commit source changes before deployment.')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    packs = sorted(args.packs.resolve().glob('*.petpack'))
    if not packs:
        raise RuntimeError('No character packages found.')
    password = sys.stdin.readline().rstrip('\r\n')
    ssh = paramiko.SSHClient()
    ssh.load_system_host_keys()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(args.host, username=args.username, password=password, timeout=15,
                allow_agent=False, look_for_keys=False)
    password = None
    ssh.get_transport().set_keepalive(15)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-' + uuid.uuid4().hex[:6]
    staging = '/tmp/offwork-web-' + stamp
    base = '/srv/offwork-pet-web'
    release = base + '/releases/' + stamp + '-' + revision[:12]
    backup = '/var/backups/offwork-pet-web/' + stamp
    data = '/var/lib/offwork-pet-web'
    quote = shlex.quote
    switched = False
    previous = ''
    had_service = False

    def run(label, command, timeout=60):
        print(label, flush=True)
        _, output, errors = ssh.exec_command(command, timeout=timeout)
        result, error = output.read().decode(), errors.read().decode()
        code = output.channel.recv_exit_status()
        if result.strip():
            print(result.strip(), flush=True)
        if error.strip():
            print(error.strip(), file=sys.stderr, flush=True)
        if code:
            raise RuntimeError(f'{label} failed (exit {code}).')
        return result.strip()

    try:
        previous = run('Read current release', 'readlink /srv/offwork-pet-web/current || true')
        had_service = run('Read existing unit', 'if test -f /etc/systemd/system/offwork-pet-web.service; then echo yes; fi') == 'yes'
        run('Create restricted upload staging', 'mkdir -m 700 ' + quote(staging))
        with tempfile.TemporaryDirectory() as temporary:
            archive = Path(temporary) / 'source.tar.gz'
            subprocess.run(['git', 'archive', '--format=tar.gz', '--output=' + str(archive), revision], cwd=ROOT, check=True)
            artifacts = [(archive, 'source.tar.gz'), *[(path, path.name) for path in packs]]
            with ssh.open_sftp() as sftp:
                sftp.get_channel().settimeout(45)
                for path, name in artifacts:
                    print('Upload ' + name, flush=True)
                    sftp.put(str(path), staging + '/' + name)
                    with path.open('rb') as source:
                        digest = hashlib.file_digest(source, 'sha256').hexdigest()
                    remote_digest = run('Verify upload ' + name, 'sha256sum ' + quote(staging + '/' + name)).split()[0]
                    if remote_digest != digest:
                        raise RuntimeError('Upload hash mismatch: ' + name)
        run('Back up Nginx and existing unit',
            f'sudo -n install -d -m 700 {quote(backup)} && '
            f'sudo -n tar -czf {quote(backup + "/nginx.tar.gz")} -C / etc/nginx && '
            f'if test -f /etc/systemd/system/offwork-pet-web.service; then sudo -n cp -a /etc/systemd/system/offwork-pet-web.service {quote(backup + "/offwork-pet-web.service")}; fi')
        content_backup = '''import pathlib, sqlite3, subprocess, sys
data, backup = map(pathlib.Path, sys.argv[1:])
if data.exists():
    subprocess.run(['tar','--exclude=catalog.sqlite3*','-czf',str(backup/'content.tar.gz'),'-C',str(data),'.'], check=True)
    if (data/'catalog.sqlite3').exists():
        with sqlite3.connect(data/'catalog.sqlite3') as source, sqlite3.connect(backup/'catalog.sqlite3') as target:
            source.backup(target)
'''
        run('Back up existing catalog if present', 'sudo -n python3 -c ' + quote(content_backup) + ' ' + quote(data) + ' ' + quote(backup))
        run('Prepare release and persistent content',
            f'if ! id offwork-web >/dev/null 2>&1; then sudo -n useradd --system --home /srv/offwork-pet-web --shell /usr/sbin/nologin offwork-web; fi; '
            f'sudo -n install -d -m 755 {quote(release)} && '
            f'sudo -n install -d -o offwork-web -g offwork-web -m 755 {quote(data)} && '
            f'sudo -n tar -xzf {quote(staging + "/source.tar.gz")} -C {quote(release)} && '
            f'sudo -n python3 -m venv --without-pip {quote(release + "/.venv")}')
        python = quote(release + '/.venv/bin/python')
        run('Install isolated website dependencies',
            f'sudo -n python3 -m pip --python {python} install --disable-pip-version-check -r {quote(release + "/requirements-dev.txt")}', 240)
        run('Run tests in the server runtime',
            f'cd {quote(release)} && sudo -n {python} -m unittest discover -s tests -v')
        for pack in packs:
            run('Import character ' + pack.name,
                f'cd {quote(release)} && sudo -n {python} -m portal.manage --data-dir {quote(data)} import-pack {quote(staging + "/" + pack.name)}')
        run('Import the live signed release feed as display metadata',
            f'cd {quote(release)} && sudo -n {python} -m portal.manage --data-dir {quote(data)} import-release /var/www/offwork-pet-updates/latest.json && '
            f'sudo -n chown -R offwork-web:offwork-web {quote(data)}')
        switched = True
        run('Enable the new website service',
            f'sudo -n ln -sfn {quote(release)} {quote(base + "/current")} && '
            f'sudo -n install -m 644 {quote(release + "/deploy/offwork-pet-web.service")} /etc/systemd/system/offwork-pet-web.service && '
            'sudo -n systemctl daemon-reload && sudo -n systemctl enable offwork-pet-web && sudo -n systemctl restart offwork-pet-web')
        for attempt in range(12):
            try:
                run('Check website before switching public traffic',
                    'curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8766/api/catalog/health', 10)
                break
            except RuntimeError:
                if attempt == 11:
                    raise
                time.sleep(1)
        # Backup copies in sites-enabled are loaded by nginx's wildcard. Move
        # only these exact legacy files into the already-created backup.
        disable_backups = '''import pathlib, shutil, sys
backup = pathlib.Path(sys.argv[1]) / 'disabled-sites'
backup.mkdir()
enabled = pathlib.Path('/etc/nginx/sites-enabled').resolve()
for name in ['default.bak.202606151643','default.bak.admin','default.bak.pre-xinxi']:
    path = enabled / name
    if path.is_file() and path.parent == enabled:
        shutil.move(str(path), str(backup/name))
'''
        run('Switch port 80 to the new website',
            'sudo -n python3 -c ' + quote(disable_backups) + ' ' + quote(backup) + ' && '
            f'sudo -n install -m 644 {quote(release + "/deploy/nginx.conf")} /etc/nginx/sites-enabled/default && '
            'sudo -n nginx -t && sudo -n systemctl reload nginx')
        run('Check public site and original desktop health',
            'curl --fail --silent --show-error --max-time 10 http://127.0.0.1/api/catalog/health && '
            'curl --fail --silent --show-error --max-time 10 http://127.0.0.1/health')
        record = {'revision': revision, 'release': release, 'backup': backup, 'data': data,
                  'previous_release': previous, 'character_packages': [path.name for path in packs],
                  'host': args.host, 'url': 'http://' + args.host + '/', 'status': 'deployed'}
        (ROOT / 'outputs').mkdir(exist_ok=True)
        (ROOT / 'outputs' / 'last-deployment.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps(record, ensure_ascii=False), flush=True)
    except Exception:
        if switched:
            print('Deployment failed; restoring the previous routing and service.', file=sys.stderr, flush=True)
            commands = [f'sudo -n tar -xzf {quote(backup + "/nginx.tar.gz")} -C /',
                        'sudo -n nginx -t && sudo -n systemctl reload nginx']
            if previous:
                commands.append(f'sudo -n ln -sfn {quote(previous)} {quote(base + "/current")}')
            if had_service:
                commands.append(f'sudo -n cp -a {quote(backup + "/offwork-pet-web.service")} /etc/systemd/system/offwork-pet-web.service')
                commands.append('sudo -n systemctl daemon-reload && sudo -n systemctl restart offwork-pet-web')
            else:
                commands.append('sudo -n systemctl disable --now offwork-pet-web')
            for command in commands:
                try:
                    run('Rollback', command)
                except Exception as rollback_error:
                    print('Rollback requires inspection: ' + str(rollback_error), file=sys.stderr, flush=True)
        raise
    finally:
        ssh.close()


if __name__ == '__main__':
    main()
