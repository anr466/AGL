#!/usr/bin/env python3
"""recon.py — مرحلة «فهم المشروع» قبل أي تعديل. بلا اعتمادات (stdlib فقط).

كل حقيقة تُسجَّل بنوعها: documented (مقروءة الآن من ملف مذكور) أو inferred (استنتاج من قرائن، يُذكر بـ«يُرجّح»).
ما لا يُعرف يُعلَن في unknowns ولا يُخمَّن. الأداة لا تحكم بالمعنى — تجمع الوقائع وتكشف الفجوات.

  python recon.py scan [--root .]          يكتب .agl/recon.json ويطبع الملخص
  python recon.py search <كلمات...>        بحث إعادة الاستخدام: ما الموجود فعلاً قبل أن تبني؟
  python recon.py check                    exit 2 إن بقي مجهول حرج (تشغيل/اختبار)
"""
import argparse
import collections
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gates import _read_json, _write_json, state_path  # noqa: E402

SKIP = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'dist', 'build', '.agl', '.next', '.pytest_cache', 'target'}
AGENT_FILES = ('AGENTS.md', 'CLAUDE.md', 'GEMINI.md', '.cursorrules', 'CONTRIBUTING.md', 'ARCHITECTURE.md')
CONFIGS = ('pyproject.toml', 'setup.cfg', 'tox.ini', '.eslintrc', '.eslintrc.json', '.prettierrc', 'tsconfig.json',
           'ruff.toml', '.flake8', 'Makefile', 'Dockerfile', 'docker-compose.yml', '.editorconfig', 'pytest.ini')
MANIFESTS = {'package.json': 'node', 'pyproject.toml': 'python', 'requirements.txt': 'python', 'setup.py': 'python',
             'go.mod': 'go', 'Cargo.toml': 'rust', 'pom.xml': 'java', 'build.gradle': 'java', 'Gemfile': 'ruby',
             'composer.json': 'php'}


def fact(value, kind, source):
    return {'value': value, 'kind': kind, 'source': source}


def walk(root, limit=5000):
    out = []
    for d, dirs, files in os.walk(root):
        dirs[:] = sorted(x for x in dirs if x not in SKIP)
        for f in sorted(files):
            out.append(os.path.relpath(os.path.join(d, f), root))
            if len(out) >= limit:
                return out
    return out


def read(root, rel, n=200_000):
    try:
        with open(os.path.join(root, rel), encoding='utf-8', errors='replace') as f:
            return f.read(n)
    except OSError:
        return ''


def node_commands(root):
    out, pj = [], read(root, 'package.json')
    if not pj:
        return out
    try:
        scripts = json.loads(pj).get('scripts', {})
    except ValueError:
        return [fact('package.json غير صالح JSON', 'documented', 'package.json')]
    pm = 'pnpm' if os.path.exists(os.path.join(root, 'pnpm-lock.yaml')) else \
        'yarn' if os.path.exists(os.path.join(root, 'yarn.lock')) else 'npm'
    for k, v in scripts.items():
        out.append(fact({'name': k, 'cmd': f'{pm} run {k}', 'body': v}, 'documented', 'package.json:scripts'))
    return out


def python_commands(root, files):
    out = []
    pp = read(root, 'pyproject.toml') + read(root, 'pytest.ini') + read(root, 'tox.ini') + read(root, 'setup.cfg')
    tests = [f for f in files if re.search(r'(^|/)(test_[^/]*|[^/]*_test)\.py$', f)]
    if 'pytest' in pp or any('pytest' in read(root, r) for r in ('requirements.txt', 'requirements-dev.txt')):
        out.append(fact({'name': 'test', 'cmd': 'python -m pytest', 'body': ''}, 'documented', 'pytest في الإعدادات'))
    elif tests:
        out.append(fact({'name': 'test', 'cmd': 'python -m unittest discover' if not any(
            t.count('/') == 0 for t in tests) else f'python {tests[0]}', 'body': ''}, 'inferred',
            f'{len(tests)} ملف اختبار بلا إعداد مصرَّح'))
    return out


