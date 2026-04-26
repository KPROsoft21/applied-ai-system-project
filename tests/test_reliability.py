from src.reliability import ReliabilityChecker


# ── shared helpers ────────────────────────────────────────────────────────────

def _catalog():
    # pop has 2 songs (no bubble), lofi has 1 (bubble), jazz absent (ghost genre)
    return [
        {"genre": "pop",  "mood": "happy",   "energy": 0.8},
        {"genre": "pop",  "mood": "intense",  "energy": 0.9},
        {"genre": "lofi", "mood": "chill",    "energy": 0.3},
    ]


def _result(score=3.0, score2=2.0):
    s1 = {"genre": "pop",  "title": "Song A", "artist": "Artist A"}
    s2 = {"genre": "lofi", "title": "Song B", "artist": "Artist B"}
    return [(s1, score, "reason1"), (s2, score2, "reason2")]


def _has_warning(report: dict, key: str) -> bool:
    return any(key in w for w in report["warnings"])


# ── GHOST_GENRE ───────────────────────────────────────────────────────────────

def test_ghost_genre_detected():
    checker = ReliabilityChecker(_catalog())
    report = checker.check({"genre": "jazz", "mood": "happy", "target_energy": 0.9}, _result())
    assert _has_warning(report, "GHOST_GENRE")


def test_valid_genre_no_ghost_warning():
    checker = ReliabilityChecker(_catalog())
    report = checker.check({"genre": "pop", "mood": "happy", "target_energy": 0.9}, _result())
    assert not _has_warning(report, "GHOST_GENRE")


# ── ENERGY_DEAD_ZONE ──────────────────────────────────────────────────────────

def test_energy_dead_zone_detected():
    # 0.5 falls inside the 0.46–0.71 catalog gap
    checker = ReliabilityChecker(_catalog())
    report = checker.check({"genre": "pop", "mood": "happy", "target_energy": 0.5}, _result())
    assert _has_warning(report, "ENERGY_DEAD_ZONE")


def test_energy_outside_dead_zone_no_warning():
    checker = ReliabilityChecker(_catalog())
    report = checker.check({"genre": "pop", "mood": "happy", "target_energy": 0.9}, _result())
    assert not _has_warning(report, "ENERGY_DEAD_ZONE")


# ── LOW_CONFIDENCE ────────────────────────────────────────────────────────────

def test_low_confidence_detected_when_top_score_below_threshold():
    checker = ReliabilityChecker(_catalog())
    weak = _result(score=0.5, score2=0.3)
    report = checker.check({"genre": "pop", "mood": "happy", "target_energy": 0.9}, weak)
    assert _has_warning(report, "LOW_CONFIDENCE")


def test_no_low_confidence_when_top_score_adequate():
    checker = ReliabilityChecker(_catalog())
    report = checker.check({"genre": "pop", "mood": "happy", "target_energy": 0.9}, _result(score=2.0))
    assert not _has_warning(report, "LOW_CONFIDENCE")


# ── NEGATIVE_SCORE ────────────────────────────────────────────────────────────

def test_negative_score_detected():
    checker = ReliabilityChecker(_catalog())
    bad = [( {"genre": "pop", "title": "T", "artist": "A"}, -1.0, "r")]
    report = checker.check({"genre": "pop", "mood": "happy", "target_energy": 0.9}, bad)
    assert _has_warning(report, "NEGATIVE_SCORE")


# ── GENRE_BUBBLE ──────────────────────────────────────────────────────────────

def test_genre_bubble_detected_for_single_song_genre():
    checker = ReliabilityChecker(_catalog())
    report = checker.check({"genre": "lofi", "mood": "chill", "target_energy": 0.3}, _result())
    assert _has_warning(report, "GENRE_BUBBLE")


def test_no_bubble_for_genre_with_multiple_songs():
    checker = ReliabilityChecker(_catalog())
    report = checker.check({"genre": "pop", "mood": "happy", "target_energy": 0.9}, _result())
    assert not _has_warning(report, "GENRE_BUBBLE")


# ── confidence formula ────────────────────────────────────────────────────────

def test_confidence_formula_decreases_per_warning():
    checker = ReliabilityChecker(_catalog())
    report = checker.check({"genre": "jazz", "mood": "happy", "target_energy": 0.5}, _result(score=0.5))
    expected = round(max(0.0, 1.0 - len(report["warnings"]) * 0.2), 2)
    assert report["confidence"] == expected


def test_all_checks_pass_gives_confidence_1():
    # pop has 2 songs, happy mood exists, energy 0.9 outside dead zone,
    # scores positive and unequal, top score >= 1.0
    checker = ReliabilityChecker(_catalog())
    report = checker.check({"genre": "pop", "mood": "happy", "target_energy": 0.9}, _result())
    assert report["confidence"] == 1.0
    assert report["warnings"] == []


# ── summary stats ─────────────────────────────────────────────────────────────

def test_summary_tracks_total_runs():
    checker = ReliabilityChecker(_catalog())
    good = _result()
    prefs = {"genre": "pop", "mood": "happy", "target_energy": 0.9}
    checker.check(prefs, good)
    checker.check(prefs, good)
    checker.check(prefs, good)
    assert checker.summary()["total_runs"] == 3


def test_summary_counts_perfect_runs():
    checker = ReliabilityChecker(_catalog())
    prefs = {"genre": "pop", "mood": "happy", "target_energy": 0.9}
    checker.check(prefs, _result())           # perfect → confidence 1.0
    checker.check({"genre": "jazz", "mood": "happy", "target_energy": 0.5}, _result(0.4))  # warnings
    assert checker.summary()["perfect_runs"] == 1


def test_summary_warning_counts_accumulate():
    checker = ReliabilityChecker(_catalog())
    ghost_prefs = {"genre": "jazz", "mood": "happy", "target_energy": 0.9}
    checker.check(ghost_prefs, _result())
    checker.check(ghost_prefs, _result())
    assert checker.summary()["warning_counts"].get("GHOST_GENRE", 0) == 2
