<div align="center">

<img src="logo/agl_logo.png" alt="AGL" width="140">

# AGL — العقل الهندسي · The Engineering Mind

**يفهم طلبك ومشروعك، ثم لا يسلّم إلا ما رآه يعمل بعين المستخدم.**
*Understands your request and project first — delivers only what it has seen working through the user's eyes.*

[![selftest](https://github.com/anr466/AGL/actions/workflows/selftest.yml/badge.svg)](https://github.com/anr466/AGL/actions/workflows/selftest.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-yellow.svg)](LICENSE)
![deps](https://img.shields.io/badge/deps-stdlib%20only-black.svg)

</div>

## المشكلة · The problem

```mermaid
flowchart LR
    A["طلب المستخدم"] --> B["الوكيل يخمّن الفهم"]
    B --> C["يكتب كوداً"]
    C --> D{"اختبارات الكود ✓"}
    D --> E["«تم!»"]
    E --> F["المستخدم يفتح الواجهة<br/>الزر مغطّى · النص غير مرئي · لا شيء يحدث"]
    style F fill:#fde8e8,stroke:#c0392b
    style E fill:#fff4d6,stroke:#b9770e
```

الاختبارات البرمجية تثبت أن **المنطق** صحيح، لا أن **الإنسان** يستطيع الاستخدام. والوكيل يبدأ غالباً دون أن يفهم الطلب بحروفه أو المشروع الذي يعمل فيه.

## الحل · The loop

```mermaid
flowchart TD
    R["طلب المستخدم (حرفياً)"] --> U["② افهم: الطلب + المشروع<br/><code>recon.py</code>"]
    U -->|مجهول حرج| Q["اسأل المستخدم"]
    U --> K["③ عقد التجربة من كلامه<br/>كل معيار = اقتباس أو استنتاج معلن<br/><code>ux_gate.py</code>"]
    K --> B["⑦ ابنِ"]
    B --> E["⑨ شغّل وانظر كمستخدم<br/>قياس موضوعي + حكم على ما رُئي"]
    E -->|FAIL| X["صنّف ← أصلح<br/><code>gate --attempt</code>"]
    X -->|3 مسارات مختلفة فاشلة| S["توقف وصعود للمستخدم"]
    X --> E
    E -->|PASS| V["<code>gates.py verify --visible ux</code><br/>قراءة عكسية"]
    V --> D["سلّم: النتيجة + الافتراضات + ما لم يُشاهَد"]
    style S fill:#fde8e8,stroke:#c0392b
    style D fill:#e6f4ea,stroke:#1e8e3e
```

| ما يمنعه | كيف |
|---|---|
| «تم» بلا دليل | القانون الحديدي: دليل طازج في نفس الرسالة، و`verify` يرفض القديم والفارغ |
| فهم مخمَّن | `request_parts` اقتباسات حرفية؛ معيار مجهول = سؤال، لا بناء |
| تخفيف التوقعات بعد رؤية النتائج | قفل العقد عند أول تشغيل؛ التخفيف «↓» يوقف الحكم حتى `relock` بتبرير |
| الدوران بلا نهاية | 3 مسارات **مختلفة** فاشلة = توقف؛ المسار شبه المكرر لا يُحسب |
| حذف ملفاتك | لا يُحذف إلا ما سجّله الوكيل قبل إنشائه، وما ليس في git |
| أوامر مدمرة | حراس شلّية + خطّاف Claude Code (`ask` / `deny`) |

## التثبيت · Install

```bash
git clone https://github.com/anr466/AGL.git
python3 AGL/install.py --claude --project /path/to/project   # أو بدون --claude لمسار عام
```

يطبع مقطع الخطّاف لـ`.claude/settings.json` ولا يعدّل شيئاً بنفسه. `SKILL.md` وحده يعمل في أي وكيل؛ الأدوات تضيف الفرض الآلي. المتطلبات: Python 3 فقط، و[Playwright](https://playwright.dev/python/) اختيارياً لاختبار الواجهات في المتصفح.

## ما بداخله

| الملف | الدور |
|---|---|
| `SKILL.md` | العقل: المبدأ، القوانين الستة، الحلقات التسع، المجلس، البروتوكولات |
| `references/` | تفاصيل الأدوات: `gates.md` · `user-eye.md` · `recon.md` |
| `gates.py` `jobs.py` `hook_pretooluse.py` | التحقق، الإيقاف، الحراس، مهام الخلفية، الفرض الإلزامي |
| `ux_gate.py` | عين المستخدم: عقد من الطلب + قياس + حكم + قفل |
| `recon.py` | فهم المشروع: ما هو موثق وما هو مستنتج وما هو مجهول |
| `BRAIN_TEST.md` `brain_score.py` | قياس العقل نفسه: سبعة اختبارات سلوكية و11 محوراً |

## حدود معلنة

- الحراس تحليل ساكن: لا تلتقط `eval` ولا `python -c`.
- الحكم الإدراكي ذاتي ما لم يُمرَّر `--by independent`.
- لا تغطية للمس على جهاز حقيقي، ولا قارئ الشاشة، ولا الشبكة البطيئة، ولا متصفحات غير Chromium.
- الخطّاف واختبار القياس لم يُجرَّبا إلا في بيئات اختبار، وعينات القياس صغيرة.
- مهام الخلفية POSIX فقط.

## المساهمة والرخصة

[CONTRIBUTING.md](CONTRIBUTING.md) · [MIT](LICENSE)
