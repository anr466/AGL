<p align="center">
  <img src="logo/agl_logo.png" alt="AGL" width="260">
</p>

<h1 align="center">AGL — Engineering OS</h1>

<p align="center">
  <strong>نظام تشغيل هندسي لوكلاء الذكاء الاصطناعي: لا ادعاء بلا دليل، ولا كتابة على git بلا موافقتك.</strong><br>
  <em>A portable skill + code gates that make an AI coding agent honest, careful and verifiable.</em>
</p>

<p align="center">
  <a href="https://github.com/anr466/AGL/actions/workflows/selftest.yml"><img src="https://github.com/anr466/AGL/actions/workflows/selftest.yml/badge.svg" alt="selftest"></a>
  <img src="https://img.shields.io/badge/license-MIT-black" alt="MIT">
  <img src="https://img.shields.io/badge/python-3.x-black" alt="python 3">
  <img src="https://img.shields.io/badge/dependencies-none-black" alt="no dependencies">
</p>

<p align="center">
  <a href="#-ماذا-يفعل">ماذا يفعل</a> ·
  <a href="#-ابدأ-في-دقيقة">ابدأ</a> ·
  <a href="#-كيف-يعمل">كيف يعمل</a> ·
  <a href="#-الأوامر">الأوامر</a> ·
  <a href="#-أسئلة-شائعة">أسئلة</a> ·
  <a href="#english">English</a>
</p>

---

## 🎯 ماذا يفعل

AGL حزمة من جزأين تعمل معاً:

| الجزء | ما هو | أثره على الوكيل |
|---|---|---|
| **`SKILL.md`** | منهجية مكتوبة (مهارة) يفعّلها المحرر عند الحاجة | يقرأ الكود قبل أن يحكم، يصنّف معرفته، يقيس أثر تعديله، ولا يعلن نجاحاً بلا دليل |
| **`gates.py`** | بوابات كودية وواجهة سطر أوامر | ترفض فعلياً أوامر git الخطرة، وتتحقق من النتائج، وتوقف الدوران بعد 3 مسارات فاشلة |

**مناسب لمن؟** من يعمل مع وكيل برمجة (Antigravity أو Claude Code أو Cursor أو غيرها) ويريد وكيلاً أصدق وأحذر.
**ليس مناسباً لـ:** الأسئلة العابرة والتعديلات التافهة — المنهجية تتناسب مع حجم المهمة ولا تُفرض عليها.

## ⚡ ابدأ في دقيقة

```bash
git clone https://github.com/anr466/AGL.git
cd AGL
python install.py                  # عام لكل مشاريعك
# أو لمشروع واحد:
python install.py --project /path/to/project
```

يُنسخ إلى `~/.gemini/config/skills/engineering-os/` (أو `<مشروع>/.agents/skills/engineering-os/`) ومعه البوابات. بعدها يفعّل المحرر المهارة تلقائياً للمهام الهندسية غير البسيطة.

**تحقق أنها تعمل:**
```bash
python gates.py git "git push"     # يطبع الرفض ويخرج برمز 1
python gates_selftest.py           # 16/16
```

> المتطلبات: Python 3 فقط، بلا مكتبات خارجية.
> لمحررات أخرى: انسخ `SKILL.md` إلى مجلد المهارات أو القواعد عندها، وأبقِ `gates.py` بجانبه.

## 🧭 كيف يعمل

```
طلبك ──► الوكيل يفعّل المهارة ──► حلقات (حقيقة ← فهم ← تنفيذ ← تحقق) ──► نتيجة بدليل
                                        │
                                        └─► gates.py يمنع/يفحص: git • تحقق • تصنيف فشل • إيقاف
```

**أمثلة على سلوك الوكيل بعد التفعيل**

| الموقف | بدون AGL | مع AGL |
|---|---|---|
| انتهى التعديل | «تم بنجاح ✅» | يشغّل الاختبار ويعرض الأمر والنتيجة ورمز الخروج |
| فشل الاختبار 3 مرات بطرق مختلفة | يستمر في التجربة | يتوقف ويكتب: ما جُرّب، الأخطاء، تخمين الجذر، وماذا يحتاج منك |
| يريد حفظ عمله | `git add -A && git commit && git push` | يقترح الملفات والرسالة وينتظر موافقتك |
| ملف لا يعرف مصدره | يعدّله أو يحذفه | لا يمس إلا ما أنشأه هو في المهمة |

**المبادئ الستة (مختصرة)**
1. الحقيقة في الكود لا الذاكرة.
2. لا لمس قبل الفهم (موثق / مستنتج / مجهول).
3. أصغر تغيير *كامل* — النطاق بالأثر.
4. التحقق الكافي: قراءة عكسية + عدّاد مستقل + حالة مرئية + طابع زمني.
5. الجذر مرة واحدة، مع تصنيف الفشل (افتراض / تنفيذ / فهم / بيئة).
6. المعتمد ثابت؛ ملفات المستخدم لا تُمس.

