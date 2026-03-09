"""
Check each Gemini key in OPENAI_API_KEY for quota / validity.

Usage:
  cd backend
  python check_keys.py
"""

import os
from openai import OpenAI
import dotenv

dotenv.load_dotenv()  # loads backend/.env if present

raw = os.getenv("OPENAI_API_KEY", "").strip()
keys = [k.strip() for k in raw.split(",") if k.strip()]

if not keys:
    print("No OPENAI_API_KEY set (or empty).")
    raise SystemExit(1)

base_url = "https://generativelanguage.googleapis.com/v1beta/openai/"

for i, key in enumerate(keys, start=1):
    print(f"\n=== Testing key #{i} ===")
    try:
        client = OpenAI(api_key=key, base_url=base_url)
        resp = client.chat.completions.create(
            model="Gemini 3 Flash",  # or gemini-3-flash-preview
            messages=[{"role": "user", "content": "test"}],
            max_tokens=5,
        )
        print("OK:", resp.choices[0].message.content)
    except Exception as e:
        msg = str(e)
        if "429" in msg or "RESOURCE_EXHAUSTED" in msg.upper():
            print("QUOTA/429:", msg)
        elif "API key" in msg or "401" in msg or "403" in msg:
            print("INVALID/REJECTED:", msg)
        else:
            print("ERROR:", msg)