# 🎵 Music Recommender Simulation

## Project Summary

In this project you will build and explain a small music recommender system.

Your goal is to:

- Represent songs and a user "taste profile" as data
- Design a scoring rule that turns that data into recommendations
- Evaluate what your system gets right and wrong
- Reflect on how this mirrors real world AI recommenders

Replace this paragraph with your own summary of what your version does.

---

## How The System Works

Real-world recommenders like Spotify combine collaborative filtering (learning from millions of users' behavior) with content-based filtering (analyzing the audio properties of songs themselves). This simulation focuses entirely on content-based filtering — it ignores other users and instead matches songs directly to what a single user says they want. The priority is "vibe proximity": rather than recommending the loudest or most popular track, the system rewards songs whose measurable attributes land closest to the user's stated preferences.

### `Song` features used in scoring

- `genre` — the musical category (pop, lofi, rock, ambient, jazz, synthwave, indie pop, hip-hop, r&b, classical, edm, country, metal, funk, soul)
- `mood` — the emotional label (happy, chill, intense, relaxed, focused, moody, uplifting, sad, melancholic, euphoric, nostalgic, angry, soulful, romantic)
- `energy` — a 0–1 float measuring intensity and activation level
- `valence` — a 0–1 float measuring emotional brightness (high = happy, low = dark)
- `acousticness` — a 0–1 float indicating how acoustic vs. electronic the track is
- `tempo_bpm` — beats per minute; stored for context and potential tiebreaking
- `danceability` — a 0–1 float; stored for context and potential tiebreaking

### `UserProfile` fields used in scoring

- `favorite_genre` — matched exactly against each song's genre
- `favorite_mood` — matched exactly against each song's mood
- `target_energy` — the desired energy level; songs are scored by closeness to this value
- `likes_acoustic` — boolean; grants a small bonus to high-acousticness songs when `True`

### Algorithm Recipe

Scoring is a weighted point sum applied to every song in the catalog. The song with the highest total is ranked first.

```
score(song, user) =
    2.0  × genre_match        ← +2.0 if genre matches exactly, else +0.0
  + 1.0  × mood_match         ← +1.0 if mood matches exactly, else +0.0
  + 1.0  × energy_proximity   ← +1.0 × (1 - |song.energy - user.target_energy|)

Maximum possible score: 4.0
```

After every song is scored, the list is sorted highest-to-lowest and the top `k` results (default 5) are returned alongside the score and a plain-language explanation.

**Why these weights?** Genre carries the most points (2.0) because it encodes the entire sonic world of a track — instrumentation, production style, tempo feel, and cultural context — none of which a single number can capture. Mood earns the second slot (1.0) because it crosses genre lines: a "chill" lofi track and a "chill" ambient track share a feeling even though they sound different, so mood alone should not override genre. Energy proximity fills the remaining point as the strongest continuous signal; it differentiates songs within the same genre and mood without requiring an exact match.

### Expected Biases

- **Genre dominance.** A 2.0-point genre bonus means two genre mismatches can never be overcome by a perfect mood and energy match combined. A great song in a related-but-different genre (e.g., ambient when the user asked for lofi) will always score lower than a mediocre same-genre track. This is the right tradeoff for a small catalog but would be too rigid at scale.
- **Exact-match brittleness.** Genre and mood are compared as plain strings. "Indie pop" and "pop" share obvious overlap but score zero genre points against each other. A user who loves "hip-hop" would get no genre credit for a "funk" song, even though the groove and rhythm feel are closely related.
- **Valence blindness.** Two songs with identical genre, mood, and energy scores can differ dramatically in emotional tone — one bright and uplifting, one dark and melancholic — and the recipe cannot tell them apart. Adding a valence similarity term would fix this.

---

## Getting Started

### Setup

1. Create a virtual environment (optional but recommended):

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # Mac or Linux
   .venv\Scripts\activate         # Windows

2. Install dependencies

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python -m src.main
```

### Running Tests

Run the starter tests with:

```bash
pytest
```

You can add more tests in `tests/test_recommender.py`.

---

## Experiments You Tried

Use this section to document the experiments you ran. For example:

- What happened when you changed the weight on genre from 2.0 to 0.5
- What happened when you added tempo or valence to the score
- How did your system behave for different types of users

---

## Limitations and Risks

Summarize some limitations of your recommender.

Examples:

- It only works on a tiny catalog
- It does not understand lyrics or language
- It might over favor one genre or mood

You will go deeper on this in your model card.

---

## Reflection

Read and complete `model_card.md`:

[**Model Card**](model_card.md)

Write 1 to 2 paragraphs here about what you learned:

- about how recommenders turn data into predictions
- about where bias or unfairness could show up in systems like this


---

## 7. `model_card_template.md`

Combines reflection and model card framing from the Module 3 guidance. :contentReference[oaicite:2]{index=2}  

```markdown
# 🎧 Model Card - Music Recommender Simulation

## 1. Model Name

Give your recommender a name, for example:

> VibeFinder 1.0

---

## 2. Intended Use

- What is this system trying to do
- Who is it for

Example:

> This model suggests 3 to 5 songs from a small catalog based on a user's preferred genre, mood, and energy level. It is for classroom exploration only, not for real users.

---

## 3. How It Works (Short Explanation)

Describe your scoring logic in plain language.

- What features of each song does it consider
- What information about the user does it use
- How does it turn those into a number

Try to avoid code in this section, treat it like an explanation to a non programmer.

---

## 4. Data

Describe your dataset.

- How many songs are in `data/songs.csv`
- Did you add or remove any songs
- What kinds of genres or moods are represented
- Whose taste does this data mostly reflect

---

## 5. Strengths

Where does your recommender work well

You can think about:
- Situations where the top results "felt right"
- Particular user profiles it served well
- Simplicity or transparency benefits

---

## 6. Limitations and Bias

Where does your recommender struggle

Some prompts:
- Does it ignore some genres or moods
- Does it treat all users as if they have the same taste shape
- Is it biased toward high energy or one genre by default
- How could this be unfair if used in a real product

---

## 7. Evaluation

How did you check your system

Examples:
- You tried multiple user profiles and wrote down whether the results matched your expectations
- You compared your simulation to what a real app like Spotify or YouTube tends to recommend
- You wrote tests for your scoring logic

You do not need a numeric metric, but if you used one, explain what it measures.

---

## 8. Future Work

If you had more time, how would you improve this recommender

Examples:

- Add support for multiple users and "group vibe" recommendations
- Balance diversity of songs instead of always picking the closest match
- Use more features, like tempo ranges or lyric themes

---

## 9. Personal Reflection

A few sentences about what you learned:

- What surprised you about how your system behaved
- How did building this change how you think about real music recommenders
- Where do you think human judgment still matters, even if the model seems "smart"


<img width="505" height="632" alt="Screenshot 2026-04-11 at 4 55 56 PM" src="https://github.com/user-attachments/assets/e8b97c9c-a4c7-4e80-958a-ebfbf31ba15f" />

