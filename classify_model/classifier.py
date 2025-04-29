import joblib
from classify_model.text_processing import clean_text, segment_text

# Placeholder for global variables
model = None
vectorizer = None
label_encoder = None

def load_model():
    global model, vectorizer, label_encoder
    model = joblib.load("classify_model/random_forest_model.pkl")
    vectorizer = joblib.load("classify_model/tfidf_vectorizer.pkl")
    label_encoder = joblib.load("classify_model/label_encoder.pkl")

def classify_message(text):
    if model is None or vectorizer is None or label_encoder is None:
        raise ValueError("Model not loaded. Call load_model() before using classify_message().")

    cleaned = clean_text(text)
    segments = segment_text(cleaned)
    if not segments:
        return []

    vectors = vectorizer.transform(segments)
    preds = model.predict(vectors)
    categories = label_encoder.inverse_transform(preds)

    return [{"sentence": s, "category": c} for s, c in zip(segments, categories)]

load_model()