التفاصيل الكاملة في [`SKILL.md`](SKILL.md).

## 🛠️ الأوامر

كلها `python gates.py <أمر>`، ورمز الخروج `1` يعني «مرفوض — توقف».

| الأمر | الغرض | مثال |
|---|---|---|
| `git` | فحص أمر git قبل تنفيذه | `gates.py git "git commit -m x"` ← مرفوض حتى `--approved` |
| `verify` | التحقق الكافي بعد عملية تخزين | `gates.py verify --label import --expected 5 --actual 5 --stored ok --visible yes --timestamp 2026-10-27` |
| `classify` | تسجيل نوع الفشل وبروتوكوله | `gates.py classify بيئة "login" "session expired"` |
| `stop` | عدّ المسارات الفاشلة المختلفة | `gates.py stop --sig "retry with proxy" --err "timeout"` |

يمكن أيضاً استيراد `gates` من Python (`StopRule`, `FileExclusivity`, `verify_readback`, `git_guard`, …).

## 📏 قياس السلوك (اختياري)

- [`BRAIN_TEST.md`](BRAIN_TEST.md): ستة اختبارات سلوكية (أولويات، اختصار مغري، أنواع الفشل، فهم قبل الحل، صدق التحقق، مجلس قرار) وقالب تقييم.
- [`brain_score.py`](brain_score.py): يحوّل أدلة الجلسة إلى نسبة مئوية عبر 10 محاور.

> هذا **تقييم ذاتي**: اربط كل علامة بدليل قابل للفحص، ويُفضَّل أن يراجعها طرف آخر.

## 📂 محتويات المستودع

```
SKILL.md              المنهجية (الملف الذي يفعّله المحرر)
gates.py              البوابات الكودية + CLI
gates_selftest.py     اختبار ذاتي (16 فحصاً) — يعمل في CI
install.py            تثبيت المهارة مع بواباتها
BRAIN_TEST.md         اختبارات السلوك + قالب التقييم
brain_score.py        مقياس رقمي (تقييم ذاتي)
logo/agl_logo.png     الشعار
.github/workflows/    CI
```

## ❓ أسئلة شائعة

<details><summary>هل تُبطئ الوكيل في المهام الصغيرة؟</summary>
لا. جدول «التناسب» في `SKILL.md` يقصر المنهجية على الحلقتين 1 و7 للتعديلات التافهة.
</details>

<details><summary>هل البوابات «إجبارية» فعلاً؟</summary>
هي أدوات يستدعيها الوكيل بتوجيه من المهارة وتعيد رمز خروج 1 عند الرفض؛ لا شيء يمنع وكيلاً يتجاهل التعليمات من تجاوزها. للإلزام الحقيقي اربطها بخطاف (hook) في محررك.
</details>

<details><summary>أين تُحفظ حالة <code>stop</code>؟</summary>
في ملف `.gates_stop.json` بالمجلد الحالي (متجاهَل في git). استخدم <code>--reset</code> لبدء مهمة جديدة.
</details>

<details><summary>هل أحتاج نسخ المجلد كاملاً؟</summary>
`install.py` ينسخ ما يلزم. نسخ `SKILL.md` وحده يعطيك القواعد النصية دون البوابات.
</details>

## 🤝 المساهمة

افتح Issue بوصف المشكلة وسلوك الوكيل المتوقع، وأرفق مخرج `python gates_selftest.py`. أي تعديل على `gates.py` يلزمه اختبار في `gates_selftest.py`.

## 📄 الترخيص

[MIT](LICENSE)

---

## English

**AGL (Engineering OS)** is a portable skill (`SKILL.md`) plus a small dependency-free Python CLI (`gates.py`) for AI coding agents.

- **Honest:** no completion claim without fresh evidence (command + output + exit code).
- **Careful:** blocks `commit`/`push`/`reset --hard`/`clean`/`add -A`/`--force` unless you approve (`git_guard`).
- **Efficient:** stops after 3 *distinct* failed approaches and escalates with a structured report.
- **Proportional:** a trivial edit gets a light process; a major decision gets the full loop.

```bash
git clone https://github.com/anr466/AGL.git && cd AGL
python install.py                  # global skill + gates
python gates_selftest.py           # 16/16
python gates.py git "git push"     # rejected, exit code 1
```

Gates are tools the agent calls under the skill's guidance; they are not an OS-level sandbox. Behavior scoring (`BRAIN_TEST.md`, `brain_score.py`) is self-assessed — attach evidence to every mark. License: MIT.
