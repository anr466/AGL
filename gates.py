#!/usr/bin/env python3
"""gates.py — البوابات الإجبارية: تحويل قوانين engineering-os إلى كود يفرض نفسه.
الفلسفة: القاعدة النصية تُنسى تحت الضغط — القاعدة داخل الأداة أصعب تجاوزاً.
أي سكربت بناء/تنفيذ يستورد هذه البوابات ولا ينفذ خطوة بدونها.
ملاحظة صدق: البوابات تفحص ما يُمرَّر لها؛ صدق مصدر الأدلة (قراءة مستقلة فعلية) مسؤولية المستدعي."""


class GateViolation(Exception):
    """البوابة رفضت الخطوة — التوقف إجباري وليس اختيارياً."""
    pass


# ═══ بوابة 1: التحقق الكافي (قائمة الفحوص الأربعة) ═══

def verify_readback(expected_count, readback_fn, label):
    """بوابة التحقق الكافي: قراءة عكسية من المصدر بعد كل عملية.
    expected_count: العدد المتوقع
    readback_fn: دالة ترجع (actual_count, evidence_dict) من المصدر المستقل
                 evidence_dict يحمل المفاتيح: stored / visible / timestamp
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
    المسار المكرر (نفس الطريقة) لا يُحسب — استدعِ can_retry قبل كل محاولة لرفض التكرار."""

    def __init__(self, max_distinct=3):
        self.max = max_distinct
        self.tried = []          # (signature, error)

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
    """حارس ملفات المهمة: ما أنشأه الوكيل هذه المهمة فقط له حق الحذف/التعديل الحُر.
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
    أي فشل بالوحدة الأولى يمنع الدفعة (GateViolation) — الواقع اختلف عمّا افترضته."""
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
    """يسجل تصنيف الفشل الذي حدده الوكيل ويرجع بروتوكوله.
    kind: أحد FAILURE_TYPES (افتراض/تنفيذ/فهم/بيئة) — يقرره الوكيل بعد التحليل، لا تخمين من نص.
    ترمي GateViolation إذا كان التصنيف غير معروف."""
    if kind not in FAILURE_TYPES:
        raise GateViolation(f'تصنيف فشل غير معروف «{kind}» — المسموح: {", ".join(FAILURE_TYPES)}')
    return {'type': kind, 'protocol': FAILURE_TYPES[kind], 'where': where[:80], 'what': what[:120]}
