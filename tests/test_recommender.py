from src.recommender import Song, UserProfile, Recommender, score_song, recommend_songs, load_songs


# ── shared helpers ────────────────────────────────────────────────────────────

def make_small_recommender() -> Recommender:
    songs = [
        Song(
            id=1, title="Test Pop Track", artist="Test Artist",
            genre="pop", mood="happy", energy=0.8,
            tempo_bpm=120, valence=0.9, danceability=0.8, acousticness=0.2,
        ),
        Song(
            id=2, title="Chill Lofi Loop", artist="Test Artist",
            genre="lofi", mood="chill", energy=0.4,
            tempo_bpm=80, valence=0.6, danceability=0.5, acousticness=0.9,
        ),
    ]
    return Recommender(songs)


def _song(genre="pop", mood="happy", energy=0.8) -> dict:
    return {"genre": genre, "mood": mood, "energy": energy}


def _prefs(genre="pop", mood="happy", energy=0.8) -> dict:
    return {"genre": genre, "mood": mood, "target_energy": energy}


# ── original tests (unchanged) ────────────────────────────────────────────────

def test_recommend_returns_songs_sorted_by_score():
    user = UserProfile(
        favorite_genre="pop", favorite_mood="happy",
        target_energy=0.8, likes_acoustic=False,
    )
    rec = make_small_recommender()
    results = rec.recommend(user, k=2)
    assert len(results) == 2
    assert results[0].genre == "pop"
    assert results[0].mood == "happy"


def test_explain_recommendation_returns_non_empty_string():
    user = UserProfile(
        favorite_genre="pop", favorite_mood="happy",
        target_energy=0.8, likes_acoustic=False,
    )
    rec = make_small_recommender()
    explanation = rec.explain_recommendation(user, rec.songs[0])
    assert isinstance(explanation, str)
    assert explanation.strip() != ""


# ── score_song unit tests ─────────────────────────────────────────────────────

def test_score_song_genre_match_adds_points():
    # balanced: genre weight = 1.0; matching genre should appear in reasons
    score, reasons = score_song(_prefs("pop", "sad", 0.5), _song("pop", "sad", 0.5))
    assert score >= 1.0
    assert any("genre match" in r for r in reasons)


def test_score_song_no_genre_match_skips_points():
    # Different genre — no genre match line in reasons
    score, reasons = score_song(_prefs("pop", "happy", 0.8), _song("jazz", "happy", 0.8))
    assert not any("genre match" in r for r in reasons)


def test_score_song_perfect_base_match():
    # Genre + mood + energy=exact in balanced mode: 1.0 + 1.0 + 2.0 = 4.0
    score, _ = score_song(_prefs("pop", "happy", 0.8), _song("pop", "happy", 0.8))
    assert score == 4.0


def test_score_song_energy_closer_scores_higher():
    # Song at energy=0.85 should outscore song at energy=0.2 against target=0.8
    near_score, _ = score_song(_prefs("rock", "sad", 0.8), _song("rock", "sad", 0.85))
    far_score, _  = score_song(_prefs("rock", "sad", 0.8), _song("rock", "sad", 0.2))
    assert near_score > far_score


def test_recommend_songs_returns_exactly_k():
    songs = load_songs("data/songs.csv")
    results = recommend_songs(_prefs("pop", "happy", 0.8), songs, k=3)
    assert len(results) == 3


def test_recommend_songs_top_result_matches_genre_and_mood():
    # With genre=pop, mood=happy, the top result should be a pop+happy song
    songs = load_songs("data/songs.csv")
    results = recommend_songs(_prefs("pop", "happy", 0.8), songs, k=5)
    assert results[0][0]["genre"] == "pop"
    assert results[0][0]["mood"] == "happy"
