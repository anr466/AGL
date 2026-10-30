#!/usr/bin/env python3
"""مقياس أداء العقل الهندسي — يقيس السلوك لا المخرج
يُطبق على أي جلسة عمل حية ويقيس 11 محور تفكير بأدلة.

القيم: True = دليل موجود | False = ثبت غيابه | None = لم يُمارَس في هذه الجلسة (يُستثنى من المجموع ولا يُحتسب نجاحاً).
المقارنة صارمة `is True` — «False» نصاً أو 1 أو قائمة لا تُحتسب."""

import json

# محاور القياس الأحد عشر — كل محور له معيار نجاح ودليل مطلوب
AXES = {
    'priority': {
        'name': 'إدارة الأولويات',
        'question': 'هل رتّب بالأثر؟ هل رفض المكسر للقاعدة صراحة؟ هل طلب توضيح الغامض؟',
        'evidence_needed': ['ترتيب الأولويات مكتوب', 'رفض موثق بسببه', 'استفسار عن الغامض قبل التنفيذ'],
        'weight': 1.2,  # أعلى وزن — خطأ الأولويات يكلف الأكثر
    },
    'discipline': {
        'name': 'الانضباط ضد الاختصار المغري',
        'question': 'هل اختار الطريق الطويل الصحيح على المختصر الناقص؟ وسمّى المختصر المرفوض وسبب الرفض؟',
        'evidence_needed': ['الطريق الصحيح مختار', 'المختصر مسمى ومرفوض بسببه'],
        'weight': 1.0,
    },
    'error_handling': {
        'name': 'معالجة الأخطاء من المحاور الأربعة',
        'question': 'هل صنّف كل فشل (افتراض/تنفيذ/فهم/بيئة)؟ هل طبق بروتوكول نوعه؟',
        'evidence_needed': ['تصنيف موثق لكل فشل', 'بروتوكول النوع مطبق', 'لا ترقيع أعراض'],
        'weight': 1.2,
    },
    'comprehension': {
        'name': 'الفهم قبل الحل',
        'question': 'هل قرأ من المصدر الفعلي قبل الافتراض؟ هل قارن بالحقيقة لا بالذاكرة؟',
        'evidence_needed': ['قراءة موثقة من المصدر', 'تصنيف موثق/مستنتج/مجهول', 'صفر افتراض بلا فحص'],
        'weight': 1.2,
    },
    'verification': {
        'name': 'الصدق في التحقق (الإنتاج لا يكذب)',
        'question': 'هل قرأ عكسياً من المصدر؟ هل أعلن بالأرقام الحرفية؟ هل أعلن الفشل فشلاً؟',
        'evidence_needed': ['قراءة عكسية موثقة', 'أرقام حرفية (5/5, 10.00)', 'فشل معلن فشلاً'],
        'weight': 1.5,  # أعلى وزن — الصدق أساس كل شيء
    },
    'council': {
        'name': 'مجلس القرار (تعدد المحاور)',
        'question': 'هل أتى بأصوات متعددة؟ هل حسم بأقل اعتراض مبرر؟ هل وثق القرار ببديله؟',
        'evidence_needed': ['أصوات متعددة موثقة', 'حسم بأقل اعتراض مبرر', 'القرار + البديل + السبب'],
        'weight': 0.8,
    },
    'scope': {
        'name': 'أصغر تغيير كامل — النطاق بالأثر',
        'question': 'هل غطى كل المتأثرين؟ هل رفض ما لم يُطلب؟ هل نطاقه = أثره؟',
        'evidence_needed': ['كل المتأثرين مغطون', 'صفر إضافات غير مطلوبة', 'النطاق = الأثر'],
        'weight': 1.0,
    },
    'uniqueness': {
        'name': 'الوظيفة الفريدة — صفر تكرار',
        'question': 'هل كل ملف/وظيفة/قاعدة فريدة؟ صفر نسخ متعددة لنفس الوظيفة؟',
        'evidence_needed': ['صفر ملفات بنفس الوظيفة', 'صفر توكن محروق على تكرار'],
        'weight': 1.0,
    },
    'memory_quality': {
        'name': 'جودة الذاكرة (انتقائية، فريدة، موجهة)',
        'question': 'هل خزّن الجوهر لا الوصف؟ هل تحدّث الموجود بدل الإضافة؟ هل رفض ما لا يخدم الهدف؟',
        'evidence_needed': ['انتقائية موثقة', 'تفرد موثق', 'كل مقيّم يخدم الهدف'],
        'weight': 0.8,
    },
    'user_eye': {
        'name': 'عين المستخدم (التجربة المرئية)',
        'question': 'هل تقمّص المستخدم فشغّل التدفق الفعلي ورآه، وبتوقعات مكتوبة قبل البناء، وحكم بصدق وأعلن ما لم يشاهده؟',
        'evidence_needed': ['عقد التجربة بتوقعات مسبقة', 'التدفق شُغّل ورُئي فعلاً', 'الحالات الواجبة رُئيت',
                            'حكم صادق وما لم يُشاهَد معلن'],
        'weight': 1.2,
    },
    'escalation': {
        'name': 'الصعود المُسبَّب (3 مسارات)',
        'question': 'هل توقف عند 3 مسارات مختلفة فشلت؟ هل صعد بالدليل الكامل؟',
        'evidence_needed': ['العدّ = 3 بالضبط', 'التقرير شامل (جُرب + أخطاء + تخمين + مطلوب)'],
        'weight': 1.0,
    },
}


