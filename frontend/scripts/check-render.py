"""Validate actual React rendering without executing any notebook/model code."""
from pathlib import Path
import json
import platform
import subprocess
import sys

frontend = Path(__file__).resolve().parents[1]
project = frontend.parent
sys.path.insert(0, str(project))
from src.dashboard import StudyService

artifacts = frontend / '.browser-artifacts'
artifacts.mkdir(exist_ok=True)
(artifacts / 'study.json').write_text(json.dumps(StudyService(project).snapshot()), encoding='utf-8')
name = {'win32': 'win32', 'linux': 'linux', 'darwin': 'darwin'}[sys.platform]
arch = 'arm64' if platform.machine().lower() in ('arm64', 'aarch64') else 'x64'
binary = frontend / 'node_modules/@esbuild' / f'{name}-{arch}' / ('esbuild.exe' if sys.platform == 'win32' else 'bin/esbuild')
subprocess.run([str(binary), 'tests/render-smoke.jsx', '--bundle', '--platform=node', '--format=esm',
                '--packages=external', '--jsx=automatic', '--outfile=.browser-artifacts/render-smoke.mjs'], cwd=frontend, check=True)
subprocess.run(['node', '.browser-artifacts/render-smoke.mjs'], cwd=frontend, check=True)
