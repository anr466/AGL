#!/usr/bin/env python3
"""hook_pretooluse.py — فرض فعلي لا طوعي: يعترض كل أمر Bash قبل تنفيذه في Claude Code.

- مخالفة قابلة للموافقة  → permissionDecision = "ask": **المستخدم** هو من يوافق، لا الوكيل بتمرير --approved.
- مخالفة نهائية (rm / أو ~ أو جذر المشروع) → "deny".

التثبيت (.claude/settings.json في المشروع أو ~/.claude/settings.json):
{ "hooks": { "PreToolUse": [ { "matcher": "Bash",
    "hooks": [ { "type": "command", "command": "python3 /مسار/hook_pretooluse.py" } ] } ] } }

ملاحظة: اختُبر هنا بمحاكاة stdin فقط، لم يُشغَّل داخل Claude Code فعلياً."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gates import GateViolation, HardViolation, shell_guard  # noqa: E402


def decide(payload):
    if payload.get('tool_name') != 'Bash':
        return None
    cmd = (payload.get('tool_input') or {}).get('command', '')
    try:
        shell_guard(cmd)
    except HardViolation as e:
        return 'deny', str(e)
    except GateViolation as e:
        return 'ask', str(e)
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # لا نكسر الأداة بسبب مدخل غير مفهوم
    d = decide(payload)
    if d:
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                                                 'permissionDecision': d[0],
                                                 'permissionDecisionReason': d[1]}}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
