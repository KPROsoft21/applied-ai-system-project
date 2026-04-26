import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Challenge 2 — Scoring modes (Strategy pattern)
# Each mode is a dict of base weights for the three core signals.
# The max base score varies by mode; bonuses from new features are additive.
# ---------------------------------------------------------------------------
SCORING_MODES: Dict[str, Dict] = {
    "balanced": {
        "genre":       1.0,
        "mood":        1.0,
        "energy":      2.0,
        "description": "Balanced — moderate emphasis on all three signals",
        "base_max":    4.0,
    },
    "genre_first": {
        "genre":       3.0,
        "mood":        1.0,
        "energy":      1.0,
        "description": "Genre-First — strongly prefers exact genre matches",
        "base_max":    5.0,
    },
    "mood_first": {
        "genre":       1.0,
        "mood":        3.0,
        "energy":      1.0,
        "description": "Mood-First — strongly prefers mood matches over genre",
        "base_max":    5.0,
    },
    "energy_focused": {
        "genre":       0.5,
        "mood":        0.5,
        "energy":      4.0,
        "description": "Energy-Focused — ranks almost entirely by energy proximity",
        "base_max":    5.0,
    },
}

# Ordinal mapping for decade proximity scoring (Challenge 1)
DECADE_ORDER: Dict[str, int] = {
    "1960s": 0, "1970s": 1, "1980s": 2,
    "1990s": 3, "2000s": 4, "2010s": 5, "2020s": 6,
}

# Max bonus points available from the five new features
# popularity: 0.50  decade: 0.50  mood_tags: 1.00  instrumental: 0.25  subgenre: 0.50
BONUS_MAX = 2.75


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float
    # Challenge 1 — new features (defaults keep existing tests passing)
    popularity: int = 50
    release_decade: str = "2020s"
    mood_tags: str = ""        # pipe-separated, e.g. "happy|uplifting|summery"
    instrumental: int = 0      # 1 = no vocals, 0 = has vocals
    subgenre: str = ""


@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


# ---------------------------------------------------------------------------
# OOP Recommender (required by tests)
# ---------------------------------------------------------------------------
class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5,
                  mode: str = "balanced") -> List[Song]:
        """Return top-k Song objects ranked by score against the given UserProfile."""
        user_prefs = {
            "genre":         user.favorite_genre,
            "mood":          user.favorite_mood,
            "target_energy": user.target_energy,
        }
        scored = sorted(
            [(song, score_song(user_prefs, vars(song), mode=mode)[0])
             for song in self.songs],
            key=lambda x: x[1],
            reverse=True,
        )
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song,
                               mode: str = "balanced") -> str:
        """Return a plain-language explanation of why song matched the user profile."""
        user_prefs = {
            "genre":         user.favorite_genre,
            "mood":          user.favorite_mood,
            "target_energy": user.target_energy,
        }
        _, reasons = score_song(user_prefs, vars(song), mode=mode)
        return "; ".join(reasons)


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------
def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    import csv
    songs = []
    logger.info("Loading songs from %s", csv_path)
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            songs.append({
                "id":             int(row["id"]),
                "title":          row["title"],
                "artist":         row["artist"],
                "genre":          row["genre"],
                "mood":           row["mood"],
                "energy":         float(row["energy"]),
                "tempo_bpm":      int(row["tempo_bpm"]),
                "valence":        float(row["valence"]),
                "danceability":   float(row["danceability"]),
                "acousticness":   float(row["acousticness"]),
                # Challenge 1 — new fields
                "popularity":     int(row.get("popularity", 50)),
                "release_decade": row.get("release_decade", "2020s"),
                "mood_tags":      row.get("mood_tags", ""),
                "instrumental":   int(row.get("instrumental", 0)),
                "subgenre":       row.get("subgenre", ""),
            })
    logger.debug("Loaded %d songs (%d fields)", len(songs), len(fieldnames))
    print(f"Loaded {len(songs)} songs  ({len(fieldnames)} fields each)")
    return songs


