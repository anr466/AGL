#!/usr/bin/env python3
"""test_ux_gate.py — اختبارات بوابة «عين المستخدم». الاختبارات البرمجية البحتة تعمل في أي بيئة؛
اختبارات المتصفح تُتخطّى تلقائياً إن لم يتوفر Playwright (لا تفشل CI)."""
import copy
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ['AGL_STATE_DIR'] = tempfile.mkdtemp()
import ux_gate as U  # noqa: E402


REQ = 'أريد أن أطلب قهوة بضغطة واحدة وأن أرى أثر الإضافة وأفهم الخطأ'


def good_contract():
    return {'type': 'web', 'locale': 'ar', 'base': '', 'request': REQ,
            'request_parts': ['أطلب قهوة بضغطة واحدة', 'أرى أثر الإضافة', 'أفهم الخطأ'],
            'out_of_scope': {},
            'persona': {'name': 'سارة', 'goal': 'تطلب قهوة', 'context': 'هاتف عربي مستعجلة'},
            'criteria': [{'id': 'C1', 'text': 'ترى أثر الإضافة', 'source': 'أرى أثر الإضافة'},
                         {'id': 'C2', 'text': 'تفهم الخطأ', 'source': 'أفهم الخطأ'},
                         {'id': 'C3', 'text': 'الطلب بإجراء واحد', 'source': 'أطلب قهوة بضغطة واحدة'}],
            'na_states': {'loading': 'لا تحميل شبكي', 'empty': 'غير منطبق هنا', 'success': 'غير منطبق هنا'},
            'journeys': [{'id': 'J1', 'priority': 'P0', 'budget': {'max_actions': 2}, 'steps': [
                {'id': 'J1.1', 'state': 'initial', 'covers': ['C1', 'C3'], 'do': {'goto': 'index.html'}, 'expect': 'تظهر شاشة المتجر كاملة'},
                {'id': 'J1.2', 'state': 'error', 'covers': ['C2'], 'do': {'click': '#x'}, 'expect': 'تظهر رسالة خطأ مفهومة'}]}]}


def ev_entry(step='J1.1', vp='mobile', sha='a', findings=None, p='P0', state=None, covers=None, text='متجر القهوة قهوة عربية'):
    return {'step': step, 'journey': 'J1', 'priority': p, 'viewport': vp, 'expect': 'يظهر المتجر', 'expect_text': [],
            'covers': covers or [], 'state': state, 'screenshot': '/x.png', 'sha': sha, 'visible_text': text,
            'findings': findings or [], 'surface': 'web'}


def jd(step='J1.1', vp='mobile', sha='a', verdict='pass', sev=None, by='self'):
    return {'step': step, 'viewport': vp, 'verdict': verdict, 'sev': sev, 'saw': 'x' * 30, 'note': '', 'sha': sha, 'by': by}


