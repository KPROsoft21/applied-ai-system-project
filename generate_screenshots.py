"""
Generates terminal-style PNG screenshots for each user profile in the
Music Recommender Simulation and saves them to screenshots/.

Run from the project root:
    python generate_screenshots.py
"""

import io
import os
import sys
import contextlib
from PIL import Image, ImageDraw, ImageFont

# ── project path ────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from src.recommender import load_songs, recommend_songs

# ── profiles ────────────────────────────────────────────────────────────────
PROFILES = [
    {
        "label":         "High-Energy Pop",
        "genre":         "pop",
        "mood":          "happy",
        "target_energy": 0.9,
    },
    {
        "label":         "Chill Lofi",
        "genre":         "lofi",
        "mood":          "chill",
        "target_energy": 0.25,
    },
    {
        "label":         "Deep Intense Rock",
        "genre":         "rock",
        "mood":          "intense",
        "target_energy": 0.92,
    },
    {
        "label":         "[EDGE] Conflicting: high energy + sad mood",
        "genre":         "r&b",
        "mood":          "sad",
        "target_energy": 0.9,
    },
    {
        "label":         "[EDGE] Ghost genre (no catalog match)",
        "genre":         "bossa nova",
        "mood":          "relaxed",
        "target_energy": 0.5,
    },
    {
        "label":         "[EDGE] Neutral energy (0.5), no dominant genre",
        "genre":         "ambient",
        "mood":          "focused",
        "target_energy": 0.5,
    },
    {
        "label":         "[EDGE] Quiet angry (energy=0.05, mood=angry)",
        "genre":         "metal",
        "mood":          "angry",
        "target_energy": 0.05,
    },
]


# ── rendering helpers ────────────────────────────────────────────────────────
BG        = (30,  30,  30)   # terminal background
FG        = (204, 204, 204)  # default text
HEADER    = (97,  175, 239)  # profile header line (blue)
RANK      = (229, 192, 123)  # song title / rank line (gold)
META      = (152, 195, 121)  # genre/mood meta row (green)
SCORE     = (198, 120, 221)  # score row (purple)
BULLET    = (86,  182, 194)  # bullet points (cyan)
BORDER    = (70,  70,  70)   # separator lines
PAD_X     = 28
PAD_Y     = 22
LINE_GAP  = 6
FONT_SIZE = 16

FONT_PATH = "/System/Library/Fonts/Menlo.ttc"


def load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_PATH, size)


def classify_line(line: str):
    """Return (text, colour) for a line."""
    stripped = line.strip()
    if stripped.startswith("="):
        return line, BORDER
    if stripped.startswith("#"):
        return line, RANK
    if stripped.startswith("Genre:"):
        return line, META
    if stripped.startswith("Score:"):
        return line, SCORE
    if stripped.startswith("•"):
        return line, BULLET
    if stripped.startswith("[EDGE]") or "Profile:" not in stripped and len(stripped) > 0 and stripped[0].isalpha():
        # could be the header label line or profile params line
        pass
    return line, FG


def build_output(profile: dict, songs: list) -> str:
    prefs = {k: v for k, v in profile.items() if k != "label"}
    recs  = recommend_songs(prefs, songs, k=5)

    buf = io.StringIO()
    label = profile["label"]
    sep   = "=" * 60

    buf.write(sep + "\n")
    buf.write(f"  {label}\n")
    buf.write(f"  genre={prefs['genre']}  mood={prefs['mood']}  "
              f"energy={prefs['target_energy']}\n")
    buf.write(sep + "\n")

    for rank, (song, score, explanation) in enumerate(recs, 1):
        buf.write(f"\n  #{rank}  {song['title']}  —  {song['artist']}\n")
        buf.write(f"       Genre: {song['genre']:<14s}  Mood: {song['mood']}\n")
        buf.write(f"       Score: {score:.3f} / 4.000\n")
        for reason in explanation.split(", "):
            buf.write(f"         • {reason}\n")

    buf.write("\n")
    return buf.getvalue()


def render_image(text: str, label: str) -> Image.Image:
    font      = load_font(FONT_SIZE)
    bold_font = load_font(FONT_SIZE)  # Menlo has no separate bold face in ttc; use same

    lines = text.splitlines()

    # Measure canvas size
    dummy = Image.new("RGB", (1, 1))
    dc    = ImageDraw.Draw(dummy)
    line_h = dc.textbbox((0, 0), "Ag", font=font)[3] + LINE_GAP
    max_w  = max(dc.textlength(ln, font=font) for ln in lines) if lines else 400

    width  = int(max_w) + PAD_X * 2
    height = len(lines) * line_h + PAD_Y * 2 + 4  # +4 for bottom breathing room

    img  = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    y = PAD_Y
    for i, line in enumerate(lines):
        # pick colour
        stripped = line.strip()
        if stripped.startswith("="):
            colour = BORDER
        elif stripped.startswith("#"):
            colour = RANK
        elif stripped.startswith("Genre:"):
            colour = META
        elif stripped.startswith("Score:"):
            colour = SCORE
        elif stripped.startswith("•"):
            colour = BULLET
        elif i in (1, 2):        # profile label + params rows (just after first === line)
            colour = HEADER
        else:
            colour = FG

        draw.text((PAD_X, y), line, font=font, fill=colour)
        y += line_h

    return img


def slug(label: str) -> str:
    return label.lower().replace(" ", "_").replace("[edge]_", "edge_") \
                        .replace("(", "").replace(")", "").replace(",", "") \
                        .replace("+", "plus").replace(":", "").replace(".", "")


def main():
    songs = load_songs("data/songs.csv")
    os.makedirs("screenshots", exist_ok=True)

    saved = []
    for profile in PROFILES:
        text  = build_output(profile, songs)
        img   = render_image(text, profile["label"])
        fname = f"screenshots/{slug(profile['label'])}.png"
        img.save(fname)
        print(f"  Saved  {fname}")
        saved.append(fname)

    print(f"\nDone — {len(saved)} screenshots written to screenshots/")


if __name__ == "__main__":
    main()
