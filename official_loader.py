# official_loader.py  (replacement)
import json, pathlib, re, logging
from typing import Dict, Tuple

DATA_ROOT = pathlib.Path("data")           # data/<contest>/*.cleaned.jsonl
ID_PAT    = re.compile(r"([a-z]+)-(\d{4})-(?:q|prob)(\d+)")  # captures contest, year, #


def _grab(obj, *keys, default=""):
    for k in keys:
        if k in obj and obj[k]:
            return obj[k]
    return default


def _canonical(pid: str) -> str:
    """Convert 'egmo-2021-q1'  ->  'EGMO-2021-prob1'."""
    m = ID_PAT.fullmatch(pid.lower())
    if not m:
        return pid.upper()                # fallback: just upper-case
    contest, year, num = m.groups()
    return f"{contest.upper()}-{year}-prob{num}"


def load_official_solutions() -> Dict[str, Tuple[str, str]]:
    """
    Returns dict:
        canonical_problem_id  ->  (question_text, official_solution)
    The canonical ID format is 'EGMO-2021-prob1', 'IMO-2024-prob6', etc.
    """
    mapping: Dict[str, Tuple[str, str]] = {}
    for jpath in DATA_ROOT.glob("*/*.cleaned.jsonl"):
        with jpath.open(encoding="utf-8") as fh:
            for line in fh:
                obj = json.loads(line)
                raw_id  = _grab(obj, "id")
                if not raw_id:
                    continue
                can_id = _canonical(raw_id)
                Q = _grab(obj, "question", "content", "statement")
                S = _grab(obj, "official_solution", "solution", "answer")
                if not S:
                    logging.warning("No solution text for %s (%s)", can_id, jpath)
                mapping[can_id] = (Q, S)
    logging.info("Loaded %d official solutions", len(mapping))
    return mapping