class Contract(unittest.TestCase):
    def test_good_contract_valid(self):
        self.assertEqual(U.validate_contract(good_contract()), [])

    def test_each_gap_is_reported(self):
        c = good_contract(); c['persona']['goal'] = ''
        self.assertTrue(any('persona.goal' in e for e in U.validate_contract(c)))
        c = good_contract(); c['criteria'].append({'id': 'C9', 'text': 'x', 'source': 'أفهم الخطأ'}); c['criteria'][0].pop('source')
        self.assertTrue(any('C9' in e or 'C1' in e for e in U.validate_contract(c)))
        c = good_contract(); c['na_states'].pop('loading')
        self.assertTrue(any('loading' in e for e in U.validate_contract(c)))
        c = good_contract(); c['journeys'][0]['steps'][0]['expect'] = 'قصير'
        self.assertTrue(any('expect' in e for e in U.validate_contract(c)))
        c = good_contract(); c['journeys'][0]['priority'] = 'P1'
        self.assertTrue(any('P0' in e for e in U.validate_contract(c)))
        self.assertTrue(U.validate_contract({'type': 'nope'}))

    def _errs(self, mut):
        c = good_contract(); mut(c)
        return U.validate_contract(c)

    def test_intent_bridge(self):
        def part(c): c['request_parts'][0] = 'أطلب شاياً'
        self.assertTrue(any('ليس اقتباساً' in e for e in self._errs(part)))
        def short(c): c['request'] = 'قهوة'
        self.assertTrue(any('request ناقص' in e for e in self._errs(short)))
        def unk(c): c['criteria'][0] = {'id': 'C1', 'text': 't', 'unknown': 'كم ثانية مقبولة؟'}
        self.assertTrue(any('اسأل المستخدم' in e for e in self._errs(unk)))
        def both(c): c['criteria'][0]['inferred'] = 'سبب كافٍ جداً هنا'
        self.assertTrue(any('مفتاح واحد' in e for e in self._errs(both)))
        def orphan(c): c['criteria'].pop()   # جزء من الطلب بلا معيار
        self.assertTrue(any('بلا معيار' in e for e in self._errs(orphan)))
        def oos(c):
            c['criteria'].pop(); c['journeys'][0]['steps'][0]['covers'] = ['C1']; c['out_of_scope'] = {'أطلب قهوة بضغطة واحدة': 'مؤجل بقرار المستخدم صراحة'}
        self.assertEqual(self._errs(oos), [])
        def thin(c): c['request_parts'] = ['أرى أثر الإضافة']
        self.assertTrue(any('لا تغطي' in e for e in self._errs(thin)))

    def test_budget_checked_statically(self):
        def over(c): c['journeys'][0]['budget']['max_actions'] = 0
        self.assertTrue(any('ميزانية' in e for e in self._errs(over)))

    def test_lock_detects_loosening(self):
        c = good_contract(); old = U.lock_view(c)
        c2 = good_contract(); c2['journeys'][0]['steps'][0]['expect_text'] = []
        self.assertEqual(U.diff_views(old, U.lock_view(c2)), [])
        c = good_contract(); c['journeys'][0]['steps'][0]['expect_text'] = ['متجر']; old = U.lock_view(c)
        c['journeys'][0]['steps'][0]['expect_text'] = []
        self.assertTrue(any(d.startswith('↓') for d in U.diff_views(old, U.lock_view(c))))
        c = good_contract(); old = U.lock_view(c); c['criteria'].pop(1)
        self.assertTrue(any('↓' in d and 'C2' in d for d in U.diff_views(old, U.lock_view(c))))
        c = good_contract(); old = U.lock_view(c); c['journeys'][0]['budget']['max_actions'] = 5
        self.assertTrue(any(d.startswith('↓') for d in U.diff_views(old, U.lock_view(c))))

    def test_report_incomplete_on_contract_change_and_assumptions(self):
        c = good_contract(); c['criteria'][1] = {'id': 'C2', 'text': 'تفهم الخطأ', 'inferred': 'المستخدم عربي فالرسالة بالعربية'}
        r = U.build_report(c, [ev_entry('J1.1', covers=['C1', 'C3']), ev_entry('J1.2', state='error', covers=['C2'])],
                           [jd('J1.1'), jd('J1.2')], lock={'view': U.lock_view(good_contract()), 'relocks': []})
        self.assertEqual(r['verdict'], 'INCOMPLETE')
        self.assertTrue(r['contract_changes'])
        self.assertTrue(r['assumptions_to_confirm'])

    def test_skeleton_is_not_valid_until_filled(self):
        for t in U.PROFILES:
            self.assertTrue(U.validate_contract(U.skeleton(t, 'x')), t)


