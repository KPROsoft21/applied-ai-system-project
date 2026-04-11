# Model Card: Music Recommender Simulation

---

## 1. Model Name

**VibeMatch 1.0**

A content-based music recommender that matches songs to a listener's stated genre, mood, and energy preferences.

---

## 2. Goal / Task

The system tries to answer one question: *given what a user says they want, which songs from the catalog are the closest match?*

It does not learn from listening history or other users. It only looks at what the user states and compares it directly to song attributes.

The task is to rank 18 songs from most to least relevant and return the top 5.

---

## 3. Data Used

- **Catalog size:** 18 songs stored in `data/songs.csv`
- **Genres represented:** pop, lofi, rock, ambient, jazz, synthwave, indie pop, hip-hop, r&b, classical, EDM, country, metal, funk, soul (15 total)
- **Moods represented:** happy, chill, intense, relaxed, focused, moody, uplifting, sad, melancholic, euphoric, nostalgic, angry, soulful, romantic (14 total)
- **Song features stored:** title, artist, genre, mood, energy (0–1 float), tempo in BPM, valence, danceability, acousticness
- **Song features actually used in scoring:** genre, mood, energy only — valence, tempo, danceability, and acousticness are stored but ignored

**Known limits of this dataset:**

13 of the 15 genres have exactly one song. Only lofi (3 songs) and pop (2 songs) have more than one representative. This means most genre searches run out of real matches after the first result.

There are no songs with energy between 0.46 and 0.71. The catalog jumps from quiet/mellow tracks (max 0.45) straight to upbeat tracks (min 0.72). Users who want something in the middle will never get a close energy match.

The dataset likely reflects the taste of whoever built it. Genres like bossa nova, reggae, blues, folk, and K-pop are completely absent.

---

## 4. Algorithm Summary

Every song in the catalog gets a score. The scores go from 0 to 4.0. The top 5 scores are returned as recommendations.

Here is how the score is calculated:

**+1.0 point** if the song's genre exactly matches what the user asked for.
Genre is pass/fail — "indie pop" does not count as "pop," even though they are related.

**+1.0 point** if the song's mood exactly matches what the user asked for.
Same rule — it must be an exact word match. "Intense" and "angry" are different moods even if they feel similar.

**Up to +2.0 points** based on how close the song's energy is to the user's target.
A perfect energy match gives the full 2.0. A song that is 0.5 away from the target gives 1.0. A song at the complete opposite end of the scale gives close to 0.

The energy score is the only one that is gradual. Genre and mood are all-or-nothing.

**What this means in practice:**
A song that matches genre and mood but has slightly off energy will almost always beat a song that matches only energy. But if no genre matches exist in the catalog, the system falls back to ranking by energy alone, which can produce results that feel completely unrelated to what the user wanted.

---

## 5. Strengths

The system works best when the user's preferred genre has more than one song in the catalog and the mood is a common one.

The **Chill Lofi** profile performed well. The catalog has three lofi songs, so the top three results were all genuine lofi matches ranked by how close their energy was to the target. A human listener would likely agree with that ordering.

The **Deep Intense Rock** profile also performed well. Storm Runner matched genre, mood, and energy so closely (score: 3.98 / 4.00) that the top result was obvious and correct.

The scoring is fully transparent. Every point is explained in the output. A user can read exactly why a song ranked where it did. That kind of explainability is rare in real-world recommenders.

The system never crashes on unusual input. Ghost genres, extreme energy values, and contradictory preferences all produce results without errors — though the results may not be useful.

---

## 6. Limitations and Bias

**Single-song genre filter bubble.**
13 of the 15 genres have exactly one song. Any user outside of lofi or pop gets one real genre match and then four slots filled by energy coincidence. A hip-hop fan, a classical fan, and a country fan all face this same problem. The system does not warn them.

**Ghost genre problem.**
If the user's preferred genre does not exist in the catalog at all, the maximum score any song can reach drops from 4.0 to 2.0. The system still returns five results. Nothing in the output flags that zero genuine matches were found. The results look just as confident as a perfect match.

**Genre label brittleness.**
Genre and mood are compared as plain text. "Indie pop" and "pop" score zero genre points against each other even though a human listener would consider them closely related. The same problem applies to "funk" and "hip-hop," or "melancholic" and "sad."

**Energy dead zone.**
There are no songs with energy between 0.46 and 0.71. Users who want medium-energy music will always get something that is either too quiet or too loud. Their best possible energy score is capped well below the maximum.

**Acousticness is invisible.**
The `UserProfile` has a `likes_acoustic` field. Songs have acousticness values from 0.03 to 0.97. The scoring function never reads either. An acoustic singer-songwriter fan and an electronic music fan get the exact same recommendations.

**High-energy skew in the catalog.**
Nine of the 18 songs have energy above 0.72. This means high-energy listeners have more options to choose from, and their runner-up slots feel more relevant. Low-energy listeners have fewer matches and their lower-ranked results drift toward unrelated genres faster.

---

## 7. Evaluation

**How we tested it:**

Seven user profiles were run through the system. Three were realistic listener types. Four were designed to break or stress-test the scoring logic.

