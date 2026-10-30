#!/usr/bin/env python3
"""test_consistency.py — يمنع عودة التناقض بين الوثائق والكود: مراجع ميتة، رخص متضاربة، أرقام مكتوبة يدوياً،
محتوى خاص، قاعدة نشر تلقائي، وحجم نواة المهارة."""
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


USER_PROJECT_FILES = {'ARCHITECTURE.md', 'AGENTS.md', 'CLAUDE.md', 'GEMINI.md'}


def read(rel):
    with open(os.path.join(HERE, rel), encoding='utf-8') as f:
        return f.read()


def tracked():
    r = subprocess.run(['git', '-C', HERE, 'ls-files'], capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.split()
    return [f for f in os.listdir(HERE) if os.path.isfile(os.path.join(HERE, f))] + \
        ['references/' + f for f in os.listdir(os.path.join(HERE, 'references'))]


def docs():
    return [f for f in tracked() if f.endswith('.md')]


class Links(unittest.TestCase):
    def test_every_referenced_file_exists(self):
        for doc in docs():
            for ref in re.findall(r'`((?:references/)?[\w\-]+\.(?:md|py))`', read(doc)):
                base = ref if '/' in ref else ref
                ok = os.path.exists(os.path.join(HERE, base)) or os.path.exists(os.path.join(HERE, 'references', base))
                if base in USER_PROJECT_FILES:
                    continue  # ملفات مشروع المستخدم لا مستودعنا (تُذكر كأمثلة)
                self.assertTrue(ok, f'{doc} يشير إلى ملف غير موجود: {ref}')

    def test_markdown_links_resolve(self):
        for doc in docs():
            for target in re.findall(r'\]\((?!https?:|#|mailto:)([^)\s#]+)', read(doc)):
                self.assertTrue(os.path.exists(os.path.join(HERE, os.path.dirname(doc), target)), f'{doc} -> {target}')


class Versions(unittest.TestCase):
    def test_skill_version_title_and_frontmatter(self):
        s = read('SKILL.md')
        v = re.search(r'^version: "([\d.]+)"', s, re.M).group(1)
        self.assertIn(f'ENGINEERING OS v{v}', s)
        self.assertRegex(s, r'(?m)^name: engineering-os$')

    def test_single_license(self):
        lic = read('LICENSE')
        self.assertIn('MIT License', lic)
        s = read('SKILL.md')
        self.assertRegex(s, r'(?m)^license: MIT$')
        for doc in docs():
            self.assertNotIn('Apache', read(doc), doc)
            self.assertNotRegex(read(doc), r'license:\s*private', doc)

    def test_no_hand_written_counters(self):
        readme = read('README.md')
        self.assertNotRegex(readme, r'tests-\d+%2F\d+', 'شارة اختبارات ثابتة')
        self.assertNotRegex(readme, r'(?i)\b\d+/\d+\s*(tests|اختبار)')
        self.assertIn('actions/workflows/selftest.yml/badge.svg', readme)


class BrainCounts(unittest.TestCase):
    def test_brain_docs_match_scoring_code(self):
        import brain_score as B
        bt = read('BRAIN_TEST.md')
        self.assertIn('السبعة', bt)
        n_axes = len(B.AXES)
        self.assertIn(f'{n_axes} محور', read('README.md') + read('brain_score.py'))
        self.assertIn('سبعة', read('SKILL.md'))
        self.assertFalse(os.path.exists(os.path.join(HERE, 'BRAIN_MEASUREMENT.md')), 'مرجعان متضاربان للقياس')

    def test_workflow_runs_every_test_file(self):
        wf = read('.github/workflows/selftest.yml')
        for f in sorted(x for x in os.listdir(HERE) if re.match(r'(test_.*|gates_selftest)\.py$', x) and x != 'test_consistency.py') + \
                ['test_consistency.py']:
            self.assertIn(f, wf, f)


class Policy(unittest.TestCase):
    def test_no_auto_push_rule_anywhere(self):
        s = read('SKILL.md')
        self.assertNotIn('يُرفع للمستودع بنفس الجلسة', s)
        self.assertIn('لا مزامنة تلقائية', s)
        self.assertIn('لا commit ولا push', s)

    def test_no_private_project_content_or_secrets(self):
        bad = ['ksa-news', 'LMS', 'CDP + Atto', 'بنك أسئلة', '40 سؤالاً']
        for f in tracked():
            if f.endswith(('.png', '.svg')) or f == 'test_consistency.py':
                continue
            txt = read(f)
            for w in bad:
                self.assertNotIn(w, txt, f'{f}: محتوى خاص «{w}»')
            self.assertIsNone(re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|github_pat_\w{20,}', txt), f'{f}: يشبه مفتاحاً')

    def test_skill_core_stays_small(self):
        self.assertLess(len(read('SKILL.md').encode()), 18_000, 'نواة المهارة تضخمت — انقل التفاصيل إلى references/')

    def test_every_tool_mentioned_in_skill_has_reference(self):
        s = read('SKILL.md')
        for tool in ('gates.py', 'ux_gate.py', 'recon.py', 'jobs.py', 'hook_pretooluse.py'):
            self.assertIn(tool, s, tool)
            self.assertTrue(os.path.exists(os.path.join(HERE, tool)), tool)
        refs = ''.join(read(f'references/{f}') for f in os.listdir(os.path.join(HERE, 'references')))
        for tool in ('gates.py', 'ux_gate.py', 'recon.py', 'jobs.py', 'hook_pretooluse.py'):
            self.assertIn(tool, refs, f'{tool} بلا توثيق في references/')

    def test_skill_documents_triage(self):
        self.assertIn('التناسب', read('SKILL.md'))

    def test_install_ships_every_runtime_file(self):
        inst = read('install.py')
        for f in ('SKILL.md', 'gates.py', 'jobs.py', 'hook_pretooluse.py', 'ux_gate.py', 'recon.py', 'brain_score.py',
                  'BRAIN_TEST.md', 'LICENSE', 'references'):
            self.assertIn(f"'{f}'", inst, f)


if __name__ == '__main__':
    unittest.main(verbosity=1)
