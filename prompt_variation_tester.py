"""
prompt-variation-tester
=======================
Test how citation rates vary across differently phrased prompts for any brand
in any industry. Uses the Perplexity API to auto-generate prompt variations,
then runs each one and logs whether your brand appears in the response.

Requirements:
    pip install requests python-dotenv

Setup:
    1. Get a free Perplexity API key at https://www.perplexity.ai/settings/api
    2. Create a .env file in the same directory:
           PERPLEXITY_API_KEY=your_key_here
    3. Edit BRAND, TOPIC, and NUM_VARIATIONS below, then run:
           python prompt_variation_tester.py

Output:
    variation_results.csv  — full log of every prompt and response
    variation_summary.txt  — ranked summary table of citation rates by prompt
"""

import csv
import os
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()

# ─── CONFIG ──────────────────────────────────────────────────────────────────

BRAND = "Your Brand Name"       # The brand or entity you are tracking
TOPIC = "your industry or niche" # e.g. "automotive SEO", "personal injury law", "B2B SaaS"
NUM_VARIATIONS = 10             # How many prompt variations to generate and test

OUTPUT_CSV = "variation_results.csv"
OUTPUT_SUMMARY = "variation_summary.txt"
MODEL = "llama-3.1-sonar-large-128k-online"

# ─── API CALL ────────────────────────────────────────────────────────────────

def query_perplexity(prompt: str, system: str = None) -> str:
    """Send a prompt to Perplexity and return the response text."""
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        raise ValueError("PERPLEXITY_API_KEY not found. Check your .env file.")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = requests.post(
        "https://api.perplexity.ai/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": MODEL, "messages": messages},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ─── PROMPT GENERATION ───────────────────────────────────────────────────────

def generate_prompt_variations(brand: str, topic: str, n: int) -> list[str]:
    """
    Ask Perplexity to generate n differently phrased prompts that a real user
    might ask when searching for services or companies in the given topic area.
    Returns a list of prompt strings.
    """
    print(f"Generating {n} prompt variations for topic: {topic}...")

    generation_prompt = f"""
Generate exactly {n} different search queries that a real person might type or
ask an AI assistant when looking for companies, services, or experts in this area:

Topic: {topic}

Rules:
- Each query must have meaningfully different phrasing and intent angle
- Cover a range of styles: some specific, some broad, some question-form, some keyword-style
- Do NOT mention "{brand}" in any of the queries
- Return ONLY the queries, one per line, numbered 1 through {n}
- No explanations, no extra text, just the numbered list
"""

    raw = query_perplexity(
        generation_prompt,
        system="You generate search query variations. Return only the numbered list, nothing else."
    )

    prompts = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        # Strip leading number and punctuation (e.g. "1. ", "1) ", "1 - ")
        for sep in [". ", ") ", " - ", ": "]:
            if line[0].isdigit() and sep in line:
                line = line.split(sep, 1)[1].strip()
                break
        if line:
            prompts.append(line)

    # Fallback: if parsing fails, return whatever non-empty lines we got
    if not prompts:
        prompts = [l.strip() for l in raw.strip().split("\n") if l.strip()]

    return prompts[:n]


# ─── CITATION CHECK ──────────────────────────────────────────────────────────

def check_citation(response_text: str, brand: str) -> bool:
    return brand.lower() in response_text.lower()


def extract_snippet(response_text: str, brand: str, window: int = 120) -> str:
    lower = response_text.lower()
    idx = lower.find(brand.lower())
    if idx == -1:
        return ""
    start = max(0, idx - window // 2)
    end = min(len(response_text), idx + len(brand) + window // 2)
    return f"...{response_text[start:end].replace(chr(10), ' ').strip()}..."


# ─── LOGGING ─────────────────────────────────────────────────────────────────

CSV_FIELDS = ["timestamp", "brand", "topic", "prompt", "cited", "snippet", "full_response"]


def log_result(row: dict) -> None:
    file_exists = os.path.isfile(OUTPUT_CSV)
    with open(OUTPUT_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


def write_summary(results: list[dict], brand: str, topic: str, timestamp: str) -> None:
    """Write a ranked summary table to a text file."""
    cited = [r for r in results if r["cited"] == "YES"]
    not_cited = [r for r in results if r["cited"] == "NO"]
    errors = [r for r in results if r["cited"] == "ERROR"]

    total = len(results)
    rate = f"{len(cited)}/{total} ({round(len(cited)/total*100)}%)" if total else "0/0"

    lines = [
        "=" * 70,
        f"PROMPT VARIATION TEST SUMMARY",
        f"Run: {timestamp}",
        f"Brand: {brand}",
        f"Topic: {topic}",
        f"Citation rate: {rate}",
        "=" * 70,
        "",
        "CITED — prompts where brand appeared:",
    ]
    if cited:
        for i, r in enumerate(cited, 1):
            lines.append(f"  {i}. {r['prompt']}")
            if r["snippet"]:
                lines.append(f"     -> {r['snippet'][:100]}")
    else:
        lines.append("  (none)")

    lines += ["", "NOT CITED — prompts where brand did not appear:"]
    if not_cited:
        for i, r in enumerate(not_cited, 1):
            lines.append(f"  {i}. {r['prompt']}")
    else:
        lines.append("  (none)")

    if errors:
        lines += ["", "ERRORS:"]
        for r in errors:
            lines.append(f"  {r['prompt']} — {r['snippet']}")

    lines += ["", "=" * 70, ""]

    with open(OUTPUT_SUMMARY, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("\n".join(lines))


# ─── MAIN ────────────────────────────────────────────────────────────────────

def run():
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\nPrompt Variation Tester — {timestamp}")
    print(f"Brand: {BRAND}")
    print(f"Topic: {TOPIC}")
    print(f"Variations: {NUM_VARIATIONS}\n")
    print("-" * 70)

    # Step 1: generate prompt variations
    try:
        prompts = generate_prompt_variations(BRAND, TOPIC, NUM_VARIATIONS)
    except Exception as e:
        print(f"Failed to generate prompts: {e}")
        return

    print(f"Generated {len(prompts)} prompts. Running citation checks...\n")

    # Step 2: test each prompt
    results = []
    for i, prompt in enumerate(prompts, 1):
        print(f"[{i}/{len(prompts)}] {prompt[:75]}...")
        try:
            response_text = query_perplexity(prompt)
            cited = check_citation(response_text, BRAND)
            snippet = extract_snippet(response_text, BRAND)

            status = "CITED  " if cited else "not cited"
            print(f"  {status}" + (f" -> {snippet[:80]}" if cited else ""))

            row = {
                "timestamp": timestamp,
                "brand": BRAND,
                "topic": TOPIC,
                "prompt": prompt,
                "cited": "YES" if cited else "NO",
                "snippet": snippet,
                "full_response": response_text.replace("\n", " "),
            }
        except requests.exceptions.HTTPError as e:
            print(f"  API error: {e}")
            row = {
                "timestamp": timestamp,
                "brand": BRAND,
                "topic": TOPIC,
                "prompt": prompt,
                "cited": "ERROR",
                "snippet": str(e),
                "full_response": "",
            }

        results.append(row)
        log_result(row)

    # Step 3: write summary
    print("-" * 70)
    write_summary(results, BRAND, TOPIC, timestamp)
    print(f"Full results saved to: {OUTPUT_CSV}")
    print(f"Summary saved to: {OUTPUT_SUMMARY}\n")


if __name__ == "__main__":
    run()
