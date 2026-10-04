# المُخبر الرقمي الذكي (CPH)

منصة ويب عربية لتنظيم بلاغات ابتزاز إلكتروني واحتيال مالي بين ضحية ومحقق، مع تحليلات قواعدية محاكاة ونموذج نصي اختياري. الخادم `app.py`. القاعدة `cph.db`.

## 1 ما هو المشروع

Cyber-Police Hub يجمع تقديم البلاغ، المرفقات، عرض الحالة، تحليل الرابط والحساب والنص والصورة بشكل تجريبي، توصيات من نموذج تعلم آلي إن وُجد ملفه، محادثة، وإشعارات. النتائج تعليمية وليست دليلاً قضائياً. هذا الحكم مذكور في README السابق ويطابقه أسلوب الدوال `_run_link_analysis` و`_run_account_analysis` التي تعتمد قواعد و`hash`.

## 2 لماذا وُجد

تنظيم مسار بلاغ من الضحية إلى المحقق على جهاز محلي: حفظ منظم في SQLite، وواجهة RTL، وتفريق واضح بين محاكاة الواجهة ونموذج TF-IDF. README السابق يشرح هذا الهدف، والكود يحققه عبر Flask و`cph.db`.

## 3 المستخدمون

| user_type | الواجهة | البيانات |
| --- | --- | --- |
| victim | `victim.html`, `analysis.html`, `chat.html` | بلاغاته فقط في `GET /api/reports` |
| investigator | `investigator.html`, `admin.html`, التحليل والمحادثة | كل البلاغات وتحديثها |

حسابات البذرة في `seed_db` إذا كان جدول `user` فارغاً:

| الدور | البريد | كلمة المرور | الاسم في البذرة |
| --- | --- | --- | --- |
| ضحية | victim@cph.gov | 123456 | أحمد محمد العلي |
| محقق | investigator@cph.gov | 123456 | المحقق خالد السعيد |

الشارة في البذرة: `INV-1001`، القسم: مكافحة الجرائم المعلوماتية.

## 4 الميزات

- تسجيل ودخول: `POST /api/register` و`POST /api/login`.
- إنشاء بلاغ `multipart` مع روابط وحسابات ولقطات ووسائط.
- تحليل رابط وحساب عند الإنشاء، وإعادة التحليل من `/api/analyze/*`.
- تحليل أسلوبي، وصورة من Base64، وبحث عكسي محاكى.
- محادثة لكل بلاغ مع إشعار للمستلم.
- توصيات `GET /api/ai-recommendations/<report_id>` عبر `cph_model.pkl` أو منطق احتياطي.
- حالة النموذج: `GET /api/ai-status`.
- إشعارات وقراءتها.
- قائمة محققين.
- صفحات HTML في جذر المشروع ونسخ تحت `static/`.

`deepfake_score` عند رفع الوسائط قيمة مشتقة من `hash` لاسم الملف، وليست كاشف تزوير. التحليل الأسلوبي كلمات مكررة وكلمات مفتاحية للهجة.

## 5 سير العمل

```
index.html -> login.js -> POST /api/login
  -> user_id يُحفظ كـ cph_token
  -> Authorization: Bearer <user_id>

ضحية: victim.js -> POST /api/reports (FormData)
  -> report + links + accounts + ملفات uploads/
  -> تحليل رابط/حساب فوري

تحليل: analysis.js?id=
  -> GET /api/reports/<id>
  -> POST /api/analyze/...
  -> GET /api/ai-recommendations/<id>

محادثة: chat.js -> GET/POST /api/chat/<id>
  -> notification للمستلم

محقق: admin.js -> PUT /api/reports/<id>
```

## 6 أمثلة واقعية

البذرة تنشئ 5 بلاغات للضحية التجريبية:

| النوع | المبلغ | الحالة | مثال الوصف المختصر |
| --- | --- | --- | --- |
| ابتزاز | 5000 | قيد الانتظار | تهديد عبر إنستقرام ورابط واتساب مزيف |
| ابتزاز | 15000 | تحت التحقيق | سناب شات وحساب blackmail_snap |
| احتيال | 800 | تحت التحقيق | استثمار تيليجرام |
| احتيال | 22000 | منتهي | متجر tech_deals_ksa |
| ابتزاز | 3500 | قيد الانتظار | ادعاء اختراق ووصف فيديو مفبرك |

