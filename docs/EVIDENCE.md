# Evidence

The problem statement asserts that a specific question is being asked and that
no accessible tool answers it. This documents how that was established, so the
assertion can be checked rather than taken on trust.

## Collection

YouTube Data API v3, July 2026. Six NASA Jet Propulsion Laboratory videos,
selected by view count from the channel's popular and recent feeds.

| Video | Comments | File |
|---|---|---|
| Curiosity Rover Animation | 8,824 | `data/curiosity_animation.txt` |
| TRAPPIST-1 | 5,902 | `data/trappist1.txt` |
| 7 Minutes of Terror | 2,161 | `data/7min_terror.txt` |
| 'Oumuamua (first interstellar asteroid) | 1,562 | `data/oumuamua.txt` |
| 3I/ATLAS, what we know | 370 | `data/3iatlas_known.txt` |
| 3I/ATLAS, approaching Mars | 303 | `data/3iatlas_mars.txt` |
| **Total** | **19,122** | |

Top-level comments only; replies are not included. Raw files are in `/data`.
The collection script is `data/yt_comments.py`. One numbered comment per line,
so each row is `grep -cE '^[0-9]+\. ' <file>`.

**These counts supersede an earlier figure of 14,293**, which this document
carried with TRAPPIST-1 at 1,073. The committed `trappist1.txt` holds 5,902,
and the earlier total was never updated to match it. The corrected total is the
one the analysis rests on: re-running the extraction rule of
`data/cluster_questions.py` over these six files reproduces the 3,171 questions
in `data/clusters.txt` exactly, so these files, at these sizes, are what was
clustered. Corrected 2026-08-30.

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

Embeddings are all-MiniLM-L6-v2, in `data/cluster_questions.py`. A re-run with
Granite embeddings was planned and has not been done, so there is one cluster
report rather than two, and no comparison between embedding models is claimed.

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

Read by hand from public channel pages in July 2026 and recorded in this
document. There is no committed data file behind them: `channel_views.csv` was
planned and never written, so unlike the comment corpora these figures cannot
be re-derived from the repository. They are reproducible only in the weak sense
that anyone can visit the same pages, where the counts will since have moved.

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
- View counts are transcribed figures, not a committed dataset. The comment
  corpora and the cluster report are in `/data` and can be re-run; the view
  counts cannot.

The claim these support is narrow: a large and repeated volume of people are
asking about interstellar intercepts, and interstellar-object content
outperforms channel baselines by a wide margin. They do not support a claim
about the general public, and none is made.