# ---------------------------------------------------------------------------
# Challenge 1 + 2 — Scoring with five new features and mode-based weights
# ---------------------------------------------------------------------------
def score_song(user_prefs: Dict, song: Dict,
               mode: str = "balanced") -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.

    Base scoring (weights determined by `mode`):
      genre match    — mode["genre"]  pts for exact string match
      mood match     — mode["mood"]   pts for exact string match
      energy prox    — mode["energy"] × (1 − |song.energy − target_energy|)

    Bonus scoring (flat, independent of mode):
      +0.00–0.50  popularity proximity   0.5 × (1 − |song_pop − target| / 100)
      +0.00–0.50  release decade prox    0.5 × max(0, 1 − |decade_diff| / 3)
      +0.25/tag   mood tag overlap       0.25 per matching tag, capped at 1.0
      +0.25       instrumental match     exact match on wants_instrumental
      +0.50       subgenre match         exact string match

    Returns:
        (score, reasons) where reasons is a list of human-readable strings.
    """
    weights = SCORING_MODES.get(mode, SCORING_MODES["balanced"])
    score = 0.0
    reasons: List[str] = []

    # ── Base signals (mode-weighted) ─────────────────────────────────────────

    if song["genre"] == user_prefs.get("genre", ""):
        pts = weights["genre"]
        score += pts
        reasons.append(f"genre match: {song['genre']} (+{pts:.1f})")

    if song["mood"] == user_prefs.get("mood", ""):
        pts = weights["mood"]
        score += pts
        reasons.append(f"mood match: {song['mood']} (+{pts:.1f})")

    target_energy = user_prefs.get("target_energy", 0.5)
    energy_pts = round(weights["energy"] * (1.0 - abs(song["energy"] - target_energy)), 3)
    score += energy_pts
    reasons.append(
        f"energy: {song['energy']} vs {target_energy} (+{energy_pts})"
    )

    # ── Challenge 1 bonus signals ─────────────────────────────────────────────

    # 1. Popularity proximity
    #    Math: 0.5 × (1 − |song_pop − user_target| / 100)
    #    Perfect match → +0.50; 50-point gap → +0.25; 100-point gap → +0.00
    pop_target = user_prefs.get("popularity_target")
    if pop_target is not None:
        song_pop = song.get("popularity", 50)
        pop_pts = round(0.5 * (1.0 - abs(song_pop - pop_target) / 100.0), 3)
        score += pop_pts
        reasons.append(f"popularity: {song_pop} vs target {pop_target} (+{pop_pts})")

    # 2. Release decade proximity
    #    Math: 0.5 × max(0, 1 − |decade_diff| / 3)
    #    Same decade → +0.50; 1 off → +0.33; 2 off → +0.17; 3+ off → +0.00
    preferred_decade = user_prefs.get("preferred_decade")
    if preferred_decade and preferred_decade in DECADE_ORDER:
        song_decade = song.get("release_decade", "2020s")
        if song_decade in DECADE_ORDER:
            diff = abs(DECADE_ORDER[song_decade] - DECADE_ORDER[preferred_decade])
            decade_pts = round(0.5 * max(0.0, 1.0 - diff / 3.0), 3)
            score += decade_pts
            reasons.append(f"decade: {song_decade} vs {preferred_decade} (+{decade_pts})")

    # 3. Mood tag overlap
    #    Math: 0.25 per matching tag, capped at 1.0
    #    Granular vibe tags that go beyond the single mood label.
    preferred_tags = user_prefs.get("preferred_mood_tags", [])
    if preferred_tags:
        song_tags = {t for t in song.get("mood_tags", "").split("|") if t}
        matched = [t for t in preferred_tags if t in song_tags]
        tag_pts = round(min(len(matched) * 0.25, 1.0), 3)
        score += tag_pts
        if tag_pts > 0:
            reasons.append(f"mood tags {matched} (+{tag_pts})")

    # 4. Instrumental preference
    #    Math: binary — +0.25 if preference matches, +0.0 if not
    wants_instrumental = user_prefs.get("wants_instrumental")
    if wants_instrumental is not None:
        song_instr = bool(song.get("instrumental", 0))
        if song_instr == wants_instrumental:
            score += 0.25
            label = "instrumental" if wants_instrumental else "has vocals"
            reasons.append(f"instrumental pref: {label} (+0.25)")

    # 5. Subgenre match
    #    Math: binary — +0.50 for exact string match, +0.00 otherwise
    preferred_subgenre = user_prefs.get("preferred_subgenre")
    if preferred_subgenre:
        if song.get("subgenre", "") == preferred_subgenre:
            score += 0.5
            reasons.append(f"subgenre match: {preferred_subgenre} (+0.50)")

    logger.debug(
        "score_song genre=%s mood=%s energy=%.2f → %.3f",
        song.get("genre"), song.get("mood"), song.get("energy", 0), score,
    )
    return round(score, 3), reasons


# ---------------------------------------------------------------------------
# Challenge 3 — Diversity and fairness reranking
# ---------------------------------------------------------------------------
def diversity_rerank(
    scored: List[Tuple[Dict, float, str]],
    k: int,
    artist_penalty: float = 0.5,
    genre_penalty: float = 0.3,
) -> List[Tuple[Dict, float, str]]:
    """
    Greedy top-k selection with artist and genre diversity penalties.

    For each open slot, each remaining candidate's score is adjusted:
      - Repeat artist already in results → subtract artist_penalty
      - Genre appears N≥2 times already  → subtract genre_penalty × N

    The base score stored in the returned tuple is the ORIGINAL score
    (not the penalised one), so displayed scores remain interpretable.
    Penalty notes are appended to the explanation string.
    """
    logger.debug("diversity_rerank: selecting %d from %d candidates", k, len(scored))
    selected: List[Tuple[Dict, float, str]] = []
    remaining = list(scored)

    while len(selected) < k and remaining:
        selected_artists = [s[0]["artist"] for s in selected]
        selected_genres  = [s[0]["genre"]  for s in selected]

        adjusted = []
        for song, base_score, explanation in remaining:
            adj = base_score
            penalty_notes: List[str] = []

            if song["artist"] in selected_artists:
                adj -= artist_penalty
                penalty_notes.append(f"repeat artist (−{artist_penalty})")

            genre_count = selected_genres.count(song["genre"])
            if genre_count >= 2:
                penalty = round(genre_penalty * genre_count, 2)
                adj -= penalty
                penalty_notes.append(f"genre ×{genre_count} (−{penalty})")

            full_expl = (
                explanation + "  ⚠ diversity: " + ", ".join(penalty_notes)
                if penalty_notes else explanation
            )
            adjusted.append((song, adj, full_expl, base_score))

        adjusted.sort(key=lambda x: x[1], reverse=True)
        best_song, _, best_expl, best_base = adjusted[0]
        selected.append((best_song, best_base, best_expl))
        remaining = [r for r in remaining if r[0]["id"] != best_song["id"]]

    return selected


# ---------------------------------------------------------------------------
# Functional entry point
# ---------------------------------------------------------------------------
def recommend_songs(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    mode: str = "balanced",
    diversity: bool = True,
) -> List[Tuple[Dict, float, str]]:
    """
    Score every song, sort highest-to-lowest, optionally apply diversity
    reranking, and return the top k results.

    Args:
        user_prefs : preference dict (see score_song for recognised keys)
        songs      : list of song dicts from load_songs()
        k          : number of results to return
        mode       : key from SCORING_MODES ("balanced", "genre_first", etc.)
        diversity  : if True, apply artist/genre diversity penalty

    Returns:
        List of (song_dict, score, explanation) tuples, length <= k.
    """
    logger.info("recommend_songs: %d songs, mode=%s, diversity=%s", len(songs), mode, diversity)
    scored = [
        (song, score, ", ".join(reasons))
        for song in songs
        for score, reasons in [score_song(user_prefs, song, mode=mode)]
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    if scored:
        logger.debug("top result: '%s' score=%.3f", scored[0][0].get("title", "?"), scored[0][1])

    if diversity:
        return diversity_rerank(scored, k)
    return scored[:k]
