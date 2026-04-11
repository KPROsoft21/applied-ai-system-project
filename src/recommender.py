from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

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

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top-k Song objects ranked by score against the given UserProfile."""
        user_prefs = {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "target_energy": user.target_energy,
        }
        scored = sorted(
            [(song, score_song(user_prefs, vars(song))[0]) for song in self.songs],
            key=lambda x: x[1],
            reverse=True,
        )
        return [song for song, _ in scored[:k]]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a plain-language string explaining why song matched the given user profile."""
        user_prefs = {
            "genre": user.favorite_genre,
            "mood": user.favorite_mood,
            "target_energy": user.target_energy,
        }
        _, reasons = score_song(user_prefs, vars(song))
        return "; ".join(reasons)

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file.
    Required by src/main.py
    """
    import csv
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id":           int(row["id"]),
                "title":        row["title"],
                "artist":       row["artist"],
                "genre":        row["genre"],
                "mood":         row["mood"],
                "energy":       float(row["energy"]),
                "tempo_bpm":    int(row["tempo_bpm"]),
                "valence":      float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    print(f"Loaded songs: {len(songs)}")
    return songs

def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.
    Required by recommend_songs() and src/main.py

    Scoring recipe (max 4.0 points):
      +1.0  exact genre match      ← halved from 2.0 (weight-shift experiment)
      +1.0  exact mood match
      +2.0  energy proximity: 1 - |song.energy - user.target_energy|   ← doubled from 1.0

    Returns:
        (score, reasons) where reasons is a list of human-readable strings
        explaining every point awarded.
    """
    score = 0.0
    reasons = []

    # Genre match — halved to 1.0 to reduce genre dominance (weight-shift experiment)
    if song["genre"] == user_prefs.get("genre", ""):
        score += 1.0
        reasons.append(f"genre match: {song['genre']} (+1.0)")

    # Mood match — second priority; mood can cross genre lines
    if song["mood"] == user_prefs.get("mood", ""):
        score += 1.0
        reasons.append(f"mood match: {song['mood']} (+1.0)")

    # Energy proximity — doubled to 2.0 max to offset halved genre weight (weight-shift experiment)
    target_energy = user_prefs.get("target_energy", 0.5)
    energy_points = round(2.0 * (1.0 - abs(song["energy"] - target_energy)), 3)
    score += energy_points
    reasons.append(f"energy proximity: {song['energy']} vs target {target_energy} (+{energy_points})")

    return round(score, 3), reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Functional implementation of the recommendation logic.
    Required by src/main.py

    Scores every song in the catalog using score_song(), sorts the results
    from highest to lowest score, and returns the top k entries.

    Returns:
        List of (song_dict, score, explanation) tuples, length <= k.
    """
    scored = [
        (song, score, ", ".join(reasons))
        for song in songs
        for score, reasons in [score_song(user_prefs, song)]
    ]

    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