def readme_commands(root):
    txt = read(root, 'README.md') or read(root, 'readme.md')
    cmds = []
    for blk in re.findall(r'```(?:bash|sh|shell|console)?\n(.*?)```', txt, re.S):
        for ln in blk.splitlines():
            ln = ln.strip().lstrip('$ ').strip()
            if re.match(r'(python3?|pip|npm|pnpm|yarn|make|docker|cargo|go|node|pytest|uv|bash|\./)\b', ln):
                cmds.append(ln)
    return [fact(c, 'documented', 'README') for c in dict.fromkeys(cmds)][:25]


ENV_USE = [r'os\.environ\[[\'"](\w+)[\'"]\]', r'os\.environ\.get\([\'"](\w+)[\'"]', r'os\.getenv\([\'"](\w+)[\'"]',
           r'process\.env\.(\w+)']


def env_vars(root, files):
    documented, used = {}, {}
    for f in files:
        base = os.path.basename(f)
        if base in ('.env.example', '.env.sample', 'env.example'):
            for ln in read(root, f).splitlines():
                m = re.match(r'\s*([A-Z][A-Z0-9_]+)\s*=', ln)
                if m:
                    documented[m.group(1)] = f
    for f in files:
        if f.endswith(('.md', '.txt')) and 'README' in f.upper():
            for m in re.findall(r'(?:export\s+|\b)([A-Z][A-Z0-9_]{3,})=', read(root, f)):
                documented.setdefault(m, f)
        if f.endswith(('.py', '.js', '.ts', '.mjs', '.jsx', '.tsx')):
            src = read(root, f)
            for pat in ENV_USE:
                for m in re.findall(pat, src):
                    used.setdefault(m, f)
    skip = {'HOME', 'PATH', 'USER', 'PWD', 'SHELL', 'LANG', 'TMPDIR', 'NODE_ENV', 'CI', 'DEBUG', 'TERM'}
    undocumented = {k: v for k, v in used.items() if k not in documented and k not in skip}
    return ([fact(k, 'documented', v) for k, v in sorted(documented.items())],
            [fact(k, 'inferred', f'يُقرأ في {v} ولا يُوثَّق') for k, v in sorted(undocumented.items())])


def ports(root, files):
    seen = {}
    for f in files:
        if f.endswith(('.py', '.js', '.ts', '.md', '.yml', '.yaml', '.json', '.env.example')):
            for m in re.findall(r'(?:port|PORT|localhost:|127\.0\.0\.1:|0\.0\.0\.0:)\s*[=:]?\s*(\d{4,5})\b', read(root, f, 60_000)):
                if 1024 <= int(m) <= 65535:
                    seen.setdefault(int(m), f)
    return [fact(p, 'inferred', f'مذكور في {f}') for p, f in sorted(seen.items())][:8]


def surfaces(root, files, stacks):
    s = []
    htmls = [f for f in files if f.endswith('.html')]
    pj = read(root, 'package.json')
    if htmls or re.search(r'"(react|vue|svelte|next|vite|angular)"', pj):
        s.append(fact('web-ui', 'inferred', f'{len(htmls)} صفحة HTML' if htmls else 'إطار واجهة في package.json'))
    text = pj + read(root, 'requirements.txt') + read(root, 'pyproject.toml')
    if re.search(r'\b(fastapi|flask|django|express|koa|hapi|aiohttp|starlette)\b', text, re.I):
        s.append(fact('api', 'inferred', 'إطار خادم في الاعتمادات'))
    if re.search(r'"bin"\s*:', pj) or any(re.search(r'argparse|click|typer', read(root, f, 20_000)) for f in files
                                          if f.endswith('.py') and f.count('/') == 0):
        s.append(fact('cli', 'inferred', 'bin أو argparse/click'))
    return s


def entrypoints(root, files):
    out = []
    for f in files:
        if f.count('/') > 1:
            continue
        b = os.path.basename(f)
        if b in ('main.py', 'app.py', 'manage.py', 'server.py', 'index.js', 'server.js', 'main.go', 'index.html', 'cli.py'):
            out.append(fact(f, 'inferred', 'اسم ملف معتاد لنقطة الدخول'))
        elif f.endswith('.py') and "__main__" in read(root, f, 20_000) and f.count('/') == 0:
            out.append(fact(f, 'inferred', 'يحتوي __main__'))
    return out[:12]