بلاغان يُربطان في `linked_case` بسبب «أسلوب كتابة متشابه». هذه بيانات زرع وليست قضايا حقيقية.

## 7 رحلة المستخدم

الضحية تسجّل الدخول، تملأ نوع البلاغ والوصف والمبلغ، ترفق لقطة، ترسل. ترى البطاقة في القائمة، تفتح التحليل، تراسل المحقق، وتقرأ الجرس.

المحقق يرى كل البلاغات، يصفّي، يحدّث الحالة أو التعيين من لوحة الإدارة، ويرد في المحادثة فيصل إشعار للضحية.

إن وُجد `models/cph_model.pkl` يظهر `model_used: true` في التوصيات. وإلا يُستخدم الاحتياطي: تهديد عالي إذا النوع «ابتزاز» أو المبلغ أكبر من 10000.

## 8 الوحدات

| المسار | الدور |
| --- | --- |
| `app.py` | API وSQLite والتحليل والزرع |
| `train_model.py` | تدريب TF-IDF وRandom Forest |
| `dataset/training_data.json` | عينات text, report_type, threat_level |
| `dataset/TRAINING_STEPS.md` | خطوات تدريب يدوية |
| `models/cph_model.pkl` | يُنشأ بعد التدريب |
| `cph.db` | يُنشأ عند `init_db` |
| `uploads/` | مرفقات بعد `secure_filename` |
| `static/js/config.js` | `CPH_SERVER` و`API_BASE` و`apiRequest` |
| `static/js/auth.js` | `cph_token` و`cph_user` |
| `static/js/login.js` `victim.js` `investigator.js` `analysis.js` `chat.js` `notifications.js` `admin.js` `theme.js` | سلوك الصفحات |
| HTML في الجذر و`static/` | واجهات |
| `static/css/style.css` | التنسيق |

## 9 الكيانات

جداول `init_db`: `user`, `investigator`, `audit_log`, `report`, `suspect_account`, `chat_screenshot`, `malicious_link`, `media_file`, `ai_analysis`, `reverse_image_search`, `stylometry_profile`, `linked_case`, `chat_message`, `notification`.

`audit_log` يُنشأ في SQL. استنتاج من الكود: مسارات API المقروءة لا تدرج فيه أثناء الدخول أو إنشاء البلاغ. الجدول جاهز وغير موصول بالمسارات الحالية.

`linked_case` يُملأ في `seed_db` فقط، بلا مسار API لإنشاء الربط.

## 10 الصلاحيات

`require_auth` يتحقق أن الرأس `Authorization: Bearer` يساوي `user_id` موجوداً في `user`. لا انتهاء صلاحية.

`GET /api/reports`: الضحية تُفلتر بـ `user_id`، والمحقق يرى الجميع.

استنتاج من الكود: امتلاك `user_id` يكفي لاستدعاء المسارات المحمية. لا فحص ملكية صف لكل مسار في الملخص العام لـ README السابق، وهذا ما يزال وصف الرمز = المعرف.

## 11 الأتمتة

- `init_db` ثم `seed_db` ثم `ensure_simulation_notifications` عند `python app.py`.
- تحليل الرابط والحساب مباشرة بعد إدراج البلاغ.
- إشعار محادثة عبر `insert_chat_notifications`.
- إشعارات محاكاة إذا لم توجد إشعارات للحسابات التجريبية.
- التدريب يدوي: `python train_model.py`. لا مهمة مجدولة.

## 12 تأثير الوحدات على بعضها

- رسالة المحادثة تنشئ `chat_message` ثم `notification`.
- تعيين `investigator_id` يغيّر مستلم إشعار الضحية: المحقق المعيّن، أو كل المحققين إن لم يُعيَّن.
- تدريب النموذج لا يغيّر البلاغات المخزنة. يغيّر فقط حقل التوصية عند الطلب التالي.
- رفع صورة يكتب ملفاً في `uploads/` وصفاً في `chat_screenshot` أو `media_file`.
- حذف `cph.db` ثم إعادة التشغيل يعيد الزرع لأن `seed_db` يعمل عندما يكون عدد المستخدمين صفراً.

