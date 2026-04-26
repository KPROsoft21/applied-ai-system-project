"""
VibeMatch — Evaluation Harness

Runs the system against 10 predefined test cases and prints a pass/fail
summary with confidence ratings. Agent step output is suppressed so each
test case shows only its check results.

Run from the project root:
    python evaluate.py
"""
import sys
import logging
logging.basicConfig(level=logging.CRITICAL)   # suppress reliability/agent console noise

from src.recommender import load_songs
from src.reliability import ReliabilityChecker
from src.agent import RecommenderAgent, CONFIDENCE_THRESHOLD

# ── test case definitions ──────────────────────────────────────────────────────
#
# Each test case has:
#   id      short identifier printed in the report
#   name    human-readable description
#   profile dict passed to agent.run()
#   checks  list of (description, lambda result -> bool) pairs
#   top_k   optional, defaults to 5
#
# Every lambda receives the full agent result dict:
#   result["results"]         List[Tuple[Dict, float, str]]
#   result["report"]          reliability report from ReliabilityChecker
#   result["mode_used"]       scoring mode that produced the final results
#   result["attempts"]        1 or 2
#   result["fallback_reason"] warning type that triggered fallback, or None
#   result["trace"]           list of reasoning step dicts

TEST_CASES = [
    {
        "id":   "TC-01",
        "name": "Perfect genre match — pop, happy, high energy",
        "profile": {
            "label": "TC-01", "mode": "balanced",
            "genre": "pop", "mood": "happy", "target_energy": 0.9,
        },
        "checks": [
            ("confidence == 1.0",           lambda r: r["report"]["confidence"] == 1.0),
            ("no fallback needed",          lambda r: r["attempts"] == 1),
            ("top result is pop genre",     lambda r: r["results"][0][0]["genre"] == "pop"),
            ("top result is happy mood",    lambda r: r["results"][0][0]["mood"] == "happy"),
        ],
    },
    {
        "id":   "TC-02",
        "name": "Ghost genre triggers agentic fallback",
        "profile": {
            "label": "TC-02", "mode": "balanced",
            "genre": "bossa nova", "mood": "relaxed", "target_energy": 0.5,
        },
        "checks": [
            ("fallback triggered (attempts==2)",   lambda r: r["attempts"] == 2),
            ("fallback_reason is GHOST_GENRE",     lambda r: r["fallback_reason"] == "GHOST_GENRE"),
            ("GHOST_GENRE warning in report",      lambda r: any("GHOST_GENRE" in w for w in r["report"]["warnings"])),
            ("fallback used a different mode",     lambda r: r["mode_used"] != "balanced"),
        ],
    },
    {
        "id":   "TC-03",
        "name": "Energy dead zone flagged",
        "profile": {
            "label": "TC-03", "mode": "balanced",
            "genre": "pop", "mood": "happy", "target_energy": 0.5,
        },
        "checks": [
            ("ENERGY_DEAD_ZONE warning present",   lambda r: any("ENERGY_DEAD_ZONE" in w for w in r["report"]["warnings"])),
            ("confidence drops below 1.0",         lambda r: r["report"]["confidence"] < 1.0),
        ],
    },
    {
        "id":   "TC-04",
        "name": "Genre bubble flagged — rock has only 1 song",
        "profile": {
            "label": "TC-04", "mode": "balanced",
            "genre": "rock", "mood": "intense", "target_energy": 0.9,
        },
        "checks": [
            ("GENRE_BUBBLE warning present",  lambda r: any("GENRE_BUBBLE" in w for w in r["report"]["warnings"])),
            ("confidence == 0.8",             lambda r: r["report"]["confidence"] == 0.8),
        ],
    },
    {
        "id":   "TC-05",
        "name": "Multi-song genre — lofi (3 songs) passes cleanly",
        "profile": {
            "label": "TC-05", "mode": "balanced",
            "genre": "lofi", "mood": "chill", "target_energy": 0.35,
        },
        "checks": [
            ("confidence == 1.0",          lambda r: r["report"]["confidence"] == 1.0),
            ("zero warnings",              lambda r: r["report"]["warnings"] == []),
            ("top result is lofi",         lambda r: r["results"][0][0]["genre"] == "lofi"),
            ("single attempt — no retry",  lambda r: r["attempts"] == 1),
        ],
    },
    {
        "id":   "TC-06",
        "name": "Score integrity — all returned scores are non-negative",
        "profile": {
            "label": "TC-06", "mode": "balanced",
            "genre": "pop", "mood": "happy", "target_energy": 0.8,
        },
        "checks": [
            ("all scores ≥ 0",   lambda r: all(s >= 0 for _, s, _ in r["results"])),
            ("exactly 5 results", lambda r: len(r["results"]) == 5),
        ],
    },
    {
        "id":   "TC-07",
        "name": "Top result holds the maximum original score",
        "profile": {
            "label": "TC-07", "mode": "balanced",
            "genre": "lofi", "mood": "chill", "target_energy": 0.35,
        },
        "checks": [
            ("results[0] score is the maximum",
             lambda r: r["results"][0][1] == max(s for _, s, _ in r["results"])),
        ],
    },
    {
        "id":   "TC-08",
        "name": "Custom k is respected",
        "profile": {
            "label": "TC-08", "mode": "balanced",
            "genre": "pop", "mood": "happy", "target_energy": 0.8,
        },
        "top_k": 3,
        "checks": [
            ("k=3 returns exactly 3 results", lambda r: len(r["results"]) == 3),
        ],
    },
    {
        "id":   "TC-09",
        "name": "Direct run — fallback_reason is None when no retry needed",
        "profile": {
            "label": "TC-09", "mode": "balanced",
            "genre": "pop", "mood": "happy", "target_energy": 0.9,
        },
        "checks": [
            ("fallback_reason is None",  lambda r: r["fallback_reason"] is None),
            ("mode_used matches input",  lambda r: r["mode_used"] == "balanced"),
        ],
    },
    {
        "id":   "TC-10",
        "name": "Trace contains at least PLAN, ACT, CHECK, DONE steps",
        "profile": {
            "label": "TC-10", "mode": "balanced",
            "genre": "pop", "mood": "happy", "target_energy": 0.9,
        },
        "checks": [
            ("trace has PLAN step",   lambda r: any(s["tag"] == "PLAN"  for s in r["trace"])),
            ("trace has ACT step",    lambda r: any(s["tag"] == "ACT"   for s in r["trace"])),
            ("trace has CHECK step",  lambda r: any(s["tag"] == "CHECK" for s in r["trace"])),
            ("trace has DONE step",   lambda r: any(s["tag"] == "DONE"  for s in r["trace"])),
        ],
    },
]

