import os
import joblib
from classify_model.text_processing import clean_text, segment_text

# Relative model path handling
MODEL_DIR = os.path.dirname(__file__)
model = joblib.load(os.path.join(MODEL_DIR, "random_forest_model.pkl"))
vectorizer = joblib.load(os.path.join(MODEL_DIR, "tfidf_vectorizer.pkl"))
label_encoder = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))

def classify_message(message: str, include_title=False):
    cleaned = clean_text(message)
    segments = segment_text(cleaned, return_titles=include_title)

    results = []
    for item in segments:
        sentence = item.get("sentence", "").strip()
        if not sentence:
            continue

        X = vectorizer.transform([sentence])
        pred = model.predict(X)
        predicted_category  = label_encoder.inverse_transform(pred)[0]

        result = {
            "sentence": sentence,
            "category": predicted_category ,
            "status": item.get("status"),
            "label":item.get("label"),
            "emoji":item.get("emoji"),
        }
        
        if include_title:
             result["title"] = item.get("title", None)
        print(result)
        results.append(result)

    return results
