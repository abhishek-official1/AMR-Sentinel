"""Run esbuild's native CLI without Node's restricted child-process pipes."""
from pathlib import Path
import platform
import shutil
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
platform_name = {'win32': 'win32', 'linux': 'linux', 'darwin': 'darwin'}.get(sys.platform)
arch = {'AMD64': 'x64', 'x86_64': 'x64', 'arm64': 'arm64', 'aarch64': 'arm64'}.get(platform.machine())
package = root / 'node_modules/@esbuild' / f'{platform_name}-{arch}'
binary = package / ('esbuild.exe' if sys.platform == 'win32' else 'bin/esbuild')
if not binary.exists():
    raise SystemExit('Native esbuild dependency missing. Run npm install in frontend first.')
dist = root / 'dist'
dist.mkdir(exist_ok=True)
shutil.copyfile(root / 'index.html', dist / 'index.html')
command = [str(binary), 'src/main.jsx', '--bundle', '--outdir=dist/assets', '--entry-names=app',
           '--sourcemap', '--jsx=automatic', '--target=es2022', '--log-level=info']
if '--watch' in sys.argv:
    command.append('--watch=forever')
else:
    # With full minification, esbuild automatically sets NODE_ENV=production.
    command.append('--minify')
subprocess.run(command, cwd=root, check=True)
