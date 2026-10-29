#!/usr/bin/env python3
"""Invoke an installed agy; all run results are JSON on stdout."""
import argparse, json, os, re, shutil, signal, subprocess, sys, tempfile
from pathlib import Path

DEFAULT = {'auto': True, 'max_retries': 2, 'models': {'simple': ['Gemini 3.8 Flash (Medium)', 'Claude Sonnet 5.5 (Medium)', 'Claude Opus 5.5 (High)'], 'medium': ['Claude Sonnet 5.5 (Medium)', 'Gemini 3.8 Flash (Medium)', 'Claude Opus 5.5 (High)'], 'complex': ['Claude Opus 5.5 (High)', 'Claude Sonnet 5.5 (Medium)', 'Gemini 3.8 Flash (Medium)']}}
CONFIG = Path(os.environ.get('AGY_DELEGATE_CONFIG', Path(os.environ.get('XDG_CONFIG_HOME', Path.home()/'.config'))/'agy-delegate'/'config.json'))
def config():
 if not CONFIG.exists(): return json.loads(json.dumps(DEFAULT))
 data=json.loads(CONFIG.read_text()); return {**DEFAULT, **data, 'models': {**DEFAULT['models'], **data.get('models', {})}}
def save(data):
 CONFIG.parent.mkdir(parents=True, exist_ok=True)
 fd,name=tempfile.mkstemp(dir=CONFIG.parent, prefix='.config-')
 try:
  with os.fdopen(fd,'w') as f: json.dump(data,f,indent=2); f.write('\n')
  os.replace(name,CONFIG)
 finally:
  if os.path.exists(name): os.unlink(name)
def snapshot(path):
 # Include tracked, staged and untracked content, not just git status labels.
 p=subprocess.run(['git','-C',str(path),'rev-parse','--show-toplevel'],capture_output=True,text=True)
 if p.returncode: return None
 root=Path(p.stdout.strip()); p=subprocess.run(['git','-C',str(root),'ls-files','-co','--exclude-standard','-z'],capture_output=True)
 if p.returncode: return None
 import hashlib
 h=hashlib.sha256()
 for name in sorted(set(p.stdout.split(b'\0'))-{b''}):
  h.update(name); f=root/os.fsdecode(name)
  try:
   if f.is_symlink(): h.update(os.readlink(f).encode())
   elif f.is_file(): h.update(f.read_bytes())
   else: h.update(b'<missing>')
  except OSError: return None
 p=subprocess.run(['git','-C',str(root),'diff','--cached','--binary'],capture_output=True)
 if p.returncode: return None
 h.update(p.stdout); return h.hexdigest()