## 13 مسرد

| المصطلح | في هذا المشروع |
| --- | --- |
| cph_token | قيمة `user_id` في localStorage |
| SHA-256 | `hash_password` بلا ملح |
| TF-IDF | `TfidfVectorizer` في التدريب، analyzer أحرف |
| Random Forest | مصنفان: نوع البلاغ ومستوى التهديد |
| CORS | `origins="*"` لأن الصفحة قد تُفتح من منفذ غير 5000 |
| OSINT | سياق وصفي. البحث العكسي في الكود قائمة منصات ودرجة من hash |

تفاصيل المصطلحات الأطول (REST, JSON, UUID, multipart, RTL, CDN) محفوظة من README السابق وما زالت تطابق `app.py` و`config.js`.

## 14 أسئلة شائعة

**هل المنفذان إلزاميان؟** `config.js` يضبط `CPH_SERVER` على `http://127.0.0.1:5000`. إن فُتحت الصفحة من المنفذ 5000 يصبح `API_BASE` نفس الأصل. إن فُتحت من منفذ آخر (مثل Live Server) تُرسل الطلبات إلى 5000. يمكن تجاوز العنوان بـ `localStorage.cph_api_url`.

**هل الذكاء الاصطناعي يفحص الصور؟** لا. `predict_with_ai` يصنّف نص الوصف فقط.

**هل درجة التزييف حقيقية؟** لا. `deepfake_score` تقريبي من hash.

**ماذا لو غاب النموذج؟** التوصيات تعمل بالاحتياطي و`model_used: false`.

## 15 مخطط المعمارية ASCII

```
المتصفح (HTML + static/js)
        |  fetch + Bearer user_id
        v
Flask app.py  0.0.0.0:5000
  CORS *
  |-- SQLite cph.db
  |-- uploads/
  |-- models/cph_model.pkl (اختياري)
  |
train_model.py -> يقرأ dataset/training_data.json
               -> يكتب cph_model.pkl
```

## 16 التقنيات المستخدمة

- Flask 3.0.0
- Flask-CORS 4.0.0
- Werkzeug 3.0.1
- Pillow 10.1.0 لقراءة الصورة وEXIF عند الرفع
- scikit-learn 1.3.2 في `train_model.py`
- pickle للنموذج
- SQLite
- HTML وCSS وJavaScript

## 17 شجرة الملفات

```
CPH/
├── app.py
├── train_model.py
├── requirements.txt
├── README.md
├── cph.db                 (عند التشغيل)
├── uploads/
├── models/cph_model.pkl   (بعد التدريب)
├── dataset/
│   ├── training_data.json
│   └── TRAINING_STEPS.md
├── index.html  victim.html  investigator.html
├── analysis.html  chat.html  admin.html
├── about.html  model-status.html
└── static/
    ├── css/style.css
    ├── js/  config.js auth.js login.js victim.js
    │        investigator.js analysis.js chat.js
    │        notifications.js admin.js theme.js
    └── نسخ HTML موازية لبعض الصفحات
```

## 18 الواجهة الأمامية

`apiRequest` يضيف `Authorization` من `cph_token` ويضبط `Content-Type: application/json`. تقديم البلاغ في `victim.js` يستخدم `FormData` حتى تنتقل الملفات. `requireAuth` يعيد إلى `index.html` بلا رمز. الاتجاه RTL. أيقونات الواجهة من رابط CDN لـ Font Awesome حسب README السابق.

`CPH_SERVER` في أعلى `config.js` هو عنوان خادم Flask. تعليق الملف يوضح استبداله بعنوان IPv4 عند فتح الواجهة من جهاز ثانٍ على الشبكة.

## 19 الواجهة الخلفية

دوال غير مسارية: `load_ai_model`, `predict_with_ai`, `get_db`, `init_db`, `hash_password`, `get_chat_notification_recipients`, `insert_chat_notifications`, `ensure_simulation_notifications`, `require_auth`, `_run_link_analysis`, `_run_account_analysis`, `seed_db`.