class Judgment(unittest.TestCase):
    E = {'visible_text': 'متجر القهوة قهوة عربية 10.00 أضف للسلة شاي أخضر 5.50 عدد العناصر 1 الإجمالي 10.80 إتمام الطلب',
         'expect': 'يصير عدد العناصر 1 ويظهر الإجمالي 10.80', 'expect_text': ['عدد العناصر: 1', 'الإجمالي: 10.80']}

    def test_rejections(self):
        self.assertIsNotNone(U.check_judgment(self.E, 'قصير', 'pass', None))
        self.assertIsNotNone(U.check_judgment(self.E, 'الصفحة تعرض منتجاً وسلة وزراً ولا شيء غريب هنا', 'pass', None))
        self.assertIsNotNone(U.check_judgment(self.E, 'رأيت عدد العناصر صار 1 والإجمالي 10.80 كما هو متوقع', 'pass', None))  # ترديد التوقع
        self.assertIsNotNone(U.check_judgment(self.E, 'عدد العناصر 1 وزر إتمام الطلب ظاهر بوضوح', 'fail', None))  # fail بلا sev
        self.assertIsNotNone(U.check_judgment(self.E, 'عدد العناصر 1 وزر إتمام الطلب ظاهر بوضوح', 'maybe', None))

    def test_accepts_real_observation(self):
        self.assertIsNone(U.check_judgment(self.E, 'العدد صار 1 والمنتجان قهوة عربية وشاي أخضر ظاهران وزر إتمام الطلب أزرق', 'pass', None))
        self.assertIsNone(U.check_judgment(self.E, 'زر إتمام الطلب يبدو رمادياً كأنه معطّل مع أن الإجمالي 10.80', 'fail', 'major'))


class Report(unittest.TestCase):
    C = good_contract()

    def rep(self, ev, js, c=None):
        return U.build_report(c or self.C, ev, js)

    def full(self, sha='a'):
        return [ev_entry('J1.1', sha=sha, state='initial', covers=['C1', 'C3']), ev_entry('J1.2', sha=sha, state='error', covers=['C2'])]

    def test_pass_only_when_everything_judged_and_covered(self):
        r = self.rep(self.full(), [jd('J1.1'), jd('J1.2')])
        self.assertEqual(r['verdict'], 'PASS', r)

    def test_unjudged_is_incomplete_not_pass(self):
        self.assertEqual(self.rep(self.full(), [jd('J1.1')])['verdict'], 'INCOMPLETE')
        self.assertEqual(self.rep(self.full(), [])['verdict'], 'INCOMPLETE')

    def test_stale_judgment_dropped_when_screenshot_changes(self):
        r = self.rep(self.full(sha='NEW'), [jd('J1.1', sha='OLD'), jd('J1.2', sha='OLD')])
        self.assertEqual(r['verdict'], 'INCOMPLETE')
        self.assertEqual(len(r['stale_judgments']), 2)

    def test_blocker_fails_even_if_judged_pass(self):
        ev = self.full(); ev[0]['findings'] = [{'axis': 'flow', 'sev': 'blocker', 'code': 'obscured_control', 'detail': 'x'}]
        self.assertEqual(self.rep(ev, [jd('J1.1'), jd('J1.2')])['verdict'], 'FAIL')

    def test_p0_major_fails_but_p1_major_does_not(self):
        f = [{'axis': 'a11y', 'sev': 'major', 'code': 'small_target', 'detail': 'x'}]
        ev = self.full(); ev[0]['findings'] = f
        self.assertEqual(self.rep(ev, [jd('J1.1'), jd('J1.2')])['verdict'], 'FAIL')
        ev = self.full(); ev[0]['findings'] = f; ev[0]['priority'] = 'P1'
        self.assertEqual(self.rep(ev, [jd('J1.1'), jd('J1.2')])['verdict'], 'PASS')

    def test_perceptual_fail_counts(self):
        r = self.rep(self.full(), [jd('J1.1', verdict='fail', sev='blocker'), jd('J1.2')])
        self.assertEqual(r['verdict'], 'FAIL')

    def test_uncovered_state_or_criterion_is_incomplete(self):
        c = copy.deepcopy(self.C); c['na_states'].pop('loading')
        self.assertIn('loading', self.rep(self.full(), [jd('J1.1'), jd('J1.2')], c)['uncovered_states'])
        ev = self.full(); ev[1]['covers'] = []
        self.assertIn('C2', self.rep(ev, [jd('J1.1'), jd('J1.2')])['uncovered_criteria'])

    def test_independent_review_required_when_asked(self):
        c = copy.deepcopy(self.C); c['require_independent'] = True
        self.assertEqual(self.rep(self.full(), [jd('J1.1'), jd('J1.2')], c)['verdict'], 'INCOMPLETE')
        r = self.rep(self.full(), [jd('J1.1', by='independent'), jd('J1.2', by='independent')], c)
        self.assertEqual(r['verdict'], 'PASS')
        self.assertEqual(r['independent_judged'], 2)


