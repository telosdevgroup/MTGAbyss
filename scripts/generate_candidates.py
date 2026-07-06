import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from db_mongo import get_mongo_db
from prompt_builder import build_prompt
from scripts.worker_generate_sections import call_ollama, perform_quality_check

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    db = get_mongo_db()
    card = db["cards"].find_one({"name": "Black Lotus"})
    
    if not card:
        print("Error: Black Lotus not found in MongoDB.")
        return

    print("Generating 5 valid candidate hooks for Black Lotus using Llama 3.1:8b...\n")
    
    prompt = build_prompt(card, language="en", section_type="hook")

    valid_candidates = []
    attempts = 0
    max_attempts = 30  # Try up to 30 times

    while len(valid_candidates) < 5 and attempts < max_attempts:
        attempts += 1
        try:
            content = call_ollama(prompt, model="llama3.1:8b")
            text = content.get("text", "").strip()
            
            # Run quality validation check
            passed, errors = perform_quality_check("Black Lotus", content, mock_mode=False)
            
            if passed:
                # Deduplicate
                if text not in [c[0] for c in valid_candidates]:
                    valid_candidates.append((text, len(text.split())))
        except Exception as e:
            pass

    print("=== Candidate Hooks (Passed Quality Checks) ===")
    for i, (text, word_count) in enumerate(valid_candidates, 1):
        print(f"{i}. \"{text}\" ({word_count} words)")
        
    if len(valid_candidates) < 5:
        print(f"\nWarning: Only generated {len(valid_candidates)} valid candidates after {attempts} attempts.")

if __name__ == "__main__":
    main()
