import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

# The energy gap in songs.csv where no songs land.
_DEAD_ZONE_LOW  = 0.46
_DEAD_ZONE_HIGH = 0.71


class ReliabilityChecker:
    def __init__(self, songs: List[Dict]) -> None:
        self._genres: set = {s["genre"] for s in songs}
        self._moods:  set = {s["mood"]  for s in songs}
        self._genre_counts: Dict[str, int] = {}
        for s in songs:
            self._genre_counts[s["genre"]] = self._genre_counts.get(s["genre"], 0) + 1

        self._runs:           int             = 0
        self._confidence_sum: float           = 0.0
        self._perfect_runs:   int             = 0
        self._warning_counts: Dict[str, int]  = {}

    def check(self, user_prefs: Dict, results: list, label: str = "") -> Dict:
        warnings: List[str] = []
        passed:   List[str] = []

        genre         = user_prefs.get("genre", "")
        mood          = user_prefs.get("mood", "")
        target_energy = float(user_prefs.get("target_energy", 0.5))

        # 1. GHOST_GENRE
        if genre and genre not in self._genres:
            msg = f"GHOST_GENRE genre '{genre}' not in catalog — 0 genre points possible"
            warnings.append(msg)
            logger.warning("%s %s", label, msg)
        else:
            passed.append("GHOST_GENRE")
            logger.debug("%s GHOST_GENRE ok (genre '%s' in catalog)", label, genre)

        # 2. GHOST_MOOD
        if mood and mood not in self._moods:
            msg = f"GHOST_MOOD mood '{mood}' not in catalog — 0 mood points possible"
            warnings.append(msg)
            logger.warning("%s %s", label, msg)
        else:
            passed.append("GHOST_MOOD")
            logger.debug("%s GHOST_MOOD ok (mood '%s' in catalog)", label, mood)

        # 3. ENERGY_DEAD_ZONE
        if _DEAD_ZONE_LOW <= target_energy <= _DEAD_ZONE_HIGH:
            msg = (
                f"ENERGY_DEAD_ZONE target_energy={target_energy} "
                f"falls in {_DEAD_ZONE_LOW}-{_DEAD_ZONE_HIGH} gap where no catalog songs land"
            )
            warnings.append(msg)
            logger.warning("%s %s", label, msg)
        else:
            passed.append("ENERGY_DEAD_ZONE")
            logger.debug("%s ENERGY_DEAD_ZONE ok (%.2f outside gap)", label, target_energy)

        # 4. NEGATIVE_SCORE
        if results and any(score < 0 for _, score, *_ in results):
            msg = "NEGATIVE_SCORE one or more result scores are negative — possible scoring bug"
            warnings.append(msg)
            logger.warning("%s %s", label, msg)
        else:
            passed.append("NEGATIVE_SCORE")
            logger.debug("%s NEGATIVE_SCORE ok", label)

        # 5. LOW_CONFIDENCE
        top_score = results[0][1] if results else 0.0
        if top_score < 1.0:
            msg = f"LOW_CONFIDENCE top score={top_score:.3f} < 1.0 — no strong catalog match"
            warnings.append(msg)
            logger.warning("%s %s", label, msg)
        else:
            passed.append("LOW_CONFIDENCE")
            logger.debug("%s LOW_CONFIDENCE ok (top score=%.3f)", label, top_score)

        # 6. SCORE_TIE
        if len(results) >= 2 and results[0][1] == results[1][1]:
            msg = (
                f"SCORE_TIE top two results share score={results[0][1]:.3f} "
                "— ranking is arbitrary"
            )
            warnings.append(msg)
            logger.warning("%s %s", label, msg)
        else:
            passed.append("SCORE_TIE")
            logger.debug("%s SCORE_TIE ok", label)

        # 7. GENRE_BUBBLE
        genre_count = self._genre_counts.get(genre, 0)
        if genre and genre in self._genres and genre_count == 1:
            msg = (
                f"GENRE_BUBBLE genre '{genre}' has only 1 song "
                "— top-5 padded with off-genre results"
            )
            warnings.append(msg)
            logger.warning("%s %s", label, msg)
        else:
            passed.append("GENRE_BUBBLE")
            logger.debug("%s GENRE_BUBBLE ok (genre '%s' has %d songs)", label, genre, genre_count)

        confidence = round(max(0.0, 1.0 - len(warnings) * 0.2), 2)

        self._runs           += 1
        self._confidence_sum += confidence
        if confidence == 1.0:
            self._perfect_runs += 1
        for w in warnings:
            key = w.split()[0]
            self._warning_counts[key] = self._warning_counts.get(key, 0) + 1

        return {
            "confidence": confidence,
            "warnings":   warnings,
            "passed":     passed,
        }

    def summary(self) -> Dict:
        avg = round(self._confidence_sum / self._runs, 2) if self._runs else 0.0
        return {
            "total_runs":      self._runs,
            "avg_confidence":  avg,
            "warning_counts":  dict(self._warning_counts),
            "perfect_runs":    self._perfect_runs,
        }
