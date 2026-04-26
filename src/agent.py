"""
Agentic recommender loop: plan → act → check → (adapt → act → check).

Each step is printed to the console as it happens so the decision chain
is fully observable. Pass verbose=False to suppress step output (used by
the evaluation harness).
"""
import logging
from typing import Dict, List, Optional

from src.recommender import recommend_songs
from src.reliability import ReliabilityChecker

logger = logging.getLogger(__name__)

CONFIDENCE_THRESHOLD = 0.8

_FALLBACK_FOR: Dict[str, str] = {
    "GHOST_GENRE":      "mood_first",
    "ENERGY_DEAD_ZONE": "mood_first",
    "LOW_CONFIDENCE":   "energy_focused",
    "GENRE_BUBBLE":     "mood_first",
    "SCORE_TIE":        "genre_first",
}


def _step(tag: str, detail: str, verbose: bool) -> Dict:
    """Print one reasoning step and return it as a trace entry."""
    if verbose:
        print(f"  [{tag:<6}] {detail}")
    logger.debug("[agent-step] [%s] %s", tag, detail)
    return {"tag": tag, "detail": detail}


class RecommenderAgent:
    """
    Wraps the scoring engine with a self-correction loop.

    Each call to run() emits observable reasoning steps:
      [PLAN]   choose scoring strategy
      [ACT ]   run scoring engine
      [CHECK]  evaluate quality via ReliabilityChecker
      [ADAPT]  (if confidence < threshold) choose fallback mode
      [ACT ]   retry with fallback
      [CHECK]  re-evaluate
      [DONE]   report which attempt is returned and why
    """

    def __init__(self, songs: List[Dict], checker: ReliabilityChecker) -> None:
        self.songs   = songs
        self.checker = checker

    def run(self, profile: Dict, top_k: int = 5, verbose: bool = True) -> Dict:
        """
        Execute the agentic loop for one user profile.

        Returns:
            results         List[Tuple[Dict, float, str]]
            report          reliability quality report dict
            mode_used       scoring mode that produced the final results
            attempts        1 = direct, 2 = fallback triggered
            fallback_reason warning type that triggered fallback, or None
            trace           list of {tag, detail} dicts — one per reasoning step
        """
        label = profile.get("label", "")
        prefs = {k: v for k, v in profile.items() if k not in ("label", "mode")}
        trace: List[Dict] = []

        if verbose:
            print(f"\n  ── {label}")

        # ── PLAN ─────────────────────────────────────────────────────────────
        mode = profile.get("mode", "balanced")
        trace.append(_step("PLAN", f"mode={mode}  (user-specified)", verbose))
        logger.info("[agent] %s  plan: mode=%s", label, mode)

        # ── ACT ──────────────────────────────────────────────────────────────
        results = recommend_songs(prefs, self.songs, k=top_k, mode=mode)
        top_title = results[0][0].get("title", "?") if results else "—"
        top_score = results[0][1] if results else 0.0
        trace.append(_step(
            "ACT",
            f"scored {len(self.songs)} songs in {mode} mode"
            f"  →  top: '{top_title}' ({top_score:.2f})",
            verbose,
        ))
        logger.info("[agent] %s  act: top='%s' score=%.2f", label, top_title, top_score)

        # ── CHECK ─────────────────────────────────────────────────────────────
        report = self.checker.check(prefs, results, label=f"{label}[1]")
        conf   = report["confidence"]
        nwarn  = len(report["warnings"])
        outcome = (
            f"threshold met ({conf:.2f} ≥ {CONFIDENCE_THRESHOLD})"
            if conf >= CONFIDENCE_THRESHOLD
            else f"below threshold ({conf:.2f} < {CONFIDENCE_THRESHOLD})"
        )
        trace.append(_step(
            "CHECK",
            f"confidence={conf:.2f}  warnings={nwarn}  →  {outcome}",
            verbose,
        ))
        logger.info("[agent] %s  check: confidence=%.2f warnings=%d", label, conf, nwarn)

        if conf >= CONFIDENCE_THRESHOLD:
            trace.append(_step("DONE", f"returning attempt-1  mode={mode}", verbose))
            return {
                "results": results, "report": report, "mode_used": mode,
                "attempts": 1, "fallback_reason": None, "trace": trace,
            }

        # ── ADAPT ─────────────────────────────────────────────────────────────
        warning_types   = [w.split()[0] for w in report["warnings"]]
        fallback_reason: Optional[str] = next(
            (wt for wt in warning_types if wt in _FALLBACK_FOR), None
        )
        fallback_mode = _FALLBACK_FOR.get(fallback_reason, "mood_first")
        if fallback_mode == mode:
            fallback_mode = "energy_focused" if mode != "energy_focused" else "balanced"

        trace.append(_step(
            "ADAPT",
            f"trigger={fallback_reason}  →  retrying with mode={fallback_mode}",
            verbose,
        ))
        logger.warning(
            "[agent] %s  adapting: trigger=%s  fallback=%s",
            label, fallback_reason, fallback_mode,
        )

        # ── ACT (retry) ────────────────────────────────────────────────────────
        fallback_results = recommend_songs(prefs, self.songs, k=top_k, mode=fallback_mode)
        fb_title = fallback_results[0][0].get("title", "?") if fallback_results else "—"
        fb_score = fallback_results[0][1] if fallback_results else 0.0
        trace.append(_step(
            "ACT",
            f"scored {len(self.songs)} songs in {fallback_mode} mode (retry)"
            f"  →  top: '{fb_title}' ({fb_score:.2f})",
            verbose,
        ))

        # ── CHECK (retry) ──────────────────────────────────────────────────────
        fallback_report = self.checker.check(
            prefs, fallback_results, label=f"{label}[2]"
        )
        fb_conf  = fallback_report["confidence"]
        fb_nwarn = len(fallback_report["warnings"])
        trace.append(_step(
            "CHECK",
            f"confidence={fb_conf:.2f}  warnings={fb_nwarn}  (retry)",
            verbose,
        ))
        logger.info("[agent] %s  fallback check: confidence=%.2f", label, fb_conf)

        # ── DONE ─────────────────────────────────────────────────────────────
        if fb_conf >= conf:
            trace.append(_step(
                "DONE",
                f"fallback ({fb_conf:.2f}) ≥ attempt-1 ({conf:.2f})"
                f"  →  returning attempt-2  mode={fallback_mode}",
                verbose,
            ))
            return {
                "results": fallback_results, "report": fallback_report,
                "mode_used": fallback_mode, "attempts": 2,
                "fallback_reason": fallback_reason, "trace": trace,
            }

        trace.append(_step(
            "DONE",
            f"attempt-1 ({conf:.2f}) > fallback ({fb_conf:.2f})"
            f"  →  returning attempt-1  mode={mode}",
            verbose,
        ))
        return {
            "results": results, "report": report,
            "mode_used": mode, "attempts": 2,
            "fallback_reason": fallback_reason, "trace": trace,
        }
