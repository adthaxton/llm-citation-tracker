"""
llm-citation-tracker
====================
Track whether your brand appears in LLM responses across multiple prompts.
Queries the Perplexity API and logs citation presence to a CSV.

Requirements:
    pip install requests python-dotenv

Setup:
    1. Get a free Perplexity API key at https://www.perplexity.ai/settings/api
    2. Create a .env file in the same directory:
           PERPLEXITY_API_KEY=your_key_here
    3. Edit BRAND and PROMPTS below, then run:
           python citation_tracker.py

Output:
    citations_log.csv — append-mode log of every query run
"""

import csv
import os
import json
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────

BRAND = "Your Brand Name"   # The brand or entity you are tracking

PROMPTS = [
    "What are the best automotive SEO agencies?",
    "Who are the top SEO companies for car dealerships?",
    "What tools should I use to optimize a dealership website for local search?",
    "How do I improve my dealership's visibility in Google AI Overviews?",
    "What companies specialize in multi-location SEO?",
]

OUTPUT_FILE = "citations_log.csv"
MODEL = "llama-3.1-sonar-large-128k-online"   # Perplexity model with web access

# ─── API CALL ────────────────────────────────────────────────────────────────

def query_perplexity(prompt: str) -> dict:
    """Send a prompt to Perplexity and return the full response dict."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not found. Check your .env file.")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Be precise and concise. Always answer in full sentences.",
            },
            {"role": "user", "content": prompt},
        ],
    }

    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers=headers,
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


# ─── CITATION CHECK ──────────────────────────────────────────────────────────

def check_citation(response_text: str, brand: str) -> bool:
    """Return True if brand name appears in the response (case-insensitive)."""
    return brand.lower() in response_text.lower()


def extract_snippet(response_text: str, brand: str, window: int = 120) -> str:
    """Return the surrounding text around the first brand mention, or empty string."""
    lower = response_text.lower()
    idx = lower.find(brand.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window // 2)
    end = min(len(response_text), idx + len(brand) + window // 2)
    snippet = response_text[start:end].replace("\n", " ").strip()
    return f"...{snippet}..."


# ─── CSV LOGGING ─────────────────────────────────────────────────────────────

FIELDNAMES = [
    "timestamp",
    "brand",
    "model",
    "prompt",
    "cited",
    "snippet",
    "full_response",
]


def log_result(row: dict) -> None:
    """Append a result row to the CSV log. Creates headers if file is new."""
    file_exists = os.path.isfile(OUTPUT_FILE)
    with open(OUTPUT_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nLLM Citation Tracker — {timestamp}")
    print(f"Brand: {BRAND}")
    print(f"Model: {MODEL}")
    print(f"Prompts: {len(PROMPTS)}\n")
    print("-" * 60)

    cited_count = 0

    for i, prompt in enumerate(PROMPTS, 1):
        print(f"[{i}/{len(PROMPTS)}] {prompt[:70]}...")
        try:
            response_data = query_perplexity(prompt)
            response_text = response_data["choices"][0]["message"]["content"]
            cited = check_citation(response_text, BRAND)
            snippet = extract_snippet(response_text, BRAND)

            if cited:
                cited_count += 1
                print(f"  CITED   -> {snippet[:80]}")
            else:
                print(f"  not cited")

            log_result({
                "timestamp": timestamp,
                "brand": BRAND,
                "model": MODEL,
                "prompt": prompt,
                "cited": "YES" if cited else "NO",
                "snippet": snippet,
                "full_response": response_text.replace("\n", " "),
            })

        except requests.exceptions.HTTPError as e:
            print(f"  API error: {e}")
            log_result({
                "timestamp": timestamp,
                "brand": BRAND,
                "model": MODEL,
                "prompt": prompt,
                "cited": "ERROR",
                "snippet": "",
                "full_response": str(e),
            })

    print("-" * 60)
    print(f"\nSummary: {BRAND} cited in {cited_count}/{len(PROMPTS)} responses")
    print(f"Results saved to: {OUTPUT_FILE}\n")


if __name__ == "__main__":
    run()
