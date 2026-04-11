"""
Command line runner for the Music Recommender Simulation.

Runs three standard user profiles and four adversarial/edge-case profiles
to evaluate scoring logic and surface unexpected behaviour.

Scoring recap (max 4.0 pts per song):
  +2.0  exact genre match
  +1.0  exact mood match
  +1.0  energy proximity: 1 - |song.energy - target_energy|
"""

from src.recommender import load_songs, recommend_songs


# ---------------------------------------------------------------------------
# Standard profiles
# ---------------------------------------------------------------------------
HIGH_ENERGY_POP = {
    "label":         "High-Energy Pop",
    "genre":         "pop",
    "mood":          "happy",
    "target_energy": 0.9,
}

CHILL_LOFI = {
    "label":         "Chill Lofi",
    "genre":         "lofi",
    "mood":          "chill",
    "target_energy": 0.25,
}

DEEP_INTENSE_ROCK = {
    "label":         "Deep Intense Rock",
    "genre":         "rock",
    "mood":          "intense",
    "target_energy": 0.92,
}

# ---------------------------------------------------------------------------
# Adversarial / edge-case profiles
# (designed to probe the scoring logic for surprising behaviour)
# ---------------------------------------------------------------------------

# A: High energy + sad mood — the two signals pull in opposite directions.
#    Does a genuinely sad low-energy song outscore a high-energy song that
#    only matches energy?
CONFLICT_ENERGY_SAD = {
    "label":         "[EDGE] Conflicting: high energy + sad mood",
    "genre":         "r&b",
    "mood":          "sad",
    "target_energy": 0.9,
}

# B: Genre that does not exist in the catalog — zero genre points for every
#    song, so mood + energy are the only differentiators.
GHOST_GENRE = {
    "label":         "[EDGE] Ghost genre (no catalog match)",
    "genre":         "bossa nova",
    "mood":          "relaxed",
    "target_energy": 0.5,
}

# C: Perfect-middle energy (0.5) with no genre/mood match likely — rewards
#    songs right at the midpoint; reveals whether mid-energy songs cluster.
NEUTRAL_ENERGY = {
    "label":         "[EDGE] Neutral energy (0.5), no dominant genre",
    "genre":         "ambient",
    "mood":          "focused",
    "target_energy": 0.5,
}

# D: Extreme low energy + angry mood — tests the floor of the energy scale
#    and whether the system surfaces a quiet-but-angry song or an accidental
#    high-energy hit because genre points dominate.
QUIET_ANGRY = {
    "label":         "[EDGE] Quiet angry (energy=0.05, mood=angry)",
    "genre":         "metal",
    "mood":          "angry",
    "target_energy": 0.05,
}

# ---------------------------------------------------------------------------

ALL_PROFILES = [
    HIGH_ENERGY_POP,
    CHILL_LOFI,
    DEEP_INTENSE_ROCK,
    CONFLICT_ENERGY_SAD,
    GHOST_GENRE,
    NEUTRAL_ENERGY,
    QUIET_ANGRY,
]


def print_results(user_prefs: dict, recommendations: list) -> None:
    label = user_prefs["label"]
    print()
    print("=" * 60)
    print(f"  {label}")
    print(f"  genre={user_prefs['genre']}  "
          f"mood={user_prefs['mood']}  "
          f"energy={user_prefs['target_energy']}")
    print("=" * 60)
    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n  #{rank}  {song['title']}  —  {song['artist']}")
        print(f"       Genre: {song['genre']:14s}  Mood: {song['mood']}")
        print(f"       Score: {score:.3f} / 4.000")
        for reason in explanation.split(", "):
            print(f"         • {reason}")
    print()


def main() -> None:
    songs = load_songs("data/songs.csv")

    for profile in ALL_PROFILES:
        # score_song / recommend_songs only read genre / mood / target_energy
        prefs = {k: v for k, v in profile.items() if k != "label"}
        recommendations = recommend_songs(prefs, songs, k=5)
        print_results(profile, recommendations)

    print("=" * 60)
    print("  Simulation complete.")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
