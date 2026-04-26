from src.recommender import load_songs
from src.reliability import ReliabilityChecker
from src.agent import RecommenderAgent, CONFIDENCE_THRESHOLD


def _make_agent():
    songs   = load_songs("data/songs.csv")
    checker = ReliabilityChecker(songs)
    return RecommenderAgent(songs, checker), checker


# ── result structure ──────────────────────────────────────────────────────────

def test_agent_result_has_all_required_keys():
    agent, _ = _make_agent()
    result = agent.run(
        {"label": "test", "mode": "balanced",
         "genre": "pop", "mood": "happy", "target_energy": 0.8},
        top_k=5,
    )
    for key in ("results", "report", "mode_used", "attempts", "fallback_reason"):
        assert key in result


def test_agent_returns_exactly_top_k_results():
    agent, _ = _make_agent()
    result = agent.run(
        {"label": "test", "mode": "balanced",
         "genre": "pop", "mood": "happy", "target_energy": 0.8},
        top_k=3,
    )
    assert len(result["results"]) == 3


# ── direct path (no fallback) ─────────────────────────────────────────────────

def test_agent_single_attempt_when_confidence_adequate():
    # pop has 2 songs, happy mood exists, energy 0.9 outside dead zone
    # → 0 warnings → confidence 1.0 → no fallback
    agent, _ = _make_agent()
    result = agent.run(
        {"label": "test", "mode": "balanced",
         "genre": "pop", "mood": "happy", "target_energy": 0.9},
        top_k=5,
    )
    assert result["attempts"] == 1
    assert result["fallback_reason"] is None
    assert result["report"]["confidence"] >= CONFIDENCE_THRESHOLD


# ── fallback path ─────────────────────────────────────────────────────────────

def test_agent_triggers_fallback_on_ghost_genre():
    # bossa nova not in catalog + energy 0.5 in dead zone → confidence 0.6 < 0.8
    agent, _ = _make_agent()
    result = agent.run(
        {"label": "test", "mode": "balanced",
         "genre": "bossa nova", "mood": "relaxed", "target_energy": 0.5},
        top_k=5,
    )
    assert result["attempts"] == 2
    assert result["fallback_reason"] == "GHOST_GENRE"


def test_agent_fallback_uses_different_mode():
    # The fallback mode must differ from the original to avoid re-running
    # the same strategy twice
    agent, _ = _make_agent()
    original_mode = "balanced"
    result = agent.run(
        {"label": "test", "mode": original_mode,
         "genre": "bossa nova", "mood": "relaxed", "target_energy": 0.5},
        top_k=5,
    )
    assert result["mode_used"] != original_mode
