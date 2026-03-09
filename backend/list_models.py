"""
Test which Gemini API key(s) from .env work.
Supports comma-separated OPENAI_API_KEY=key1,key2,key3.
Run: cd backend && python list_models.py
"""
import os
import dotenv
dotenv.load_dotenv()

raw = (os.getenv("OPENAI_API_KEY") or "").strip()
keys = [k.strip() for k in raw.split(",") if k.strip() and k.strip() != "your-openai-key-here"]

if not keys:
    print("No OPENAI_API_KEY set in .env. Add a Gemini key from Google AI Studio (aistudio.google.com).")
    exit(1)

from openai import OpenAI
base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

for i, key in enumerate(keys):
    try:
        client = OpenAI(api_key=key, base_url=base_url)
        models = client.models.list()
        count = len(models.data) if models.data else 0
        print(f"Key #{i+1}: OK ({count} models)")
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower():
            print(f"Key #{i+1}: Quota exceeded (429) – try another key or use it later.")
        elif "API key" in err or "401" in err or "403" in err:
            print(f"Key #{i+1}: Invalid or rejected – check key at aistudio.google.com")
        else:
            print(f"Key #{i+1}: Failed – {e}")