class Probe(unittest.TestCase):
    P = {'overflow': False, 'scrollW': 0, 'offscreen': [], 'obscured': [], 'lowc': [], 'clipped': [], 'broken': [], 'small': [],
         'unnamed': [], 'rtl': []}

    def f(self, **kw):
        return U.findings_from_probe({**self.P, **kw}, True)

    def test_severity_mapping(self):
        self.assertEqual(self.f(lowc=[{'text': 't', 'ratio': 1.0, 'need': 4.5}])[0]['sev'], 'blocker')  # نص غير مرئي
        self.assertEqual(self.f(lowc=[{'text': 't', 'ratio': 2.0, 'need': 4.5}])[0]['sev'], 'major')
        self.assertEqual(self.f(lowc=[{'text': 't', 'ratio': 4.0, 'need': 4.5}])[0]['sev'], 'minor')
        self.assertEqual(self.f(obscured=[{'sel': '#b', 'by': 'div'}])[0]['sev'], 'blocker')
        self.assertEqual(self.f(clipped=[{'sel': 's', 'ellipsis': True, 'text': 't'}])[0]['sev'], 'minor')

    def test_rtl_overflow_detected_via_element_positions(self):  # عيب اكتشفته التجربة: RTL لا يظهر في scrollWidth
        r = self.f(offscreen=[{'sel': '.card', 'left': -307, 'right': 359}])
        self.assertEqual(r[0]['code'], 'horizontal_overflow')


class Cli(unittest.TestCase):
    def test_init_then_check_fails_until_filled(self):
        d = tempfile.mkdtemp(); p = os.path.join(d, 'c.json')
        env = {**os.environ, 'AGL_STATE_DIR': d}
        r = subprocess.run([sys.executable, os.path.join(HERE, 'ux_gate.py'), 'init', 'web', '--out', p], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'ux_gate.py'), 'contract-check', p], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        r = subprocess.run([sys.executable, os.path.join(HERE, 'ux_gate.py'), 'run', p], env=env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)  # لا تشغيل بعقد ناقص

    def test_documented_in_skill(self):
        with open(os.path.join(HERE, 'SKILL.md'), encoding='utf-8') as f:
            s = f.read()
        for w in ('ux_gate.py', 'contract-check', 'judge', 'INCOMPLETE'):
            self.assertIn(w, s, w)


class BrainIntegration(unittest.TestCase):
    """يمنع تراجع التكامل بين المهارة ومقياس العقل."""

    def test_user_eye_axis_exists_and_matches_brain_test(self):
        import brain_score as B
        self.assertIn('user_eye', B.AXES)
        with open(os.path.join(HERE, 'BRAIN_TEST.md'), encoding='utf-8') as f:
            bt = f.read()
        for ax in ('priority', 'discipline', 'error_handling', 'comprehension', 'verification', 'council', 'user_eye'):
            self.assertIn(f'`{ax}`', bt, ax)
        self.assertIn('السبعة', bt)

    def test_skill_references_user_eye_and_brain_test(self):
        with open(os.path.join(HERE, 'SKILL.md'), encoding='utf-8') as f:
            s = f.read()
        for w in ('3-ب', 'user_eye', 'عقد التجربة', 'لا «اكتمل» بغير', 'تقمّص'):
            self.assertIn(w, s, w)

    def test_brain_score_booleans_are_strict(self):  # قاعدة المهارة نفسها: is True لا truthiness
        import brain_score as B
        ev = {a: {e: 'False' for e in B.AXES[a]['evidence_needed']} for a in B.AXES}
        self.assertEqual(B.score_session(ev)['percentage'], 0)
        ev = {a: {e: True for e in B.AXES[a]['evidence_needed']} for a in B.AXES}
        self.assertEqual(B.score_session(ev)['percentage'], 100)

    def test_demo_run_is_labelled(self):
        out = subprocess.run([sys.executable, os.path.join(HERE, 'brain_score.py')], capture_output=True, text=True).stdout
        self.assertIn('_demo', out)


