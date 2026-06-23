"""
app.py — Redrob AI Candidate Ranker · Vercel Sandbox (single-file, flat)

Serves the frontend AND the ranking API from one Flask app, with zero
subfolders required. Vercel auto-detects "app.py" at the project root as
a Python WSGI entrypoint with no vercel.json needed.

Routes:
  GET  /                      -> the dashboard UI
  GET  /sample_candidates.json -> bundled 100-candidate sample
  POST /api/rank               -> { "candidates": [...] } -> ranked JSON
"""

import sys
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_file

sys.path.insert(0, str(Path(__file__).parent))
from scorer import score_candidate

BASE = Path(__file__).parent
app = Flask(__name__)


@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/", methods=["GET"])
def home():
    return send_file(BASE / "index.html")


@app.route("/sample_candidates.json", methods=["GET"])
def sample():
    return send_file(BASE / "sample_candidates.json", mimetype="application/json")


@app.route("/api/rank", methods=["OPTIONS"])
def rank_options():
    return "", 200


@app.route("/api/rank", methods=["POST"])
def rank():
    try:
        data = request.get_json(force=True, silent=True) or {}
        candidates = data.get("candidates", [])[:100]

        if not candidates:
            return jsonify({"error": "No candidates provided"}), 400

        results = []
        t0 = time.time()
        for c in candidates:
            try:
                score, comps, reasoning = score_candidate(c)
                results.append({
                    "candidate_id":   c.get("candidate_id", "?"),
                    "score":          round(score, 4),
                    "reasoning":      reasoning,
                    "components":     {k: round(v, 1) for k, v in comps.items()},
                    "profile":        c.get("profile", {}),
                    "skills":         c.get("skills", []),
                    "career_history": c.get("career_history", []),
                    "redrob_signals": c.get("redrob_signals", {}),
                    "is_honeypot":    score == 0.0,
                })
            except Exception as exc:
                results.append({
                    "candidate_id": c.get("candidate_id", "?"),
                    "score": 0.0, "reasoning": f"Scoring error: {exc}",
                    "components": {}, "profile": {}, "skills": [],
                    "career_history": [], "redrob_signals": {},
                    "is_honeypot": False,
                })

        results.sort(key=lambda x: (-x["score"], x["candidate_id"]))
        for i, r in enumerate(results, 1):
            r["rank"] = i

        honey = sum(1 for r in results if r["is_honeypot"])

        return jsonify({
            "ranked":    results,
            "total":     len(results),
            "honeypots": honey,
            "top_score": results[0]["score"] if results else 0,
            "runtime_s": round(time.time() - t0, 3),
        })

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


# Vercel's Python runtime looks for a top-level WSGI callable named `app`
# (already satisfied above). No vercel.json or api/ folder needed.

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860, debug=False)
