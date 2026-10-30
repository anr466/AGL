#!/usr/bin/env python3
"""ux_gate.py — بوابة «عين المستخدم»: التحقق مما يراه المستخدم لا مما يُنفَّذ في الكود.

الدورة:  contract (قبل البناء) ← run (أدلة موضوعية + لقطات) ← judge (حكم إدراكي بتقمّص المستخدم) ← gate.
النتائج:  PASS (0) | FAIL (1) | INCOMPLETE (2) | لا أداة تشغيل (3) | توقف إجباري بعد 3 مسارات فاشلة (4).  لا يُعلَن «اكتمل» إلا عند PASS.
جسر النية: العقد يُشتق من طلب المستخدم الحرفي (request_parts) وكل معيار يُربط باقتباس أو استنتاج معلن أو سؤال؛ وقفل العقد
عند أول تشغيل يكشف أي تخفيف للتوقعات بعد رؤية النتائج.

صدق القياس:
- الأدلة الموضوعية (قابلية النقر، التغطية، التباين، الفيض، ردّ الفعل، الأخطاء) تُحسب آلياً ولا يحكم الوكيل فيها.
- الحكم الإدراكي يسجّله الوكيل بعد رؤية اللقطة فعلاً؛ التوقع يُؤخذ من العقد المسجَّل مسبقاً لا من الحكم نفسه،
  والوصف يجب أن يطابق نص الشاشة، والحكم يسقط تلقائياً إن تغيّرت اللقطة (دليل طازج).
- ما لا تغطيه الأداة (لمس حقيقي، قارئ شاشة، أجهزة فعلية، شبكة بطيئة) يُسرد في التقرير ولا يُعدّ مختبَراً."""

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gates import GateViolation, StopTriggered, record_attempt, state_path, _read_json, _write_json  # noqa: E402

SEV_W = {'blocker': 40, 'major': 15, 'minor': 5}
DEFAULT_VIEWPORTS = [{'name': 'mobile', 'width': 375, 'height': 667}, {'name': 'desktop', 'width': 1280, 'height': 800}]

# ملف تعريف لكل نوع مشروع: المحاور المقاسة + الحالات التي يجب أن يراها المستخدم + نوع «السطح» الذي يراه
PROFILES = {
    'web': {'surface': 'متصفح (لقطة شاشة)',
            'axes': ['flow', 'visual', 'legibility', 'feedback', 'responsive', 'a11y', 'language', 'performance', 'errors', 'intent'],
            'states': ['initial', 'success', 'empty', 'error', 'loading']},
    'cli': {'surface': 'طرفية (نص المخرج)',
            'axes': ['flow', 'feedback', 'errors', 'language', 'performance', 'intent'],
            'states': ['success', 'error', 'help']},
    'api': {'surface': 'استجابات (نص)', 'axes': ['flow', 'errors', 'performance', 'intent'], 'states': ['success', 'error']},
    'doc': {'surface': 'تصيير (لقطة شاشة لملف HTML/PDF)',
            'axes': ['visual', 'legibility', 'language', 'intent'], 'states': ['initial']},
}
AXIS_AR = {'flow': 'اكتمال التدفق', 'visual': 'سلامة العرض', 'legibility': 'المقروئية', 'feedback': 'ردّ الفعل',
           'responsive': 'الاستجابة للأحجام', 'a11y': 'الوصول والتلامس', 'language': 'اللغة/الاتجاه',
           'performance': 'الإحساس بالسرعة', 'errors': 'الأخطاء الخفية', 'intent': 'مطابقة النية'}
NOT_COVERED = ['اللمس الحقيقي على جهاز فعلي', 'قارئ الشاشة', 'لوحة المفاتيح وتسلسل التركيز', 'شبكة بطيئة/غير مستقرة',
               'متصفحات غير Chromium', 'محتوى حي (بيانات إنتاج حقيقية)']

# ───────────────────────── العقد ─────────────────────────


ACTION_KEYS = ('click', 'fill', 'press', 'select', 'cmd')


_STOP = {'أريد', 'اريد', 'أن', 'ان', 'أنا', 'من', 'إلى', 'الى', 'على', 'في', 'مع', 'هذا', 'هذه', 'لكن', 'أو', 'ثم', 'كي', 'لكي',
         'want', 'the', 'and', 'for', 'with', 'that', 'this', 'can', 'would', 'like'}


def _cw(s):
    """كلمات المحتوى (بلا كلمات الربط ولا حرف العطف «و» الملتصق) لفحص تغطية الطلب."""
    out = set()
    for w in re.findall(r'[\w\u0600-\u06FF]{3,}', (s or '').lower()):
        if len(w) > 3 and w[0] == 'و':
            w = w[1:]
        if w not in _STOP:
            out.add(w)
    return out