def _browser_ok():
    try:
        if os.path.isdir('/opt/pw-browsers'):
            os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/opt/pw-browsers')
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return True
    except Exception:
        return False


class GateFlow(unittest.TestCase):
    """حلقة التسليم المغلقة عبر CLI بلا متصفح: أدلة مُجهَّزة → gate → attempt → stop → relock."""

    def setUp(self):
        import json
        self.json = json
        self.d = tempfile.mkdtemp()
        self.env = {**os.environ, 'AGL_STATE_DIR': os.path.join(self.d, 'st')}
        os.makedirs(os.path.join(self.d, 'st', 'ux'))
        self.cpath = os.path.join(self.d, 'c.json')
        with open(self.cpath, 'w', encoding='utf-8') as f:
            json.dump(good_contract(), f, ensure_ascii=False)

    def put(self, ev, judgments, lock=True):
        st = os.path.join(self.d, 'st', 'ux')
        with open(os.path.join(st, 'evidence.json'), 'w', encoding='utf-8') as f:
            self.json.dump(ev, f, ensure_ascii=False)
        with open(os.path.join(st, 'judgments.jsonl'), 'w', encoding='utf-8') as f:
            for j in judgments:
                f.write(self.json.dumps(j, ensure_ascii=False) + '\n')
        if lock:
            v = U.lock_view(good_contract())
            with open(os.path.join(st, 'lock.json'), 'w', encoding='utf-8') as f:
                self.json.dump({'sha': U._view_sha(v), 'view': v, 'relocks': [], 't': 0}, f, ensure_ascii=False)

    def cli(self, *a):
        return subprocess.run([sys.executable, os.path.join(HERE, 'ux_gate.py'), *a], capture_output=True, text=True, env=self.env)

    def good_ev(self, bad=False):
        ev = [ev_entry('J1.1', state='initial', covers=['C1', 'C3']), ev_entry('J1.2', state='error', covers=['C2'])]
        if bad:
            ev[0]['findings'] = [{'axis': 'flow', 'sev': 'blocker', 'code': 'obscured_control', 'detail': 'x'}]
        return ev

    def test_pass_writes_last_gate_bound_to_evidence(self):
        self.put(self.good_ev(), [jd('J1.1'), jd('J1.2')])
        r = self.cli('gate', self.cpath)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        import hashlib
        with open(os.path.join(self.d, 'st', 'ux', 'last_gate.json'), encoding='utf-8') as f:
            lg = self.json.load(f)
        with open(os.path.join(self.d, 'st', 'ux', 'evidence.json'), 'rb') as f:
            sha = hashlib.sha1(f.read()).hexdigest()
        self.assertEqual((lg['verdict'], lg['evidence_sha']), ('PASS', sha))

    def test_three_distinct_failed_attempts_stop_with_code_4(self):
        self.put(self.good_ev(bad=True), [jd('J1.1'), jd('J1.2')])
        self.assertEqual(self.cli('gate', self.cpath).returncode, 1)
        codes = [self.cli('gate', self.cpath, '--attempt', a).returncode
                 for a in ('رفع z-index للزر', 'استبدال الغطاء بعنصر مختلف تماماً', 'إعادة بناء البطاقة بلا موضع مطلق')]
        self.assertEqual(codes, [1, 1, 4])

    def test_near_duplicate_attempt_not_counted_as_new_path(self):
        self.put(self.good_ev(bad=True), [jd('J1.1'), jd('J1.2')])
        self.cli('gate', self.cpath, '--attempt', 'رفع z-index للزر')
        r = self.cli('gate', self.cpath, '--attempt', 'رفع z-index للزر الآن')
        self.assertEqual(r.returncode, 1)
        with open(os.path.join(self.d, 'st', 'stop.json'), encoding='utf-8') as f:
            self.assertEqual(len(self.json.load(f)['tried']), 1)  # المسار شبه المكرر لم يُحسب مساراً جديداً

    def test_loosening_after_lock_is_incomplete_until_relock(self):
        c = good_contract(); c['journeys'][0]['steps'][0]['expect_text'] = ['متجر']
        self.cpath2 = os.path.join(self.d, 'c2.json')
        v = U.lock_view(c)
        self.put(self.good_ev(), [jd('J1.1'), jd('J1.2')], lock=False)
        with open(os.path.join(self.d, 'st', 'ux', 'lock.json'), 'w', encoding='utf-8') as f:
            self.json.dump({'sha': U._view_sha(v), 'view': v, 'relocks': [], 't': 0}, f, ensure_ascii=False)
        r = self.cli('gate', self.cpath)           # العقد الحالي حذف توقعاً مقفولاً
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn('↓', r.stdout)
        self.assertEqual(self.cli('relock', self.cpath, '--reason', 'قصير').returncode, 1)
        self.assertEqual(self.cli('relock', self.cpath, '--reason', 'المستخدم عدّل الطلب وأزال هذا التوقع').returncode, 0)
        r = self.cli('gate', self.cpath)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('المستخدم عدّل الطلب', r.stdout)

    def test_gate_without_evidence_is_exit_3(self):
        self.assertEqual(self.cli('gate', self.cpath).returncode, 3)




