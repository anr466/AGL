<p align="center">
  <img src="logo/agl_logo.png" alt="AGL Logo" width="240">
</p>

<h1 align="center">AGL — Engineering OS</h1>

<p align="center">
  <strong>نظام تشغيل معرفي وهندسي لوكلاء البرمجة بالذكاء الاصطناعي.</strong><br>
  <em>يحوّل الوكيل من «مولّد كود مندفع ومخادع» إلى «مهندس برمجيات منضبط، صادق، وقابل للتحقق».</em><br>
  <strong>A cognitive operating system that turns AI coding agents into disciplined, honest, root-cause engineers.</strong>
</p>

<p align="center">
  <a href="https://github.com/anr466/AGL/actions/workflows/selftest.yml"><img src="https://github.com/anr466/AGL/actions/workflows/selftest.yml/badge.svg" alt="selftest"></a>
  <img src="https://img.shields.io/badge/license-MIT-black" alt="MIT">
  <img src="https://img.shields.io/badge/python-3.x-black" alt="python 3">
  <img src="https://img.shields.io/badge/zero--dependencies-pure%20python-black" alt="zero dependencies">
</p>

<p align="center">
  <a href="#-المشكلة-لماذا-تفشل-وكلاء-البرمجة-معك">المشكلة</a> ·
  <a href="#-حلول-agl-الهندسية">الحلول الهندسية</a> ·
  <a href="#-قبل-وبعد-agl">قبل وبعد</a> ·
  <a href="#-ابدأ-في-دقيقة">التثبيت والتشغيل</a> ·
  <a href="#-البوابات-الكودية-gatespy">البوابات</a> ·
  <a href="#english">English</a>
</p>

---

## 🛑 المشكلة: لماذا تُحبطك وكلاء البرمجة الحالية؟

أي مطور يستخدم وكلاء الذكاء الاصطناعي (Claude Code، Cursor، Antigravity، Codex وغيرهم) يصطدم يومياً بهذه **الأمراض السلوكية القاتلة**:

1. **وهم الإنجاز والادعاء الكاذب (Hallucination of Completion):**  
   الوكيل يكتب تعديلاً ثم يعلن بابتماس وثقة: *«تم حل المشكلة وتعمل بنجاح! ✅»*، بينما هو في الحقيقة **لم يشغّل الكود أصلاً**، أو شغّل أمراً فشل وتجاهل رمز الخروج، لتكتشف بنفسك أن الكود معطّل بالكامل.
2. **الترقيع التسكيني وتجاهل الجذر (Whack-a-Mole Patching):**  
   عند ظهور خطأ، يضع الوكيل `try/catch` عشوائي أو يلف السطر بشرط شكلي يسكّت الخطأ ظاهرياً، فينقل العطل لمكان آخر ويفسد المعمارية بدلاً من معرفة سبب الخلل الحقيقي.
3. **الدوران اللانهائي واحتراق التوكنات (Infinite Looping & Token Burn):**  
   عندما يتعثر، يعيد المحاولة بنفس الطريقة الفاشلة مع تغيير تافه 5 إلى 10 مرات متتالية، مستنزفاً نافذة السياق ومحفظتك دون أن يتوقف ليطلب توضيحاً.
4. **التعديل الأعمى قبل الفهم (Shooting from the Hip):**  
   يقفز فوراً لتعديل الملفات بناءً على "تخمين" أو افتراضات غير واقعية، دون أن يقرأ البنية الفعلية للمشروع، فيعيد اختراع ما هو مبني بالفعل أو يكسر أجزاء أخرى.
5. **العمى أحادي الزاوية وغياب النقد الذاتي (Single-Bias Blindness):**  
   يفكر في أسهل حل سطحي يخطر له، ولا يهاجم خطته ذاتياً: *«كيف قد يفشل هذا؟ ماذا لو كان المدخل غير صالح؟ هل سيعمل بيد مستخدم حقيقي في الإنتاج؟»*.
6. **العبث بالبيئة والتخريب الصامت (Destructive Drift):**  
   يحذف أو يغيّر ملفات مستقرة، أو يكتب أوامر `git` مدمرة وعشوائية دون تفويض من المطور.

---

## 🧠 حلول AGL: كيف يُعيد بناء عقل الوكيل؟