def _intent_errors(c):
    """جسر النية: العقد مشتق من الطلب الحرفي لا من تخمين. فحص آلي للتتبّع لا للفهم الدلالي —
    مراجعة الأجزاء والمعايير تبقى حكماً بشرياً/مستقلاً."""
    req = _norm(c.get('request', ''))
    if len(req) < 10:
        return ['request ناقص: انسخ طلب المستخدم حرفياً (≥10 أحرف) — العقد يُشتق منه لا من تخمينك']
    errs, parts = [], c.get('request_parts') or []
    if not parts:
        errs.append('request_parts فارغة: فكّك الطلب إلى أجزاء حرفية (كل جزء اقتباس من الطلب)')
    covered = set()
    for p in parts:
        if _norm(p) not in req:
            errs.append(f'جزء ليس اقتباساً من الطلب: «{p}»')
        covered |= _cw(p)
    rw = _cw(req)
    if parts and rw and len(rw - covered) / len(rw) > 0.2:
        errs.append(f'request_parts لا تغطي الطلب (أكثر من 20% من كلماته): {sorted(rw - covered)[:8]}')
    pnorm, cited = {_norm(p) for p in parts}, set()
    for cr in c.get('criteria', []):
        cid = cr.get('id')
        keys = [k for k in ('source', 'inferred', 'unknown') if cr.get(k)]
        if len(keys) != 1:
            errs.append(f'{cid}: مفتاح واحد فقط من source (اقتباس) | inferred (استنتاج + سببه) | unknown (سؤال للمستخدم)')
        elif keys[0] == 'unknown':
            errs.append(f'{cid}: معيار مجهول — اسأل المستخدم قبل البناء: {cr["unknown"]}')
        elif keys[0] == 'source':
            if _norm(cr['source']) not in pnorm:
                errs.append(f'{cid}: source يجب أن يطابق جزءاً من request_parts')
            else:
                cited.add(_norm(cr['source']))
        elif len(str(cr['inferred']).strip()) < 10:
            errs.append(f'{cid}: سبب الاستنتاج ناقص')
    oos = {_norm(k): v for k, v in (c.get('out_of_scope') or {}).items()}
    for k, v in oos.items():
        if len(str(v).strip()) < 10:
            errs.append(f'out_of_scope «{k}»: السبب ناقص')
    for n in sorted(pnorm - cited - set(oos)):
        errs.append(f'جزء من الطلب بلا معيار يخدمه ولا تبرير لخروجه من النطاق (out_of_scope): «{n}»')
    for j in c.get('journeys', []):
        b = (j.get('budget') or {}).get('max_actions')
        if b is not None:
            n = sum(1 for s in j.get('steps', []) if any(k in s.get('do', {}) for k in ACTION_KEYS))
            if n > b:
                errs.append(f'الرحلة {j.get("id")} تتطلب {n} إجراءات والميزانية المشتقة من الطلب {b}')
    return errs


def lock_view(c):
    """ما يُقفَل عند أول تشغيل: الطلب والمعايير والتوقعات والميزانيات (لا الإجراءات: إصلاح محدِّد لا يُعدّ تخفيفاً)."""
    return copy.deepcopy({'request': c.get('request', ''), 'request_parts': c.get('request_parts', []),
            'criteria': {x.get('id'): {'text': x.get('text'), 'source': x.get('source'), 'inferred': x.get('inferred')}
                         for x in c.get('criteria', [])},
            'budgets': {j.get('id'): j.get('budget') or {} for j in c.get('journeys', [])},
            'steps': {s.get('id'): {'expect': s.get('expect'), 'expect_text': s.get('expect_text', []),
                                    'expect_visible': s.get('expect_visible', []), 'covers': s.get('covers', [])}
                      for j in c.get('journeys', []) for s in j.get('steps', [])}})


def diff_views(old, new):
    """تغييرات العقد عن المقفول. «↓» = تخفيف محتمل (حذف توقع/خطوة/معيار أو رفع ميزانية)."""
    out = []
    if old['request'] != new['request']:
        out.append('طلب المستخدم تغيّر')
    for k in sorted(set(old['request_parts']) ^ set(new['request_parts'])):
        out.append(f'↓ جزء الطلب «{k}» ' + ('حُذف' if k in old['request_parts'] else 'أُضيف'))
    for cid in sorted(set(old['criteria']) | set(new['criteria'])):
        if cid not in new['criteria']:
            out.append(f'↓ المعيار {cid} حُذف')
        elif cid not in old['criteria']:
            out.append(f'المعيار {cid} أُضيف')
        elif old['criteria'][cid] != new['criteria'][cid]:
            out.append(f'↓ المعيار {cid} تغيّر')
    for jid in sorted(set(old['budgets']) | set(new['budgets'])):
        ob, nb = old['budgets'].get(jid, {}).get('max_actions'), new['budgets'].get(jid, {}).get('max_actions')
        if ob != nb:
            out.append(f'{"↓ " if (nb is None or (ob is not None and nb > ob)) else ""}ميزانية {jid}: {ob} ← {nb}')
    for sid in sorted(set(old['steps']) | set(new['steps'])):
        if sid not in new['steps']:
            out.append(f'↓ الخطوة {sid} حُذفت')
            continue
        if sid not in old['steps']:
            out.append(f'الخطوة {sid} أُضيفت')
            continue
        o, n = old['steps'][sid], new['steps'][sid]
        for key in ('expect_text', 'expect_visible'):
            gone = [x for x in o[key] if x not in n[key]]
            if gone:
                out.append(f'↓ {sid}: حُذف توقع {key}: {gone}')
            if [x for x in n[key] if x not in o[key]]:
                out.append(f'{sid}: أُضيف توقع {key}')
        if o['expect'] != n['expect']:
            out.append(f'↓ {sid}: نص «expect» تغيّر')
        if o['covers'] != n['covers']:
            out.append(f'{sid}: covers تغيّرت')
    return out


