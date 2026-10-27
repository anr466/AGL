#!/usr/bin/env python3
"""jobs.py — مهام خلفية للوكيل: أطلق أمراً طويلاً (اختبارات، بناء، فحص) ثم واصل العمل أو استقبل أمراً آخر،
واسأل عن النتيجة لاحقاً بدل انتظار انتهائه داخل الرد.

كل أمر يمرّ أولاً عبر shell_guard (نفس حماية البوابات). الحالة في .agl/jobs/<id>/.
python jobs.py start "<أمر>" [--name N] [--timeout S] [--approved]
python jobs.py list | status ID | tail ID [-n 20] | wait ID... [--timeout S] | result ID | cancel ID

نص `result` مصمَّم ليكون «دليلاً طازجاً» للقانون الحديدي: الأمر + رمز الخروج + المدة + آخر المخرجات.

حدود صدق: هذا يوازي تنفيذ **الأوامر**. توازي *وكلاء النموذج* نفسه (subagents تفكّر بالتوازي)
يوفّره المحرر/المنصة (مثل Claude Code: subagents و run_in_background) ولا يمكن لسكربت تقليده."""

import json
import os
import signal
import subprocess
import sys
import time
import uuid

if os.name == 'nt':
    sys.exit('jobs.py يعمل على Linux/macOS فقط (يعتمد على مجموعات العمليات POSIX).')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gates import GateViolation, shell_guard, state_path, _read_json, _write_json  # noqa: E402


def jobs_dir():
    return os.path.join(os.path.dirname(state_path('x')), 'jobs')


def _jdir(jid):
    return os.path.join(jobs_dir(), jid)


def _meta(jid):
    return _read_json(os.path.join(_jdir(jid), 'meta.json'), None)


def _save(jid, m):
    _write_json(os.path.join(_jdir(jid), 'meta.json'), m)


def _alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    try:  # العملية الزومبي (انتهت ولم تُحصد) تُعدّ ميتة
        with open(f'/proc/{pid}/stat') as f:
            return f.read().rsplit(')', 1)[1].split()[0] != 'Z'
    except (OSError, IndexError):
        return True


def _fresh(jid):
    """يُصلح الحالة: running بلا عملية حية = lost."""
    m = _meta(jid)
    if m and m['status'] == 'running':
        pid = m.get('runner_pid')
        if pid and not _alive(pid):
            m = _meta(jid)  # أعد القراءة: ربما انتهى للتو
            if m['status'] == 'running':
                m['status'], m['end'] = 'lost', time.time()
                _save(jid, m)
    return m


def start(command, name=None, timeout=None, approved=False):
    shell_guard(command, approved)  # يرمي GateViolation إن رُفض
    jid = time.strftime('%H%M%S-') + uuid.uuid4().hex[:4]
    os.makedirs(_jdir(jid), exist_ok=True)
    _save(jid, {'id': jid, 'name': name or command[:40], 'command': command, 'status': 'running',
                'start': time.time(), 'timeout': timeout, 'cwd': os.getcwd()})
    env = dict(os.environ, AGL_STATE_DIR=os.path.dirname(state_path('x')))
    p = subprocess.Popen([sys.executable, os.path.abspath(__file__), '_run', jid],
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True, env=env)
    m = _meta(jid)
    m['runner_pid'] = p.pid
    _save(jid, m)
    return jid


def _run(jid):
    m = _meta(jid)
    log = open(os.path.join(_jdir(jid), 'out.log'), 'wb')
    child = subprocess.Popen(m['command'], shell=True, cwd=m['cwd'], stdout=log, stderr=subprocess.STDOUT,
                             stdin=subprocess.DEVNULL, start_new_session=True)
    m = _meta(jid)
    m['pid'] = child.pid
    _save(jid, m)
    try:
        code = child.wait(timeout=m.get('timeout'))
        status = 'done' if code == 0 else 'failed'
    except subprocess.TimeoutExpired:
        os.killpg(child.pid, signal.SIGKILL)
        code, status = -9, 'timeout'
    m = _meta(jid)
    if m['status'] == 'cancelled':
        return
    m.update(status=status, exit_code=code, end=time.time())
    _save(jid, m)


def tail(jid, n=20):
    try:
        with open(os.path.join(_jdir(jid), 'out.log'), encoding='utf-8', errors='replace') as f:
            return ''.join(f.readlines()[-n:])
    except OSError:
        return ''


def wait(jids, timeout=None):
    t0 = time.time()
    while True:
        ms = [_fresh(j) for j in jids]
        if all(m and m['status'] != 'running' for m in ms):
            return ms
        if timeout is not None and time.time() - t0 > timeout:
            return ms
        time.sleep(0.2)


def cancel(jid):
    m = _fresh(jid)
    if not m or m['status'] != 'running':
        return False
    m['status'], m['end'] = 'cancelled', time.time()
    _save(jid, m)
    for pid in (m.get('pid'), m.get('runner_pid')):
        if pid:
            try:
                os.killpg(pid, signal.SIGTERM)
            except OSError:
                pass
    return True


def result(jid, n=15):
    m = _fresh(jid)
    if not m:
        raise GateViolation(f'مهمة غير موجودة: {jid}')
    dur = (m.get('end') or time.time()) - m['start']
    return (f"[{m['id']}] {m['name']}\nالأمر: {m['command']}\nالحالة: {m['status']} | "
            f"رمز الخروج: {m.get('exit_code', '—')} | المدة: {dur:.1f}ث\n--- آخر المخرجات ---\n{tail(jid, n)}")


def main(argv=None):
    import argparse
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, 'reconfigure'):
            s.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(prog='jobs.py')
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('start'); s.add_argument('command'); s.add_argument('--name')
    s.add_argument('--timeout', type=float); s.add_argument('--approved', action='store_true')
    sp.add_parser('list')
    for c in ('status', 'result', 'cancel'):
        sp.add_parser(c).add_argument('id')
    t = sp.add_parser('tail'); t.add_argument('id'); t.add_argument('-n', type=int, default=20)
    w = sp.add_parser('wait'); w.add_argument('ids', nargs='+'); w.add_argument('--timeout', type=float)
    r = sp.add_parser('_run'); r.add_argument('id')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'start':
            print(start(a.command, a.name, a.timeout, a.approved))
        elif a.cmd == '_run':
            _run(a.id)
        elif a.cmd == 'list':
            d = jobs_dir()
            for j in sorted(os.listdir(d)) if os.path.isdir(d) else []:
                m = _fresh(j)
                if m:
                    print(f"{m['id']}  {m['status']:9} {m['name']}")
        elif a.cmd == 'status':
            m = _fresh(a.id)
            print(json.dumps(m, ensure_ascii=False) if m else 'غير موجودة')
        elif a.cmd == 'tail':
            print(tail(a.id, a.n), end='')
        elif a.cmd == 'wait':
            ms = wait(a.ids, a.timeout)
            for m in ms:
                print(f"{m['id']} {m['status']} exit={m.get('exit_code', '—')}")
            return 0 if all(m['status'] == 'done' for m in ms) else 1
        elif a.cmd == 'result':
            print(result(a.id))
        elif a.cmd == 'cancel':
            print('أُلغيت' if cancel(a.id) else 'ليست قيد التشغيل')
    except GateViolation as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