| Profile | Genre | Mood | Energy | Type |
|---|---|---|---|---|
| High-Energy Pop | pop | happy | 0.90 | Standard |
| Chill Lofi | lofi | chill | 0.25 | Standard |
| Deep Intense Rock | rock | intense | 0.92 | Standard |
| Conflicting signals | r&b | sad | 0.90 | Adversarial |
| Ghost genre | bossa nova | relaxed | 0.50 | Adversarial |
| Neutral energy | ambient | focused | 0.50 | Adversarial |
| Quiet angry | metal | angry | 0.05 | Adversarial |

For each run, we checked: Did the #1 result feel right? Did the runner-up slots make sense? Did the system behave strangely with bad input?

**What surprised us:**

The standard profiles mostly worked. Sunrise City, Library Rain, and Storm Runner each ranked first for the listener type they matched, and that felt correct.

The runner-up slots were the problem. After the catalog ran out of genre matches, the system filled remaining slots with high-energy songs from completely unrelated genres. A happy pop listener ended up with a rock song and an EDM song in positions 4 and 5.

The biggest surprise was the Quiet Angry profile. The user asked for energy 0.05 — near silence. The system returned Iron Curtain, a metal track with energy 0.97, the loudest song in the entire catalog. It won because genre and mood matched exactly. No weight on the energy side was strong enough to override the genre-and-mood bonus.

The Ghost Genre profile confirmed that the system has no way to say "I don't have anything for you." It returned five songs as if they were genuine matches.

**Weight-shift experiment:**

We halved the genre weight (2.0 → 1.0) and doubled the energy weight (1.0 → 2.0). The total maximum score stayed at 4.0.

This changed the ranking on two profiles. For the Neutral Energy profile, Focus Flow (lofi, focused, energy 0.40) correctly moved above Spacewalk Thoughts (ambient, chill, energy 0.28) because it matched the mood and had closer energy. That felt more accurate.

The High-Energy Pop and Deep Intense Rock profiles did not change at all. The same five songs appeared in the same order. That told us the catalog's small size is a bigger problem than the weights.

---

## 8. Intended Use and Non-Intended Use

**This system is designed for:**

- Classroom exploration of how content-based recommendation works
- Learning how scoring weights affect results
- Practicing with Python data structures and function design
- Experimenting with small datasets to understand algorithm behavior

**This system should NOT be used for:**

- Making real music recommendations to real users
- Replacing a music streaming service or playlist tool
- Drawing conclusions about what music is "objectively" better
- Making decisions that affect people's access to content or resources

The catalog is too small, the scoring is too rigid, and too many song features are ignored for this to work as a real product. It is a learning tool, not a production system.

---

## 9. Ideas for Improvement

**1. Add a confidence or coverage score.**
When fewer than two genre matches exist in the catalog, the output should say so. Something like "only 1 genre match found" would help the user understand that the results are best-effort, not genuine recommendations. This is a one-line change in `recommend_songs()` that would make results much more honest.

**2. Use acousticness in scoring.**
The data is already there — every song has an acousticness value and every user profile has a `likes_acoustic` flag. Adding a small bonus (around +0.5) for acoustic songs when the user prefers acoustic, and for electronic songs when they do not, would use existing data that is currently being thrown away. This directly addresses one of the clearest gaps in the current model.

**3. Expand the catalog and introduce genre families.**
Adding at least 5 songs per genre would fix the filter bubble problem at its root. A related improvement would be grouping similar genres (pop and indie pop, hip-hop and funk, classical and ambient) so that a near-miss genre earns partial credit instead of zero. This would make recommendations feel less brittle when the user's exact genre has thin coverage.

---

## 10. Personal Reflection

**Biggest learning moment:**

The most surprising thing was discovering how fast a small catalog breaks the recommender. The scoring logic worked exactly as designed — but once a genre had only one song, the system had nothing left to do. It just sorted by energy, which produced recommendations that felt random. The algorithm was not wrong; the data was too thin to support it. That gap between "the code is correct" and "the results are useful" was the clearest lesson of the whole project.

**How AI tools helped — and when to double-check:**

AI tools (including Claude) helped write cleaner scoring logic, generate test profiles, and spot the exact lines where `likes_acoustic` was being silently ignored. They were most useful for explaining *why* something was happening — for example, tracing exactly why Iron Curtain ranked first for a quiet profile by working out the math step by step.

The moments that required manual checking were when the AI suggested something that sounded right but needed verification against the actual data. For example, the claim that "the catalog skews toward high energy" had to be confirmed by reading the CSV and counting. Trusting a description without checking the numbers would have led to wrong conclusions.

**What surprised me about simple algorithms:**

A three-term scoring formula — genre, mood, energy — produces results that feel like a real recommendation for at least the first result in most profiles. That is striking. The system has no memory, no learning, and no awareness of musical relationships. It just adds up three numbers. Yet when all three signals align, the output feels like something a knowledgeable DJ might actually choose. The illusion of intelligence comes entirely from choosing the right features, not from a complex model.

What broke that illusion immediately was any profile where one signal conflicted with another. The Quiet Angry profile — loud genre, silent energy target — revealed that the system has no judgment about which signal matters more in context. It just adds points mechanically. Real recommendations require understanding tradeoffs that simple addition cannot capture.

**What I would try next:**

The first thing would be adding partial genre credit — so that "indie pop" earns 0.5 genre points against a "pop" search instead of zero. This single change would fix the Rooftop Lights problem without changing any weights or adding new features.

After that, I would add the acousticness term and expand the catalog to at least 5 songs per genre. With those two changes, the system would be using all the data it already has and would stop running out of meaningful results after the first or second pick.