AGL لا يقدم مجرد نصوص تشجيعية، بل يزرع **نظام تشغيل هندسي صارم ومحكم** عبر ركيزتين:
- **مهارة منهجية (`SKILL.md`):** تفرض حلقات التفكير والانضباط المعرفي على الوكيل.
- **بوابات برمجية (`gates.py`):** كود فعلي يفحص التحقق، ويحسب المحاولات الفاشلة، ويحجب العبث التلقائي (والفرض الإلزامي عبر الخطّاف في Claude Code).

### 1. القانون الحديدي (Iron Law): منع وهم الإنجاز
> **«لا ادعاء إنجاز بدون دليل تحقق طازج في نفس الرسالة — الدليل المتذكَّر لا يُحتسب.»**
- يمر الوكيل بدالة البوابة الصارمة: (1) حدد أمر الإثبات ➔ (2) نفّذه كاملاً ➔ (3) اقرأ المخرج والرمز ➔ (4) تحقق من إثبات الادعاء ➔ (5) فقط حينها يحق له ادعاء الإنجاز مدعوماً برقم ودليل مستقل.

### 2. استئصال الجذر وتصنيف الفشل الرباعي
- يمنع الترقيع تماماً؛ عند أي فشل، يُجبر الوكيل على تصنيف الخلل إلى واحد من 4 مسارات محددة وتطبيق بروتوكوله:
  - **فشل افتراض:** اختبر وحدة يدوياً ثم أعد البناء.
  - **فشل تنفيذ:** صحح الجذر مرة واحدة في الكود المشترك (لا ترقّع كل caller).
  - **فشل فهم:** توقف وارجع للمستخدم والمواصفة.
  - **فشل بيئة:** أعد ضبط البيئة/المصادقة، ولا تعبث بالكود السليم لمعالجة خلل بيئة.

### 3. قاعدة الإيقاف (Stop Rule): إنهاء الدوران وحرق التوكن
- يحسب الوكيل محاولاته الفاشلة عبر `gates.py stop`.
- إذا فشلت **3 مسارات مختلفة**: يتوقف الوكيل إجبارياً عن التجربة، ويصعّد للمطور تقريراً منظماً: (ما جُرّب حرفياً + رسالة كل فشل + تخمين الجذر + ما يحتاجه من المطور لحسم الأمر).

### 4. سلسلة الحقيقة: لا لمس قبل الفهم
```
الذاكرة ← توجّه الفهم    |    الكود الحقيقي ← يحسم البناء    |    الإنتاج بيد المستخدم ← الحكم النهائي
```
- الحقيقة دائماً في الكود الحالي، لا في افتراضات الذاكرة.
- يُصنّف الوكيل معرفته إجبارياً: **موثق** (قرأه الآن من الملف) / **مستنتج** (يُذكر صراحة أنه ترجيح) / **مجهول** (يُفحص قبل كتابة سطر واحد).

### 5. مجلس الشخصيات الستة (The Council Protocol)
عند القرارات المعمارية أو البناء الكبير، لا ينفرد الوكيل برأي متسرع، بل يمرر قراره بستة أصوات عقلانية:
| الشخصية | ولايتها | سؤالها الحاكم |
|---|---|---|
| **الباني الصارم** | الاتفاقيات والتنفيذ | «أصغر تغيير كامل يلمس كل المتأثرين — أين؟» |
| **الناقد الأحمر** | مهاجمة الخطة وهدم الافتراضات | «كيف يفشل هذا؟ ماذا لم يفكر فيه أحد؟» |
| **الحارس** | الأمان وحدود الثقة | «ماذا لو كان المدخل خبيثاً؟ ماذا لو تخطينا التحقق؟» |
| **صوت المستخدم** | الإنتاج والتجربة الحقيقية | «هل يشتغل بيد مستخدم حقيقي في الإنتاج الآن؟» |
| **المؤرخ** | الذاكرة ومنع التكرار | «هل هذا موثق؟ هل يعيد اختراع موجود؟ هل الخريطة تطابق الواقع؟» |
| **الطموح** | الحلول الذكية المبتكرة | «هل توجد طريقة أذكى؟ (يحدّه الناقد من التضخم)» |

