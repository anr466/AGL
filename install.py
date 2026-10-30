#!/usr/bin/env python3
"""install.py — يثبّت engineering-os كمهارة مع بواباتها في مكان واحد.
الاستخدام:
  python install.py                 # عام: ~/.gemini/config/skills/engineering-os
  python install.py --project DIR   # لمشروع: DIR/.agents/skills/engineering-os
  python install.py --target PATH   # مسار مخصص
  python install.py --claude [--project DIR]   # Claude Code: ~/.claude/skills أو DIR/.claude/skills
يبقى gates.py بجانب SKILL.md فيجده الوكيل: python <مسار المهارة>/gates.py ..."""

import argparse
import json
import shutil
from pathlib import Path

FILES = ['SKILL.md', 'gates.py', 'jobs.py', 'hook_pretooluse.py', 'ux_gate.py', 'recon.py', 'brain_score.py', 'BRAIN_TEST.md', 'LICENSE']
DIRS = ['references']


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--project')
    g.add_argument('--target')
    ap.add_argument('--claude', action='store_true', help='ثبّت في مسار Claude Code (.claude/skills)')
    a = ap.parse_args()
    if a.claude and a.target:
        ap.error('--claude لا يُجمع مع --target')
    if a.target:
        dest = Path(a.target)
    elif a.claude:
        dest = Path(a.project or Path.home()) / '.claude' / 'skills' / 'engineering-os'
    elif a.project:
        dest = Path(a.project) / '.agents' / 'skills' / 'engineering-os'
    else:
        dest = Path.home() / '.gemini' / 'config' / 'skills' / 'engineering-os'
    src = Path(__file__).resolve().parent
    dest.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        shutil.copy2(src / f, dest / f)
    for d in DIRS:
        shutil.copytree(src / d, dest / d, dirs_exist_ok=True)
    print(f'تم التثبيت في: {dest}')
    print('تنبيه: لا تُبقِ نسختين بنفس الاسم (عامة + مشروع) بإصدارين مختلفين.')
    print('نصيحة: أضف .agl/ إلى .gitignore في مشروعك (حالة البوابات والمهام الخلفية).')
    if a.claude:
        hook = {'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': [
            {'type': 'command', 'command': f'python3 {dest / "hook_pretooluse.py"}'}]}]}}
        print('\nللفرض الإلزامي أضف هذا إلى .claude/settings.json (لا يُعدَّل تلقائياً):')
        print(json.dumps(hook, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()