دوال المسارات: `index`, `api_init`, `api_register`, `api_login`, `api_get_reports`, `api_create_report`, `api_get_report`, `api_update_report`, `api_analyze_link`, `api_analyze_account`, `api_analyze_image`, `api_analyze_stylometry`, `api_reverse_image`, `api_get_chat`, `api_send_message`, `api_get_notifications`, `api_notifications_read_all`, `api_notification_read`, `api_ai_status`, `api_get_investigators`, `api_ai_recommendations`.

`GET /` يرسل `static/index.html`.

## 20 تدفق الطلب

1. JSON أو FormData يصل إلى Flask.
2. `require_auth` يقرأ Bearer ويقارنه بـ `user.user_id`.
3. `get_db()` يفتح `cph.db` مع `timeout=30`.
4. الكتابة تتم ثم `commit`.
5. الرد JSON. الصفحة الثابتة تُبنى في المتصفح من هذا JSON.

تحليل الرابط: قاموس افتراضي (دولة غير معروفة، VPN خطأ، قائمة سوداء خطأ، تهديد منخفض). وجود `instagram` يضبط دولة الولايات المتحدة وVPN إذا `hash(url) % 5 == 0` وقائمة سوداء إذا `% 10 == 0`. وجود `t.me` أو `telegram` يضبط ألمانيا وVPN وتهديداً عالياً. الثقة المخزنة تقريباً 0.85.

تحليل الحساب: `h = abs(hash(username)) % 100`. بوت إذا `h < 25`. التصنيف وهمي أو مسروق أو حقيقي حسب العتبات في README السابق وهذا الكود.

## 21 قاعدة البيانات

ملف واحد `cph.db`.

العلاقة: صف `user` يقابله صف `investigator` للمحقق. `report.user_id` الضحية. `report.investigator_id` من جدول `investigator` لا من `user` مباشرة.

جداول تحمل `report_id`: الحسابات، الروابط، اللقطات، الوسائط، التحليل، الأسلوب، الرسائل، الإشعارات.

`reverse_image_search.media_id` يشير إلى `media_file`.

كلمات المرور: `password_hash` = SHA-256 سداسي عشري.

## 22 نقاط النهاية

| الطريقة | المسار | الغرض | المعاملات | مصادقة | الرد |
| --- | --- | --- | --- | --- | --- |
| GET | `/` | صفحة ثابتة | - | لا | HTML |
| POST | `/api/init` | init_db وتنبيهات المحاكاة | - | لا | JSON |
| POST | `/api/register` | مستخدم جديد | full_name, email, password, user_type وحقول إقامة | لا | JSON وuser_id |
| POST | `/api/login` | دخول | email, password | لا | JSON user_id, user_type |
| GET | `/api/reports` | قائمة | filter اختياري للمحقق | Bearer | JSON |
| POST | `/api/reports` | إنشاء | report_type, description, financial_amount, residency_info, links, accounts, screenshots, media | Bearer | JSON |
| GET | `/api/reports/<id>` | تفاصيل مجمّعة | report_id | Bearer | JSON |
| PUT | `/api/reports/<id>` | تحديث حالة/محقق/ملاحظات | حقول JSON | Bearer | JSON |
| POST | `/api/analyze/link` | تحليل رابط | url, report_id اختياري | Bearer | JSON |
| POST | `/api/analyze/account` | تحليل حساب | username, platform, report_id | Bearer | JSON |
| POST | `/api/analyze/image` | صورة Base64 | image, report_id | Bearer | JSON أبعاد ودرجة |
| POST | `/api/analyze/stylometry` | أسلوب | text, report_id | Bearer | JSON |
| POST | `/api/reverse-image` | بحث عكسي محاكى | بيانات صورة | Bearer | JSON منصات |
| GET | `/api/chat/<report_id>` | رسائل | report_id | Bearer | JSON |
| POST | `/api/chat/<report_id>` | إرسال | message | Bearer | JSON + إشعار |
| GET | `/api/notifications` | صندوق المستخدم | - | Bearer | JSON |
| POST | `/api/notifications/read-all` | تعليم الكل | - | Bearer | JSON |
| POST | `/api/notifications/<id>/read` | تعليم واحد | notification_id | Bearer | JSON |
| GET | `/api/ai-status` | هل النموذج محمّل | - | لا | JSON |
| GET | `/api/investigators` | قائمة المحققين | - | Bearer | JSON |
| GET | `/api/ai-recommendations/<report_id>` | توصيات | report_id | Bearer | JSON threat, type, model_used |

