"""
Music Recommender Simulation — main runner.

Challenges implemented:
  1. Five new song features scored with explicit math rules.
  2. Four scoring modes: balanced, genre_first, mood_first, energy_focused.
  3. Diversity penalty: repeat artists and genre saturation are penalised.
  4. Tabulate-based summary table for every profile's top-5.
  5. Reliability/Testing System: ReliabilityChecker validates every result set.
  6. Agentic Workflow: RecommenderAgent plans, acts, checks, and retries on
     low confidence before results are shown.
"""

import logging
from tabulate import tabulate
from src.recommender import load_songs, SCORING_MODES
from src.reliability import ReliabilityChecker
from src.agent import RecommenderAgent

# ── logging setup ────────────────────────────────────────────────────────────

def _configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    fh = logging.FileHandler("recommender.log", mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    ))
    root.addHandler(fh)
    ch = logging.StreamHandler()
    ch.setLevel(logging.WARNING)
    ch.setFormatter(logging.Formatter("%(levelname)s  %(message)s"))
    root.addHandler(ch)


# ── helpers ──────────────────────────────────────────────────────────────────

def _max_score(mode: str, user_prefs: dict) -> float:
    """Return the theoretical maximum score for a given mode + pref set."""
    base = SCORING_MODES.get(mode, SCORING_MODES["balanced"])["base_max"]
    bonus = 0.0
    if user_prefs.get("popularity_target") is not None: bonus += 0.50
    if user_prefs.get("preferred_decade"):               bonus += 0.50
    if user_prefs.get("preferred_mood_tags"):            bonus += 1.00
    if user_prefs.get("wants_instrumental") is not None: bonus += 0.25
    if user_prefs.get("preferred_subgenre"):             bonus += 0.50
    return base + bonus

# ── Standard profiles ─────────────────────────────────────────────────────────

HIGH_ENERGY_POP = {
    "label":               "High-Energy Pop",
    "mode":                "genre_first",
    "genre":               "pop",
    "mood":                "happy",
    "target_energy":       0.9,
    "popularity_target":   80,
    "preferred_decade":    "2020s",
    "preferred_mood_tags": ["happy", "uplifting", "energetic"],
    "wants_instrumental":  False,
    "preferred_subgenre":  "dance pop",
}

CHILL_LOFI = {
    "label":               "Chill Lofi",
    "mode":                "mood_first",
    "genre":               "lofi",
    "mood":                "chill",
    "target_energy":       0.25,
    "popularity_target":   60,
    "preferred_decade":    "2020s",
    "preferred_mood_tags": ["chill", "focused", "peaceful"],
    "wants_instrumental":  True,
    "preferred_subgenre":  "lo-fi hip-hop",
}

DEEP_INTENSE_ROCK = {
    "label":               "Deep Intense Rock",
    "mode":                "energy_focused",
    "genre":               "rock",
    "mood":                "intense",
    "target_energy":       0.92,
    "popularity_target":   75,
    "preferred_decade":    "2010s",
    "preferred_mood_tags": ["intense", "aggressive", "powerful"],
    "wants_instrumental":  False,
    "preferred_subgenre":  "alternative rock",
}

# ── Adversarial / edge-case profiles ─────────────────────────────────────────

CONFLICT_ENERGY_SAD = {
    "label":               "[EDGE] Conflicting: high energy + sad mood",
    "mode":                "balanced",
    "genre":               "r&b",
    "mood":                "sad",
    "target_energy":       0.9,
    "preferred_mood_tags": ["sad", "heartbreak"],
    "wants_instrumental":  False,
}

GHOST_GENRE = {
    "label":               "[EDGE] Ghost genre (no catalog match)",
    "mode":                "balanced",
    "genre":               "bossa nova",
    "mood":                "relaxed",
    "target_energy":       0.5,
    "preferred_mood_tags": ["relaxed", "cozy"],
}

NEUTRAL_ENERGY = {
    "label":               "[EDGE] Neutral energy (0.5), no dominant genre",
    "mode":                "mood_first",
    "genre":               "ambient",
    "mood":                "focused",
    "target_energy":       0.5,
    "preferred_mood_tags": ["focused", "calm"],
    "wants_instrumental":  True,
}

