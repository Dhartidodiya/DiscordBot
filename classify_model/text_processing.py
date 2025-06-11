import spacy
import re
import string
from langdetect import detect
import nltk
from nltk.tokenize.punkt import PunktSentenceTokenizer
from nltk.data import load
from transformers import pipeline

# Load once globally (or cache elsewhere for performance)
classifier_en = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
classifier_fr = pipeline("zero-shot-classification", model="morit/french_xlm_xnli")  # or mtheo/camembert-base-xnli

# Ensure punkt is downloaded
nltk.download('punkt', quiet=True)

# Load spaCy models (English + French)
nlp_en = spacy.load("en_core_web_sm")
nlp_fr = spacy.load("fr_core_news_sm")

STATUS_LABELS_EN = ["Completed", "In Progress", "On Hold"]
STATUS_LABELS_FR = ["Terminé", "En cours", "En attente"]

STATUS_EMOJIS = {
    "Completed": "🟢", "In Progress": "🟡", "On Hold": "🔴",
    "Terminé": "🟢", "En cours": "🟡", "En attente": "🔴"
}

KNOWN_TITLES = {
    "Neofid", "Tribuneo", "DiscordBot", "TeintExpress", "Stage", "Conformité RGPD"
}



# Clean message text
def clean_text(text):
    text = str(text)
    text = re.sub(r"[\t\r]+", " ", text)  # keep newlines!
    text = re.sub(r"[>|\\]+", "", text)
    
    pattern = r"\b(?:rapport\s+quotidien\s+)?d[’'`]?\s*(activit[eéèê]|acticit[eéèê])\b\s*:?"
    text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip()


# Normalize markdown asterisks
def normalize_asterisks(text):
    return re.sub(r"(\*{2,})\s*\*{0,2}\s*([\w\s\-]+?)\s*\*{0,2}\s*(\*{2,})", r"**\2**", text)

# Extract titles and sentences
def extract_titles_sentences(text):
    text = str(text).strip()
    lines = text.splitlines()
    results = []
    current_title = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Title detection (based on known projects)
        if line in KNOWN_TITLES:
            current_title = line
            continue

        if current_title is None and len(line.split()) <= 4 and not any(p in line for p in ".!?"):
            current_title = line
            continue

        cleaned = re.sub(r"^[\s\u00A0\u200B\u202F]*[•\-‣◦●▪]?\s*", "", line).strip()
        sentence = cleaned
        results.append((current_title or None, sentence))

    # Fallbacks
    if not results:
        pattern_multi = re.compile(r"\*{1,2}([^*]+?)\*{1,2}\s*-\s*([^*]+)", flags=re.DOTALL)
        matches = pattern_multi.findall(text)
        if matches:
            for title, sentence in matches:
                sentence = re.sub(r"^\s*-\s*", "", sentence)
                results.append((title.strip(), sentence.strip()))
            return results

        fallback_colon = re.match(r"^(projet\s+\w+|\w+)\s*:?-?\s*(.*)", text, flags=re.IGNORECASE)
        if fallback_colon:
            return [(fallback_colon.group(1).strip(), fallback_colon.group(2).strip())]

        return [(None, text.strip())]

    return results




# NLTK tokenizer fallback
def get_tokenizer(lang):
    try:
        return load(f"tokenizers/punkt/{lang}.pickle")
    except LookupError:
        return PunktSentenceTokenizer()
    
    
def get_status_from_model(sentence: str):
    try:
        lang = detect(sentence)
    except:
        lang = "en"  # fallback
    
    if lang == "fr":
        result = classifier_fr(sentence, STATUS_LABELS_FR)
    else:
        result = classifier_en(sentence, STATUS_LABELS_EN)

    top_label = result["labels"][0]
    emoji = STATUS_EMOJIS.get(top_label, "🟢")
    
    return top_label, emoji


def segment_text(text, return_titles=False):
    #  Clean & normalize
    cleaned_text = clean_text(text)
    cleaned_text = normalize_asterisks(cleaned_text)

    #  Break into (title, raw_sentence) pairs
    segments = extract_titles_sentences(cleaned_text)
    output = []

    for title, raw_sentence in segments:
        sentence = raw_sentence.strip()

        label, emoji = get_status_from_model(sentence)

        print(f"✅ Detected status → {label} {emoji}")


        if return_titles:
            output.append({
                "title":    title,
                "sentence": sentence,
                "status":   label.lower(),
                "label":    label,
                "emoji":    emoji
            })
        else:
            output.append(sentence)

    return output


# Manual test
if __name__ == "__main__":
    test = ""
    
    import json
    print(json.dumps(segment_text(test, return_titles=True), indent=2, ensure_ascii=False))