@unittest.skipUnless(_browser_ok(), 'Playwright/Chromium غير متوفر — تُتخطّى اختبارات المتصفح')
class Browser(unittest.TestCase):
    PAGE = '''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<style>body{font:16px sans-serif;margin:0;padding:16px}button{min-height:44px;min-width:44px;padding:8px 14px;background:#1a56db;color:#fff;border:0}
#m{margin-top:10px;color:#0a7a2f}%s</style></head><body><h1>متجر</h1><div class="card"><span>قهوة عربية</span><button id="b">أضف للسلة</button></div>
<div id="m"></div>%s<script>document.getElementById('b').onclick=()=>{document.getElementById('m').textContent='تمت الإضافة بنجاح'}</script></body></html>'''

    def run_variant(self, css='', body=''):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, 'index.html'), 'w', encoding='utf-8') as f:
            f.write(self.PAGE % (css, body))
        c = {'type': 'web', 'locale': 'ar', 'base': 'file://' + d + '/',
             'viewports': [{'name': 'mobile', 'width': 375, 'height': 667}],
             'journeys': [{'id': 'J1', 'priority': 'P0', 'steps': [
                 {'id': 'J1.1', 'covers': [], 'do': {'goto': 'index.html'}, 'expect': 'تظهر الصفحة', 'expect_text': ['متجر']},
                 {'id': 'J1.2', 'covers': [], 'do': {'click': '#b'}, 'expect': 'تظهر رسالة', 'expect_text': ['تمت الإضافة بنجاح']}]}]}
        ev = U.run_web(c, os.path.join(d, 'shots'))
        return {f['code'] for e in ev for f in e['findings']}

    def test_clean_page_has_no_findings(self):
        self.assertEqual(self.run_variant(), set())

    def test_invisible_overlay_blocks_click(self):
        codes = self.run_variant(body='<div style="position:fixed;inset:0;background:rgba(255,255,255,0.01)"></div>')
        self.assertTrue({'action_failed', 'obscured_control'} <= codes, codes)

    def test_invisible_success_text(self):
        self.assertIn('low_contrast', self.run_variant(css='#m{color:#fff !important}'))

    def test_rtl_mobile_overflow_detected(self):  # انحدار: visualViewport + اتجاه RTL
        self.assertIn('horizontal_overflow', self.run_variant(css='.card{min-width:640px}'))

    def test_no_feedback_detected(self):
        self.assertIn('no_visible_feedback', self.run_variant(css='#m{display:none}'))


if __name__ == '__main__':
    unittest.main(verbosity=1)