QUIET_ANGRY = {
    "label":               "[EDGE] Quiet angry (energy=0.05, mood=angry)",
    "mode":                "energy_focused",
    "genre":               "metal",
    "mood":                "angry",
    "target_energy":       0.05,
    "preferred_mood_tags": ["angry", "aggressive"],
}

ALL_PROFILES = [
    HIGH_ENERGY_POP,
    CHILL_LOFI,
    DEEP_INTENSE_ROCK,
    CONFLICT_ENERGY_SAD,
    GHOST_GENRE,
    NEUTRAL_ENERGY,
    QUIET_ANGRY,
]

# ── display ───────────────────────────────────────────────────────────────────

def print_results(profile: dict, agent_result: dict) -> None:
    recommendations = agent_result["results"]
    report          = agent_result["report"]
    mode_used       = agent_result["mode_used"]
    attempts        = agent_result["attempts"]
    fallback_reason = agent_result["fallback_reason"]

    label     = profile["label"]
    mode_desc = SCORING_MODES.get(mode_used, {}).get("description", mode_used)

    prefs_for_max = {k: v for k, v in profile.items()
                     if k not in ("label", "mode")}
    max_score = _max_score(mode_used, prefs_for_max)

    print()
    print("=" * 72)
    print(f"  {label}")
    print(f"  mode: {mode_used}  ({mode_desc})")
    print(f"  genre={profile.get('genre')}  "
          f"mood={profile.get('mood')}  "
          f"energy={profile.get('target_energy')}  "
          f"max_score={max_score:.2f}")
    print("=" * 72)

    rows = []
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        parts = explanation.split(", ")
        reason_lines = "\n".join(f"• {p}" for p in parts)
        rows.append([
            f"#{rank}",
            song["title"],
            song["artist"],
            song["genre"],
            song["mood"],
            song.get("subgenre", ""),
            song.get("popularity", "—"),
            song.get("release_decade", "—"),
            f"{score:.3f} / {max_score:.2f}",
            reason_lines,
        ])

    headers = [
        "#", "Title", "Artist", "Genre", "Mood",
        "Subgenre", "Pop", "Era", "Score", "Reasons",
    ]
    print(tabulate(rows, headers=headers, tablefmt="rounded_outline",
                   maxcolwidths=[None, 22, 18, 12, 10, 20, 4, 6, 14, 42]))

    # Agent status line
    if attempts == 1:
        print(f"  Agent        attempts=1  mode={mode_used}  (direct)")
    else:
        print(f"  Agent        attempts=2  mode={mode_used}  "
              f"[fallback triggered: {fallback_reason}]")

    # Reliability status line
    confidence = report["confidence"]
    warnings   = report["warnings"]
    passed     = report["passed"]
    if warnings:
        print(f"  Reliability  confidence={confidence:.2f}  "
              f"passed={len(passed)}  warnings={len(warnings)}")
        for w in warnings:
            print(f"  [WARN] {w}")
    else:
        print(f"  Reliability  confidence={confidence:.2f}  all checks passed")
    print()


# ── Runner ────────────────────────────────────────────────────────────────────

def main() -> None:
    _configure_logging()
    songs   = load_songs("data/songs.csv")
    checker = ReliabilityChecker(songs)
    agent   = RecommenderAgent(songs, checker)

    for profile in ALL_PROFILES:
        agent_result = agent.run(profile, top_k=5)
        print_results(profile, agent_result)

    summary = checker.summary()
    print("=" * 72)
    print(f"  Reliability Summary — {summary['total_runs']} profiles evaluated")
    print(f"  Average confidence : {summary['avg_confidence']:.2f}")
    print(f"  Perfect runs       : {summary['perfect_runs']} / {summary['total_runs']}")
    wc = summary["warning_counts"]
    if wc:
        print("  Warning breakdown  :")
        for key, count in wc.items():
            print(f"    {key:<20} : {count}")
    else:
        print("  No warnings detected")
    print("  Full log saved to  : recommender.log")
    print("=" * 72)
    print()
    print("=" * 72)
    print("  Simulation complete.")
    print("=" * 72)
    print()


if __name__ == "__main__":
    main()
