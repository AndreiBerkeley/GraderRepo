#!/usr/bin/env python3
"""
Secure & grader-aware Flask back-end for Contest Problem Viewer
"""

import json
import pathlib
import re
import subprocess
import base64
from datetime import datetime
from flask import (
    Flask, jsonify, send_from_directory,
    request, abort
)
from werkzeug.utils import secure_filename

# ————————————————————————————————————
#  Config / constants
# ————————————————————————————————————
app           = Flask(__name__, static_folder='static')
DATA_DIR      = pathlib.Path("data")
OUTPUTS_DIR   = pathlib.Path("outputs")
REVIEWS_FILE  = pathlib.Path("reviews.jsonl")
GRADES_DIR    = OUTPUTS_DIR / "grades"

NAME_RE   = re.compile(r"^[A-Za-z0-9_-]+$")
FILE_RE   = re.compile(
    r"^(?P<contest>[A-Za-z0-9_-]+)-(?P<year>\d{4})-prob(?P<prob>\d+)\.tex$"
)

# -----------------------------------------------------------------------------
#  Helpers
# -----------------------------------------------------------------------------
def _safe(name: str) -> str:
    """whitelist simple directory names (contest, student, grader)."""
    if not NAME_RE.fullmatch(name):
        abort(404)
    return name

def _jsonl_count(fp: pathlib.Path) -> int:
    return sum(1 for _ in fp.open(encoding="utf-8") if _.strip())

# -----------------------------------------------------------------------------
#  Scanners (for drop-down indices)
# -----------------------------------------------------------------------------
def scan_data_index():
    out = {}
    for cd in DATA_DIR.iterdir():
        if not cd.is_dir():
            continue
        years = {}
        for fn in cd.glob("*.cleaned.jsonl"):
            year = fn.stem.replace(".cleaned", "")
            years[year] = _jsonl_count(fn)
        if years:
            out[cd.name] = years
    return out


def scan_students_index():
    """Return {student: [ {contest, year, problem, path} ] }."""
    students = {}
    if not OUTPUTS_DIR.exists():
        return students

    pat = re.compile(
        r"^(?P<contest>[A-Za-z0-9_-]+)-(?P<year>\d{4})-prob(?P<prob>\d+)\.(?:tex|pdf|txt)$"
    )

    for student_dir in OUTPUTS_DIR.iterdir():
        if not student_dir.is_dir() or student_dir.name == "grades":
            continue
        entries = []
        for file in student_dir.iterdir():
            m = pat.match(file.name)
            if m:
                entries.append({
                    "contest": m["contest"],
                    "year":    m["year"],
                    "problem": int(m["prob"]),
                    "path":    file.name
                })
        if entries:
            students[student_dir.name] = entries
    return students


def scan_graders_index():
    """
    Return {grader: {graded: [ {contest, year, problem, path} ] } }
    """
    graders = {}
    pat = re.compile(
        r"^(?P<contest>[A-Za-z0-9_-]+)-(?P<year>\d{4})-prob(?P<prob>\d+)\.json$"
    )
    if not GRADES_DIR.exists():
        return graders

    for grader_dir in GRADES_DIR.iterdir():
        if not grader_dir.is_dir():
            continue
        graded_map = {}
        for graded_dir in grader_dir.iterdir():
            if not graded_dir.is_dir():
                continue
            entries = []
            for fp in graded_dir.iterdir():
                m = pat.match(fp.name)
                if m:
                    entries.append({
                        "contest": m["contest"],
                        "year":    m["year"],
                        "problem": int(m["prob"]),
                        "path":    fp.name
                    })
            if entries:
                graded_map[graded_dir.name] = entries
        if graded_map:
            graders[grader_dir.name] = graded_map
    return graders

# -----------------------------------------------------------------------------
#  API routes
# -----------------------------------------------------------------------------
@app.route("/api/index_data")
def api_index_data():
    return jsonify(scan_data_index())

@app.route("/api/index_students")
def api_index_students():
    return jsonify(scan_students_index())

@app.route("/api/index_graders")
def api_index_graders():
    return jsonify(scan_graders_index())

# -----------------------------------------------------------------------------
#  Static file serving (with safer names)
# -----------------------------------------------------------------------------
@app.route("/data/<contest>/<filename>")
def serve_data(contest, filename):
    _safe(contest)
    fn = DATA_DIR / contest / secure_filename(filename)
    if not fn.exists():
        abort(404)
    return send_from_directory(fn.parent, fn.name)

@app.route("/outputs/<student>/<filename>")
def serve_output(student, filename):
    _safe(student)
    fn = OUTPUTS_DIR / student / secure_filename(filename)
    if not fn.exists():
        abort(404)
    return send_from_directory(fn.parent, fn.name)

# --- grades ------------------------------------------------------------------
@app.route("/outputs/grades/<grader>/<graded>/<filename>")
def serve_grade_multi(grader, graded, filename):
    _safe(grader); _safe(graded)
    fn = GRADES_DIR / grader / graded / secure_filename(filename)
    if not fn.exists():
        abort(404)
    return send_from_directory(fn.parent, fn.name)

# legacy (grader omitted)
@app.route("/outputs/grades/<graded>/<filename>")
def serve_grade_legacy(graded, filename):
    _safe(graded)
    fn = GRADES_DIR / graded / secure_filename(filename)
    if not fn.exists():
        abort(404)
    return send_from_directory(fn.parent, fn.name)

# catch-all must be LAST otherwise it masks more specific routes
@app.route("/outputs/<path:filename>")
def serve_output_file(filename):
    fn = OUTPUTS_DIR / secure_filename(filename)
    if not fn.exists():
        abort(404)
    return send_from_directory(OUTPUTS_DIR, fn.name)

# -----------------------------------------------------------------------------
#  Utility endpoints
# -----------------------------------------------------------------------------
@app.route("/compile_asy", methods=["POST"])
def compile_asy():
    body = request.get_json(silent=True) or {}
    code = body.get("code", "")
    proc = subprocess.run(
        ["asy", "-f", "svg", "-o", "-", "-"],
        input=code.encode("utf-8"),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10
    )
    if proc.returncode != 0:
        return (proc.stderr.decode("utf-8"), 500)

    uri = "data:image/svg+xml;base64," + base64.b64encode(proc.stdout).decode("ascii")
    return jsonify(svg=uri)


@app.route("/save_review", methods=["POST"])
def save_review():
    data = request.get_json(silent=True)
    if not data:
        return ("Invalid JSON", 400)

    # simple file-lock via exclusive open on POSIX
    line = json.dumps(data, ensure_ascii=False) + "\n"
    stamp = datetime.utcnow().isoformat(timespec='seconds')

    with open(REVIEWS_FILE, "a", encoding="utf-8") as fp:
        fp.write(line)

    app.logger.info("Review saved %s", stamp)
    return jsonify(status="ok")

# -----------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "viewer.html")

# -----------------------------------------------------------------------------
if __name__ == "__main__":                      # pragma: no cover
    app.run(host="0.0.0.0", port=5050, debug=False)
