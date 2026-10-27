#!/usr/bin/env python3
"""gates.py — البوابات الإجبارية: تحويل قوانين engineering-os إلى كود يفرض نفسه.

الفلسفة: القاعدة النصية تُنسى تحت الضغط — القاعدة داخل الأداة أصعب تجاوزاً.
ملاحظة صدق: البوابات تفحص ما يُمرَّر لها؛ صدق مصدر الأدلة مسؤولية المستدعي.
للفرض الفعلي (لا الطوعي) استخدم hook_pretooluse.py الذي يعترض أوامر Bash قبل تنفيذها."""

import difflib
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime

try:
    import fcntl
except ImportError:  # ويندوز
    fcntl = None


class GateViolation(Exception):
    """البوابة رفضت الخطوة — التوقف إجباري وليس اختيارياً."""


class HardViolation(GateViolation):
    """رفض نهائي: لا تفتحه موافقة (جذر النظام، مجلد المنزل، جذر المشروع...)."""


class SimilarPath(GateViolation):
    """المسار الجديد يشبه مساراً سابقاً — يلزم توضيح الفرق الجوهري."""


# ═══ حالة المشروع (.agl/) ═══
def project_root(start=None):
    base = os.path.abspath(start or os.getcwd())
    p = base
    while True:
        if os.path.exists(os.path.join(p, '.git')):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            return base
        p = parent


def state_path(name):
    d = os.environ.get('AGL_STATE_DIR') or os.path.join(project_root(), '.agl')
    return os.path.join(d, name)


def _read_json(path, default):
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(path, data):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    tmp = f'{path}.{os.getpid()}.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


class _Lock:
    """قفل ملف بسيط لحماية القراءة-ثم-الكتابة عند تعدد العمليات (وكلاء الخلفية)."""

    def __init__(self, path):
        self.path = path + '.lock'
        self.f = None

    def __enter__(self):
        os.makedirs(os.path.dirname(self.path) or '.', exist_ok=True)
        self.f = open(self.path, 'w')
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        if fcntl:
            fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


# ═══ بوابة 1: التحقق الكافي ═══
_TRUE = {'yes', 'true', '1', 'y', 'ok', 'نعم'}
_FALSE = {'', 'no', 'false', '0', 'none', 'null', 'n', 'لا', 'nan'}


def _is_true_flag(v):
    """علامة منطقية صريحة: 'no' و'false' ليسا صحيحين."""
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return v != 0
    return str(v).strip().lower() in _TRUE


def _has_value(v):
    """قيمة مخزنة: أي قيمة غير فارغة وليست نفياً صريحاً."""
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() not in _FALSE


def _valid_timestamp(v):
    """طابع زمني حقيقي: ISO-8601 أو epoch موجب — لا نص حر مثل 'now'."""
    if isinstance(v, bool) or v is None:
        return False
    if isinstance(v, (int, float)):
        return v > 0
    s = str(v).strip()
    try:
        return float(s) > 0
    except ValueError:
        pass
    try:
        datetime.fromisoformat(s.replace('Z', '+00:00'))
        return True
    except ValueError:
        return False


