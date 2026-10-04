# -*- coding: utf-8 -*-

import json
import os
import pickle
import re

# التحقق من وجود المكتبات
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, classification_report
except ImportError:
    print("يجب تثبيت scikit-learn: pip install scikit-learn")
    exit(1)

DATASET_PATH = os.path.join(os.path.dirname(__file__), 'dataset', 'training_data.json')
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

def clean_arabic_text(text):
    if not text:
        return ""
    text = re.sub(r'[^\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def load_dataset():
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['samples']

def train():
    print("تحميل الداتاسيت...")
    samples = load_dataset()
    
    texts = [clean_arabic_text(s['text']) for s in samples]
    report_types = [s['report_type'] for s in samples]
    threat_levels = [s['threat_level'] for s in samples]
    
    print(f"عدد العينات: {len(texts)}")
    
    # تحويل النص إلى متجهات TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=500,
        ngram_range=(1, 2),
        min_df=1,
        analyzer='char_wb',
        max_df=0.95
    )
    X = vectorizer.fit_transform(texts)
    
    # تدريب مصنف نوع البلاغ
    y_type = report_types
    X_train, X_test, y_train, y_test = train_test_split(X, y_type, test_size=0.2, random_state=42)
    
    clf_type = RandomForestClassifier(n_estimators=100, random_state=42)
    clf_type.fit(X_train, y_train)
    y_pred_type = clf_type.predict(X_test)
    
    print("\n--- تصنيف نوع البلاغ (ابتزاز/احتيال) ---")
    print(f"الدقة: {accuracy_score(y_test, y_pred_type):.2%}")
    print(classification_report(y_test, y_pred_type))
    
    # تدريب مصنف مستوى التهديد
    y_threat = threat_levels
    X_train, X_test, y_train, y_test = train_test_split(X, y_threat, test_size=0.2, random_state=42)
    
    clf_threat = RandomForestClassifier(n_estimators=100, random_state=42)
    clf_threat.fit(X_train, y_train)
    y_pred_threat = clf_threat.predict(X_test)
    
    print("\n--- تصنيف مستوى التهديد ---")
    print(f"الدقة: {accuracy_score(y_test, y_pred_threat):.2%}")
    print(classification_report(y_test, y_pred_threat))
    
    # حفظ النماذج
    model_path = os.path.join(MODEL_DIR, 'cph_model.pkl')
    with open(model_path, 'wb') as f:
        pickle.dump({
            'vectorizer': vectorizer,
            'clf_type': clf_type,
            'clf_threat': clf_threat
        }, f)
    
    print(f"\nتم حفظ النموذج في: {model_path}")
    return True

if __name__ == '__main__':
    train()
