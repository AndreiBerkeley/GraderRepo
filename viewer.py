#!/usr/bin/env python3
import json, pathlib, subprocess, base64
from flask import Flask, jsonify, send_from_directory, request, abort

app = Flask(__name__, static_folder='static')

DATA_DIR     = pathlib.Path("data")
OUTPUTS_DIR  = pathlib.Path("outputs")
REVIEWS_FILE = pathlib.Path("reviews.jsonl")

def scan_data_index():
    idx = {}
    for cd in DATA_DIR.iterdir():
        if not cd.is_dir(): continue
        yrs = {}
        for fn in cd.glob("*.cleaned.jsonl"):
            year = fn.stem.replace(".cleaned","")
            cnt  = sum(1 for _ in fn.open(encoding="utf8") if _.strip())
            yrs[year] = cnt
        if yrs: idx[cd.name] = yrs
    return idx

def scan_students_index():
    studs = {}
    if not OUTPUTS_DIR.exists(): return studs
    for sd in OUTPUTS_DIR.iterdir():
        if not sd.is_dir(): continue
        ents = []
        for f in sd.glob("*"):
            parts = f.stem.split("-")
            if len(parts)>=3 and parts[2].startswith("prob"):
                c,y,p = parts[0], parts[1], parts[2][4:]
                ents.append({"contest":c,"year":y,"problem":int(p),"path":f.name})
        if ents: studs[sd.name] = ents
    return studs

@app.route("/api/index_data")
def api_index_data():
    return jsonify(scan_data_index())

@app.route("/api/index_students")
def api_index_students():
    return jsonify(scan_students_index())

@app.route("/data/<contest>/<filename>")
def serve_data(contest, filename):
    d = DATA_DIR / contest
    if not (d/filename).exists(): abort(404)
    return send_from_directory(str(d), filename)

@app.route("/outputs/<student>/<filename>")
def serve_output(student, filename):
    d = OUTPUTS_DIR / student
    if not (d/filename).exists(): abort(404)
    return send_from_directory(str(d), filename)

@app.route("/outputs/grades/<student>/<filename>")
def serve_grade(student, filename):
    d = OUTPUTS_DIR / "grades" / student
    if not (d/filename).exists(): abort(404)
    return send_from_directory(str(d), filename)

@app.route("/compile_asy", methods=["POST"])
def compile_asy():
    body = request.get_json(silent=True) or {}
    code = body.get("code","")
    proc = subprocess.run(
        ["asy","-f","svg","-o","-","-"],
        input=code.encode("utf8"),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    if proc.returncode != 0:
        return (proc.stderr.decode("utf8"), 500)
    uri = "data:image/svg+xml;base64," + base64.b64encode(proc.stdout).decode("ascii")
    return jsonify(svg=uri)

@app.route("/save_review", methods=["POST"])
def save_review():
    data = request.get_json(silent=True)
    if not data:
        return ("Invalid JSON", 400)
    with open(REVIEWS_FILE, "a", encoding="utf8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")
    return jsonify(status="ok")

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "viewer.html")


if __name__ == "__main__":
    app.run(debug=True)