def verify_readback(expected_count, readback_fn, label):
    """بوابة التحقق الكافي: قراءة عكسية من المصدر بعد كل عملية.
    evidence_dict: stored (قيمة) / visible (علامة صريحة) / timestamp (ISO أو epoch)."""
    actual, evidence = readback_fn()
    checks = {
        'العدّاد الفعلي': actual == expected_count,
        'القيمة المخزنة': _has_value(evidence.get('stored')),
        'الحالة المرئية': _is_true_flag(evidence.get('visible')),
        'السجل الزمني': _valid_timestamp(evidence.get('timestamp')),
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise GateViolation(f'[{label}] فشل التحقق الكافي — الفحوص الناقصة: {", ".join(failed)} | '
                            f'المتوقع {expected_count}، الفعلي {actual}')
    return {'actual': actual, 'evidence': evidence, 'checks': checks}


# ═══ بوابة 2: قاعدة الإيقاف (3 مسارات مختلفة، مع كشف التشابه) ═══
def _norm_sig(s):
    return ' '.join(re.sub(r'[\W_]+', ' ', str(s).lower()).split())


def similar_signatures(a, b):
    """تشابه معجمي: لا يلتقط المرادفات (adjust≈fix) لذلك يُكمَّل بشرط «الفرق الجوهري»."""
    na, nb = _norm_sig(a), _norm_sig(b)
    ta, tb = set(na.split()), set(nb.split())
    if not ta or not tb:
        return False
    if ta <= tb or tb <= ta:
        return True
    if len(ta & tb) / len(ta | tb) >= 0.6:
        return True
    if min(len(na), len(nb)) >= 25 and difflib.SequenceMatcher(None, na, nb).ratio() >= 0.8:
        return True
    return False


class StopRule:
    """عدّاد المسارات الفاشلة المختلفة. 3 مسارات مختلفة فشلت = توقف إجباري وصعود مُسبَّب.
    المسار المطابق لا يُحسب. المسار المشابه (لا المطابق) يُرفض ما لم يُكتب الفرق الجوهري (≥20 حرفاً)."""

    def __init__(self, max_distinct=3):
        self.max = max_distinct
        self.tried = []  # (signature, error)
        self.diffs = {}  # signature -> الفرق الجوهري

    def _distinct(self):
        return len({_norm_sig(s) for s, _ in self.tried})

    def can_retry(self, new_signature):
        n = _norm_sig(new_signature)
        return all(n != _norm_sig(s) for s, _ in self.tried)

    def find_similar(self, signature):
        n = _norm_sig(signature)
        for s, _ in self.tried:
            if _norm_sig(s) != n and similar_signatures(s, signature):
                return s
        return None

    def record_failure(self, signature, error, diff=None):
        n = _norm_sig(signature)
        is_new = all(n != _norm_sig(s) for s, _ in self.tried)
        if is_new:
            near = self.find_similar(signature)
            if near and not (diff and len(diff.strip()) >= 20):
                raise SimilarPath(
                    f'المسار «{signature}» يشبه «{near}» — إن كان مساراً مختلفاً فعلاً '
                    f'اكتب الفرق الجوهري (≥20 حرفاً) عبر --diff، وإلا فهو نفس المسار.')
            if diff:
                self.diffs[signature] = diff.strip()
        self.tried.append((signature, str(error)[:120]))
        distinct = self._distinct()
        if distinct >= self.max:
            report = '\n'.join(f'- {s}: {e}' for s, e in self.tried)
            raise GateViolation(
                f'قاعدة الإيقاف: {distinct} مسارات مختلفة فشلت — توقف إجباري، صعود مُسبَّب:\n{report}\n'
                f'المطلوب من الإنسان: مراجعة المسارات أعلاه وتحديد الاتجاه.')
        warnings = []
        last = [_norm_sig(e) for _, e in self.tried[-3:]]
        if len(last) == 3 and len(set(last)) == 1 and last[0]:
            warnings.append('نفس رسالة الخطأ 3 مرات متتالية — غالباً الجذر لم يتغير رغم تغيّر «المسار».')
        return {'distinct': distinct, 'warnings': warnings}


# ═══ بوابة 3: حصرية الملفات ═══
def _is_git_tracked(path):
    d = os.path.dirname(path)
    if not os.path.isdir(d):
        return False
    try:
        r = subprocess.run(['git', 'ls-files', '--error-unmatch', '--', path],
                           cwd=d, capture_output=True, timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _under(p, roots):
    return any(p == c or p.startswith(c.rstrip(os.sep) + os.sep) for c in roots)


class FileExclusivity:
    """ما أنشأه الوكيل هذه المهمة فقط له حق الحذف/التعديل الحُر.
    قاعدة التسجيل: سجّل المسار **قبل** إنشائه. مسار موجود مسبقاً لا يُسجَّل (وإلا لسجّل الوكيل ملفات المستخدم).
    ملف متتبَّع في git لا يُحذف حتى لو سُجّل. persist: مسار json لحفظ الحالة بين الاستدعاءات."""

    def __init__(self, persist=None):
        self.persist = persist
        self.created = set(_read_json(persist, [])) if persist else set()

    def _save(self):
        if self.persist:
            _write_json(self.persist, sorted(self.created))

    def register_created(self, path):
        p = os.path.abspath(str(path))
        root = project_root()
        if p == os.path.abspath(os.sep) or p == os.path.expanduser('~') or root == p or root.startswith(p + os.sep):
            raise HardViolation(f'لا يُسجَّل «{p}» كملف منشأ: جذر/منزل/مشروع.')
        if os.path.exists(p) and p not in self.created:
            raise GateViolation(f'«{p}» موجود مسبقاً — ليس من إنشائك. سجّل المسار قبل الإنشاء لا بعده.')
        self.created.add(p)
        self._save()

    def allow_delete(self, path):
        raw = str(path)
        p = os.path.abspath(os.path.expanduser(raw))
        if _under(p, self.created):
            if _is_git_tracked(p):
                raise GateViolation(f'رفض «{raw}»: مسجَّل لكنه متتبَّع في git — ملف مستقر لا يُحذف.')
            return True
        raise GateViolation(
            f'رفض حذف/تعديل «{raw}»: ليس من إنشاء الوكيل في هذه المهمة — '
            f'ملفات المستخدم والإنتاج لا تُمس دون موافقة صريحة.')

    def allow_overwrite(self, path):
        return self.allow_delete(path)


# ═══ بوابة 4: قاعدة الوحدة قبل الدفعة ═══
def unit_before_batch(unit_fn, batch_fn, batch_args_list):
    if not unit_fn():
        raise GateViolation('فشلت الوحدة الأولى — الدفعة موقوفة. افحص الافتراضات: البنية، المصادقة، المدخلات.')
    return batch_fn(batch_args_list)


# ═══ بوابة 5: تصنيف الفشل الرباعي ═══
FAILURE_TYPES = {
    'افتراض': 'أعد فتح مرحلة الفهم — اختبر الوحدة يدوياً ثم أعد البناء',
    'تنفيذ': 'صحح الجذر مرة في الكود المشترك — لا ترقيع كل caller',
    'فهم': 'ارجع للمستخدم/المواصفة — لا تنفذ أكثر على فهم خاطئ',
    'بيئة': 'أعد المصادقة/البيئة ثم أعد — لا تعدّل الكود لخلل بيئة',
}


def classify_failure(kind, where, what):
    if kind not in FAILURE_TYPES:
        raise GateViolation(f'تصنيف فشل غير معروف «{kind}» — المسموح: {", ".join(FAILURE_TYPES)}')
    return {'type': kind, 'protocol': FAILURE_TYPES[kind], 'where': where[:80], 'what': what[:120]}


# ═══ تحليل الشل (أساس git_guard و shell_guard) ═══
_WRAPPERS = {'sudo', 'env', 'command', 'nohup', 'time', 'exec', 'builtin', 'xargs', 'nice',
             'ionice', 'stdbuf', 'timeout'}
_SHELLS = {'sh', 'bash', 'zsh', 'dash', 'ksh'}
_ASSIGN = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*=')


def _tokenize(command):
    try:
        lex = shlex.shlex(command.replace('\n', ' ; '), posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        return list(lex)
    except ValueError:
        raise GateViolation(f'أمر غير مفهوم: {command}')


def _simple_commands(command, depth=0):
    """يفكك أمر الشل إلى أوامر بسيطة: يقسم على && || ; | ويفتح sh -c و$(...) والرموز الخلفية."""
    if depth > 4:
        raise GateViolation('تداخل أوامر عميق جداً — مرفوض.')
    out = []
    for inner in re.findall(r'\$\(([^()]*)\)', command) + re.findall(r'`([^`]*)`', command):
        out += _simple_commands(inner, depth + 1)
    seg, segs = [], []
    for t in _tokenize(command):
        if t and set(t) <= set(';&|()'):
            if seg:
                segs.append(seg)
            seg = []
        else:
            seg.append(t)
    if seg:
        segs.append(seg)
    for s in segs:
        while s and _ASSIGN.match(s[0]):
            s = s[1:]
        had_xargs = False
        while s and os.path.basename(s[0]) in _WRAPPERS:
            had_xargs = had_xargs or os.path.basename(s[0]) == 'xargs'
            w = os.path.basename(s[0])
            s = s[1:]
            while s and (s[0].startswith('-') or _ASSIGN.match(s[0])):
                s = s[1:]
            if w == 'timeout' and s:
                s = s[1:]
        if not s:
            continue
        if os.path.basename(s[0]) in _SHELLS:
            idx = next((i for i, a in enumerate(s[1:], 1) if re.fullmatch(r'-[a-z]*c[a-z]*', a)), None)
            if idx is not None and idx + 1 < len(s):
                out += _simple_commands(s[idx + 1], depth + 1)
                continue
        out.append((['__xargs__'] if had_xargs else []) + s)
    return out


# ═══ بوابة 6: حارس git ═══
_GIT_OPT_WITH_VAL = {'-C', '-c', '--git-dir', '--work-tree', '--namespace', '--exec-path',
                     '--super-prefix', '--config-env'}
_HISTORY_WRITERS = {'commit', 'push', 'pull', 'rebase', 'merge', 'cherry-pick', 'revert', 'am',
                    'filter-branch', 'update-ref', 'replace', 'notes'}
_TAG_READ = {'-l', '--list', '-n', '--contains', '--no-contains', '--merged', '--no-merged',
             '--points-at', '--sort', '-v', '--verify'}


def _has(args, *names):
    return any(a in names or any(n.startswith('--') and a.startswith(n + '=') for n in names) for a in args)


def _short_cluster(args, ch):
    return any(re.fullmatch(r'-[A-Za-z]+', a) and ch in a[1:] for a in args)


def _git_reasons(args):
    i = 0
    while i < len(args) and args[i].startswith('-'):
        i += 2 if args[i] in _GIT_OPT_WITH_VAL else 1
    sub = args[i] if i < len(args) else ''
    rest = args[i + 1:]
    r = []
    force = _has(rest, '--force', '--force-with-lease', '-f') or _short_cluster(rest, 'f')
    if sub in _HISTORY_WRITERS:
        r.append(f'git {sub} يكتب على التاريخ')
    if sub == 'tag' and rest and not _has(rest, *_TAG_READ):
        r.append('git tag ينشئ/يحذف وسماً')
    if sub == 'stash' and not (rest and rest[0] in {'list', 'show'}):
        r.append('git stash يغيّر الشجرة العاملة')
    if sub == 'reset' and _has(rest, '--hard', '--merge', '--keep'):
        r.append('reset --hard مدمر')
    if sub == 'clean' and not _has(rest, '-n', '--dry-run'):
        r.append('clean يحذف ملفات غير متتبعة')
    if sub == 'checkout' and ('--' in rest or '.' in rest or force or _has(rest, '-B')):
        r.append('checkout يتجاهل/يكتب فوق تعديلات غير محفوظة')
    if sub == 'restore' and not (_has(rest, '--staged', '-S') and not _has(rest, '--worktree', '-W')):
        r.append('restore يتجاهل تعديلات الشجرة العاملة')
    if sub == 'switch' and (force or _has(rest, '--discard-changes', '-C')):
        r.append('switch يتجاهل تعديلات غير محفوظة')
    if sub == 'branch' and (_has(rest, '-d', '-D', '--delete', '-m', '-M', '--move') or force):
        r.append('تغيير/حذف فرع')
    if sub in {'rm', 'gc', 'prune'} or (sub == 'reflog' and _has(rest, 'expire', 'delete')):
        r.append(f'git {sub} يحذف')
    if sub == 'add' and (_has(rest, '-A', '--all', '.', ':/', '-u') or force):
        r.append('add أعمى/قسري — حدّد الملفات')
    if _has(rest, '--no-verify'):
        r.append('تجاوز الفحوص (--no-verify)')
    if force and sub in {'push', 'pull', 'rebase', 'merge', 'commit'}:
        r.append('خيار قسري')
    return list(dict.fromkeys(r))


def git_guard(command, approved=False):
    """يفحص أمر git (حتى لو داخل سلسلة && أو sh -c أو بعد -C). approved=True يمررها المستدعي —
    للفرض الحقيقي لا تعتمد عليها: استخدم hook_pretooluse.py الذي يسأل المستخدم نفسه."""
    reasons = []
    for toks in _simple_commands(command):
        toks = [t for t in toks if t != '__xargs__']
        if toks and os.path.basename(toks[0]) == 'git':
            reasons += _git_reasons(toks[1:])
    if reasons and not approved:
        raise GateViolation('حارس git رفض: ' + '؛ '.join(dict.fromkeys(reasons)) +
                            ' — يلزم طلب/موافقة صريحة من المستخدم.')
    return True


# ═══ بوابة 7: حارس الشل العام (حذف/كتابة فوق/أوامر مدمرة) ═══
_GLOB = re.compile(r'[*?\[]')


def _rm_reasons(args, excl, xargs):
    reasons, hard = [], []
    if _has(args, '--no-preserve-root'):
        hard.append('--no-preserve-root')
    targets, after = [], False
    for a in args:
        if after or not a.startswith('-'):
            targets.append(a)
        elif a == '--':
            after = True
    if xargs and not targets:
        reasons.append('xargs rm: الأهداف غير معروفة مسبقاً')
    home, root = os.path.expanduser('~'), project_root()
    for t in targets:
        if t in {'~', '$HOME', '/', '/*', '~/*', '.', '..', '*', './*'}:
            hard.append(f'rm على «{t}»')
            continue
        p = os.path.abspath(os.path.expanduser(t))
        if p in {os.path.abspath(os.sep), home} or root == p or root.startswith(p + os.sep):
            hard.append(f'rm على «{t}» (جذر/منزل/مشروع)')
            continue
        if _GLOB.search(t):
            reasons.append(f'rm بنمط «{t}» لا يمكن التحقق من نطاقه')
            continue
        try:
            excl.allow_delete(p)
        except GateViolation:
            reasons.append(f'rm «{t}»: ليس من إنشاء الوكيل')
    return reasons, hard


def shell_guard(command, approved=False, exclusivity=None):
    """بوابة موحّدة لأي أمر Bash. ترجع True أو ترمي GateViolation (قابل للموافقة) / HardViolation (نهائي)."""
    excl = exclusivity or FileExclusivity(persist=state_path('created.json'))
    reasons, hard = [], []
    for toks in _simple_commands(command):
        xargs = bool(toks) and toks[0] == '__xargs__'
        toks = [t for t in toks if t != '__xargs__']
        if not toks:
            continue
        name, args = os.path.basename(toks[0]), toks[1:]
        if name == 'git':
            reasons += _git_reasons(args)
        elif name == 'rm':
            r, h = _rm_reasons(args, excl, xargs)
            reasons += r
            hard += h
        elif name == 'shred' or name.startswith('mkfs'):
            reasons.append(f'{name} مدمر')
        elif name == 'dd' and any(a.startswith('of=') for a in args):
            reasons.append('dd يكتب على هدف')
        elif name == 'truncate':
            reasons.append('truncate يقتطع ملفاً')
        elif name == 'find' and ('-delete' in args or '-exec' in args):
            reasons.append('find -delete/-exec قد يحذف')
        elif name in {'chmod', 'chown', 'chgrp'} and _has(args, '-R', '--recursive'):
            reasons.append(f'{name} -R تغيير صلاحيات متكرر')
        for k, t in enumerate(toks[:-1]):
            if t == '>':
                tgt = toks[k + 1]
                if tgt.startswith('/dev/'):
                    continue
                p = os.path.abspath(os.path.expanduser(tgt))
                if os.path.exists(p) and not _under(p, excl.created):
                    reasons.append(f'«>» يكتب فوق ملف موجود «{tgt}» ليس من إنشاء الوكيل')
    if hard:
        raise HardViolation('حارس الشل (نهائي): ' + '؛ '.join(dict.fromkeys(hard)))
    if reasons and not approved:
        raise GateViolation('حارس الشل رفض: ' + '؛ '.join(dict.fromkeys(reasons)) +
                            ' — يلزم موافقة صريحة من المستخدم.')
    return True


# ═══ واجهة سطر الأوامر: python gates.py <أمر> ═══
def _cli(argv=None):
    import argparse
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, 'reconfigure'):
            s.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(prog='gates.py', description='بوابات engineering-os')
    sp = ap.add_subparsers(dest='cmd', required=True)
    v = sp.add_parser('verify', help='التحقق الكافي: أدلة القراءة العكسية الأربعة')
    v.add_argument('--label', required=True)
    v.add_argument('--expected', type=int, required=True)
    v.add_argument('--actual', type=int, required=True)
    v.add_argument('--stored', default='')
    v.add_argument('--visible', default='')
    v.add_argument('--timestamp', default='')
    c = sp.add_parser('classify', help='تصنيف فشل: افتراض|تنفيذ|فهم|بيئة')
    c.add_argument('kind'); c.add_argument('where'); c.add_argument('what')
    g = sp.add_parser('git', help='فحص أمر git قبل تنفيذه')
    g.add_argument('command'); g.add_argument('--approved', action='store_true')
    sh = sp.add_parser('shell', help='فحص أي أمر شل (git/rm/dd/...) قبل تنفيذه')
    sh.add_argument('command'); sh.add_argument('--approved', action='store_true')
    fl = sp.add_parser('files', help='حصرية الملفات: register (قبل الإنشاء) | check | list')
    fl.add_argument('action', choices=['register', 'check', 'list']); fl.add_argument('paths', nargs='*')
    s = sp.add_parser('stop', help='تسجيل مسار فاشل (حالة في .agl/stop.json)')
    s.add_argument('--state', default=None)
    s.add_argument('--sig', required=True); s.add_argument('--err', default='')
    s.add_argument('--diff', default=None, help='الفرق الجوهري عن المسار المشابه (≥20 حرفاً)')
    s.add_argument('--reset', action='store_true')
    a = ap.parse_args(argv)
    try:
        if a.cmd == 'verify':
            ts = datetime.now().isoformat() if a.timestamp.strip().lower() == 'now' else a.timestamp
            ev = {'stored': a.stored, 'visible': a.visible, 'timestamp': ts}
            r = verify_readback(a.expected, lambda: (a.actual, ev), a.label)
            print(json.dumps(r['checks'], ensure_ascii=False))
        elif a.cmd == 'classify':
            print(json.dumps(classify_failure(a.kind, a.where, a.what), ensure_ascii=False))
        elif a.cmd == 'git':
            git_guard(a.command, a.approved)
            print('مسموح')
        elif a.cmd == 'shell':
            shell_guard(a.command, a.approved)
            print('مسموح')
        elif a.cmd == 'files':
            fe = FileExclusivity(persist=state_path('created.json'))
            if a.action == 'list':
                print(json.dumps(sorted(fe.created), ensure_ascii=False))
            else:
                for p in a.paths:
                    fe.register_created(p) if a.action == 'register' else fe.allow_delete(p)
                print('تم' if a.action == 'register' else 'مسموح')
        elif a.cmd == 'stop':
            path = a.state or state_path('stop.json')
            with _Lock(path):
                if a.reset and os.path.exists(path):
                    os.remove(path)
                raw = _read_json(path, {})
                st = StopRule()
                st.tried = [tuple(x) for x in (raw if isinstance(raw, list) else raw.get('tried', []))]
                st.diffs = {} if isinstance(raw, list) else raw.get('diffs', {})
                if not st.can_retry(a.sig):
                    raise GateViolation(f'المسار «{a.sig}» جُرّب سابقاً — غيّر الطريقة فعلاً.')
                res, err = None, None
                try:
                    res = st.record_failure(a.sig, a.err, a.diff)
                except SimilarPath:
                    raise
                except GateViolation as e:
                    err = e
                _write_json(path, {'tried': st.tried, 'diffs': st.diffs})
                if err:
                    raise err
            print(f'مسارات مختلفة فاشلة: {res["distinct"]}/{st.max}')
            for w in res['warnings']:
                print('تحذير:', w)
    except GateViolation as e:
        print(str(e), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(_cli())
