# Evidence

The problem statement asserts that a specific question is being asked and that
no accessible tool answers it. This documents how that was established, so the
assertion can be checked rather than taken on trust.

## Collection

YouTube Data API v3, July 2026. Six NASA Jet Propulsion Laboratory videos,
selected by view count from the channel's popular and recent feeds.

| Video | Comments |
|---|---|
| Curiosity Rover Animation | 8,824 |
| 7 Minutes of Terror | 2,161 |
| 'Oumuamua (first interstellar asteroid) | 1,562 |
| TRAPPIST-1 | 1,073 |
| 3I/ATLAS explainers (two videos) | 673 |
| **Total** | **14,293** |

Top-level comments only; replies are not included. Raw files are in `/data`.
The collection script is `data/yt_comments.py`.

## Method

1. Extract lines containing a question mark, discarding fragments under four
   words as rhetorical noise
2. Sentence embeddings
3. Dimensionality reduction with UMAP, then density-based clustering with
   HDBSCAN, leaf selection
4. Report cluster size, source mix, and centroid-nearest samples

The first clustering attempt ran HDBSCAN directly on 384-dimensional
embeddings and collapsed into a single cluster of 2,276 questions. Density
estimation degrades in high dimensions. Adding UMAP before clustering resolved
it. Both the failure and the fix are in the commit history; the failed
configuration is not presented as a result.

Embeddings were originally all-MiniLM-L6-v2 and were re-run with Granite
embeddings. Both cluster reports are retained so the difference is inspectable.

## Results

59 clusters, 1,065 questions classified as noise. Leading technical clusters:

| Theme | Questions |
|---|---|
| Travel time and mission windows | ~170 |
| Interstellar characterization and intercept | ~85 |
| Entry, descent, and landing physics | ~77 |
| Signal delay and data rates | ~37 |
| Rover power | ~37 |
| Habitability and tidal locking | ~23 |

Non-technical clusters (budget politics, filming-in-space claims, unrelated
commentary) are present and are reported rather than removed, since selective
deletion would make the technical proportions unfalsifiable.

Full report: `/data/clusters.txt`.

## View counts

Recorded from public channel pages, July 2026, in `/data/channel_views.csv`.

Across 30 sampled recent NASA JPL uploads, views ranged from 4,000 to 60,000.
The 3I/ATLAS explainer, posted in the same period, recorded 511,000. The
next-highest recent upload recorded 174,000.

Samples from two other space channels were recorded in the same period. On
Fraser Cain's channel, where top content sits near 400,000, the 3I/ATLAS guide
recorded 511,000 in eight months. StarTalk's interstellar-object episode
recorded 4 million.

A third channel, Cool Worlds, was sampled and showed no comparable operational
demand; its highest-viewed content is speculative and philosophical. It is
reported here because it is a case where the pattern did not appear.

## Limits

- Six videos from one channel plus three sampled channels. Not a random sample
  of public interest.
- Comment sections skew toward engaged viewers, not the general public.
- Question extraction is punctuation-based and will miss questions phrased as
  statements.
- Cluster boundaries depend on hyperparameters. `min_cluster_size` and
  `min_samples` are recorded in the script; different values produce different
  counts.
- View counts were read at one point in time and will have changed.

The claim these support is narrow: a large and repeated volume of people are
asking about interstellar intercepts, and interstellar-object content
outperforms channel baselines by a wide margin. They do not support a claim
about the general public, and none is made.