# ── runner ─────────────────────────────────────────────────────────────────────

def run_evaluation() -> bool:
    songs   = load_songs("data/songs.csv")
    checker = ReliabilityChecker(songs)
    agent   = RecommenderAgent(songs, checker)

    total_checks = sum(len(tc["checks"]) for tc in TEST_CASES)
    passed = 0
    failed = 0
    confidences = []

    print()
    print("=" * 66)
    print("  VibeMatch — Evaluation Harness")
    print(f"  {len(TEST_CASES)} test cases  ·  {total_checks} checks")
    print("=" * 66)
    print()

    for tc in TEST_CASES:
        top_k  = tc.get("top_k", 5)
        result = agent.run(tc["profile"], top_k=top_k, verbose=False)
        confidences.append(result["report"]["confidence"])

        tc_passed = 0
        tc_failed = 0

        print(f"[{tc['id']}] {tc['name']}")
        for check_name, check_fn in tc["checks"]:
            try:
                ok = bool(check_fn(result))
            except Exception as exc:
                ok = False
                check_name = f"{check_name}  (ERROR: {exc})"

            mark   = "+" if ok else "x"
            status = "PASS" if ok else "FAIL"
            print(f"        [{mark}] {status:<4}  {check_name}")

            if ok:
                passed += 1
                tc_passed += 1
            else:
                failed += 1
                tc_failed += 1

        tc_total  = tc_passed + tc_failed
        tc_conf   = result["report"]["confidence"]
        tc_status = "all passed" if tc_failed == 0 else f"{tc_failed} failed"
        print(f"             confidence={tc_conf:.2f}  {tc_passed}/{tc_total} checks  {tc_status}")
        print()

    total   = passed + failed
    pct     = round(passed / total * 100, 1) if total else 0.0
    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else 0.0

    print("=" * 66)
    print(f"  Results          : {passed} / {total} checks passed  ({pct}%)")
    print(f"  Avg confidence   : {avg_conf:.2f}")
    print(f"  Test cases run   : {len(TEST_CASES)}")
    print(f"  Confidence threshold used : {CONFIDENCE_THRESHOLD}")
    print("=" * 66)
    print()

    return failed == 0


if __name__ == "__main__":
    ok = run_evaluation()
    sys.exit(0 if ok else 1)
