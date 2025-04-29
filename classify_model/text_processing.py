import spacy
import re
from langdetect import detect
import nltk
from transformers import pipeline, MBart50Tokenizer, MBartForConditionalGeneration
from nltk.tokenize.punkt import PunktSentenceTokenizer
from nltk.data import load

# Download punkt only once
nltk.download('punkt')


# 🛠 Custom tokenizer loader with fallback
def get_tokenizer(lang):
    lang_map = {'en': 'english', 'fr': 'french'}
    lang_name = lang_map.get(lang, 'english')

    try:
        return load(f'tokenizers/punkt/{lang_name}.pickle')
    except LookupError as e:
        print(f"[WARN] Could not load punkt tokenizer for {lang_name}: {e}")
        return PunktSentenceTokenizer()


# ✅ Manual test block
if __name__ == "__main__":
    tokenizer_fr = get_tokenizer('fr')
    tokenizer_en = get_tokenizer('en')

    text_fr = "Bonjour. Je m'appelle Paul. Comment ça va ?"
    print("French Tokenizer Output:", tokenizer_fr.tokenize(text_fr))

    text_en = "Hello. My name is John. How are you?"
    print("English Tokenizer Output:", tokenizer_en.tokenize(text_en))
# Load spaCy models
nlp_en = spacy.load("en_core_web_sm")
nlp_fr = spacy.load("fr_core_news_sm")

# Load mBART model
tokenizer = MBart50Tokenizer.from_pretrained('facebook/mbart-large-50')
model = MBartForConditionalGeneration.from_pretrained('facebook/mbart-large-50')
hf_sentence_splitter = pipeline("text2text-generation", model=model, tokenizer=tokenizer)

# Text cleaner
def clean_text(text):
    text = re.sub(r"[\n\t\r]+", " ", text)
    text = re.sub(r"\*\*|\>\s*", "", text)
    text = re.sub(r"\brapport\s+quotidien(?:\s+d'activité)?\s*:?", "", text, flags=re.IGNORECASE)
    return text.strip().lower()

# 🔍 Multilingual sentence segmenter with robust fallback
def segment_text(text):
    try:
        lang = detect(text)
    except Exception:
        lang = 'en'

    lang_nltk = {'en': 'english', 'fr': 'french'}.get(lang, 'english')
    nlp = nlp_fr if lang == 'fr' else nlp_en

    # First try spaCy
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents]

    # Fallback 1: Check if spaCy returned only one long sentence
    if len(sentences) <= 1:
        # Split on period if present
        if '.' in text:
            sentences = [s.strip() for s in text.split('.') if s.strip()]
        
        # Fallback 2: Try comma split if still short
        if len(sentences) <= 1 and ',' in text:
            comma_split = [s.strip() for s in text.split(',') if s.strip()]
            if len(comma_split) > 1:
                sentences = comma_split

    # Final fallback: use NLTK Punkt
    if len(sentences) <= 1:
        tokenizer = get_tokenizer(lang_nltk)
        sentences = tokenizer.tokenize(text)

    return sentences