### 6. التناسب (Triage): المنهجية بحجم المهمة
AGL ليس بيروقراطية ثقيلة؛ المنهجية تتكيف ذاتياً مع حجم الطلب:
- **سؤال أو تعديل تافه:** حلقة القراءة والتنفيذ فقط (لا مجلس ولا تعقيد).
- **ميزة أو إصلاح عادي:** قراءة ➔ فهم ➔ تصميم ➔ تنفيذ ➔ تحقق بجذر المشكلة.
- **مشروع كبير / قرار معماري / تعثر:** كامل الحلقات + انعقاد المجلس + فحص البوابات.

---

## ⚖️ قبل وبعد AGL

| الموقف | الوكيل بدون AGL (المعتاد) | الوكيل بتشغيل AGL |
|---|---|---|
| **إصلاح عطل** | يغير سطراً ويقول فوراً «تم الإصلاح بنجاح! 🎉» دون أن يجرّب. | يشغّل أمر الفحص، يقرأ المخرج والـ exit code، ويعلن النتيجة برقم ودليل قاطع. |
| **استمرار الخطأ** | يكرر نفس المحاولة أو ترقيعات شكلية 8 مرات ويحرق رصيدك. | يتوقف عند 3 مسارات مختلفة ويقدم تقريراً هندسياً بما جربه والمطلوب منك. |
| **خطأ في كود مستدعى** | يضع `try/except: pass` أو يسكّت الخطأ في الواجهة. | يصنّف الخطأ، ويصلح الجذر في الدالة المشتركة لجميع المتأثرين. |
| **مشروع جديد غريب** | يقفز لتعديل الكود متخيلاً أسماء دوال ومكتبات. | يقرأ نقاط الدخول وتدفق البيانات ويكتب تصنيف معرفته قبل لمس أي ملف. |
| **القرارات المعمارية** | يختار أول حل يتبادر لذهنه وغالباً ما يكون هشاً. | يمرر الفكرة على مجلس الستة، يهاجمها نقدياً، ويوثق القرار وبديله المرفوض. |
| **حفظ التغييرات** | ينفّذ `git add -A && git push --force` ويدمر تعديلاتك غير المحفوظة. | يحجبه `gates.py` (وبخطّاف Claude Code يصير الحجب إلزامياً: يسألك أنت لا الوكيل)؛ يقترح الملفات المحددة والرسالة وينتظر موافقتك الصريحة. |

---

## ⚡ ابدأ في دقيقة

```bash
git clone https://github.com/anr466/AGL.git
cd AGL

# التثبيت عاماً لكل مشاريعك على جهازك:
python install.py

# أو التثبيت لمشروع محدد فقط:
python install.py --project /path/to/your/project
```

يقوم السكربت بنسخ `SKILL.md` والبوابات (`gates.py` و`jobs.py` و`hook_pretooluse.py`) معاً في مسار المهارات.
المسارات: عام `~/.gemini/config/skills/engineering-os` (Antigravity/Gemini) • `--project DIR` ⇒ `DIR/.agents/skills/...` •
**Claude Code:** `python install.py --claude` (عام: `~/.claude/skills/...`) أو `--claude --project DIR` (`DIR/.claude/skills/...`) — ويطبع لك مقطع الخطّاف لـ`settings.json`.

> `jobs.py` (المهام الخلفية) يعمل على Linux/macOS فقط؛ `gates.py` والبقية محمولة.

### فحص سلامة التثبيت:
```bash
python gates_selftest.py   # فحص ذاتي للبوابات (16/16 ✓)
python test_hardening.py   # اختبارات التحصين والمهام الخلفية (28 اختباراً)
```

> **المتطلبات:** بيئة `Python 3` قياسية فقط (بدون أي مكتبات خارجية `Zero Dependencies`).

---

## 🛠️ البوابات الكودية (`gates.py`)

البوابات هي الجسر البرمجي الذي يحوّل مبادئ AGL إلى كود تنفيذي يستدعيه الوكيل أو المطور عبر سطر الأوامر:

```bash
python gates.py <أمر>
```

