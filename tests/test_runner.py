import json, os, subprocess, tempfile, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'agy-delegate.py'
class RunnerTests(unittest.TestCase):
 def setUp(self):
  self.tmp = tempfile.TemporaryDirectory(); self.path = Path(self.tmp.name)
  self.fake = self.path / 'agy'; self.fake.write_text('#!/usr/bin/env python3\nimport os,sys\nm=sys.argv[sys.argv.index("--model")+1]\nprint("quota exceeded" if m == "first" else "done")\nsys.exit(1 if m == "first" else 0)\n'); self.fake.chmod(0o755)
  self.config = self.path / 'config.json'; self.config.write_text(json.dumps({'models': {'simple':['first','second'], 'medium':['second'], 'complex':['second']},'max_retries':2,'auto':True}))
  self.env = dict(os.environ, AGY_DELEGATE_CONFIG=str(self.config), AGY_BIN=str(self.fake))
 def tearDown(self): self.tmp.cleanup()
 def call(self,*args): return subprocess.run(['python3',str(RUN),*args],cwd=self.path,env=self.env,text=True,capture_output=True)
 def test_quota_retries_other_model(self):
  p=self.call('run','--complexity','simple','--read-only','hello'); self.assertEqual(p.returncode,0,p.stderr); r=json.loads(p.stdout); self.assertEqual([x['model'] for x in r['attempts']],['first','second'])
 def test_auto_off_is_respected(self):
  self.assertEqual(self.call('auto','off').returncode,0); p=self.call('run','--automatic','hello'); self.assertEqual(json.loads(p.stdout)['status'],'disabled')
 def test_permission_failure_is_not_retried(self):
  self.fake.write_text('#!/bin/sh\necho "permission denied" >&2\nexit 1\n'); p=self.call('run','hello'); self.assertEqual(len(json.loads(p.stdout)['attempts']),1)
if __name__=='__main__': unittest.main()

class AdditionalTests(unittest.TestCase):
 def test_installer_and_uninstaller_preserve_modified_skill(self):
  with tempfile.TemporaryDirectory() as d:
   home=Path(d); inst=ROOT/'install.py'; base=['python3',str(inst)]; opts=['--host','both','--home',d,'--prefix',str(home/'local'),'--yes']
   p=subprocess.run(base+['install']+opts,capture_output=True,text=True); self.assertEqual(p.returncode,0,p.stderr)
   skill=home/'.agents/skills/agy-delegate/SKILL.md'; self.assertTrue(skill.exists()); skill.write_text('user modification')
   p=subprocess.run(base+['uninstall']+opts,capture_output=True,text=True); self.assertEqual(p.returncode,0,p.stderr); self.assertEqual(skill.read_text(),'user modification'); self.assertFalse((home/'local/bin/agy-delegate').exists())
 def test_partial_changes_prevent_retry(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); subprocess.run(['git','init','-q',d],check=True); fake=root/'fake'; fake.write_text('#!/bin/sh\necho changed > partial\necho quota exceeded\nexit 1\n'); fake.chmod(0o755)
   cfg=root/'cfg.json'; cfg.write_text(json.dumps({'models':{'medium':['one','two']},'max_retries':2})); env=dict(os.environ,AGY_BIN=str(fake),AGY_DELEGATE_CONFIG=str(cfg)); p=subprocess.run(['python3',str(RUN),'run','hello'],cwd=d,env=env,capture_output=True,text=True); result=json.loads(p.stdout); self.assertEqual(result['status'],'quota'); self.assertEqual(len(result['attempts']),1); self.assertTrue(result['workspace_changed'])
 def test_timeout(self):
  with tempfile.TemporaryDirectory() as d:
   fake=Path(d)/'fake'; fake.write_text('#!/bin/sh\nsleep 10\n'); fake.chmod(0o755); env=dict(os.environ,AGY_BIN=str(fake),AGY_DELEGATE_CONFIG=str(Path(d)/'cfg')); p=subprocess.run(['python3',str(RUN),'run','--timeout','1','hello'],cwd=d,env=env,capture_output=True,text=True); self.assertEqual(json.loads(p.stdout)['status'],'timeout')

class DiagnosticsTests(unittest.TestCase):
 def run_fake(self, stderr, exit_code=1):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d); fake=root/'agy'; fake.write_text('#!/usr/bin/env python3\nimport sys\nsys.stderr.write('+repr(stderr)+')\nprint("ok" if '+str(exit_code)+' == 0 else "", end="")\nsys.exit('+str(exit_code)+')\n'); fake.chmod(0o755)
   env=dict(os.environ, AGY_BIN=str(fake), AGY_DELEGATE_CONFIG=str(root/'config')); proc=subprocess.run(['python3',str(RUN),'run','--read-only','hello'],cwd=d,env=env,capture_output=True,text=True); return json.loads(proc.stdout)
 def test_sandbox_denial_is_identified(self):
  result=self.run_fake('Failed to start: listen tcp 127.0.0.1:0: socket: operation not permitted\nread-only file system'); self.assertEqual(result['status'],'environment_restricted'); self.assertEqual(len(result['attempts']),1); self.assertIn('permissions',result['message'].lower())
 def test_model_fallback_warning_is_visible_on_success(self):
  result=self.run_fake('Model ID Claude not in local config, defaulting to CCPA',0); self.assertTrue(result['attempts'][0]['model_unconfirmed']); self.assertIn('model',result['message'].lower())
