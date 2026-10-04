# -*- coding: utf-8 -*-

import os
import re
import json
import pickle
import sqlite3
import hashlib
import uuid
import base64
from datetime import datetime
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from PIL import Image
import io

AI_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'models', 'cph_model.pkl')
_ai_model = None

def load_ai_model():
    global _ai_model
    if _ai_model is None and os.path.exists(AI_MODEL_PATH):
        try:
            with open(AI_MODEL_PATH, 'rb') as f:
                _ai_model = pickle.load(f)
        except Exception:
            _ai_model = None
    return _ai_model

def predict_with_ai(text):
    model = load_ai_model()
    if not model or not text:
        return None
    try:
        cleaned = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\s]', '', str(text))
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        if not cleaned:
            return None
        X = model['vectorizer'].transform([cleaned])
        report_type = model['clf_type'].predict(X)[0]
        threat_level = model['clf_threat'].predict(X)[0]
        return {'report_type': report_type, 'threat_level': threat_level}
    except Exception:
        return None

app = Flask(__name__, static_folder='static')
CORS(app, origins="*", allow_headers=["Content-Type", "Authorization"])
app.config['SECRET_KEY'] = 'cph-security-key-2025'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_PATH = os.path.join(os.path.dirname(__file__), 'cph.db')

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS user (
        user_id TEXT PRIMARY KEY,
        full_name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        user_type TEXT NOT NULL,
        nationality TEXT,
        national_id TEXT,
        iqama_number TEXT,
        residency_status TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS investigator (
        investigator_id TEXT PRIMARY KEY,
        user_id TEXT UNIQUE,
        badge_number TEXT,
        department TEXT,
        cases_solved INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES user(user_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        action_type TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES user(user_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS report (
        report_id TEXT PRIMARY KEY,
        user_id TEXT,
        investigator_id TEXT,
        report_type TEXT,
        description TEXT,
        status TEXT DEFAULT 'قيد الانتظار',
        priority TEXT DEFAULT 'متوسط',
        financial_amount REAL,
        residency_info TEXT,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        case_stage TEXT,
        FOREIGN KEY (user_id) REFERENCES user(user_id),
        FOREIGN KEY (investigator_id) REFERENCES investigator(investigator_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS suspect_account (
        account_id TEXT PRIMARY KEY,
        report_id TEXT,
        platform_name TEXT,
        username TEXT,
        followers_count INTEGER DEFAULT 0,
        following_count INTEGER DEFAULT 0,
        is_bot INTEGER DEFAULT 0,
        created_at TEXT,
        username_changes TEXT,
        account_classification TEXT,
        FOREIGN KEY (report_id) REFERENCES report(report_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS chat_screenshot (
        screenshot_id TEXT PRIMARY KEY,
        report_id TEXT,
        file_path TEXT,
        extracted_text TEXT,
        FOREIGN KEY (report_id) REFERENCES report(report_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS malicious_link (
        link_id TEXT PRIMARY KEY,
        report_id TEXT,
        link_url TEXT,
        server_country TEXT,
        threat_level TEXT,
        is_blacklisted INTEGER DEFAULT 0,
        vpn_detected INTEGER DEFAULT 0,
        FOREIGN KEY (report_id) REFERENCES report(report_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS media_file (
        media_id TEXT PRIMARY KEY,
        report_id TEXT,
        file_type TEXT,
        file_path TEXT,
        exif_data TEXT,
        deepfake_score REAL,
        FOREIGN KEY (report_id) REFERENCES report(report_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS ai_analysis (
        analysis_id TEXT PRIMARY KEY,
        report_id TEXT,
        analysis_type TEXT,
        result TEXT,
        confidence_score REAL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (report_id) REFERENCES report(report_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS reverse_image_search (
        reverse_id TEXT PRIMARY KEY,
        media_id TEXT,
        potential_matches TEXT,
        match_score REAL,
        FOREIGN KEY (media_id) REFERENCES media_file(media_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS stylometry_profile (
        style_id TEXT PRIMARY KEY,
        report_id TEXT,
        repeated_words TEXT,
        spelling_errors TEXT,
        suspected_dialect TEXT,
        key_phrases TEXT,
        FOREIGN KEY (report_id) REFERENCES report(report_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS linked_case (
        link_case_id TEXT PRIMARY KEY,
        report_id_1 TEXT,
        report_id_2 TEXT,
        same_style INTEGER,
        link_reason TEXT,
        FOREIGN KEY (report_id_1) REFERENCES report(report_id),
        FOREIGN KEY (report_id_2) REFERENCES report(report_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS chat_message (
        message_id TEXT PRIMARY KEY,
        report_id TEXT,
        sender_id TEXT,
        message_text TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        read_status INTEGER DEFAULT 0,
        FOREIGN KEY (report_id) REFERENCES report(report_id),
        FOREIGN KEY (sender_id) REFERENCES user(user_id)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS notification (
        notification_id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        recipient_user_id TEXT NOT NULL,
        sender_user_id TEXT,
        title TEXT NOT NULL,
        body TEXT,
        read_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (report_id) REFERENCES report(report_id),
        FOREIGN KEY (recipient_user_id) REFERENCES user(user_id),
        FOREIGN KEY (sender_user_id) REFERENCES user(user_id)
    )''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def get_chat_notification_recipients(c, report_row, sender_user_id):
    victim_uid = report_row['user_id']
    if sender_user_id == victim_uid:
        inv_id = report_row['investigator_id']
        if inv_id:
            c.execute('SELECT user_id FROM investigator WHERE investigator_id = ?', (inv_id,))
            row = c.fetchone()
            return [row['user_id']] if row else []
        c.execute('SELECT user_id FROM investigator')
        return [r['user_id'] for r in c.fetchall()]
    return [victim_uid] if victim_uid else []

def insert_chat_notifications(c, report_id, sender_user_id, message_text):
    c.execute('SELECT * FROM report WHERE report_id = ?', (report_id,))
    report = c.fetchone()
    if not report:
        return
    report_d = dict(report)
    recipients = get_chat_notification_recipients(c, report_d, sender_user_id)
    if not recipients:
        return
    c.execute('SELECT full_name FROM user WHERE user_id = ?', (sender_user_id,))
    srow = c.fetchone()
    sender_name = srow['full_name'] if srow else 'مستخدم'
    preview = (message_text or '')[:200]
    title = 'رسالة جديدة من ' + sender_name
    for rid in recipients:
        if rid == sender_user_id:
            continue
        nid = str(uuid.uuid4())
        c.execute(
            'INSERT INTO notification (notification_id, report_id, recipient_user_id, sender_user_id, title, body) VALUES (?, ?, ?, ?, ?, ?)',
            (nid, report_id, rid, sender_user_id, title, preview)
        )

def ensure_simulation_notifications():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id FROM user WHERE email = ?', ('victim@cph.gov',))
    vr = c.fetchone()
    c.execute('SELECT user_id FROM user WHERE email = ?', ('investigator@cph.gov',))
    ir = c.fetchone()
    if not vr or not ir:
        conn.close()
        return
    victim_uid = vr['user_id']
    inv_uid = ir['user_id']
    c.execute('SELECT COUNT(*) FROM notification WHERE recipient_user_id = ?', (victim_uid,))
    vcount = c.fetchone()[0]
    c.execute('SELECT COUNT(*) FROM notification WHERE recipient_user_id = ?', (inv_uid,))
    icount = c.fetchone()[0]
    if vcount > 0 and icount > 0:
        conn.close()
        return
    c.execute('SELECT report_id FROM report WHERE user_id = ? ORDER BY submitted_at DESC LIMIT 5', (victim_uid,))
    rids = [row['report_id'] for row in c.fetchall()]
    if not rids:
        conn.close()
        return
    def ins(recip, send, rid, title, body, is_read):
        nid = str(uuid.uuid4())
        if is_read:
            c.execute(
                '''INSERT INTO notification (notification_id, report_id, recipient_user_id, sender_user_id, title, body, read_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)''',
                (nid, rid, recip, send, title, body)
            )
        else:
            c.execute(
                'INSERT INTO notification (notification_id, report_id, recipient_user_id, sender_user_id, title, body) VALUES (?, ?, ?, ?, ?, ?)',
                (nid, rid, recip, send, title, body)
            )
    r0, r1, r2 = rids[0], rids[min(1, len(rids) - 1)], rids[min(2, len(rids) - 1)]
    if vcount == 0:
        ins(victim_uid, inv_uid, r0, 'تم استلام بلاغك', 'تم تسجيل بلاغك في النظام وهو قيد المراجعة من قبل فريق العمل.', False)
        ins(victim_uid, inv_uid, r1, 'تحديث من المحقق', 'جاري تحليل الحساب والروابط المرفقة. يمكنك فتح صفحة التواصل للرد على أي استفسار.', False)
        ins(victim_uid, inv_uid, r2, 'تذكير أمني', 'لا تفتح روابط جديدة من المجهول ولا تُجري تحويلات مالية إضافية حتى تنتهي المتابعة.', True)
    if icount == 0:
        ins(inv_uid, victim_uid, r0, 'بلاغ يحتاج متابعة', 'وصول بلاغ ابتزاز إلكتروني—يرجى مراجعة التفاصيل والتواصل مع المبلغ عند الحاجة.', False)
        ins(inv_uid, victim_uid, r1, 'رسالة من المبلغ', 'المبلغ يطلب متابعة سريعة للحالة بعد آخر التحديثات.', False)
    conn.commit()
    conn.close()

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return jsonify({'error': 'يجب تسجيل الدخول'}), 401
        token = auth.split(' ')[1]
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT user_id FROM user WHERE user_id = ?', (token,))
        user = c.fetchone()
        conn.close()
        if not user:
            return jsonify({'error': 'جلسة منتهية'}), 401
        return f(token, *args, **kwargs)
    return decorated

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/init', methods=['POST'])
def api_init():
    init_db()
    ensure_simulation_notifications()
    return jsonify({'status': 'تم تهيئة قاعدة البيانات'})

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    user_id = str(uuid.uuid4())
    password_hash = hash_password(data['password'])
    
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO user (user_id, full_name, email, password_hash, user_type, nationality, national_id, iqama_number, residency_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (user_id, data['full_name'], data['email'], password_hash, data['user_type'],
             data.get('nationality'), data.get('national_id'), data.get('iqama_number'), data.get('residency_status')))
        
        if data['user_type'] == 'investigator':
            inv_id = str(uuid.uuid4())
            c.execute('INSERT INTO investigator (investigator_id, user_id, badge_number, department) VALUES (?, ?, ?, ?)',
                (inv_id, user_id, data.get('badge_number', ''), data.get('department', '')))
        
        conn.commit()
        conn.close()
        return jsonify({'user_id': user_id, 'message': 'تم التسجيل بنجاح'})
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({'error': 'البريد الإلكتروني مُسجّل مسبقاً'}), 400

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    password_hash = hash_password(data['password'])
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_id, full_name, email, user_type FROM user WHERE email = ? AND password_hash = ?',
        (data['email'], password_hash))
    user = c.fetchone()
    conn.close()
    
    if user:
        return jsonify({
            'user_id': user['user_id'],
            'full_name': user['full_name'],
            'user_type': user['user_type'],
            'message': 'تم تسجيل الدخول بنجاح'
        })
    return jsonify({'error': 'بريد أو كلمة مرور غير صحيحة'}), 401

@app.route('/api/reports', methods=['GET'])
@require_auth
def api_get_reports(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_type FROM user WHERE user_id = ?', (user_id,))
    u = c.fetchone()
    user_type = u['user_type'] if u else 'victim'
    
    filter_status = request.args.get('filter', 'all')
    
    if user_type == 'victim':
        c.execute('''SELECT r.*, i.full_name as investigator_name FROM report r
            LEFT JOIN user i ON r.investigator_id = (SELECT investigator_id FROM investigator WHERE user_id = i.user_id)
            WHERE r.user_id = ? ORDER BY r.submitted_at DESC''', (user_id,))
    else:
        c.execute('''SELECT r.*, u.full_name as victim_name FROM report r
            LEFT JOIN user u ON r.user_id = u.user_id
            ORDER BY r.submitted_at DESC''')
    
    rows = c.fetchall()
    conn.close()
    
    reports = []
    for r in rows:
        rep = dict(r)
        rep['submitted_at'] = rep['submitted_at'][:19] if rep.get('submitted_at') else ''
        if filter_status == 'new' and rep['status'] != 'قيد الانتظار':
            continue
        if filter_status == 'investigating' and rep['status'] != 'تحت التحقيق':
            continue
        if filter_status == 'solved' and rep['status'] != 'منتهي':
            continue
        reports.append(rep)
    
    return jsonify(reports)

def _run_link_analysis(conn, link_id, report_id, url):
    analysis = {'server_country': 'غير معروف', 'vpn_proxy': False, 'blacklisted': False, 'threat_level': 'منخفض'}
    if 'instagram' in url.lower():
        analysis['server_country'] = 'الولايات المتحدة'
        analysis['vpn_proxy'] = (hash(url) % 5) == 0
        analysis['blacklisted'] = (hash(url) % 10) == 0
    elif 't.me' in url or 'telegram' in url.lower():
        analysis['server_country'] = 'ألمانيا'
        analysis['vpn_proxy'] = True
        analysis['threat_level'] = 'عالي'
    if analysis['vpn_proxy'] or analysis['blacklisted']:
        analysis['threat_level'] = 'عالي'
    c = conn.cursor()
    c.execute('UPDATE malicious_link SET server_country=?, threat_level=?, is_blacklisted=?, vpn_detected=? WHERE link_id=?',
        (analysis['server_country'], analysis['threat_level'], 1 if analysis['blacklisted'] else 0, 1 if analysis['vpn_proxy'] else 0, link_id))
    c.execute('INSERT INTO ai_analysis (analysis_id, report_id, analysis_type, result, confidence_score) VALUES (?, ?, ?, ?, ?)',
        (str(uuid.uuid4()), report_id, 'Link', json.dumps(analysis, ensure_ascii=False), 0.85))

def _run_account_analysis(conn, acc_id, report_id, username, platform):
    h = abs(hash(username)) % 100
    is_bot = h < 25
    followers = 100 + (h * 50) % 5000
    classification = 'وهمي' if is_bot else ('مسروق' if h < 40 else 'حقيقي')
    c = conn.cursor()
    c.execute('UPDATE suspect_account SET followers_count=?, is_bot=?, account_classification=? WHERE account_id=?',
        (followers, 1 if is_bot else 0, classification, acc_id))
    c.execute('INSERT INTO ai_analysis (analysis_id, report_id, analysis_type, result, confidence_score) VALUES (?, ?, ?, ?, ?)',
        (str(uuid.uuid4()), report_id, 'Account', json.dumps({'classification': classification, 'followers': followers, 'is_bot': is_bot}, ensure_ascii=False), 0.82))

@app.route('/api/reports', methods=['POST'])
@require_auth
def api_create_report(user_id):
    data = request.form
    report_id = str(uuid.uuid4())
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO report (report_id, user_id, report_type, description, status, financial_amount, residency_info)
        VALUES (?, ?, ?, ?, 'قيد الانتظار', ?, ?)''',
        (report_id, user_id, data.get('report_type', 'ابتزاز'), data.get('description', ''),
         float(data.get('financial_amount', 0) or 0), data.get('residency_info', '')))
    
    links_data = json.loads(data.get('links', '[]'))
    for link in links_data:
        link_id = str(uuid.uuid4())
        url = link.get('url', '')
        c.execute('''INSERT INTO malicious_link (link_id, report_id, link_url)
            VALUES (?, ?, ?)''', (link_id, report_id, url))
        _run_link_analysis(conn, link_id, report_id, url)
    
    accounts_data = json.loads(data.get('accounts', '[]'))
    for acc in accounts_data:
        acc_id = str(uuid.uuid4())
        username = acc.get('username', '')
        platform = acc.get('platform', 'إنستقرام')
        c.execute('''INSERT INTO suspect_account (account_id, report_id, platform_name, username)
            VALUES (?, ?, ?, ?)''', (acc_id, report_id, platform, username))
        _run_account_analysis(conn, acc_id, report_id, username, platform)

    c.execute('SELECT full_name FROM user WHERE user_id = ?', (user_id,))
    vrow = c.fetchone()
    victim_name = vrow['full_name'] if vrow else 'مبلّغ'
    preview = (data.get('description') or '')[:200]
    title = 'بلاغ جديد من ' + victim_name
    body = preview or ('نوع: ' + (data.get('report_type') or 'بلاغ'))
    c.execute('SELECT user_id FROM investigator')
    for inv_row in c.fetchall():
        i_uid = inv_row['user_id']
        if i_uid == user_id:
            continue
        nid = str(uuid.uuid4())
        c.execute(
            'INSERT INTO notification (notification_id, report_id, recipient_user_id, sender_user_id, title, body) VALUES (?, ?, ?, ?, ?, ?)',
            (nid, report_id, i_uid, user_id, title, body)
        )

    conn.commit()
    conn.close()
    
    if 'screenshots' in request.files:
        for f in request.files.getlist('screenshots'):
            if f.filename:
                fn = secure_filename(f"{uuid.uuid4()}_{f.filename}")
                fp = os.path.join(app.config['UPLOAD_FOLDER'], fn)
                f.save(fp)
                sid = str(uuid.uuid4())
                conn = get_db()
                c = conn.cursor()
                c.execute('INSERT INTO chat_screenshot (screenshot_id, report_id, file_path) VALUES (?, ?, ?)',
                    (sid, report_id, f"uploads/{fn}"))
                conn.commit()
                conn.close()
    
    if 'media' in request.files:
        for f in request.files.getlist('media'):
            if f.filename:
                fn = secure_filename(f"{uuid.uuid4()}_{f.filename}")
                fp = os.path.join(app.config['UPLOAD_FOLDER'], fn)
                f.save(fp)
                mid = str(uuid.uuid4())
                exif_data = ''
                deepfake_score = None
                try:
                    img = Image.open(fp)
                    if hasattr(img, '_getexif') and img._getexif():
                        exif_data = str(img._getexif())
                    deepfake_score = 0.15 + (hash(fn) % 30) / 100
                except:
                    pass
                conn = get_db()
                c = conn.cursor()
                c.execute('INSERT INTO media_file (media_id, report_id, file_type, file_path, exif_data, deepfake_score) VALUES (?, ?, ?, ?, ?, ?)',
                    (mid, report_id, 'صورة', f"uploads/{fn}", exif_data, deepfake_score))
                conn.commit()
                conn.close()
    
    return jsonify({'report_id': report_id, 'message': 'تم تقديم البلاغ بنجاح'})

@app.route('/api/reports/<report_id>', methods=['GET'])
@require_auth
def api_get_report(user_id, report_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM report WHERE report_id = ?', (report_id,))
    r = c.fetchone()
    if not r:
        conn.close()
        return jsonify({'error': 'البلاغ غير موجود'}), 404
    
    report = dict(r)
    c.execute('SELECT user_type FROM user WHERE user_id = ?', (user_id,))
    ut = c.fetchone()
    user_type = ut['user_type'] if ut else 'victim'
    if user_type == 'victim' and report.get('user_id') != user_id:
        conn.close()
        return jsonify({'error': 'غير مصرح بعرض هذا البلاغ'}), 403
    
    c.execute('SELECT * FROM suspect_account WHERE report_id = ?', (report_id,))
    report['accounts'] = [dict(x) for x in c.fetchall()]
    
    c.execute('SELECT * FROM chat_screenshot WHERE report_id = ?', (report_id,))
    report['screenshots'] = [dict(x) for x in c.fetchall()]
    
    c.execute('SELECT * FROM malicious_link WHERE report_id = ?', (report_id,))
    report['links'] = [dict(x) for x in c.fetchall()]
    
    c.execute('SELECT * FROM media_file WHERE report_id = ?', (report_id,))
    report['media'] = [dict(x) for x in c.fetchall()]
    
    c.execute('SELECT * FROM ai_analysis WHERE report_id = ?', (report_id,))
    report['ai_analyses'] = [dict(x) for x in c.fetchall()]
    
    c.execute('SELECT * FROM stylometry_profile WHERE report_id = ?', (report_id,))
    report['stylometry'] = [dict(x) for x in c.fetchall()]
    
    c.execute('SELECT * FROM linked_case WHERE report_id_1 = ? OR report_id_2 = ?', (report_id, report_id))
    report['linked_cases'] = [dict(x) for x in c.fetchall()]
    
    conn.close()
    return jsonify(report)

@app.route('/api/reports/<report_id>', methods=['PUT'])
@require_auth
def api_update_report(user_id, report_id):
    data = request.json
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT user_type FROM user WHERE user_id = ?', (user_id,))
    ut = c.fetchone()
    if not ut or ut['user_type'] != 'investigator':
        conn.close()
        return jsonify({'error': 'تحديث البلاغ متاح للمحققين فقط'}), 403

    c.execute('SELECT * FROM report WHERE report_id = ?', (report_id,))
    prev = c.fetchone()
    if not prev:
        conn.close()
        return jsonify({'error': 'البلاغ غير موجود'}), 404
    prev_row = dict(prev)
    old_status = prev_row.get('status')

    updates = []
    params = []
    if 'status' in data:
        updates.append('status = ?')
        params.append(data['status'])
    if 'investigator_id' in data:
        updates.append('investigator_id = ?')
        params.append(data['investigator_id'] if data['investigator_id'] else None)
    if 'notes' in data:
        updates.append('notes = ?')
        params.append(data['notes'])
    if 'case_stage' in data:
        updates.append('case_stage = ?')
        params.append(data['case_stage'])
    if 'priority' in data:
        updates.append('priority = ?')
        params.append(data['priority'])
    
    if not updates:
        conn.close()
        return jsonify({'error': 'لا يوجد تحديث'}), 400
    
    params.append(report_id)
    c.execute(f"UPDATE report SET {', '.join(updates)} WHERE report_id = ?", params)

    victim_uid = prev_row.get('user_id')
    if 'status' in data and victim_uid and data['status'] != old_status:
        nid = str(uuid.uuid4())
        c.execute(
            '''INSERT INTO notification (notification_id, report_id, recipient_user_id, sender_user_id, title, body)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (nid, report_id, victim_uid, user_id, 'تحديث حالة البلاغ',
             f'تم تغيير حالة بلاغك إلى: {data["status"]}')
        )

    conn.commit()
    conn.close()
    return jsonify({'message': 'تم التحديث'})

@app.route('/api/analyze/link', methods=['POST'])
@require_auth
def api_analyze_link(user_id):
    data = request.json
    url = data.get('url', '')
    report_id = data.get('report_id')
    
    analysis = {
        'server_country': 'غير معروف',
        'vpn_proxy': False,
        'blacklisted': False,
        'threat_level': 'منخفض'
    }
    
    if 'instagram' in url.lower():
        analysis['server_country'] = 'الولايات المتحدة'
        analysis['vpn_proxy'] = (hash(url) % 5) == 0
        analysis['blacklisted'] = (hash(url) % 10) == 0
    elif 't.me' in url or 'telegram' in url.lower():
        analysis['server_country'] = 'ألمانيا'
        analysis['vpn_proxy'] = True
        analysis['threat_level'] = 'عالي'
    elif 'whatsapp' in url.lower():
        analysis['server_country'] = 'الولايات المتحدة'
    
    if analysis['vpn_proxy'] or analysis['blacklisted']:
        analysis['threat_level'] = 'عالي'
    
    if report_id:
        conn = get_db()
        c = conn.cursor()
        link_id = str(uuid.uuid4())
        c.execute('''INSERT INTO malicious_link (link_id, report_id, link_url, server_country, threat_level, is_blacklisted, vpn_detected)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (link_id, report_id, url, analysis['server_country'], analysis['threat_level'],
             1 if analysis['blacklisted'] else 0, 1 if analysis['vpn_proxy'] else 0))
        aid = str(uuid.uuid4())
        c.execute('''INSERT INTO ai_analysis (analysis_id, report_id, analysis_type, result, confidence_score)
            VALUES (?, ?, 'Link', ?, 0.85)''', (aid, report_id, json.dumps(analysis, ensure_ascii=False)))
        conn.commit()
        conn.close()
    
    return jsonify(analysis)

@app.route('/api/analyze/account', methods=['POST'])
@require_auth
def api_analyze_account(user_id):
    data = request.json
    username = data.get('username', '')
    platform = data.get('platform', 'إنستقرام')
    report_id = data.get('report_id')
    
    h = abs(hash(username)) % 100
    is_bot = h < 25
    followers = 100 + (h * 50) % 5000
    created_approx = f"202{2 + h % 4}-0{(h % 9) + 1}-0{(h % 28) + 1}"
    classification = 'وهمي' if is_bot else ('مسروق' if h < 40 else 'حقيقي')
    
    result = {
        'created_approx': created_approx,
        'username_changes': 'محاكاة: تغيير واحد سابق' if h % 3 == 0 else 'لا يوجد',
        'followers': followers,
        'is_bot': is_bot,
        'classification': classification
    }
    
    if report_id:
        conn = get_db()
        c = conn.cursor()
        acc_id = str(uuid.uuid4())
        c.execute('''INSERT INTO suspect_account (account_id, report_id, platform_name, username, followers_count, is_bot, account_classification)
            VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (acc_id, report_id, platform, username, followers, 1 if is_bot else 0, classification))
        aid = str(uuid.uuid4())
        c.execute('''INSERT INTO ai_analysis (analysis_id, report_id, analysis_type, result, confidence_score)
            VALUES (?, ?, 'Account', ?, 0.82)''', (aid, report_id, json.dumps(result, ensure_ascii=False)))
        conn.commit()
        conn.close()
    
    return jsonify(result)

@app.route('/api/analyze/image', methods=['POST'])
@require_auth
def api_analyze_image(user_id):
    data = request.json
    if 'image' in data:
        try:
            img_data = base64.b64decode(data['image'].split(',')[1])
            img = Image.open(io.BytesIO(img_data))
            w, h = img.size
        except:
            w, h = 0, 0
    else:
        w, h = 0, 0
    
    deepfake_score = 0.12 + ((hash(str(w)+str(h)) % 40) / 100)
    exif_found = (hash(str(w)) % 3) == 0
    
    return jsonify({
        'deepfake_probability': round(deepfake_score * 100, 1),
        'exif_found': exif_found,
        'exif_summary': 'بيانات EXIF موجودة - تم استخراجها' if exif_found else 'لا توجد بيانات EXIF',
        'explanation': 'تحليل احتمالي بناءً على خصائص الصورة'
    })

@app.route('/api/analyze/stylometry', methods=['POST'])
@require_auth
def api_analyze_stylometry(user_id):
    data = request.json
    text = data.get('text', '')
    report_id = data.get('report_id')
    
    words = text.split()
    repeated = list(set([w for w in words if words.count(w) > 1]))[:5]
    dialect = 'خليجي' if any(x in text for x in ['يا', 'وايد', 'شوي']) else 'مصري' if any(x in text for x in ['بصراحة', 'يعني']) else 'فصحى'
    
    result = {
        'repeated_words': repeated[:5],
        'spelling_errors': ['محاكاة أخطاء شائعة'],
        'dialect': dialect,
        'key_phrases': ['ابتزاز', 'فلوس', 'توصيل'] if len(text) > 10 else []
    }
    
    if report_id:
        conn = get_db()
        c = conn.cursor()
        sid = str(uuid.uuid4())
        c.execute('''INSERT INTO stylometry_profile (style_id, report_id, repeated_words, spelling_errors, suspected_dialect, key_phrases)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (sid, report_id, json.dumps(repeated), json.dumps(result['spelling_errors']),
             dialect, json.dumps(result['key_phrases'])))
        conn.commit()
        conn.close()
    
    return jsonify(result)

@app.route('/api/reverse-image', methods=['POST'])
@require_auth
def api_reverse_image(user_id):
    data = request.json
    platforms = ['إنستقرام', 'تويتر', 'فيسبوك', 'لينكد إن', 'تيليجرام']
    match = 0.65 + (hash(str(data.get('image', ''))[:10]) % 25) / 100
    return jsonify({
        'potential_matches': platforms[:2],
        'match_score': round(match * 100, 1),
        'explanation': 'محاكاة نتائج البحث العكسي - احتمالية التطابق مع منصات أخرى'
    })

@app.route('/api/chat/<report_id>', methods=['GET'])
@require_auth
def api_get_chat(user_id, report_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT m.*, u.full_name FROM chat_message m
        LEFT JOIN user u ON m.sender_id = u.user_id
        WHERE m.report_id = ? ORDER BY m.sent_at''', (report_id,))
    rows = c.fetchall()
    conn.close()
    messages = [dict(r) for r in rows]
    return jsonify(messages)

@app.route('/api/chat/<report_id>', methods=['POST'])
@require_auth
def api_send_message(user_id, report_id):
    data = request.json
    msg_text = data.get('message', '')
    msg_id = str(uuid.uuid4())
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT INTO chat_message (message_id, report_id, sender_id, message_text) VALUES (?, ?, ?, ?)',
        (msg_id, report_id, user_id, msg_text))
    insert_chat_notifications(c, report_id, user_id, msg_text)
    conn.commit()
    conn.close()
    return jsonify({'message_id': msg_id, 'message': 'تم الإرسال'})

@app.route('/api/notifications', methods=['GET'])
@require_auth
def api_get_notifications(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        '''SELECT n.notification_id, n.report_id, n.recipient_user_id, n.sender_user_id, n.title, n.body,
        n.read_at, n.created_at, u.full_name AS sender_name
        FROM notification n LEFT JOIN user u ON n.sender_user_id = u.user_id
        WHERE n.recipient_user_id = ? ORDER BY n.created_at DESC LIMIT 80''',
        (user_id,)
    )
    rows = c.fetchall()
    c.execute('SELECT COUNT(*) FROM notification WHERE recipient_user_id = ? AND read_at IS NULL', (user_id,))
    unread = c.fetchone()[0]
    conn.close()
    items = []
    for r in rows:
        d = dict(r)
        if d.get('created_at'):
            d['created_at'] = str(d['created_at'])[:19]
        if d.get('read_at'):
            d['read_at'] = str(d['read_at'])[:19]
        items.append(d)
    return jsonify({'notifications': items, 'unread_count': unread})

@app.route('/api/notifications/read-all', methods=['POST'])
@require_auth
def api_notifications_read_all(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE notification SET read_at = CURRENT_TIMESTAMP WHERE recipient_user_id = ? AND read_at IS NULL', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/notifications/<notification_id>/read', methods=['POST'])
@require_auth
def api_notification_read(user_id, notification_id):
    conn = get_db()
    c = conn.cursor()
    c.execute(
        'UPDATE notification SET read_at = CURRENT_TIMESTAMP WHERE notification_id = ? AND recipient_user_id = ?',
        (notification_id, user_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/api/ai-status', methods=['GET'])
def api_ai_status():
    loaded = load_ai_model() is not None
    return jsonify({
        'model_loaded': loaded,
        'model_path': AI_MODEL_PATH,
        'message': 'النموذج المدرب جاهز' if loaded else 'قم بتشغيل python train_model.py لتدريب النموذج'
    })

@app.route('/api/investigators', methods=['GET'])
@require_auth
def api_get_investigators(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT i.investigator_id, i.badge_number, i.department, u.full_name
        FROM investigator i JOIN user u ON i.user_id = u.user_id''')
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/ai-recommendations/<report_id>', methods=['GET'])
@require_auth
def api_ai_recommendations(user_id, report_id):
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT * FROM report WHERE report_id = ?', (report_id,))
    r = c.fetchone()
    if not r:
        conn.close()
        return jsonify({'error': 'البلاغ غير موجود'}), 404
    report = dict(r)
    c.execute('SELECT * FROM malicious_link WHERE report_id = ?', (report_id,))
    links = [dict(x) for x in c.fetchall()]
    c.execute('SELECT * FROM suspect_account WHERE report_id = ?', (report_id,))
    accounts = [dict(x) for x in c.fetchall()]
    c.execute('SELECT * FROM ai_analysis WHERE report_id = ?', (report_id,))
    analyses = [dict(x) for x in c.fetchall()]
    conn.close()
    desc = report.get('description', '')
    pred = predict_with_ai(desc)
    if pred:
        threat = pred['threat_level']
        predicted_type = pred['report_type']
        model_used = True
    else:
        threat = 'عالي' if report.get('report_type') == 'ابتزاز' or (report.get('financial_amount') or 0) > 10000 else 'متوسط'
        predicted_type = report.get('report_type')
        model_used = False
    recommendations = {
        'threat_level': threat,
        'predicted_type': predicted_type,
        'model_used': model_used,
        'summary': f'تحليل تلقائي: البلاغ من نوع {predicted_type} بقيمة {report.get("financial_amount") or 0} ريال. النموذج المدرب يوصي بمعالجة أولوية.' if model_used else f'تحليل قاعدي: البلاغ من نوع {report.get("report_type")} بقيمة {report.get("financial_amount") or 0} ريال. قم بتدريب النموذج (python train_model.py) لتفعيل التحليل الذكي.',
        'recommendations': [
            'فحص الروابط المرفقة ضد القوائم السوداء العالمية',
            'تحليل أسلوب الكتابة وربطه مع بلاغات سابقة',
            'البحث العكسي عن صورة البروفايل عبر منصات OSINT',
            'استخراج بيانات EXIF من الصور المرفقة',
            'فحص تاريخ إنشاء الحساب وتغييرات اليوزر'
        ],
        'confidence': 0.89
    }
    return jsonify(recommendations)

def seed_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM user')
    if c.fetchone()[0] > 0:
        conn.close()
        return
    victim_id = str(uuid.uuid4())
    inv_user_id = str(uuid.uuid4())
    inv_id = str(uuid.uuid4())
    c.execute('''INSERT INTO user (user_id, full_name, email, password_hash, user_type, nationality, residency_status, national_id)
        VALUES (?, ?, ?, ?, 'victim', 'سعودي', 'سعودي', '1234567890')''',
        (victim_id, 'أحمد محمد العلي', 'victim@cph.gov', hash_password('123456')))
    c.execute('''INSERT INTO user (user_id, full_name, email, password_hash, user_type, nationality, residency_status)
        VALUES (?, ?, ?, ?, 'investigator', 'سعودي', 'سعودي')''',
        (inv_user_id, 'المحقق خالد السعيد', 'investigator@cph.gov', hash_password('123456')))
    c.execute('INSERT INTO investigator (investigator_id, user_id, badge_number, department, cases_solved) VALUES (?, ?, ?, ?, ?)',
        (inv_id, inv_user_id, 'INV-1001', 'مكافحة الجرائم المعلوماتية', 12))
    for i in range(5):
        rid = str(uuid.uuid4())
        types = ['ابتزاز', 'احتيال', 'ابتزاز', 'احتيال', 'ابتزاز']
        statuses = ['قيد الانتظار', 'تحت التحقيق', 'تحت التحقيق', 'منتهي', 'قيد الانتظار']
        priorities = ['عالي', 'متوسط', 'منخفض', 'متوسط', 'عالي']
        amounts = [5000, 15000, 800, 22000, 3500]
        c.execute('''INSERT INTO report (report_id, user_id, investigator_id, report_type, description, status, priority, financial_amount, residency_info, notes, case_stage)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (rid, victim_id, inv_id if i in [1,2,3] else None, types[i],
             [
                 'تعرضت لابتزاز عبر إنستقرام. شخص مجهول أضافني وبدأ يرسل رسائل تهديد. يطلب 5000 ريال وإلا سينشر صوراً شخصية ادعى أنها لي (وهمية). أرسل لي رابطاً لتطبيق واتساب مزيف. أريد الإبلاغ فوراً.',
                 'شخص على سناب شات هددني بنشر محادثات قديمة مع صديقة. طلب 15000 ريال بالتحويل. أرسل لقطة شاشة لمحادثة معدّلة. الحساب اسمه @blackmail_snap ظهر قبل أسبوع فقط. أرجو المتابعة العاجلة.',
                 'وقع victim على عرض استثمار إلكتروني عبر تيليجرام. وعدوا بعوائد 50% شهرياً. دفعت 800 ريال ثم اختفى الحساب. الرابط كان bit.ly مشبوه. أريد استرداد المبلغ وملاحقة المحتالين.',
                 'تعاملت مع متجر إلكتروني وهمي على إنستقرام يبيع إلكترونيات بأسعار منخفضة. طلبوا الدفع مسبقاً. بعد تحويل 22000 ريال أوقفوا التواصل. الحساب @tech_deals_ksa لديه 15 ألف متابع لكن يبدو أن معظمهم بوتات.',
                 'شخص يدعي أنه قرصان اخترق جوالاتي وحصل على صور. يطلب 3500 ريال. أرسل فيديو قصير ادعى أنه من كاميرا غرفتي لكن يبدو مفبركاً (ديب فيك). الحساب على تيليجرام بدون صورة بروفايل.',
             ][i], statuses[i], priorities[i], amounts[i], 'سعودي',
             (None, 'تم تعيين المحقق. جاري تحليل الحساب والروابط.', 'التحقق من الرابط ومسار التحويل.', 'تم ربط القضية ببلاغات مشابهة. الملف مرفوع للنيابة.', None)[min(i,4)],
             (None, 'التحقق من مصدر التهديد', 'تتبع الحساب البنكي', 'مغلق - محالة للجهات المختصة', None)[min(i,4)]))
        acc_id = str(uuid.uuid4())
        platforms = ['إنستقرام', 'سناب شات', 'تيليجرام', 'إنستقرام', 'تيليجرام']
        usernames = ['blackmail_fake', 'blackmail_snap', 'invest_scam_tg', 'tech_deals_ksa', 'anonymous_tg']
        c.execute('''INSERT INTO suspect_account (account_id, report_id, platform_name, username, followers_count, is_bot, account_classification)
            VALUES (?, ?, ?, ?, ?, ?, ?)''', (acc_id, rid, platforms[i], usernames[i], 500 + i*200, 1 if i % 2 == 0 else 0, 'وهمي' if i % 2 == 0 else 'حقيقي'))
        link_id = str(uuid.uuid4())
        c.execute('''INSERT INTO malicious_link (link_id, report_id, link_url, server_country, threat_level, is_blacklisted, vpn_detected)
            VALUES (?, ?, ?, ?, ?, ?, ?)''', (link_id, rid, f'https://instagram.com/fake_{i}', 'الولايات المتحدة', 'عالي' if i < 2 else 'متوسط', 1 if i == 0 else 0, 1 if i == 1 else 0))
        c.execute('''INSERT INTO ai_analysis (analysis_id, report_id, analysis_type, result, confidence_score)
            VALUES (?, ?, ?, ?, ?)''', (str(uuid.uuid4()), rid, 'Link', json.dumps({'server_country': 'الولايات المتحدة', 'vpn_proxy': i==1, 'blacklisted': i==0, 'threat_level': 'عالي' if i<2 else 'متوسط'}, ensure_ascii=False), 0.85))
        c.execute('''INSERT INTO ai_analysis (analysis_id, report_id, analysis_type, result, confidence_score)
            VALUES (?, ?, ?, ?, ?)''', (str(uuid.uuid4()), rid, 'Account', json.dumps({'classification': 'وهمي' if i%2==0 else 'حقيقي', 'followers': 500+i*200, 'is_bot': i%2==0}, ensure_ascii=False), 0.82))
        c.execute('''INSERT INTO stylometry_profile (style_id, report_id, repeated_words, spelling_errors, suspected_dialect, key_phrases)
            VALUES (?, ?, ?, ?, ?, ?)''', (str(uuid.uuid4()), rid, '["فلوس","ابعت","تحويل","عاجل"]', '["فلوس","مبالغ"]', 'خليجي', '["ابتزاز","تحويل","تهديد"]'))
        if i == 0:
            c.execute('INSERT INTO chat_message (message_id, report_id, sender_id, message_text) VALUES (?, ?, ?, ?)',
                (str(uuid.uuid4()), rid, victim_id, 'تم تقديم البلاغ. متى سيتم الرد عليه؟'))
        elif i in [1, 2]:
            chat_msgs = [
                (victim_id, 'السلام عليكم، أنا المبلغ عن البلاغ. هل تم استلام المرفقات التي أرسلتها؟'),
                (inv_user_id, 'وعليكم السلام. نعم تم استلامها. فريق التحليل يعمل على فحص الحساب والرابط. سنعود لكم خلال 24-48 ساعة.'),
                (victim_id, 'شكراً. الرابط اللي أرسلوه كان يفتح تطبيق واتساب مزيف يطلب صلاحيات كاملة. أحتمال يريدون الوصول لجهازي.'),
                (inv_user_id, 'تم تسجيل الملاحظة. هذا سلوك شائع في ابتزاز الفئة هذه. احذر من فتح أي روابط إضافية ولاتحول أي مبلغ.'),
            ] if i == 1 else [
                (victim_id, 'تحية، أريد متابعة بلاغ الاحتيال. هل تم تتبع الحساب البنكي للتحويل؟'),
                (inv_user_id, 'نعم. التحويل ذهب لحساب وهمي تم إغلاقه. نعمل على ربطه بحسابات أخرى من بلاغات مشابهة.'),
                (victim_id, 'لو حصل أي تطور يرجى إعلامي فوراً. المبلغ ليس كبيراً لكن المهم القبض عليهم.'),
                (inv_user_id, 'حاضر. سنتواصل معك فور وجود أي تحديث.'),
            ]
            for sender_id, msg in chat_msgs:
                c.execute('INSERT INTO chat_message (message_id, report_id, sender_id, message_text) VALUES (?, ?, ?, ?)',
                    (str(uuid.uuid4()), rid, sender_id, msg))
        elif i == 3:
            c.execute('INSERT INTO chat_message (message_id, report_id, sender_id, message_text) VALUES (?, ?, ?, ?)',
                (str(uuid.uuid4()), rid, inv_user_id, 'تم إحالة الملف للنيابة. سنخبركم بأي تطورات.'))
    c.execute('SELECT report_id FROM report ORDER BY submitted_at LIMIT 2')
    rows = c.fetchall()
    if len(rows) >= 2:
        c.execute('INSERT INTO linked_case (link_case_id, report_id_1, report_id_2, same_style, link_reason) VALUES (?, ?, ?, 1, ?)',
            (str(uuid.uuid4()), rows[0][0], rows[1][0], 'أسلوب كتابة متشابه'))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    seed_db()
    ensure_simulation_notifications()
    # 0.0.0.0 يسمح بالوصول من أجهزة أخرى على الشبكة (لابتوب الضحية + لابتوب المحقق). 127.0.0.1 يقبل الجهاز المضيف فقط.
    app.run(host='0.0.0.0', port=5000, debug=True)
