#!/usr/bin/env python3
"""test_recon.py — مرحلة فهم المشروع على مشاريع مؤقتة: الوقائع الموثقة، الاستنتاج المعلن، المجهول لا يُخمَّن."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ['AGL_STATE_DIR'] = tempfile.mkdtemp()
import recon  # noqa: E402


def make(files):
    d = tempfile.mkdtemp()
    for rel, txt in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', encoding='utf-8') as f:
            f.write(txt)
    return d


class Scan(unittest.TestCase):
    def test_node_project_documented_facts(self):
        d = make({'package.json': json.dumps({'scripts': {'test': 'jest', 'dev': 'vite'}, 'dependencies': {'react': '1'}}),
                  'pnpm-lock.yaml': '', 'index.html': '<html></html>', '.env.example': 'API_URL=x\n',
                  'src/a.js': 'const k = process.env.API_URL; const s = process.env.SECRET_KEY;'})
        r = recon.scan(d)
        cmds = {c['value']['name']: c['value']['cmd'] for c in r['commands']}
        self.assertEqual(cmds['test'], 'pnpm run test')
        self.assertTrue(all(c['kind'] == 'documented' for c in r['commands']))
        self.assertIn('web-ui', [s['value'] for s in r['surfaces']])
        self.assertEqual([e['value'] for e in r['env_undocumented']], ['SECRET_KEY'])
        self.assertIn('API_URL', [e['value'] for e in r['env_documented']])
        self.assertEqual(r['stacks'][0]['kind'], 'documented')

    def test_unknowns_are_declared_not_guessed(self):
        r = recon.scan(make({'notes.txt': 'hello'}))
        what = [u['what'] for u in r['unknowns']]
        self.assertTrue(any('لغة' in w for w in what))
        self.assertTrue(any('الاختبار' in w for w in what))
        self.assertEqual(r['commands'], [])

    def test_python_test_command_marked_inferred(self):
        r = recon.scan(make({'app.py': 'print(1)', 'test_app.py': 'import unittest'}))
        t = [c for c in r['commands'] if c['value']['name'] == 'test'][0]
        self.assertEqual(t['kind'], 'inferred')

    def test_readme_commands_and_agent_rules(self):
        r = recon.scan(make({'README.md': '```bash\npip install -e .\npytest -q\n```\n', 'AGENTS.md': 'rules', 'x.py': ''}))
        self.assertIn('pytest -q', [c['value'] for c in r['readme_commands']])
        self.assertEqual([a['value'] for a in r['agent_rules']], ['AGENTS.md'])
        self.assertFalse(any('الاختبار' in u['what'] for u in r['unknowns']))

    def test_duplicates_and_skipped_dirs(self):
        r = recon.scan(make({'a/parser.py': '', 'b/parser.py': '', 'node_modules/x/parser.py': ''}))
        self.assertEqual(len(r['duplicates']), 1)
        self.assertEqual(len(r['duplicates'][0]['value']), 2)

    def test_dirty_git_is_reported(self):
        d = make({'a.py': 'x'})
        subprocess.run(['git', 'init', '-q'], cwd=d)
        r = recon.scan(d)
        self.assertEqual(r['git']['value']['dirty_files'], 1)
        self.assertTrue(any('git' in u['what'] for u in r['unknowns']))

    def test_search_finds_definitions_first(self):
        d = make({'a.py': 'def parse_invoice(x):\n    pass\n', 'b.py': '# invoice mention\n'})
        top = recon.search(d, ['invoice'])[0]
        self.assertTrue(top[1].startswith('a.py:1'))


class Cli(unittest.TestCase):
    def run_cli(self, *a):
        return subprocess.run([sys.executable, os.path.join(HERE, 'recon.py'), *a], capture_output=True, text=True,
                              env=os.environ)

    def test_check_exits_2_on_critical_unknown(self):
        d = make({'notes.txt': 'x'})
        self.assertEqual(self.run_cli('scan', '--root', d).returncode, 0)
        r = self.run_cli('check')
        self.assertEqual(r.returncode, 2, r.stdout)

    def test_check_passes_when_known(self):
        d = make({'package.json': json.dumps({'scripts': {'test': 't', 'start': 's'}})})
        self.run_cli('scan', '--root', d)
        self.assertEqual(self.run_cli('check').returncode, 0)


if __name__ == '__main__':
    unittest.main(verbosity=1)