def main():
 p=argparse.ArgumentParser(prog='agy-delegate'); sub=p.add_subparsers(dest='action',required=True)
 run=sub.add_parser('run'); run.add_argument('prompt'); run.add_argument('--dir',default='.'); run.add_argument('--complexity',choices=['simple','medium','complex'],default='medium'); run.add_argument('--model'); run.add_argument('--timeout',type=int,default=900); run.add_argument('--max-retries',type=int); run.add_argument('--conversation'); run.add_argument('--automatic',action='store_true'); run.add_argument('--force',action='store_true'); run.add_argument('--sandbox',action='store_true'); run.add_argument('--read-only',action='store_true',help='Task asks agy not to edit; permits quota retry without a Git snapshot')
 auto=sub.add_parser('auto'); auto.add_argument('value',choices=['on','off']); sub.add_parser('status'); sub.add_parser('doctor')
 a=p.parse_args(); c=config()
 if a.action=='auto': c['auto']=a.value=='on'; save(c); print('Automatic delegation: '+a.value); return 0
 if a.action=='status': print(json.dumps({'config':str(CONFIG),**c},indent=2)); return 0
 if a.action=='doctor':
  binary=os.environ.get('AGY_BIN','agy'); found=shutil.which(binary); print(json.dumps({'agy':found,'config':str(CONFIG),'automatic':c['auto'],'note':'Run agy interactively to check authentication; headless permissions depend on your environment.'},indent=2)); return 0 if found else 1
 if a.automatic and not a.force and not c['auto']:
  print(json.dumps({'status':'disabled','attempts':[]})); return 2
 if a.timeout<=0 or (a.max_retries is not None and a.max_retries<0): p.error('timeout must be positive and retries non-negative')
 work=Path(a.dir).resolve()
 if not work.is_dir(): p.error('directory does not exist')
 models=c['models'][a.complexity]; models=([a.model]+[x for x in models if x!=a.model]) if a.model else models
 if not models or any(not isinstance(m,str) or not m or m.startswith('-') for m in models): p.error('configure valid model names')
 retries=a.max_retries if a.max_retries is not None else c['max_retries']; attempts=[]; baseline=snapshot(work)
 for model in list(dict.fromkeys(models))[:retries+1]:
  cmd=[os.environ.get('AGY_BIN','agy'),'--print',a.prompt,'--model',model,'--print-timeout',f'{a.timeout}s','--disable-slash-commands','--add-dir',str(work)]
  if a.conversation: cmd+=['--conversation',a.conversation]
  if a.sandbox: cmd+=['--sandbox']
  def interrupt(signum, frame):
   raise KeyboardInterrupt
  previous=signal.signal(signal.SIGTERM,interrupt)
  try:
   child=subprocess.Popen(cmd,cwd=work,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
   try: out,err=child.communicate(timeout=a.timeout+2); code=child.returncode; timed=False
   except subprocess.TimeoutExpired:
    os.killpg(child.pid,signal.SIGTERM)
    try: out,err=child.communicate(timeout=3)
    except subprocess.TimeoutExpired: os.killpg(child.pid,signal.SIGKILL); out,err=child.communicate()
    code=child.returncode; timed=True
  except FileNotFoundError:
   print(json.dumps({'status':'missing_cli','attempts':attempts,'message':'Install and authenticate agy first.'})); return 1
  except KeyboardInterrupt:
   os.killpg(child.pid,signal.SIGTERM); child.wait(); print(json.dumps({'status':'cancelled','attempts':attempts})); return 130
  signal.signal(signal.SIGTERM,previous)
  out=out.decode(errors='replace')[-100000:]; err=err.decode(errors='replace')[-4000:]; combined=out+'\n'+err
  # Errors take precedence over quota to prevent unsafe retries.
  if timed: status='timeout'
  elif code != 0 and re.search(r'(?is)(listen tcp[^\n]*socket: operation not permitted|read-only file system)',err): status='environment_restricted'
  elif re.search(r'(?i)(unauthenticated|authentication|login required|permission denied|permission required|invalid argument)',combined): status='permission_or_auth_error'
  elif re.search(r'(?i)(quota (?:exceeded|exhausted)|rate.limit|resource.exhausted|too many requests|\b429\b)',combined): status='quota'
  elif code!=0: status='error'
  elif not out.strip(): status='empty_output'
  else: status='success'
  match=re.search(r'(?i)conversation(?:[ _-]?id)?["\s:=]+([\w-]{6,128})',combined)
  after=snapshot(work); changed=baseline is not None and after!=baseline
  model_unconfirmed=bool(re.search(r'(?i)model id .*?not in local config, defaulting',err))
  attempts.append({'model':model,'model_unconfirmed':model_unconfirmed,'status':status,'exit_code':code,'output':out,'stderr':err,'conversation_id':a.conversation or (match.group(1) if match else None),'workspace_changed':changed if baseline is not None else None})
  if status!='quota' or changed or (baseline is None and not a.read_only): break
 result={'status':status,'model':model,'attempts':attempts,'conversation_id':attempts[-1]['conversation_id'],'workspace_changed':attempts[-1]['workspace_changed']}
 if status=='environment_restricted': result['message']='agy could not start because its environment denied filesystem or network access. Check host permissions for agy state and network; do not bypass host policy.'
 if model_unconfirmed: result['model_warning']='agy reported the requested model was not in local config and used a default; check agy models and configuration.'
 if model_unconfirmed and status=='success': result['message']=result['model_warning']
 if status=='quota': result['message']='Inspect partial work before retrying; if unavailable, use an allowed native subagent or continue directly.'
 if status=='permission_or_auth_error': result['message']='Check login and headless permissions. No permissions were auto-approved.'
 print(json.dumps(result,ensure_ascii=False)); return 0 if status=='success' else 1
if __name__=='__main__':
 try: sys.exit(main())
 except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError) as e: print(json.dumps({'status':'configuration_error','message':str(e)})); sys.exit(1)