def _view_sha(v):
    return hashlib.sha1(json.dumps(v, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def validate_contract(c):
    """يرجع قائمة أخطاء؛ فارغة = العقد صالح. العقد يُكتب قبل البناء من طلب المستخدم الفعلي."""
    errs = []
    t = c.get('type')
    if t not in PROFILES:
        return [f'type غير معروف «{t}» — المسموح: {", ".join(PROFILES)}']
    per = c.get('persona') or {}
    for k in ('name', 'goal', 'context'):
        if len(str(per.get(k, '')).strip()) < 3:
            errs.append(f'persona.{k} ناقص — من المستخدم وماذا يريد وفي أي سياق (جهاز/لغة/استعجال)؟')
    crit = {x.get('id'): x for x in c.get('criteria', [])}
    if not crit:
        errs.append('criteria فارغة — اكتب معايير قبول من منظور المستخدم (ما الذي يجعله راضياً؟)')
    js = c.get('journeys', [])
    if not js:
        errs.append('journeys فارغة')
    if js and not any(j.get('priority') == 'P0' for j in js):
        errs.append('لا رحلة P0 — حدّد الرحلة التي إن فشلت فشل المنتج')
    covered, tags, ids = set(), set(), set()
    for j in js:
        for s in j.get('steps', []):
            sid = s.get('id')
            if not sid or sid in ids:
                errs.append(f'معرّف خطوة مفقود/مكرر: {sid}')
            ids.add(sid)
            if len(str(s.get('expect', '')).strip()) < 10:
                errs.append(f'{sid}: «expect» (ما يتوقع المستخدم رؤيته) ناقص — يُكتب قبل التنفيذ')
            if not s.get('do'):
                errs.append(f'{sid}: لا إجراء')
            covered.update(s.get('covers', []))
            if s.get('state'):
                tags.add(s['state'])
    for cid in crit:
        if cid not in covered:
            errs.append(f'المعيار {cid} غير مربوط بأي خطوة (covers)')
    for cid in covered - set(crit):
        errs.append(f'خطوة تشير إلى معيار غير موجود: {cid}')
    na = c.get('na_states', {})
    for st in PROFILES[t]['states']:
        if st not in tags and not str(na.get(st, '')).strip():
            errs.append(f'الحالة «{st}» لا خطوة تغطيها ولا مبرر عدم الانطباق في na_states')
    errs += _intent_errors(c)
    return errs


def skeleton(t, request):
    p = PROFILES[t]
    return {'type': t, 'request': request, 'request_parts': [], 'out_of_scope': {}, 'locale': 'ar',
            'base': 'http://localhost:8000/' if t == 'web' else '',
            'persona': {'name': '', 'goal': '', 'context': ''},
            'criteria': [{'id': 'C1', 'text': 'ما الذي يجعل المستخدم راضياً؟ (من منظوره)', 'source': 'جزء حرفي من request_parts'}],
            'viewports': DEFAULT_VIEWPORTS if t == 'web' else [{'name': 'default'}],
            'na_states': {},
            'journeys': [{'id': 'J1', 'priority': 'P0', 'goal': '', 'budget': {'max_actions': 0}, 'steps': [
                {'id': 'J1.1', 'state': p['states'][0], 'covers': ['C1'],
                 'do': {'goto': '/'} if t == 'web' else {'cmd': ''},
                 'expect': 'ما يتوقع المستخدم أن يراه بعد هذه الخطوة (قبل التنفيذ)',
                 'expect_text': []}]}],
            '_profile': {'surface': p['surface'], 'axes': p['axes'], 'states_required': p['states']}}


# ───────────────────────── الفحوص الموضوعية (متصفح) ─────────────────────────
PROBE_JS = r"""
(opts) => {
  const out = {overflow:false, scrollW:0, clipped:[], small:[], lowc:[], unnamed:[], broken:[], rtl:[], obscured:[]};
  // ما يراه المستخدم فعلاً: visualViewport (في الجوال يوسّع المتصفح نافذة التخطيط innerWidth ليحتوي الفيض فيخفيه عن القياس)
  const vw = (window.visualViewport ? visualViewport.width : innerWidth), vh = innerHeight, mobile = opts.mobile;
  const vwLayout = innerWidth;
  out.overflow = document.documentElement.scrollWidth > vw + 1; out.scrollW = document.documentElement.scrollWidth;
  out.offscreen = [];
  const sel = el => el.id ? '#'+el.id : el.tagName.toLowerCase() + ((typeof el.className==='string' && el.className.trim()) ? '.'+el.className.trim().split(/\s+/)[0] : '');
  const vis = el => { const r=el.getBoundingClientRect(), s=getComputedStyle(el);
    return r.width>0 && r.height>0 && s.visibility!=='hidden' && s.display!=='none'; };
  const parse = c => { const m=c.match(/rgba?\(([^)]+)\)/); if(!m) return null; const p=m[1].split(',').map(parseFloat);
    return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}; };
  const lum = c => { const f=v=>{v/=255; return v<=0.03928? v/12.92 : Math.pow((v+0.055)/1.055,2.4)};
    return 0.2126*f(c.r)+0.7152*f(c.g)+0.0722*f(c.b); };
  const opacityChain = el => { let o=1, e=el; while(e){ o*=parseFloat(getComputedStyle(e).opacity); e=e.parentElement;} return o; };
  const bgOf = el => { const layers=[]; let e=el;
    while(e){ const s=getComputedStyle(e); if(s.backgroundImage!=='none') return null;
      const c=parse(s.backgroundColor); if(c && c.a>0){ layers.push(c); if(c.a>=0.99) break; } e=e.parentElement; }
    let b={r:255,g:255,b:255};
    for(let i=layers.length-1;i>=0;i--){ const l=layers[i]; b={r:l.r*l.a+b.r*(1-l.a), g:l.g*l.a+b.g*(1-l.a), b:l.b*l.a+b.b*(1-l.a)}; }
    return b; };
  const all = Array.from(document.querySelectorAll('body *'));
  for (const el of all) {
    if (!vis(el)) continue;
    const s = getComputedStyle(el);
    const own = Array.from(el.childNodes).filter(n=>n.nodeType===3 && n.textContent.trim()).map(n=>n.textContent.trim()).join(' ');
    if (own) {
      const fg = parse(s.color), bg = bgOf(el);
      if (fg && bg) {
        const a = fg.a * opacityChain(el);
        const eff = {r:fg.r*a+bg.r*(1-a), g:fg.g*a+bg.g*(1-a), b:fg.b*a+bg.b*(1-a)};
        const L1=lum(eff), L2=lum(bg); const ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
        const px=parseFloat(s.fontSize), bold=parseInt(s.fontWeight)>=700;
        const need=(px>=24||(px>=18.66&&bold))?3:4.5;
        if (ratio < need) out.lowc.push({sel:sel(el), ratio:+ratio.toFixed(2), need, text:own.slice(0,30)});
      }
      if (/[\u0600-\u06FF]/.test(own) && s.direction==='ltr' && s.textAlign!=='center' && own.length>=8 && s.display!=='inline')
        out.rtl.push({sel:sel(el), text:own.slice(0,30)});
      if ((s.overflowX==='hidden'||s.overflowX==='clip') && el.scrollWidth > el.clientWidth+1)
        out.clipped.push({sel:sel(el), ellipsis:s.textOverflow==='ellipsis', text:own.slice(0,30)});
    }
    { const rr = el.getBoundingClientRect();   // RTL: الفيض يمتد يساراً ولا يظهر في scrollWidth، لذا نفحص مواضع العناصر
      if ((own || el.matches('a[href],button,input,select,textarea')) && (rr.right > vw + 1 || rr.left < -1) && getComputedStyle(el).position !== 'fixed')
        out.offscreen.push({sel:sel(el), left:Math.round(rr.left), right:Math.round(rr.right)}); }
    if (el.tagName==='IMG' && el.complete && el.naturalWidth===0) out.broken.push({sel:sel(el)});
    const interactive = el.matches('a[href],button,input:not([type=hidden]),select,textarea,[role=button],[onclick]');
    if (interactive) {
      const r = el.getBoundingClientRect();
      const m = Math.min(r.width, r.height);
      if (m < (mobile?44:24)) out.small.push({sel:sel(el), size:Math.round(m), major: m < (mobile?32:16)});
      const name = (el.innerText||'').trim() || el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('placeholder')
        || (el.labels && el.labels.length) || el.getAttribute('alt') || (el.querySelector('img[alt]')&&el.querySelector('img[alt]').getAttribute('alt'));
      if (!name) out.unnamed.push({sel:sel(el)});
      const cx = r.left + r.width/2, cy = r.top + r.height/2;
      if (cx>=0 && cx<=vwLayout && cy>=0 && cy<=vh) {
        const top = document.elementFromPoint(cx, cy);
        if (top && !(el.contains(top) || top.contains(el))) out.obscured.push({sel:sel(el), by:sel(top)});
      }
    }
  }
  out.text = (document.body.innerText||'').replace(/\s+/g,' ').trim().slice(0,3000);
  return out;
}
"""


def _norm(s):
    return re.sub(r'\s+', ' ', s or '').strip()


def findings_from_probe(pr, mobile):
    F = []
    add = lambda axis, sev, code, detail: F.append({'axis': axis, 'sev': sev, 'code': code, 'detail': detail})
    if pr['offscreen'] and not pr['overflow']:
        x = pr['offscreen'][0]
        add('responsive', 'major' if mobile else 'minor', 'horizontal_overflow',
            f'محتوى خارج حدود الشاشة (مثلاً {x["sel"]} من {x["left"]} إلى {x["right"]}px) — يضيع على المستخدم')
    if pr['overflow']:
        add('responsive', 'major' if mobile else 'minor', 'horizontal_overflow',
            f'الصفحة أعرض من الشاشة ({pr["scrollW"]}px) — تمرير أفقي')
    for x in pr['obscured'][:5]:
        add('flow', 'blocker', 'obscured_control', f'{x["sel"]} مغطّى بـ {x["by"]} — لا يمكن للمستخدم الضغط عليه')
    for x in pr['lowc'][:6]:
        sev = 'blocker' if x['ratio'] < 1.5 else ('major' if x['ratio'] < 3 else 'minor')
        add('legibility', sev, 'low_contrast', f'«{x["text"]}» تباين {x["ratio"]} (المطلوب {x["need"]})')
    for x in pr['clipped'][:5]:
        add('visual', 'minor' if x['ellipsis'] else 'major', 'clipped_text', f'نص مقصوص في {x["sel"]}: «{x["text"]}»')
    for x in pr['broken'][:5]:
        add('visual', 'major', 'broken_image', f'صورة معطوبة {x["sel"]}')
    for x in pr['small'][:6]:
        add('a11y', 'major' if x['major'] else 'minor', 'small_target', f'هدف لمس صغير {x["sel"]} ({x["size"]}px)')
    for x in pr['unnamed'][:5]:
        add('a11y', 'major', 'unnamed_control', f'عنصر تحكم بلا اسم يُقرأ/يُفهم: {x["sel"]}')
    for x in pr['rtl'][:3]:
        add('language', 'major', 'rtl_wrong', f'نص عربي باتجاه LTR في {x["sel"]}: «{x["text"]}»')
    return F


def _sha(b):
    return hashlib.sha1(b).hexdigest()


def run_web(c, outdir, settle_ms=400, feedback_cap_ms=4000, text_wait_ms=6000):
    try:
        if os.path.isdir('/opt/pw-browsers'):
            os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH', '/opt/pw-browsers')
        from playwright.sync_api import sync_playwright, Error as PWError
    except ImportError:
        print('لا يوجد Playwright (pip install playwright && playwright install chromium). '
              'بدونه لا يمكن ادّعاء تحقق بصري — أعلن ذلك صراحة.', file=sys.stderr)
        return None
    os.makedirs(outdir, exist_ok=True)
    base = c.get('base', '')
    ev = []
    with sync_playwright() as p:
        br = p.chromium.launch()
        for vp in c.get('viewports', DEFAULT_VIEWPORTS):
            mobile = vp['width'] < 500
            for j in c['journeys']:
                ctx = br.new_context(viewport={'width': vp['width'], 'height': vp['height']}, locale=c.get('locale', 'ar'),
                                     is_mobile=mobile, has_touch=mobile)
                pg = ctx.new_page()
                logs = []
                pg.on('console', lambda m, L=logs: L.append(('console', m.text)) if m.type == 'error' else None)
                pg.on('pageerror', lambda e, L=logs: L.append(('pageerror', str(e)[:160])))
                pg.on('requestfailed', lambda r, L=logs: L.append(('requestfailed', r.url[:100])))
                pg.on('response', lambda r, L=logs: L.append(('http', f'{r.status} {r.url[:100]}')) if r.status >= 400 else None)
                for s in j['steps']:
                    F, d = [], s['do']
                    t0 = time.perf_counter()
                    before = _sha(pg.screenshot()) if pg.url != 'about:blank' else ''
                    try:
                        if 'goto' in d:
                            pg.goto(urllib.parse.urljoin(base, d['goto']), wait_until='load', timeout=8000)
                        elif 'click' in d:
                            pg.click(d['click'], timeout=3000)
                        elif 'fill' in d:
                            pg.fill(d['fill']['selector'], d['fill']['value'], timeout=3000)
                        elif 'press' in d:
                            pg.press(d['press']['selector'], d['press']['key'], timeout=3000)
                        elif 'select' in d:
                            pg.select_option(d['select']['selector'], d['select']['value'], timeout=3000)
                        elif 'hover' in d:
                            pg.hover(d['hover'], timeout=3000)
                        elif 'wait' in d:
                            pg.wait_for_timeout(int(d['wait']))
                    except PWError as e:
                        msg = str(e).split('\n')[0][:140]
                        F.append({'axis': 'flow', 'sev': 'blocker', 'code': 'action_failed',
                                  'detail': f'المستخدم لا يستطيع تنفيذ «{list(d)[0]}»: {msg}'})
                    t_feedback = None
                    if any(k in d for k in ('click', 'press', 'select')) and not s.get('expect_no_change'):
                        while (time.perf_counter() - t0) * 1000 < feedback_cap_ms:
                            if _sha(pg.screenshot()) != before:
                                t_feedback = int((time.perf_counter() - t0) * 1000)
                                break
                            pg.wait_for_timeout(100)
                        if t_feedback is None and not [f for f in F if f['code'] == 'action_failed']:
                            F.append({'axis': 'feedback', 'sev': 'major', 'code': 'no_visible_feedback',
                                      'detail': f'لم يتغير شيء مرئي خلال {feedback_cap_ms}ms بعد الإجراء'})
                        elif t_feedback and t_feedback > 1000:
                            F.append({'axis': 'performance', 'sev': 'major',
                                      'code': 'slow_feedback', 'detail': f'أول ردّ فعل مرئي بعد {t_feedback}ms'})
                    exp = s.get('expect_text', [])
                    t_exp = None
                    deadline = time.perf_counter() + text_wait_ms / 1000
                    while True:
                        txt = _norm(pg.inner_text('body')) if pg.url != 'about:blank' else ''
                        if all(_norm(x) in txt for x in exp):
                            t_exp = int((time.perf_counter() - t0) * 1000)
                            break
                        if time.perf_counter() > deadline:
                            break
                        pg.wait_for_timeout(150)
                    miss = [x for x in exp if _norm(x) not in txt]
                    if miss:
                        F.append({'axis': 'intent', 'sev': 'major', 'code': 'expected_text_missing',
                                  'detail': f'النص المتوقع غير ظاهر للمستخدم: {miss}'})
                    elif t_exp and t_exp > 3000:
                        F.append({'axis': 'performance', 'sev': 'minor', 'code': 'slow_result',
                                  'detail': f'النتيجة المتوقعة بعد {t_exp}ms'})
                    pg.wait_for_timeout(settle_ms)
                    for sel_ in s.get('expect_visible', []):
                        ok = False
                        try:
                            ok = pg.locator(sel_).first.is_visible()
                        except PWError:
                            pass
                        if not ok:
                            F.append({'axis': 'flow', 'sev': 'major', 'code': 'expected_element_not_visible',
                                      'detail': f'العنصر المتوقع غير ظاهر: {sel_}'})
                    pr = pg.evaluate(PROBE_JS, {'mobile': mobile})
                    F += findings_from_probe(pr, mobile)
                    for kind, m in logs:
                        F.append({'axis': 'errors', 'sev': 'major' if kind in ('pageerror', 'http') else 'minor',
                                  'code': f'{kind}', 'detail': m})
                    logs.clear()
                    shot = os.path.join(outdir, f'{vp["name"]}_{s["id"]}.png')
                    png = pg.screenshot(path=shot)
                    ev.append({'step': s['id'], 'journey': j['id'], 'priority': j.get('priority', 'P1'), 'viewport': vp['name'],
                               'expect': s['expect'], 'expect_text': s.get('expect_text', []), 'covers': s.get('covers', []), 'state': s.get('state'),
                               'screenshot': shot, 'sha': _sha(png), 'visible_text': pr['text'],
                               'timing_ms': {'first_feedback': t_feedback, 'expected_text': t_exp},
                               'findings': F, 'surface': 'web'})
                ctx.close()
        br.close()
    return ev


def run_cli(c, outdir):
    import subprocess
    os.makedirs(outdir, exist_ok=True)
    ev = []
    for j in c['journeys']:
        for s in j['steps']:
            d, F = s['do'], []
            t0 = time.perf_counter()
            try:
                r = subprocess.run(d['cmd'], shell=True, input=d.get('stdin'), capture_output=True, text=True, timeout=30,
                                   cwd=c.get('cwd') or None)
                out, err, rc = r.stdout, r.stderr, r.returncode
            except subprocess.TimeoutExpired:
                out, err, rc = '', 'timeout', -1
                F.append({'axis': 'performance', 'sev': 'blocker', 'code': 'hang', 'detail': 'الأمر لم ينته خلال 30ث'})
            ms = int((time.perf_counter() - t0) * 1000)
            exp_rc = s.get('expect_rc', 0)
            if rc != exp_rc:
                F.append({'axis': 'flow', 'sev': 'blocker', 'code': 'wrong_exit', 'detail': f'رمز الخروج {rc} والمتوقع {exp_rc}'})
            if 'Traceback (most recent call last)' in err or re.search(r'\bat \S+\.js:\d+', err):
                F.append({'axis': 'errors', 'sev': 'blocker', 'code': 'raw_traceback',
                          'detail': 'يُعرض على المستخدم تتبّع أخطاء خام بدل رسالة مفهومة'})
            if not (out + err).strip() and not s.get('expect_no_output'):
                F.append({'axis': 'feedback', 'sev': 'major', 'code': 'silent', 'detail': 'لا مخرجات: المستخدم لا يعرف ماذا حدث'})
            txt = _norm(out + ' ' + err)
            miss = [x for x in s.get('expect_text', []) if _norm(x) not in txt]
            if miss:
                F.append({'axis': 'intent', 'sev': 'major', 'code': 'expected_text_missing', 'detail': f'غير ظاهر: {miss}'})
            if ms > 2000:
                F.append({'axis': 'performance', 'sev': 'minor', 'code': 'slow', 'detail': f'{ms}ms'})
            tf = os.path.join(outdir, f'default_{s["id"]}.txt')
            open(tf, 'w', encoding='utf-8').write(f'$ {d["cmd"]}\n--- stdout ---\n{out}\n--- stderr ---\n{err}\n[rc={rc}] [{ms}ms]\n')
            ev.append({'step': s['id'], 'journey': j['id'], 'priority': j.get('priority', 'P1'), 'viewport': 'default',
                       'expect': s['expect'], 'expect_text': s.get('expect_text', []), 'covers': s.get('covers', []), 'state': s.get('state'), 'screenshot': tf,
                       'sha': _sha(open(tf, 'rb').read()), 'visible_text': txt[:3000], 'timing_ms': {'run': ms},
                       'findings': F, 'surface': 'cli'})
    return ev


# ───────────────────────── الحكم الإدراكي ─────────────────────────


def words(s):
    return set(re.findall(r'[\w\u0600-\u06FF]{3,}', s or ''))


def check_judgment(entry, saw, verdict, sev):
    """يرفض الوصف الذي لا يطابق الشاشة فعلاً (حاجز ضد الحكم بلا رؤية)."""
    if verdict not in ('pass', 'fail', 'unsure'):
        return 'verdict يجب أن يكون pass|fail|unsure'
    if len(saw.strip()) < 25:
        return 'الوصف «saw» قصير: صف ما رأيته فعلاً بجملة كاملة (≥25 حرفاً)'
    vt = words(entry['visible_text'])
    need = 2 if len(vt) >= 6 else 1
    seen = words(saw) & vt
    if len(seen) < need:
        return 'الوصف لا يطابق نص الشاشة — لا تحكم قبل أن ترى اللقطة (اقرأها بأداة view) ثم صف ما فيها'
    scripted = words(entry.get('expect', '')) | words(' '.join(entry.get('expect_text', [])))
    if not (seen - scripted):
        return ('الوصف يردّد التوقع المسجَّل فقط — اذكر شيئاً رأيته خارج السيناريو '
                '(عنصراً آخر على الشاشة، ترتيباً، لوناً، ما قد يربك المستخدم)')
    if verdict == 'fail' and sev not in SEV_W:
        return 'الفشل يلزمه --sev blocker|major|minor'
    return None


def cmd_judge(a):
    evp = state_path('ux/evidence.json')
    ev = _read_json(evp, None)
    if not ev:
        print('لا أدلة: شغّل run أولاً', file=sys.stderr)
        return 3
    e = next((x for x in ev if x['step'] == a.step and x['viewport'] == a.viewport), None)
    if not e:
        print(f'لا دليل للخطوة {a.step}/{a.viewport}', file=sys.stderr)
        return 3
    if not os.path.exists(e['screenshot']):
        print('اللقطة مفقودة', file=sys.stderr)
        return 3
    err = check_judgment(e, a.saw, a.verdict, a.sev)
    if err:
        print('مرفوض: ' + err, file=sys.stderr)
        return 1
    rec = {'step': a.step, 'viewport': a.viewport, 'verdict': a.verdict, 'sev': a.sev, 'saw': a.saw, 'note': a.note,
           'sha': e['sha'], 'expect': e['expect'], 'by': a.by, 't': time.time()}
    jp = state_path('ux/judgments.jsonl')
    os.makedirs(os.path.dirname(jp), exist_ok=True)
    open(jp, 'a', encoding='utf-8').write(json.dumps(rec, ensure_ascii=False) + '\n')
    blk = [f for f in e['findings'] if f['sev'] == 'blocker']
    if a.verdict == 'pass' and blk:
        print(f'تحذير: سُجّل pass لكن الأدلة الموضوعية فيها {len(blk)} blocker — الموضوعي يغلب في التقرير')
    print('سُجّل')
    return 0


# ───────────────────────── التقرير والبوابة ─────────────────────────


def build_report(contract, ev, judgments, lock=None):
    prof = PROFILES[contract['type']]
    cur = {(e['step'], e['viewport']): e for e in ev}
    latest = {}
    for j in judgments:
        k = (j['step'], j['viewport'])
        if k in cur and j['sha'] == cur[k]['sha']:  # الحكم يسقط إن تغيّرت اللقطة
            latest[k] = j
    stale = [k for k in {(j['step'], j['viewport']) for j in judgments} if k in cur and k not in latest]
    findings = []
    for e in ev:
        for f in e['findings']:
            findings.append({**f, 'step': e['step'], 'viewport': e['viewport'], 'p0': e['priority'] == 'P0', 'src': 'objective'})
        j = latest.get((e['step'], e['viewport']))
        if j and j['verdict'] == 'fail':
            findings.append({'axis': 'intent', 'sev': j['sev'], 'code': 'perceptual_fail', 'detail': j['saw'][:140] + (' | ' + j['note'] if j['note'] else ''),
                             'step': e['step'], 'viewport': e['viewport'], 'p0': e['priority'] == 'P0', 'src': 'perceptual'})
    uniq, seen = [], set()
    for f in findings:
        k = (f['code'], f['detail'], f['step'], f['viewport'])
        if k not in seen:
            seen.add(k)
            uniq.append(f)
    findings = uniq
    unjudged = [f'{e["step"]}/{e["viewport"]}' for e in ev if (e['step'], e['viewport']) not in latest]
    unsure = [f'{k[0]}/{k[1]}' for k, j in latest.items() if j['verdict'] == 'unsure']
    need_indep = [f'{e["step"]}/{e["viewport"]}' for e in ev if contract.get('require_independent') and e['priority'] == 'P0'
                  and (e['step'], e['viewport']) in latest and latest[(e['step'], e['viewport'])].get('by') != 'independent']
    changes = diff_views(lock['view'], lock_view(contract)) if lock else []
    assumptions = [f'{x["id"]}: {x["inferred"]}' for x in contract.get('criteria', []) if x.get('inferred')]
    tags = {e['state'] for e in ev if e['state']}
    na = contract.get('na_states', {})
    uncovered_states = [s for s in prof['states'] if s not in tags and s not in na]
    covered = {c for e in ev for c in e['covers']}
    uncovered_crit = [x['id'] for x in contract.get('criteria', []) if x['id'] not in covered]
    axes = {}
    for ax in prof['axes']:
        fs = [f for f in findings if f['axis'] == ax]
        axes[ax] = max(0, 100 - sum(SEV_W[f['sev']] for f in fs))
    blockers = [f for f in findings if f['sev'] == 'blocker']
    p0_major = [f for f in findings if f['sev'] == 'major' and f['p0']]
    if blockers or p0_major:
        verdict = 'FAIL'
    elif unjudged or unsure or uncovered_states or uncovered_crit or stale or need_indep or changes:
        verdict = 'INCOMPLETE'
    else:
        verdict = 'PASS'
    return {'verdict': verdict, 'axes': axes, 'blockers': len(blockers), 'p0_majors': len(p0_major),
            'majors': sum(f['sev'] == 'major' for f in findings), 'minors': sum(f['sev'] == 'minor' for f in findings),
            'unjudged': unjudged, 'unsure': unsure, 'need_independent_review': need_indep,
            'self_judged': sum(j.get('by', 'self') == 'self' for j in latest.values()), 'independent_judged': sum(j.get('by') == 'independent' for j in latest.values()), 'stale_judgments': [f'{a}/{b}' for a, b in stale],
            'uncovered_states': uncovered_states, 'uncovered_criteria': uncovered_crit,
            'contract_changes': changes, 'relocks': [r_['reason'] for r_ in (lock or {}).get('relocks', [])],
            'assumptions_to_confirm': assumptions,
            'findings': findings, 'not_covered': NOT_COVERED}


def print_report(r):
    mark = {'PASS': '✅ PASS', 'FAIL': '❌ FAIL', 'INCOMPLETE': '⚠️ INCOMPLETE'}[r['verdict']]
    print(f'{mark}  | blockers={r["blockers"]} majors={r["majors"]} (P0: {r["p0_majors"]}) minors={r["minors"]}')
    print('المحاور: ' + ' • '.join(f'{AXIS_AR[a]} {s}' for a, s in r['axes'].items()))
    for f in sorted(r['findings'], key=lambda f: -SEV_W[f['sev']])[:14]:
        print(f'  [{f["sev"]:7}] {f["step"]}/{f["viewport"]} {f["code"]}: {f["detail"]}')
    for k, lbl in (('unjudged', 'خطوات لم تُحكم بعد'), ('unsure', 'أحكام «غير متأكد»'), ('need_independent_review', 'تنتظر مراجعاً مستقلاً'), ('stale_judgments', 'أحكام سقطت (تغيّرت اللقطة)'),
                   ('uncovered_states', 'حالات لم يرها المستخدم'), ('uncovered_criteria', 'معايير بلا تغطية'),
                   ('contract_changes', 'العقد تغيّر بعد القفل (relock بتبرير أو تراجع)'), ('relocks', 'تعديلات عقد مبرَّرة'),
                   ('assumptions_to_confirm', 'افتراضات تُؤكَّد مع المستخدم عند التسليم')):
        if r[k]:
            print(f'  ← {lbl}: {", ".join(r[k])}')
    print(f'  أحكام إدراكية: ذاتية={r["self_judged"]} مستقلة={r["independent_judged"]}')
    print('  لا تغطيه هذه البوابة: ' + '، '.join(r['not_covered']))


def main(argv=None):
    for s in (sys.stdout, sys.stderr):
        if hasattr(s, 'reconfigure'):
            s.reconfigure(encoding='utf-8')
    ap = argparse.ArgumentParser(prog='ux_gate.py', description='بوابة عين المستخدم')
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('profile'); p.add_argument('type', choices=list(PROFILES))
    i = sp.add_parser('init'); i.add_argument('type', choices=list(PROFILES)); i.add_argument('--request', default='')
    i.add_argument('--out', default=None)
    ck = sp.add_parser('contract-check'); ck.add_argument('contract')
    r = sp.add_parser('run'); r.add_argument('contract')
    j = sp.add_parser('judge'); j.add_argument('step'); j.add_argument('--viewport', default='default')
    j.add_argument('--verdict', required=True); j.add_argument('--saw', required=True)
    j.add_argument('--sev'); j.add_argument('--note', default='')
    j.add_argument('--by', default='self', choices=['self', 'independent'], help='independent = مراجع آخر (وكيل بعيون جديدة أو إنسان)')
    g = sp.add_parser('gate'); g.add_argument('contract'); g.add_argument('--json', action='store_true')
    g.add_argument('--attempt', default=None, help='عند FAIL: ما جرّبته للإصلاح — يُسجَّل في قاعدة الإيقاف (3 مسارات مختلفة = توقف)')
    rl = sp.add_parser('relock', help='اعتماد تعديل العقد بعد القفل مع تبرير'); rl.add_argument('contract'); rl.add_argument('--reason', required=True)
    a = ap.parse_args(argv)
    if a.cmd == 'profile':
        pr = PROFILES[a.type]
        print(json.dumps({'surface': pr['surface'], 'axes': {x: AXIS_AR[x] for x in pr['axes']}, 'states': pr['states']},
                         ensure_ascii=False, indent=1))
        return 0
    if a.cmd == 'init':
        out = a.out or state_path('ux/contract.json')
        _write_json(out, skeleton(a.type, a.request))
        print(f'عقد أولي: {out} — املأه من طلب المستخدم قبل أي بناء')
        return 0
    if a.cmd == 'judge':
        return cmd_judge(a)
    c = json.load(open(a.contract, encoding='utf-8'))
    errs = validate_contract(c)
    if a.cmd == 'contract-check':
        for e in errs:
            print('✗', e)
        print('العقد صالح' if not errs else f'{len(errs)} نقص — لا بناء قبل إكماله')
        return 0 if not errs else 1
    if errs:
        print('العقد غير صالح — أصلحه أولاً (contract-check):\n  ' + '\n  '.join(errs), file=sys.stderr)
        return 1
    shots = state_path('ux/shots')
    if a.cmd == 'run':
        ev = run_web(c, shots) if c['type'] in ('web', 'doc') else run_cli(c, shots)
        if ev is None:
            return 3
        _write_json(state_path('ux/evidence.json'), ev)
        if not os.path.exists(state_path('ux/lock.json')):  # أول تشغيل: قفل الطلب والمعايير والتوقعات
            v = lock_view(c)
            _write_json(state_path('ux/lock.json'), {'sha': _view_sha(v), 'view': v, 'relocks': [], 't': time.time()})
        n = sum(len(e['findings']) for e in ev)
        print(f'نُفِّذت {len(ev)} خطوة×حجم | {n} ملاحظة موضوعية | اللقطات: {shots}\n'
              f'الآن: افتح كل لقطة بأداة view بعين المستخدم، ثم `judge` لكل خطوة، ثم `gate`.')
        return 0
    if a.cmd == 'relock':
        lk = _read_json(state_path('ux/lock.json'), None)
        if not lk:
            print('لا قفل — شغّل run أولاً', file=sys.stderr)
            return 3
        if len(a.reason.strip()) < 15:
            print('التبرير قصير (≥15 حرفاً): لماذا تغيّر العقد؟ (مثلاً: المستخدم عدّل طلبه)', file=sys.stderr)
            return 1
        v = lock_view(c)
        ch = diff_views(lk['view'], v)
        if not ch:
            print('لا تغيير عن القفل')
            return 0
        lk['relocks'].append({'t': time.time(), 'reason': a.reason.strip(), 'changes': ch})
        lk['view'], lk['sha'] = v, _view_sha(v)
        _write_json(state_path('ux/lock.json'), lk)
        print(f'اعتُمد {len(ch)} تغيير بتبرير مسجَّل (يظهر في تقرير gate)')
        return 0
    if a.cmd == 'gate':
        evp = state_path('ux/evidence.json')
        ev = _read_json(evp, None)
        if not ev:
            print('لا أدلة — شغّل run', file=sys.stderr)
            return 3
        jp = state_path('ux/judgments.jsonl')
        js = [json.loads(l) for l in open(jp, encoding='utf-8')] if os.path.exists(jp) else []
        rep = build_report(c, ev, js, _read_json(state_path('ux/lock.json'), None))
        with open(evp, 'rb') as f:
            esha = hashlib.sha1(f.read()).hexdigest()
        _write_json(state_path('ux/last_gate.json'), {'verdict': rep['verdict'], 't': time.time(), 'evidence_sha': esha,
                                                      'contract_sha': _view_sha(lock_view(c))})
        if a.json:
            print(json.dumps(rep, ensure_ascii=False, indent=1))
        else:
            print_report(rep)
        if rep['verdict'] == 'FAIL':
            top = max(rep['findings'], key=lambda f: SEV_W[f['sev']]) if rep['findings'] else {'code': 'fail', 'detail': ''}
            if a.attempt:
                try:
                    res = record_attempt(a.attempt, f'{top["code"]}: {top["detail"]}'[:120])
                    print(f'سُجّلت المحاولة: مسارات مختلفة فاشلة {res["distinct"]}/{res["max"]}', file=sys.stderr)
                except StopTriggered as e:
                    print(str(e), file=sys.stderr)
                    return 4
                except GateViolation as e:
                    print(str(e), file=sys.stderr)
            elif not a.json:
                print('  ← بعد الإصلاح: run ثم gate --attempt "<ما جرّبته>" (يحسبها قاعدة الإيقاف: 3 مسارات مختلفة = توقف وصعود)')
        return {'PASS': 0, 'FAIL': 1, 'INCOMPLETE': 2}[rep['verdict']]
    return 0


if __name__ == '__main__':
    sys.exit(main())
