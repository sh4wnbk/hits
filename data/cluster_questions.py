#!/usr/bin/env python3
"""Cluster fan questions from comment corpora.

Usage:
    python3 cluster_questions.py out_report.txt corpus1.txt corpus2.txt ...

Pipeline: extract question lines -> embed (all-MiniLM-L6-v2) ->
HDBSCAN clustering -> report with cluster sizes, source mix, samples.
"""

import re
import sys
from collections import Counter
from pathlib import Path

import hdbscan
import numpy as np
from sentence_transformers import SentenceTransformer

MIN_WORDS = 4  # skip "why?" / "how??" noise


def extract_questions(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = re.sub(r"^\d+\.\s*", "", line).strip()
        if "?" in text and len(text.split()) >= MIN_WORDS:
            out.append(text)
    return out


def main():
    if len(sys.argv) < 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    report_path = sys.argv[1]
    questions, sources = [], []
    for f in sys.argv[2:]:
        p = Path(f)
        qs = extract_questions(p)
        questions.extend(qs)
        sources.extend([p.stem] * len(qs))
        print(f"{p.stem}: {len(qs)} questions", file=sys.stderr)

    print(f"Embedding {len(questions)} questions...", file=sys.stderr)
    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = model.encode(questions, show_progress_bar=True, normalize_embeddings=True)

    import umap

    reduced = umap.UMAP(n_neighbors=15, n_components=5, min_dist=0.0,
                        metric="cosine", random_state=42).fit_transform(emb)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=15, min_samples=5,
                                cluster_selection_method="leaf", metric="euclidean")
    labels = clusterer.fit_predict(reduced)

    n_clusters = labels.max() + 1
    noise = int((labels == -1).sum())
    lines = [f"Questions: {len(questions)} | Clusters: {n_clusters} | Noise: {noise}\n"]

    order = sorted(range(n_clusters), key=lambda c: -(labels == c).sum())
    for c in order:
        idx = np.where(labels == c)[0]
        src_mix = Counter(sources[i] for i in idx)
        # representative samples: closest to cluster centroid
        centroid = emb[idx].mean(axis=0)
        dists = np.linalg.norm(emb[idx] - centroid, axis=1)
        reps = idx[np.argsort(dists)[:5]]

        lines.append(f"=== Cluster {c} | size {len(idx)} | sources {dict(src_mix)}")
        for i in reps:
            lines.append(f"  - {questions[i][:200]}")
        lines.append("")

    Path(report_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {report_path}")


if __name__ == "__main__":
    main()