## 23 المصادقة

لا JWT. الرمز هو `user_id`. كلمة المرور SHA-256 بلا ملح (`hashlib.sha256`). التسجيل يدرج `user`، وإذا كان النوع محققاً يدرج `investigator`.

## 24 الأمان الموجود فعلياً في الكود

- معاملات SQL `?`.
- `secure_filename` للمرفقات.
- حد الجسم 16 ميجابايت.
- CORS لكل الأصول.
- `SECRET_KEY` ثابت داخل `app.py` (القيمة غير مذكورة هنا).
- `debug=True` و`host='0.0.0.0'`.
- الرمز لا ينتهي ولا يُبطَل عند الخروج إلا بحذفه من المتصفح.
- جدول `audit_log` غير مستخدم من المسارات.
- التحليلات ليست أدوات تحقيق.

## 25 مفاتيح الإعداد بدون قيم

لا ملف `.env`.

| المفتاح | المكان |
| --- | --- |
| SECRET_KEY | ثابت في `app.py` |
| UPLOAD_FOLDER | مجلد `uploads` |
| MAX_CONTENT_LENGTH | 16 ميجابايت |
| DB_PATH | `cph.db` |
| AI_MODEL_PATH | `models/cph_model.pkl` |
| CPH_SERVER | `static/js/config.js` |
| cph_api_url | localStorage اختياري |

## 26 التكاملات

- Flask-CORS.
- Pillow للصور.
- scikit-learn عند التدريب.
- لا بريد ولا SMS ولا مزود OSINT خارجي. التوصيات النصية تذكر خطوات (قوائم سوداء، OSINT) كنص ثابت داخل `api_ai_recommendations` ولا تنفّذها.

## 27 المهام المجدولة

غير موجود في الملفات الحالية. لا Procfile.

## 28 تخزين الملفات

`uploads/` للقطات والوسائط. المسار يُحفظ في `chat_screenshot.file_path` أو `media_file.file_path`. النموذج في `models/`.

## 29 التسجيل

لا `logging` قياسي ظاهر في رأس `app.py`. الإشعارات جدول `notification`. `audit_log` مخطط فقط.

## 30 التثبيت من requirements

```
pip install -r requirements.txt
python app.py
```

التدريب الاختياري:

```
python train_model.py
```

افتح الواجهة. إن كانت الصفحة على منفذ غير 5000 أبقِ Flask على 5000 أو عدّل `CPH_SERVER`.

## 31 دليل التطوير

- المسارات كلها في `app.py`.
- غيّر `CPH_SERVER` عند التجربة من جهاز آخر على الشبكة، كما في تعليق `config.js`.
- بعد تدريب النموذج أعد تشغيل Flask حتى يعيد `load_ai_model` القراءة (التحميل كسول عند أول تنبؤ إذا كان المتغير العام فارغاً).
- راجع `dataset/TRAINING_STEPS.md` لتفاصيل العينات.
- لا تعتمد درجات المحاكاة في تقرير رسمي.

## 32 النشر

غير موجود في الملفات الحالية: Procfile أو إعداد Heroku. التشغيل الموثق: `app.run(host='0.0.0.0', port=5000, debug=True)`.

## 33 النسخ الاحتياطي

انسخ `cph.db` و`uploads/` و`models/cph_model.pkl` إن وُجد. حذف القاعدة وحدها يعيد حسابات البذرة عند التشغيل التالي.

## 34 استكشاف الأخطاء

| العرض | السبب في الكود | ما تفعله |
| --- | --- | --- |
| فشل fetch | Flask متوقف أو عنوان خاطئ | شغّل `app.py` وراجع `CPH_SERVER` |
| CORS | صفحة من أصل مختلف | Flask-CORS مفعّل لـ `*` |
| توصيات بلا نموذج | غياب pkl | `python train_model.py` |
| إشعارات فارغة | لم تُستدعَ المحاكاة | أعد تشغيل التطبيق أو `POST /api/init` |
| دخول مرفوض | القاعدة ليست بذرة فارغة وكلمة مختلفة | راجع صف `user` أو احذف `cph.db` لإعادة الزرع |

