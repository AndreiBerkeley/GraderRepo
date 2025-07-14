import os
import glob
import json
from google import genai

import logging, time
from tqdm import tqdm   # progress bars

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)

SYSTEM_PROMPT = (
    "You are a competitive math expert. Produce a complete and rigorous, "
    "step-by-step solution to the given problem. Use clear English and MathJax-compatible LaTeX for any equations."
)

PROJECT_ID = "ramps-457621"
LOCATION   = "us-central1"

client2 = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

def ask_gemini(statement: str) -> str:
    response = client2.models.generate_content(
        model="gemini-2.5-pro",  # the recommended Gemini “flash” model
        contents=SYSTEM_PROMPT
    )
    return response.text.strip()


def main(data_folder="data", out_folder="outputs"):
    total_ok, total_fail = 0, 0
    for contest in tqdm(os.listdir(data_folder), desc="Contests"):
        contest_dir = os.path.join(data_folder, contest)
        if not os.path.isdir(contest_dir):
            continue

        gm_dir = os.path.join(out_folder, "gemini")
        os.makedirs(gm_dir, exist_ok=True)

        pattern = os.path.join(contest_dir, "*.cleaned.jsonl")
        for path in tqdm(glob.glob(pattern), desc=f"{contest} files", leave=False):
            year = os.path.basename(path).split(".")[0]
            gm_file = os.path.join(gm_dir, f"{contest}-{year}.jsonl")
            ok, fail = 0, 0
            t0 = time.time()
            with open(path) as infile, open(gm_file, "w") as fgm:
                for line in tqdm(infile, desc=f"{contest}-{year} problems", leave=False):
                    obj  = json.loads(line)
                    stmt = obj.get("content") or obj.get("question") \
                           or obj.get("statement") or ""
                    pid  = obj.get("id") or f"{contest}-{year}-prob?"
                    try:
                        sol_gm = ask_gemini(stmt)
                        ok += 1
                    except Exception as e:
                        logging.warning("✗ %s – %s", pid, e)
                        sol_gm = f"ERROR: {e}"
                        fail += 1
                    fgm.write(json.dumps({"id": pid,
                                          "solution": sol_gm}) + "\n")

            elapsed = time.time() - t0
            total_ok += ok; total_fail += fail
    logging.info("=== Finished: %d ok, %d failed ===", total_ok, total_fail)

if __name__ == "__main__":
    main()
