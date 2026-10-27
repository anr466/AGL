#!/usr/bin/env python3
"""test_hardening.py — كل ثغرة وُجدت في gates.py الأصلية لها اختبار هنا. التشغيل: python test_hardening.py"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
_tmp = tempfile.mkdtemp()
os.environ['AGL_STATE_DIR'] = os.path.join(_tmp, 'state')

import gates  # noqa: E402
from gates import GateViolation, HardViolation, SimilarPath, StopRule, FileExclusivity  # noqa: E402

GOOD = {'stored': 'v', 'visible': 'yes', 'timestamp': '2026-10-27T10:00:00'}


def blocked(cmd):
    try:
        gates.git_guard(cmd)
        return False
    except GateViolation:
        return True


class Verify(unittest.TestCase):
    def test_negations_no_longer_pass(self):
        for bad in ({'stored': 'no'}, {'visible': 'false'}, {'visible': 'no'}, {'timestamp': 'now'},
                    {'timestamp': 'abc'}, {'stored': ''}, {'visible': '0'}):
            ev = {**GOOD, **bad}
            with self.assertRaises(GateViolation, msg=bad):
                gates.verify_readback(3, lambda: (3, ev), 't')

    def test_valid_passes(self):
        self.assertTrue(all(gates.verify_readback(3, lambda: (3, GOOD), 't')['checks'].values()))
        gates.verify_readback(3, lambda: (3, {'stored': 5, 'visible': True, 'timestamp': 1.7e9}), 't')


class GitGuard(unittest.TestCase):
    def test_previously_bypassed(self):
        for c in ['git -C /repo commit -m x', 'git add f && git commit -m x', 'git restore .',
                  'git checkout .', 'git -c user.name=a push', 'bash -c "git push origin main"',
                  'echo $(git reset --hard)', 'git switch -f main', 'git reset --hard HEAD~1',
                  'git add -A', 'git commit --no-verify -m x', 'sudo git push --force']:
            self.assertTrue(blocked(c), c)

    def test_read_only_not_blocked(self):
        for c in ['git status', 'git log -5 --oneline', 'git diff', 'git stash list', 'git tag -l',
                  'git branch', 'git -C /repo status', 'git restore --staged f', 'git add file.py',
                  'git commit-graph verify', 'ls | grep git']:
            self.assertFalse(blocked(c), c)

    def test_approved(self):
        self.assertTrue(gates.git_guard('git commit -m x', approved=True))


class Stop(unittest.TestCase):
    def test_near_duplicates_rejected(self):
        s = StopRule()
        s.record_failure('fix import', 'e1')
        with self.assertRaises(SimilarPath):
            s.record_failure('fix import path', 'e2')
        s.record_failure('fix import path', 'e2', diff='تغيير مسار الاستيراد من نسبي إلى مطلق في الحزمة')
        self.assertEqual(s._distinct(), 2)

    def test_labels_not_false_positive(self):  # مثال README نفسه
        s = StopRule()
        s.record_failure('approach_A', 'x')
        s.record_failure('approach_B', 'y')

    def test_stops_at_three(self):
        s = StopRule()
        s.record_failure('a b c', 'e1')
        s.record_failure('xyz', 'e2')
        with self.assertRaises(GateViolation):
            s.record_failure('qrs tuv', 'e3')

    def test_same_error_warning(self):
        s = StopRule(max_distinct=9)
        s.record_failure('aaa', 'timeout')
        s.record_failure('bbb', 'timeout')
        r = s.record_failure('ccc', 'timeout')
        self.assertTrue(r['warnings'])


class Files(unittest.TestCase):
    def test_register_before_create_and_delete(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'scratch.txt')
        fe = FileExclusivity(persist=os.path.join(d, 'c.json'))
        fe.register_created(p)
        open(p, 'w').close()
        self.assertTrue(FileExclusivity(persist=os.path.join(d, 'c.json')).allow_delete(p))  # يثبت بين الاستدعاءات

    def test_cannot_claim_existing_user_file(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'user.txt')
        open(p, 'w').close()
        with self.assertRaises(GateViolation):
            FileExclusivity().register_created(p)

    def test_unregistered_denied(self):
        with self.assertRaises(GateViolation):
            FileExclusivity().allow_delete('/tmp/whatever_user_file')

    def test_tracked_file_denied_even_if_registered(self):
        d = tempfile.mkdtemp()
        subprocess.run(['git', 'init', '-q'], cwd=d)
        p = os.path.join(d, 'a.txt')
        fe = FileExclusivity()
        fe.register_created(p)
        open(p, 'w').close()
        subprocess.run(['git', 'add', 'a.txt'], cwd=d)
        with self.assertRaises(GateViolation):
            fe.allow_delete(p)


class Shell(unittest.TestCase):
    def test_rm_rules(self):
        d = tempfile.mkdtemp()
        mine, theirs = os.path.join(d, 'mine.txt'), os.path.join(d, 'theirs.txt')
        open(theirs, 'w').close()
        gates.FileExclusivity(persist=gates.state_path('created.json')).register_created(mine)
        open(mine, 'w').close()
        self.assertTrue(gates.shell_guard(f'rm {mine}'))
        with self.assertRaises(GateViolation):
            gates.shell_guard(f'rm {theirs}')
        with self.assertRaises(GateViolation):
            gates.shell_guard(f'rm -rf {d}/*')
        for h in ('rm -rf /', 'rm -rf ~', 'rm -rf .'):
            with self.assertRaises(HardViolation):
                gates.shell_guard(h, approved=True)  # الموافقة لا تفتح النهائي

    def test_misc_destructive(self):
        for c in ['dd if=/dev/zero of=/tmp/x', 'find . -delete', 'chmod -R 777 .', 'git push && echo hi']:
            with self.assertRaises(GateViolation, msg=c):
                gates.shell_guard(c)

    def test_overwrite_redirect(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'x.txt')
        open(p, 'w').close()
        with self.assertRaises(GateViolation):
            gates.shell_guard(f'echo hi > {p}')
        gates.shell_guard('echo hi > /dev/null')
        gates.shell_guard(f'echo hi > {d}/new_file.txt')


class Hook(unittest.TestCase):
    def run_hook(self, cmd):
        r = subprocess.run([sys.executable, os.path.join(HERE, 'hook_pretooluse.py')], capture_output=True,
                           text=True, input=json.dumps({'tool_name': 'Bash', 'tool_input': {'command': cmd}}),
                           env=os.environ)
        return r.returncode, (json.loads(r.stdout)['hookSpecificOutput']['permissionDecision'] if r.stdout else None)

    def test_decisions(self):
        self.assertEqual(self.run_hook('git status'), (0, None))
        self.assertEqual(self.run_hook('git push origin main'), (0, 'ask'))
        self.assertEqual(self.run_hook('rm -rf ~'), (0, 'deny'))


class Jobs(unittest.TestCase):
    def j(self, *a):
        return subprocess.run([sys.executable, os.path.join(HERE, 'jobs.py'), *a], capture_output=True,
                              text=True, env=os.environ)

    def test_start_returns_immediately_and_parallel(self):
        t0 = time.time()
        ids = [self.j('start', 'sleep 2; echo job%d' % i).stdout.strip() for i in range(3)]
        self.assertLess(time.time() - t0, 1.5)  # 3 مهام × 2ث لم تُنتظر
        self.assertIn('running', self.j('status', ids[0]).stdout)
        w = self.j('wait', *ids, '--timeout', '10')
        self.assertEqual(w.returncode, 0, w.stdout)
        self.assertLess(time.time() - t0, 5)  # متوازية: ≈2ث لا 6ث
        self.assertIn('job1', self.j('result', ids[1]).stdout)

    def test_failure_and_exit_code_captured(self):
        i = self.j('start', 'echo boom; exit 3').stdout.strip()
        self.j('wait', i, '--timeout', '10')
        out = self.j('result', i).stdout
        self.assertIn('failed', out)
        self.assertIn('رمز الخروج: 3', out)

    def test_guard_applies_to_background(self):
        r = self.j('start', 'git push origin main')
        self.assertEqual(r.returncode, 1)
        self.assertIn('حارس', r.stderr)

    def test_cancel_and_timeout(self):
        i = self.j('start', 'sleep 30').stdout.strip()
        time.sleep(0.5)
        self.assertIn('أُلغيت', self.j('cancel', i).stdout)
        k = self.j('start', 'sleep 30', '--timeout', '1').stdout.strip()
        self.j('wait', k, '--timeout', '10')
        self.assertIn('timeout', self.j('status', k).stdout)


def read_skill():
    with open(os.path.join(HERE, 'SKILL.md'), encoding='utf-8') as f:
        return f.read()


class Install(unittest.TestCase):
    def run_install(self, *a):
        home = tempfile.mkdtemp()
        r = subprocess.run([sys.executable, os.path.join(HERE, 'install.py'), *a], capture_output=True,
                           text=True, env={**os.environ, 'HOME': home})
        return r, home

    def test_claude_project_and_hook_snippet(self):
        proj = tempfile.mkdtemp()
        r, _ = self.run_install('--claude', '--project', proj)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = os.path.join(proj, '.claude', 'skills', 'engineering-os')
        for f in ('SKILL.md', 'gates.py', 'jobs.py', 'hook_pretooluse.py'):
            self.assertTrue(os.path.exists(os.path.join(d, f)), f)
        snippet = json.loads(r.stdout[r.stdout.index('{'):])
        self.assertTrue(snippet['hooks']['PreToolUse'][0]['hooks'][0]['command'].endswith('hook_pretooluse.py'))

    def test_claude_global_and_default_unchanged(self):
        r, home = self.run_install('--claude')
        self.assertTrue(os.path.exists(os.path.join(home, '.claude', 'skills', 'engineering-os', 'SKILL.md')))
        r, home = self.run_install()
        self.assertTrue(os.path.exists(os.path.join(home, '.gemini', 'config', 'skills', 'engineering-os', 'gates.py')))

    def test_claude_with_target_rejected(self):
        r, _ = self.run_install('--claude', '--target', tempfile.mkdtemp())
        self.assertNotEqual(r.returncode, 0)


class SkillAndPolicyConsistency(unittest.TestCase):
    """يمنع تراجع التناسق بين الوثائق والكود."""

    def test_skill_version_matches_title(self):
        s = read_skill()
        import re
        v = re.search(r'^version: "([\d.]+)"', s, re.M).group(1)
        self.assertIn(f'ENGINEERING OS v{v}', s)

    def test_every_cli_command_documented_in_skill(self):
        s = read_skill()
        for c in ('verify', 'classify', 'git', 'shell', 'files', 'stop'):
            self.assertIn(f'| `{c}', s, c)

    def test_skill_cleanup_rule_matches_enforcement(self):
        # القاعدة النصية يجب أن تذكر شرط التسجيل المسبق الذي يفرضه الكود
        s = read_skill()
        self.assertIn('files register', s)

    def test_agent_workflow_register_create_delete(self):  # ما تأمر به SKILL.md فعلاً ينجح
        d = tempfile.mkdtemp()
        p = os.path.join(d, 'scratch', 't.txt')
        g = lambda *a: subprocess.run([sys.executable, os.path.join(HERE, 'gates.py'), *a],
                                      capture_output=True, text=True, env=os.environ).returncode
        self.assertEqual(g('files', 'register', p), 0)
        os.makedirs(os.path.dirname(p))
        open(p, 'w').close()
        self.assertEqual(g('shell', f'rm {p}'), 0)


if __name__ == '__main__':
    unittest.main(verbosity=1)