| الأمر | ما يفعله لحماية المشروع | مثال تشغيل |
|---|---|---|
| `git` | يمنع أوامر الكتابة والمسح والتعديل التلقائي على git دون موافقة معلنة | `gates.py git "git commit -m fix"` ➔ رفض برمز خروج `1` حتى تمرير `--approved` |
| `verify` | فرض قراءة عكسية لأربعة أدلة مستقلة (العدّاد، القيمة، الظهور، التوقيت) | `gates.py verify --label save --expected 3 --actual 3 --stored yes --visible yes --timestamp now` |
| `classify` | يمنع تخمين أسباب الفشل ويلزم الوكيل ببروتوكول نوعه | `gates.py classify افتراض "form" "missing field"` |
| `stop` | عدّاد مسارات فاشلة يمنع دوران الوكيل ويوقفه عند المحاولة 3؛ المسار المشابه يلزمه `--diff` | `gates.py stop --sig "approach_A" --err "Connection reset"` |
| `shell` | حارس شامل: `rm`/`dd`/`find -delete`/الكتابة فوق ملف؛ يفكك `&&` و`sh -c` و`git -C` | `gates.py shell "rm -rf build"` ➔ رفض ما لم تكن مسجَّلة |
| `files` | حصرية الملفات: سجّل **قبل** الإنشاء ولا تحذف إلا المسجَّل غير المتتبَّع | `gates.py files register scratch/t.txt` |

---

## 📂 محتويات المستودع

```
AGL/
├── SKILL.md               ← العقل والمنهجية الهندسية الكاملة (تفعّله المحررات)
├── gates.py               ← البوابات الكودية + واجهة سطر الأوامر (CLI)
├── gates_selftest.py      ← الاختبارات الذاتية الشاملة للبوابات (16 فحصاً)
├── test_hardening.py      ← اختبارات التحصين: ثغرات git/verify/stop/ملفات + المهام الخلفية (28 اختباراً)
├── jobs.py                ← مهام خلفية: أطلق أمراً طويلاً وواصل العمل، ثم wait/result بدليل طازج
├── hook_pretooluse.py     ← خطّاف Claude Code يفرض البوابات ويسأل المستخدم الفعلي (فرض لا طوعي)
├── install.py             ← سكربت تثبيت المهارة مع بواباتها بنقرة واحدة
├── BRAIN_TEST.md          ← حقل اختبار سلوك وتفكير الوكيل + قالب التقييم
├── brain_score.py         ← مقياس أداء رقمي يقيس سلوك الوكيل بالأدلة
├── logo/agl_logo.png      ← الشعار الموحد
└── .github/workflows/     ← أتمتة الاختبارات والتكامل المستمر (CI)
```

---

## 📄 الترخيص

مرخص تحت رخصة [MIT](LICENSE) — مفتوح المصدر بالكامل وحر للاستخدام الشخصي والتجاري والتعديل.

---

## English

### What is AGL?
**AGL (Engineering OS)** is a cognitive operating system and portable framework for AI coding agents (Claude Code, Cursor, Antigravity, and others). It transforms agents from impulsive code-churners that hallucinate completion into disciplined, root-cause-driven software engineers.

### Core Problems Solved:
1. **Hallucination of Completion:** Agents declaring victory without running or verifying code.
   - *Fix:* The **Iron Law** & **Gate Function** — no claim without fresh, verifiable evidence and exit codes.
2. **Whack-a-Mole Symptom Patching:** Wrapping errors in generic `try/except` instead of fixing the root cause.
   - *Fix:* 4-category failure classification (Assumption, Implementation, Comprehension, Environment) with mandatory shared-code root fixes.
3. **Infinite Loops & Token Drain:** Repeating failed attempts blindly.
   - *Fix:* **The Stop Rule** — automatically aborts after 3 distinct failed paths and produces an actionable escalation brief.
4. **Blind Modifying (Shooting from the Hip):** Modifying files based on guesswork before reading reality.
   - *Fix:* **Truth Hierarchy** (Code > Memory) and 3-tier knowledge tagging (Documented / Inferred / Unknown).
5. **Single-Bias Blindness:** Overly optimistic or lazy solutions.
   - *Fix:* **The Council of Six** (Builder, Red Critic, Guard, User Voice, Historian, Ambitious) stress-testing major decisions.
6. **Destructive Environment Actions:** Accidental resets, overwriting user changes, or blind git pushes.
   - *Fix:* File Exclusivity (register-before-create) + `git_guard` / `shell_guard`; in Claude Code the `hook_pretooluse.py` hook makes it enforced (asks the *user*, not the agent).

```bash
git clone https://github.com/anr466/AGL.git && cd AGL
python install.py                  # Installs skill + gates + jobs + hook (add --claude for Claude Code)
python gates_selftest.py           # 16/16 checks pass
python test_hardening.py           # 28 hardening + background-jobs tests
python jobs.py start "pytest -q"   # background job: returns an id immediately (Linux/macOS)
```
