import os, glob, json, time, logging
from tqdm import tqdm
from openai import OpenAI

SYSTEM_PROMPT = (
    "You are a competitive math expert. Produce a complete and rigorous, "
    "step-by-step solution to the given problem. Use clear English and "
    "MathJax-compatible LaTeX for equations."
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def solve_with_openai(question: str) -> str:
    resp = client.chat.completions.create(
        model="o3",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": question},
        ],
    )
    return resp.choices[0].message.content.strip()

def main(data_dir="data", out_root="outputs/openai"):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s %(message)s",
        datefmt="%H:%M:%S",
    )
    ok_total = fail_total = 0
    for contest in tqdm(os.listdir(data_dir), desc="Contests"):
        cdir = os.path.join(data_dir, contest)
        if not os.path.isdir(cdir):
            continue
        os.makedirs(out_root, exist_ok=True)

        for path in tqdm(
            glob.glob(os.path.join(cdir, "*.cleaned.jsonl")),
            desc=f"{contest} files",
            leave=False,
        ):
            year = os.path.basename(path).split(".")[0]
            out_path = os.path.join(out_root, f"{contest}-{year}.jsonl")
            ok = fail = 0
            t0 = time.time()
            with open(path) as fin, open(out_path, "w") as fout:
                for line in tqdm(fin, desc=f"{contest}-{year}", leave=False):
                    obj  = json.loads(line)
                    q    = obj.get("content") or obj.get("question") \
                           or obj.get("statement") or ""
                    pid  = obj.get("id") or f"{contest}-{year}-?"
                    try:
                        sol = solve_with_openai(q)
                        ok += 1
                    except Exception as e:
                        logging.warning("✗ %s – %s", pid, e)
                        sol = f"ERROR: {e}"
                        fail += 1
                    fout.write(json.dumps({"id": pid, "solution": sol}) + "\n")
            logging.info("✓ %s  (%d ok, %d failed, %.1fs)",
                         out_path, ok, fail, time.time() - t0)
            ok_total += ok; fail_total += fail
    logging.info("=== Finished: %d ok, %d failed ===", ok_total, fail_total)

if __name__ == "__main__":
    main()
