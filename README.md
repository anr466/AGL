<div align="center">

<img src="logo/agl_logo.png" alt="AGL" width="180">

# AGL — The Engineering Mind

**العقل الهندسي الموحد**

*Turns AI coding agents from impulsive generators into disciplined engineers.*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-13%2F13-brightgreen.svg)](gates_selftest.py)
[![Deps](https://img.shields.io/badge/deps-zero-black.svg)]()
[![ar](https://img.shields.io/badge/lang-العربية-green.svg)]()

[Install](#-install) · [The 6 Laws](#-the-six-laws) · [العربية](#-ar)

</div>

---

## The Problem

Every AI coding agent shares the same failures:

```text
❌ Says "done!" without verification
❌ Patches symptoms, ignores root cause
❌ Repeats the same mistake every session
❌ Over-engineers what nobody asked for
❌ Loops infinitely, burning tokens
```

## The Fix

```text
✅ Iron Law: fresh evidence in this message — or no claim
✅ Root cause once — never patch symptoms
✅ Council of 6 reviews every major decision
✅ Stop after 3 distinct failed paths — escalate
✅ Memory is a curated knowledge base, not a log
```

**One file. Any editor. Any agent.**

---

## ✨ What You Get

| | | |
|---|---|---|
| 🏛️ | **Council of 6** | Every architectural decision reviewed by 6 voices — builder, red team, guardian, user, historian, visionary |
| ⚖️ | **Iron Law** | Fresh evidence in this message — or no claim |
| 🧬 | **Knowledge Tiers** | Documented / Inferred / Unknown — prevents deciding on unknowns |
| 📁 | **File Exclusivity** | Adopted stays / Experimental goes — user files untouchable |
| 🛑 | **Stop Rule** | 3 distinct failed paths = escalate with evidence |
| 🌍 | **Arabic / RTL** | First framework with full Arabic methodology |

---

## 📥 Install

### One File (any editor)

Copy `SKILL.md` to your agent's skills folder:
- **Claude Code**: `.claude/skills/engineering-os/SKILL.md`
- **Cursor**: `.cursor/rules/engineering-os.mdc`
- **Any agent**: add to system prompt

### Full Package (enforcement gates)

```bash
git clone https://github.com/anr466/AGL.git
python3 AGL/install.py --project /path/to/your/project
```

`gates.py` gives you code-level enforcement: verify_readback, StopRule, FileExclusivity, classify_failure.

---

## 🌍 Arabic / العربية

<div dir="rtl">

### AGL — العقل الهندسي الموحد

نظام تشغيل معرفي يحوّل وكيل البرمجة من مولّد كود مندفع إلى مهندس منضبط.

**المشكلة**: الوكيل يقول «نجح!» بلا تحقق، يرقّع الأعراض، يكرر نفس الخطأ، يبالغ بالتعقيد، ويدور بلا نهاية.

**الحل**: القانون الحديدي (دليل طازج أو لا ادعاء) + الجذر مرة + مجلس ستة + قاعدة الإيقاف + ذاكرة انتقائية موجهة للهدف.

**ميزة فريدة**: أول إطار يدعم العربية والـRTL بمنهجية هندسية كاملة — من ندوب حقيقية ببيئة عربية.

</div>

---

## 📂 Structure

```text
AGL/
├── SKILL.md              ← The Brain
├── LICENSE               ← Apache-2.0
├── README.md             ← This file
├── BRAIN_TEST.md         ← Brain test battery (6 tests)
├── brain_score.py        ← Mind performance score (10 axes)
├── gates.py              ← Enforcement gates
├── gates_selftest.py     ← Gate self-test (13/13)
├── install.py            ← Auto-installer
├── hook_pretooluse.py    ← Pre-tool-use gate
├── ux_gate.py            ← UX gate
├── test_hardening.py     ← Hardening tests
├── test_ux_gate.py       ← UX gate tests
├── jobs.py               ← Scheduled jobs
├── logo/                 ← Logo assets
└── docs/                 ← Documentation
```

---

## 📄 License

Apache-2.0
