import spacy
import re
import string
from langdetect import detect
import nltk
from nltk.tokenize.punkt import PunktSentenceTokenizer
from nltk.data import load
from model.task_model import TaskModel  
task_model = TaskModel()

# Ensure punkt is downloaded
nltk.download('punkt', quiet=True)

# Load spaCy models (English + French)
nlp_en = spacy.load("en_core_web_sm")
nlp_fr = spacy.load("fr_core_news_sm")

# Clean message text
def clean_text(text):
    text = str(text)
    text = re.sub(r"[\t\r]+", " ", text)  # keep newlines!
    text = re.sub(r"[>|\\]+", "", text)
    
    pattern = r"\b(?:rapport\s+quotidien\s+)?d[’'`]?\s*(activit[eéèê]|acticit[eéèê])\b\s*:?"
    text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip().lower()


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

        if len(line.split()) <= 4 and not any(p in line for p in ".!?"):
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

# Full segmenter with spaCy + fallback logic
def segment_text(text, return_titles=False):
    
    cleaned_text = clean_text(text)
    
    cleaned_text = normalize_asterisks(cleaned_text)
    
    segments = extract_titles_sentences(cleaned_text)
   
    output = []
    
    #  Known status keywords
    status_keywords = {
    # Completed
    "done", "completed", "finished", "complete",
    "terminé", "terminée", "termine", "terminer", "fin", "fini", "fait", "succès", "réalisé", "realisé", "clôturé", "cloturé", "clôture", "cloture",

    #  In Progress
    "in progress", "doing", "working", "active", "wip", "processing",
    "en cours", "cours", "en traitement", "traitement", "en marche", "en train de faire", "traiter",

    #  On Hold
    "on hold", "paused", "waiting", "hold", "pending", "standby",
    "en attente", "attente", "bloqué", "bloque", "bloquée", "bloques", "suspendu", "interrompu", "gelé", "gelée"
}

    # Process each segment
    for title, raw_sentence in segments:
        sentence = raw_sentence.strip()
        raw_status = "in progress"

        status_match = re.search(r"\s*[-:]\s*([^\n\r]+)$", sentence)
         
        if status_match:
            possible_status = status_match.group(1).strip().lower().strip(string.punctuation)
            if possible_status in status_keywords:
                raw_status = possible_status
                sentence = re.sub(r"\s*[-:]\s*" + re.escape(status_match.group(1)) + r"$", "", sentence, flags=re.UNICODE).strip()
                print(" Detected Status Keyword:", raw_status)
                print(" Cleaned Sentence:", sentence)
            else:
                print("⚠️ Found trailing text but not a known status keyword:", possible_status)
        else:
            print(" No status-like ending found. Defaulting to:", raw_status)

        if return_titles:
            output.append({
                "title": title,
                "sentence": sentence,
                "status": raw_status
            })
        else:
            output.append(sentence)

    print("\n Final Segments Output:", output)
    return output


# Manual test
if __name__ == "__main__":
    test = ""
    
    import json
    print(json.dumps(segment_text(test, return_titles=True), indent=2, ensure_ascii=False))