## 35 الاعتماديات مع الإصدارات من requirements.txt

| الحزمة | الإصدار |
| --- | --- |
| Flask | 3.0.0 |
| Flask-CORS | 4.0.0 |
| werkzeug | 3.0.1 |
| Pillow | 10.1.0 |
| scikit-learn | 1.3.2 |

## 36 القيود

- تحليل الرابط والحساب والصورة والبحث العكسي محاكاة.
- النموذج النصي يصنّف الوصف فقط، وعلى عينات `training_data.json`.
- المصادقة معرف مستخدم مكشوف للمتصفح.
- SHA-256 بلا ملح.
- لا صلاحية صفية كاملة.
- `audit_log` و`linked_case` بلا واجهة إنشاء كاملة.
- وضع التصحيح مفتوح على الشبكة المحلية.

## 37 الحالة الحالية

الخادم يزرع بيانات تجريبية، يقدّم REST، ويحمّل النموذج إن وُجد الملف. الواجهات HTML/JS منفصلة عن عملية Flask ويمكن تقديمها من منفذ آخر. المشروع مناسب للعرض التعليمي.

## 38 قرارات المعمارية

- رمز الدخول = `user_id` لتبسيط الواجهة التعليمية.
- تحليل فوري عند إنشاء البلاغ حتى تظهر بطاقات التحليل بلا خطوة إضافية.
- نموذج اختياري حتى يعمل المشروع بلا scikit-learn وقت التشغيل إذا لم يُستدعَ التدريب. الاستدلال يستورد النموذج المحفوظ عبر pickle، وscikit-learn مطلوب عند التنبؤ أيضاً لأن الكائنات من هذه المكتبة.
- فصل `investigator_id` عن `user_id`.
- CORS مفتوح لأن الواجهة والـ API قد يختلف منفذهما.

## 39 سجل التغييرات

غير موثق كأرقام إصدار للتطبيق. ملف الداتاسيت في README السابق يذكر `version: 1.0` داخل JSON العينات. لا سجل زمني في المستودع داخل هذا الملف.

## System Overview

واجهة عربية ترفع بلاغ ابتزاز أو احتيال إلى Flask، فيُخزَّن في SQLite مع مرفقات. التحليل الظاهر قواعد وتجزئة. صندوق التوصيات يستخدم غابة عشوائية على النص إذا دُرّب النموذج. المحادثة تولّد إشعارات بين الضحية والمحقق المعيّن.

## Quick Reference

| البند | القيمة |
| --- | --- |
| تشغيل | `python app.py` |
| API | `http://127.0.0.1:5000/api` |
| ضحية | victim@cph.gov / 123456 |
| محقق | investigator@cph.gov / 123456 |
| رمز المتصفح | `cph_token` = user_id |
| نموذج | `models/cph_model.pkl` |
| تدريب | `python train_model.py` |

## Quick Start

```
pip install -r requirements.txt
python app.py
python train_model.py
```

شغّل Flask أولاً واتركه يعمل. افتح `index.html` عبر الخادم أو عبر خادم ملفات ثابت. إن تغيّر عنوان الجهاز عدّل `CPH_SERVER`.

## For Non-Technical Users

اختر حساب الضحية لتقديم بلاغ، أو حساب المحقق لمراجعة البلاغات. الدرجات التي تراها على الروابط والحسابات عروض تعليمية داخل البرنامج. احفظ كلمة المرور التجريبية للعرض فقط، ولا تستخدم المنصة كقناة بلاغ رسمي.

## For Developers

المنطق في `app.py`. الواجهة تثق بـ `API_BASE`. فرّق في أي شرح بين `_run_link_analysis` و`predict_with_ai`. جدول `audit_log` مخطط بلا كتابة من المسارات. قبل أي استخدام خارج المعمل استبدل المصادقة وملح كلمات المرور وأوقف `debug`.
