#!/usr/bin/env python3
"""
Grade Olympiad solutions with Gemini.

Student answers   : outputs/<student>/<problem>.tex
Official solutions: data/<contest>/<year>.cleaned.jsonl   (loaded centrally)
Grades written to : outputs/grades/gemini/<student>/<problem>.json
"""

import os, json, logging, pathlib
from google import genai
from official_loader import load_official_solutions     # <- NEW

GRADER   = "gemini"
STUDENTS = ["openai", "gemini"]
ROOT_OUT = pathlib.Path("outputs")

SYSTEM_PROMPT = (
    "You are an IMO grader. Given the problem statement, an official solution, "
    "and a student's attempt, output a JSON object with keys `verdict`, "
    "`score` (0-7), and `feedback`."
)

client = genai.Client(vertexai=True,
                      project="ramps-457621",
                      location="us-central1")

official_map = load_official_solutions()                # <- NEW


# --- gemini_grader.py --------------------------------------------------------
def _wrap(text: str) -> dict:
    """Return a single-part wrapper required by Vertex AI Gemini."""
    return {"text": text}

def grade_with_gemini(question: str, official: str, student: str) -> dict:
    """Call Gemini, return the parsed JSON grade."""
    full_prompt = (
        f"{SYSTEM_PROMPT}\n\n"                # ← include rubric first
        f"Problem statement:\n{question}\n\n"
        f"Official solution:\n{official}\n\n"
        f"Student solution:\n{student}\n\n"
        "Grade the student answer."
    )

    resp = client.models.generate_content(
        model="gemini-2.5-pro",
        contents=[
            {"role": "user", "parts": [_wrap(full_prompt)]},  # ← no 'system'
        ],
    )

    raw = resp.text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "verdict":  "ERROR",
            "score":    0,
            "feedback": f"Could not parse model output:\n{raw}",
        }


def main():
    logging.basicConfig(level=logging.INFO,
                        format="%(levelname)s %(message)s")

    for student in STUDENTS:
        stu_dir = ROOT_OUT / student
        if not stu_dir.exists():
            logging.warning("Student dir %s missing – skipped", stu_dir)
            continue

        for tex_path in stu_dir.glob("*.tex"):
            pid = tex_path.stem
            if pid not in official_map:
                logging.warning("No official record for %s – skipped", pid)
                continue

            question, official_sol = official_map[pid]
            student_sol = tex_path.read_text(encoding="utf-8")
            grade = grade_with_gemini(question, official_sol, student_sol)

            out_path = ROOT_OUT / "grades" / GRADER / student / f"{pid}.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(json.dumps(grade, ensure_ascii=False, indent=2), encoding="utf-8")
            logging.info("✓ %s → %s", pid, out_path)

if __name__ == "__main__":
    main()