def git_state(root):
    def g(*a):
        try:
            return subprocess.run(['git', '-C', root, *a], capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            return ''
    if not g('rev-parse', '--is-inside-work-tree'):
        return fact({'repo': False}, 'documented', 'git')
    dirty = [l for l in g('status', '--porcelain').splitlines() if l.strip()]
    return fact({'repo': True, 'branch': g('rev-parse', '--abbrev-ref', 'HEAD'), 'dirty_files': len(dirty),
                 'last': g('log', '-1', '--format=%h %s')}, 'documented', 'git')


def duplicates(files):
    by = collections.defaultdict(list)
    for f in files:
        by[os.path.splitext(os.path.basename(f))[0].lower().replace('-', '_')].append(f)
    return [fact(v, 'inferred', 'نفس الاسم الأساسي في أكثر من مكان — تحقق قبل أن تضيف نسخة') for k, v in by.items()
            if len(v) > 1 and k not in ('__init__', 'index', 'readme', 'license', 'main', 'test', 'setup', 'types', 'utils')][:12]


def scan(root='.'):
    root = os.path.abspath(root)
    files = walk(root)
    stacks = sorted({MANIFESTS[os.path.basename(f)] for f in files if os.path.basename(f) in MANIFESTS and f.count('/') <= 1})
    ext = collections.Counter(os.path.splitext(f)[1] or '(none)' for f in files)
    if not stacks:  # لا manifest: استنتج من الامتدادات
        stacks = [lang for e, lang in (('.py', 'python'), ('.js', 'node'), ('.ts', 'node'), ('.go', 'go'), ('.rs', 'rust'))
                  if ext.get(e)]
        stacks = sorted(set(stacks))
    docs_cmds = node_commands(root) + python_commands(root, files)
    envd, envu = env_vars(root, files)
    r = {
        'root': root, 'files': len(files),
        'stacks': [fact(s, 'documented' if any(os.path.basename(f) in MANIFESTS and MANIFESTS[os.path.basename(f)] == s
                                               for f in files) else 'inferred', 'manifest/امتدادات') for s in stacks],
        'commands': docs_cmds, 'readme_commands': readme_commands(root),
        'env_documented': envd, 'env_undocumented': envu, 'ports': ports(root, files),
        'surfaces': surfaces(root, files, stacks), 'entrypoints': entrypoints(root, files),
        'configs': [fact(f, 'documented', f) for f in files if os.path.basename(f) in CONFIGS and f.count('/') <= 1],
        'agent_rules': [fact(f, 'documented', f) for f in files if os.path.basename(f) in AGENT_FILES],
        'docs': [fact(f, 'documented', f) for f in files if f.lower().endswith('.md') and f.count('/') <= 1][:15],
        'git': git_state(root), 'extensions': dict(ext.most_common(8)), 'duplicates': duplicates(files),
    }
    r['unknowns'] = unknowns(r)
    return r


def unknowns(r):
    u = []
    has_test = any(c['value'].get('name') == 'test' for c in r['commands'] if isinstance(c['value'], dict)) or \
        any(re.search(r'\b(test|pytest|unittest)\b', c['value']) for c in r['readme_commands'])
    has_run = any(isinstance(c['value'], dict) and c['value'].get('name') in ('start', 'dev', 'serve') for c in r['commands']) \
        or any(re.search(r'\b(run|start|dev|serve|python3? \S+\.py|node \S+)\b', c['value']) for c in r['readme_commands']) \
        or bool(r['entrypoints'])
    if not r['stacks']:
        u.append({'what': 'لغة/إطار المشروع', 'critical': True, 'ask': 'ما التقنية المستخدمة؟ لا manifest ولا ملفات مصدر'})
    if not has_test:
        u.append({'what': 'أمر الاختبار', 'critical': True, 'ask': 'كيف تُشغَّل الاختبارات؟ لا أمر موثّق — لا تفترض'})
    if not has_run:
        u.append({'what': 'أمر التشغيل', 'critical': True, 'ask': 'كيف يُشغَّل المشروع؟ لا start/dev ولا نقطة دخول'})
    if r['env_undocumented']:
        u.append({'what': 'متغيرات بيئة غير موثقة: ' + ', '.join(f['value'] for f in r['env_undocumented'][:6]),
                  'critical': False, 'ask': 'ما قيمها الصالحة؟ الكود يقرؤها ولا .env.example يوثقها'})
    if r['git'].get('value', {}).get('dirty_files'):
        u.append({'what': f"عمل غير محفوظ في git ({r['git']['value']['dirty_files']} ملف)", 'critical': False,
                  'ask': 'هل هذه تغييرات المستخدم؟ لا تلمسها (القانون 6)'})
    if not r['agent_rules'] and not r['docs']:
        u.append({'what': 'اتفاقيات المشروع', 'critical': False, 'ask': 'لا توثيق — استخلص الاتفاقيات من الكود وأعلنها كاستنتاج'})
    return u


def summary(r):
    L = [f"المشروع: {r['root']} — {r['files']} ملف | " + ', '.join(f['value'] for f in r['stacks'])]
    for key, title in (('commands', 'أوامر موثقة'), ('readme_commands', 'أوامر README'), ('entrypoints', 'نقاط دخول'),
                       ('surfaces', 'أسطح (يحدد نوع عقد عين المستخدم)'), ('agent_rules', 'قواعد المشروع (تسبق مهارتنا)'),
                       ('duplicates', 'تكرار محتمل')):
        v = r[key]
        if v:
            show = [json.dumps(f['value'], ensure_ascii=False) if not isinstance(f['value'], str) else f['value'] for f in v[:6]]
            L.append(f"  {title} [{len(v)}]: " + ' | '.join(s[:70] for s in show))
    g = r['git']['value']
    if g.get('repo'):
        L.append(f"  git: {g['branch']} — {g['dirty_files']} ملف غير محفوظ — آخر: {g['last']}")
    L.append('  ما هو «مستنتج» (يُرجّح) لا «موثق»: ' + str(sum(1 for k in ('commands', 'surfaces', 'entrypoints', 'ports')
                                                              for f in r[k] if f['kind'] == 'inferred')) + ' عنصر')
    if r['unknowns']:
        L.append('  مجهول يُحسم قبل البناء:')
        for x in r['unknowns']:
            L.append(f"    {'✗ حرج' if x['critical'] else '·'} {x['what']} ← {x['ask']}")
    return '\n'.join(L)


def search(root, words):
    """إعادة الاستخدام: أين تظهر هذه الكلمات (أسماء ملفات + تعريفات + نصوص)؟"""
    root = os.path.abspath(root)
    hits = []
    pats = [re.compile(re.escape(w), re.I) for w in words]
    for f in walk(root):
        name = f.lower()
        sc = sum(1 for p in pats if p.search(name)) * 3
        if f.endswith(('.py', '.js', '.ts', '.go', '.rs', '.md', '.html', '.json', '.yml', '.yaml', '.toml', '.sh')):
            txt = read(root, f, 100_000)
            for ln_no, ln in enumerate(txt.splitlines(), 1):
                m = sum(1 for p in pats if p.search(ln))
                if m:
                    sc += m
                    if re.match(r'\s*(def|class|function|const|export|func|fn|pub)\b', ln) and m:
                        hits.append((m * 5, f'{f}:{ln_no}', ln.strip()[:90]))
        if sc:
            hits.append((sc, f, ''))
    hits.sort(key=lambda h: -h[0])
    return hits[:15]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('scan'); s.add_argument('--root', default='.'); s.add_argument('--json', action='store_true')
    q = sp.add_parser('search'); q.add_argument('words', nargs='+'); q.add_argument('--root', default='.')
    sp.add_parser('check')
    a = ap.parse_args(argv)
    if a.cmd == 'scan':
        r = scan(a.root)
        _write_json(state_path('recon.json'), r)
        print(json.dumps(r, ensure_ascii=False, indent=1) if a.json else summary(r))
        return 0
    if a.cmd == 'search':
        for sc, where, ln in search(a.root, a.words):
            print(f'{sc:>3}  {where}  {ln}')
        return 0
    if a.cmd == 'check':
        r = _read_json(state_path('recon.json'), None)
        if not r:
            print('لا recon.json — شغّل scan أولاً', file=sys.stderr)
            return 3
        crit = [x for x in r['unknowns'] if x['critical']]
        for x in crit:
            print(f"✗ {x['what']} ← {x['ask']}")
        print('جاهز للبناء' if not crit else f'{len(crit)} مجهول حرج — اسأل قبل أن تبني')
        return 2 if crit else 0
    return 0


if __name__ == '__main__':
    sys.exit(main())
