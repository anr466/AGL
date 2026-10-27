#!/usr/bin/env python3
"""gates_selftest.py — اختبار ذاتي حقيقي للبوابات. التشغيل: python gates_selftest.py"""

import sys
from gates import (GateViolation, verify_readback, StopRule, FileExclusivity,
                   unit_before_batch, classify_failure, FAILURE_TYPES, git_guard, _cli)

results = []


def check(name, fn):
    try:
        fn()
        results.append((name, True, ''))
    except Exception as e:  # noqa: BLE001
        results.append((name, False, repr(e)))


def raises(fn):
    try:
        fn()
    except GateViolation:
        return
    raise AssertionError('كان يجب أن ترمي GateViolation')


GOOD = {'stored': 'v', 'visible': True, 'timestamp': '2026-01-01T00:00:00'}

# 1 verify_readback
check('verify: نجاح كامل', lambda: verify_readback(3, lambda: (3, GOOD), 't')['checks'])
check('verify: عدّاد خاطئ', lambda: raises(lambda: verify_readback(3, lambda: (2, GOOD), 't')))
check('verify: دليل ناقص', lambda: raises(lambda: verify_readback(3, lambda: (3, {'stored': 'v'}), 't')))

# 2 StopRule
def stop_three():
    s = StopRule()
    s.record_failure('a', 'e1')
    s.record_failure('b', 'e2')
    raises(lambda: s.record_failure('c', 'e3'))


def stop_repeat_not_counted():
    s = StopRule()
    for _ in range(5):
        s.record_failure('same', 'e')  # نفس المسار — لا يُحسب مساراً جديداً


def can_retry():
    s = StopRule()
    s.record_failure('a', 'e')
    assert s.can_retry('b') and not s.can_retry('a')


check('stop: 3 مختلفة توقف', stop_three)
check('stop: المكرر لا يُحسب', stop_repeat_not_counted)
check('stop: can_retry', can_retry)

# 3 FileExclusivity
def excl():
    f = FileExclusivity()
    f.register_created('tmp.txt')
    assert f.allow_delete('tmp.txt')
    raises(lambda: f.allow_delete('user.txt'))
    raises(lambda: f.allow_overwrite('user.txt'))


check('files: حصرية', excl)

# 4 unit_before_batch
def unit_ok():
    assert unit_before_batch(lambda: True, lambda xs: len(xs), [1, 2, 3]) == 3


def unit_fail():
    called = []
    raises(lambda: unit_before_batch(lambda: False, lambda xs: called.append(1), [1]))
    assert not called


check('unit: نجاح ثم دفعة', unit_ok)
check('unit: فشل يمنع الدفعة', unit_fail)

# 5 classify_failure
def classify():
    for k in FAILURE_TYPES:
        assert classify_failure(k, 'w', 'x')['type'] == k
    raises(lambda: classify_failure('غير معروف', 'w', 'x'))


check('classify: أربعة أنواع ورفض المجهول', classify)


# 6 git_guard
def git_read_ok():
    for c in ('git status', 'git log -5 --oneline', 'git diff', 'git -c user.name=x status'):
        assert git_guard(c)


def git_write_blocked():
    for c in ('git commit -m x', 'git push origin main', 'git reset --hard HEAD~1', 'git clean -fd',
              'git checkout -- f.txt', 'git add -A', 'git add .', 'git push --force', 'git commit --no-verify',
              'git -c user.name=x commit -m y', 'git rebase main', 'git branch -D x'):
        raises(lambda c=c: git_guard(c))


def git_approved():
    assert git_guard('git commit -m x', approved=True)
    assert git_guard('git add README.md')


check('git: القراءة مسموحة', git_read_ok)
check('git: الكتابة/المدمر مرفوض', git_write_blocked)
check('git: الموافقة تسمح', git_approved)

# 7 CLI
check('cli: git يرفض برمز 1', lambda: (_ for _ in ()).throw(AssertionError()) if _cli(['git', 'git push']) != 1 else None)
check('cli: verify ينجح برمز 0', lambda: (_ for _ in ()).throw(AssertionError()) if _cli(
    ['verify', '--label', 't', '--expected', '2', '--actual', '2', '--stored', 'v', '--visible', 'y', '--timestamp', 'now']) != 0 else None)
check('cli: classify يرفض المجهول', lambda: (_ for _ in ()).throw(AssertionError()) if _cli(['classify', 'x', 'w', 'w']) != 1 else None)
passed = sum(1 for _, ok, _ in results if ok)
for name, ok, err in results:
    print(('✓ ' if ok else '✗ ') + name + (f'  {err}' if err else ''))
print(f'{passed}/{len(results)}')
sys.exit(0 if passed == len(results) else 1)