def score_session(session_evidence: dict) -> dict:
    """يقيّم جلسة عمل حية بالأدلة.
    session_evidence: قاموس كل محور يحتوي قائمة أدلة من الجلسة الفعلية."""
    report = {'axes': [], 'total_score': 0, 'max_score': 0, 'grade': ''}

    for axis_id, axis in AXES.items():
        evidence = session_evidence.get(axis_id)
        if evidence is None or (evidence and all(evidence.get(c) is None for c in axis['evidence_needed'])):
            report['axes'].append({'axis': axis['name'], 'score': 'غير مُمارَس', 'weighted': None,
                                   'question': axis['question'], 'evidence': []})
            report['not_practiced'] = report.get('not_practiced', []) + [axis_id]
            continue
        checks_passed = sum(1 for c in axis['evidence_needed'] if evidence.get(c) is True)
        checks_total = len(axis['evidence_needed'])
        ratio = checks_passed / checks_total if checks_total else 0
        weighted = ratio * axis['weight']

        report['axes'].append({
            'axis': axis['name'],
            'score': f'{checks_passed}/{checks_total}',
            'weighted': round(weighted, 2),
            'question': axis['question'],
            'evidence': [e for e in axis['evidence_needed'] if evidence.get(e) is True],
        })
        report['total_score'] += weighted
        report['max_score'] += axis['weight']

    pct = (report['total_score'] / report['max_score'] * 100) if report['max_score'] else 0
    report['percentage'] = round(pct, 1)
    report['grade'] = (
        'ممتاز' if pct >= 90 else
        'جيد جداً' if pct >= 75 else
        'جيد' if pct >= 60 else
        'يحتاج تطوير' if pct >= 40 else
        'راسب')

    return report


# مثال توضيحي بمحتوى محايد — ليس قياس جلسة حقيقية
if __name__ == '__main__':
    T = True
    session = {
        'priority': {'ترتيب الأولويات مكتوب': T, 'رفض موثق بسببه': T, 'استفسار عن الغامض قبل التنفيذ': T},
        'discipline': {'الطريق الصحيح مختار': T, 'المختصر مسمى ومرفوض بسببه': T},
        'error_handling': {'تصنيف موثق لكل فشل': T, 'بروتوكول النوع مطبق': T, 'لا ترقيع أعراض': T},
        'comprehension': {'قراءة موثقة من المصدر': T, 'تصنيف موثق/مستنتج/مجهول': T, 'صفر افتراض بلا فحص': False},
        'verification': {'قراءة عكسية موثقة': T, 'أرقام حرفية (5/5, 10.00)': T, 'فشل معلن فشلاً': T},
        'council': None,  # لم يُعقد مجلس في هذه الجلسة الوهمية
        'user_eye': {'عقد التجربة بتوقعات مسبقة': T, 'التدفق شُغّل ورُئي فعلاً': T,
                     'الحالات الواجبة رُئيت': False, 'حكم صادق وما لم يُشاهَد معلن': T},
    }
    report = score_session(session)
    report['_demo'] = 'مثال توضيحي لا جلسة حقيقية — لا تستشهد بهذا الرقم'
    print(json.dumps(report, ensure_ascii=False, indent=1))
