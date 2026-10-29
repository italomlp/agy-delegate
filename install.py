#!/usr/bin/env python3
import argparse, os, shutil, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser(); p.add_argument('action',choices=['install','uninstall']); p.add_argument('--host',choices=['codex','opencode','both'],default='both'); p.add_argument('--prefix',type=Path,default=Path.home()/'.local'); p.add_argument('--home',type=Path,default=Path.home(),help='Override home for test or custom installation'); p.add_argument('--yes',action='store_true'); a=p.parse_args()
hosts=['codex','opencode'] if a.host=='both' else [a.host]
targets=[(ROOT/'agy-delegate.py',a.prefix/'bin'/'agy-delegate')]
for host in hosts:
 base=a.home/'.agents'/'skills' if host=='codex' else a.home/'.config'/'opencode'/'skills'
 targets.append((ROOT/'skills'/'agy-delegate'/'SKILL.md',base/'agy-delegate'/'SKILL.md'))
for source,target in targets: print(f'{a.action}: {target}')
if a.action=='install':
 conflicts=[t for s,t in targets if t.exists() and t.read_bytes()!=s.read_bytes()]
 if conflicts: print('Refusing to overwrite existing files: '+', '.join(map(str,conflicts)),file=sys.stderr); sys.exit(1)
 if not a.yes and input('Install these files? [y/N] ').strip().lower()!='y': sys.exit(1)
 for source,target in targets:
  target.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,target)
else:
 if not a.yes and input('Remove matching installed files? [y/N] ').strip().lower()!='y': sys.exit(1)
 for source,target in targets:
  if target.exists() and target.read_bytes()==source.read_bytes(): target.unlink()
  elif target.exists(): print(f'Preserved modified file: {target}',file=sys.stderr)
