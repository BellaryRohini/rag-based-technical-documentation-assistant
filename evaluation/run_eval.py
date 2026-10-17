"""Small repeatable API smoke-evaluation. Start the API and index the corpus first."""
import json
import os
from pathlib import Path
import sys

import requests

BASE_URL = os.getenv("RAG_API_URL", "http://127.0.0.1:8000")
CASES = Path(__file__).with_name("questions.json")


def main() -> int:
    cases = json.loads(CASES.read_text(encoding="utf-8"))
    results = []
    for case in cases:
        response = requests.post(f"{BASE_URL}/query", json={"question": case["question"]}, timeout=180)
        response.raise_for_status()
        payload = response.json()
        answer = payload["answer"].lower()
        status_ok = payload["status"] == case["expected_status"]
        terms = case.get("expected_terms", [])
        terms_hit = sum(term.lower() in answer for term in terms)
        terms_ok = not terms or terms_hit > 0
        citations_ok = payload["status"] != "answered" or "[source " in answer
        results.append({"question": case["question"], "status_ok": status_ok, "terms_ok": terms_ok, "citations_ok": citations_ok, "passed": status_ok and terms_ok and citations_ok})
        print(("PASS" if results[-1]["passed"] else "FAIL") + f" | {case['question']}")
    passed = sum(item["passed"] for item in results)
    print(f"\\nEvaluation: {passed}/{len(results)} passed")
    print(json.dumps(results, indent=2))
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
