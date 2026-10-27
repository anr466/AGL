#!/usr/bin/env python3
"""install.py — يثبّت engineering-os كمهارة مع بواباتها في مكان واحد.
الاستخدام:
  python install.py                 # عام: ~/.gemini/config/skills/engineering-os
  python install.py --project DIR   # لمشروع: DIR/.agents/skills/engineering-os
  python install.py --target PATH   # مسار مخصص
يبقى gates.py بجانب SKILL.md فيجده الوكيل: python <مسار المهارة>/gates.py ..."""

import argparse
import shutil
from pathlib import Path

FILES = ['SKILL.md', 'gates.py', 'brain_score.py', 'BRAIN_TEST.md', 'LICENSE']


def main():
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument('--project')
    g.add_argument('--target')
    a = ap.parse_args()
    if a.target:
        dest = Path(a.target)
    elif a.project:
        dest = Path(a.project) / '.agents' / 'skills' / 'engineering-os'
    else:
        dest = Path.home() / '.gemini' / 'config' / 'skills' / 'engineering-os'
    src = Path(__file__).resolve().parent
    dest.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        shutil.copy2(src / f, dest / f)
    print(f'تم التثبيت في: {dest}')
    print('تنبيه: لا تُبقِ نسختين بنفس الاسم (عامة + مشروع) بإصدارين مختلفين.')


if __name__ == '__main__':
    main()