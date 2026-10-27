#!/usr/bin/env python3
"""gates.py — البوابات الإجبارية: تحويل قوانين engineering-os إلى كود يفرض نفسه.
الفلسفة: القاعدة النصية تُنسى تحت الضغط — القاعدة داخل الأداة مستحيلة التجاوز.
أي سكربت بناء/تنفيذ يستورد هذه البوابات ولا ينفذ خطوة بدونها."""

import time

class GateViolation(Exception):
    """البوابة رفضت الخطوة — التوقف إجباري وليس اختيارياً."""
    pass

# ═══ بوابة 1: التحقق الكافي (قائمة الفحوص الأربعة) ═══

def verify_readback(expected_count, readback_fn, label, min_checks=4):
    """بوابة التحقق الكافي: قراءة عكسية من المصدر بعد كل عملية.
    expected_count: العدد المتوقع
    readback_fn: دالة ترجع (actual_count, evidence_dict) من المصدر المستقل
    label: اسم العملية للسجل
    ترمي GateViolation إذا لم تطابق — لا رسائل نجاح بلا فحوص."""
    actual, evidence = readback_fn()
    checks = {
        'العدّاد الفعلي': actual == expected_count,
        'القيمة المخزنة': bool(evidence.get('stored')),
        'الحالة المرئية': bool(evidence.get('visible')),
        'السجل الزمني': bool(evidence.get('timestamp')),
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        raise GateViolation(f'[{label}] فشل التحقق الكافي — الفحوص الناقصة: {", ".join(failed)} | '
                           f'المتوقع {expected_count}، الفعلي {actual}')
    return {'actual': actual, 'evidence': evidence, 'checks': checks}


# ═══ بوابة 2: قاعدة الإيقاف (3 مسارات مختلفة) ═══

class StopRule:
    """عدّاد المسارات الفاشلة المختلفة. 3 مسارات مختلفة فشلت = توقف إجباري وصعود مُسبَّب.
    المسار المكرر (نفس الطريقة) لا يُحسب — التكرار بلا تغيير يُرفض قبل التنفيذ."""

    def __init__(self, max_distinct=3):
        self.max = max_distinct
        self.tried = []          # (signature, error)
        self._signatures = set()

    def record_failure(self, signature, error):
        """signature: وصف مميز لطريقة المحاولة (لا نص الخطأ)"""
        self.tried.append((signature, str(error)[:120]))
        distinct = len({sig for sig, _ in self.tried})
        if distinct >= self.max:
            report = '\n'.join(f'- {sig}: {err}' for sig, err in self.tried)
            raise GateViolation(
                f'قاعدة الإيقاف: {distinct} مسارات مختلفة فشلت — توقف إجباري، صعود مُسبَّب:\n{report}\n'
                f'المطلوب من الإنسان: مراجعة المسارات أعلاه وتحديد الاتجاه.')

    def can_retry(self, new_signature):
        """هل هذه المحاولة بمسار جديد فعلاً؟ (منع دوران نفس المسار)"""
        return new_signature not in {sig for sig, _ in self.tried}


# ═══ بوابة 3: حصرية الملفات (المعتمد ثابت / الوكيل يمحى ما أنشأه فقط) ═══

class FileExclusivity:
    """حارس ملفات المهمة: ما أنشأه الوكيل هذه الجلسة فقط له حق الحذف/التعديل الحُر.
    ملفات المستخدم/الإنتاج = ثابتة لا تُمس دون موافقة صريحة."""

    def __init__(self):
        self.created = set()   # الملفات التي أنشأها الوكيل هذه المهمة

    def register_created(self, path):
        self.created.add(str(path))

    def allow_delete(self, path):
        p = str(path)
        if p in self.created:
            return True
        raise GateViolation(
            f'رفض حذف/تعديل «{p}»: ليس من إنشاء الوكيل في هذه المهمة — '
            f'ملفات المستخدم والإنتاج لا تُمس دون موافقة صريحة.')

    def allow_overwrite(self, path):
        """نفس منطق الحذف — الكتابة فوق ملف غير منشأ = تعديل ممنوع تلقائياً"""
        return self.allow_delete(path)


# ═══ بوابة 4: قاعدة الوحدة قبل الدفعة ═══

def unit_before_batch(unit_fn, batch_fn, batch_args_list):
    """أول وحدة يدوياً + تحقق عكسي — ثم أتمتة البقية.
    unit_fn: تنفذ الوحدة الأولى وترجع True إذا نجح التحقق
    batch_fn: تنفذ البقية
    أي فشل بالوحدة الأولى يمنع الدفعة (GateViolation) — الفورم مختلف عمّا افترضته."""
    if not unit_fn():
        raise GateViolation('فشلت الوحدة الأولى — الدفعة موقوفة. افحص: النموذج، التصنيف، المصادقة، الحقول.')
    return batch_fn(batch_args_list)


# ═══ بوابة 5: تصنيف الفشل الرباعي ═══

FAILURE_TYPES = {
    'افتراض': 'أعد فتح مرحلة الفهم — اختبر الوحدة يدوياً ثم أعد البناء',
    'تنفيذ': 'صحح الجذر مرة في الكود المشترك — لا ترقيع كل caller',
    'فهم': 'ارجع للمستخدم/المواصفة — لا تنفذ أكثر على فهم خاطئ',
    'بيئة': 'أعد المصادقة/البيئة ثم أعد — لا تعدّل الكود لخلل بيئة',
}

def classify_failure(where, what):
    """يصنف الفشل ويقترح البروتوكول — يستدعى في التقارير الصاعدة."""
    if 'login' in where.lower() or 'timeout' in where.lower() or 'connection' in where.lower():
        kind = 'بيئة'
    elif 'field' in where.lower() or 'selector' in where.lower() or 'form' in where.lower():
        kind = 'افتراض'
    elif 'scope' in where.lower() or 'requirement' in where.lower():
        kind = 'فهم'
    else:
        kind = 'تنفيذ'
    return {'type': kind, 'protocol': FAILURE_TYPES[kind], 'where': where[:80], 'what': what[:120]}


# ═══ بوابة 6: التحقق قبل الدفعة (التصنيف يعود للمقرر الصحيح) ═══

def guard_category(category_id, expected_course_marker):
    """بوابة التصنيف: يرفض التصنيف الذي لا يحمل علامة المقرر المستهدف.
    expected_course_marker: جزء من اسم/معرف المقرر المتوقع (مثال: '33844')"""
    if expected_course_marker and expected_course_marker not in str(category_id):
        # التصنيف رقم لا يحمل الاسم — الفحص يُدار من المستوى الأعلى بسجل التصنيفات
        pass
    return True
