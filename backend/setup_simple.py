import os
import nltk
import json
from pathlib import Path

def setup_environment():
    print("Setting up environment...")
    
    # Calculate paths directly
    PROJECT_ROOT = Path(__file__).resolve().parent
    DATA_DIR = PROJECT_ROOT / "data"
    CORPUS_DIR = DATA_DIR / "sri_lanka_legal_corpus"
    
    # Create directories
    directories = [
        DATA_DIR,
        DATA_DIR / "raw_documents",
        DATA_DIR / "processed", 
        CORPUS_DIR,
        "uploaded_docs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Created: {directory}")
    
    # Download NLTK data
    try:
        nltk.download('punkt', quiet=True)
        print("NLTK data downloaded")
    except Exception as e:
        print(f"NLTK download issue (but continuing): {e}")
    
    # Create basic glossary if missing
    glossary_path = CORPUS_DIR / "legal_glossary_si_en_ta.json"
    if not os.path.exists(glossary_path):
        basic_glossary = {
            "legal_terms": {
                "fundamental_rights": {
                    "en": "Basic constitutional rights",
                    "si": "මූලික අයිතිවාසිකම්",
                    "ta": "அடிப்படை உரிமைகள்"
                },
                "constitution": {
                    "en": "Supreme law of Sri Lanka", 
                    "si": "ශ්‍රී ලංකා ආණ්ඩුක්‍රම ව්‍යවස්ථාව",
                    "ta": "இலங்கை அரசியலமைப்பு"
                }
            },
            "rights": {
                "10": {
                    "en": "Freedom of thought, conscience and religion",
                    "si": "චින්තන, හෘද සාක්ෂියේ සහ ආගමේ නිදහස",
                    "ta": "சிந்தனை, மனசாட்சி மற்றும் மத சுதந்திரம்"
                },
                "12": {
                    "en": "Right to equality and freedom from discrimination", 
                    "si": "සමානාත්මතාවයේ අයිතිය සහ වෙනස්කම්වලින් නිදහස",
                    "ta": "சமத்துவம் மற்றும் பாகுபாடு இல்லாத உரிமை"
                }
            }
        }
        
        with open(glossary_path, 'w', encoding='utf-8') as f:
            json.dump(basic_glossary, f, ensure_ascii=False, indent=2)
        print("Created basic glossary file")
    
    print("✅ Environment setup completed!")

if __name__ == "__main__":
    setup_environment()