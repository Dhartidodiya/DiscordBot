import os
import joblib
from classify_model.text_processing import clean_text, segment_text

# Relative model path handling
MODEL_DIR = os.path.dirname(__file__)
model = joblib.load(os.path.join(MODEL_DIR, "random_forest_model.pkl"))
vectorizer = joblib.load(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
label_encoder = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))

def classify_message(message: str):
    cleaned = clean_text(message)
    sentences = segment_text(cleaned)
    
    results = []
    for sent in sentences:
        X = vectorizer.transform([sent])
        pred = model.predict(X)
        label = label_encoder.inverse_transform(pred)[0]
        results.append({
            "sentence": sent,
            "category": label
        })
    return results