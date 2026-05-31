#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch and classify papers for the UAV VLN survey hub.

Design goals of this version:
1. Only use six survey topics.
2. Make classification stricter and score-based.
3. Allow cross-labeling, but at most 3 topic tags per paper.
4. Reduce overly broad retrieval by using more precise arXiv queries.
"""

import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple
from urllib.parse import quote

import feedparser
import requests
from dateutil import parser as date_parser

ARXIV_API = "https://export.arxiv.org/api/query"

TOPIC_ORDER = [
    "Foundations",
    "Traditional UAV VLN",
    "UAV VLA",
    "UAV WAM",
    "Datasets & Simulators",
    "Evaluation",
]

# Tighter query set. General foundational papers are kept, but broad non-relevant
# categories are reduced by avoiding too many generic world-model or embodied queries.
SEARCH_QUERIES = [
    '"vision-language navigation"',
    '"language-guided navigation"',
    '((uav OR drone OR aerial) AND (navigation OR "visual navigation"))',
    '((uav OR drone OR aerial) AND ("slam" OR "path planning" OR "obstacle avoidance" OR "semantic map"))',
    '((uav OR drone OR aerial) AND ("instruction following" OR "language grounding" OR "language-conditioned navigation"))',
    '("vision-language-action" OR "vision language action" OR "openvla" OR "rt-2" OR "octo")',
    '((uav OR drone OR aerial) AND ("vision-language-action" OR "language-conditioned policy" OR "action token"))',
    '("world action model" OR "action-conditioned world model" OR "video world model" OR "generative world model")',
    '((uav OR drone OR aerial) AND ("world model" OR "future observation prediction" OR "model-based reinforcement learning"))',
    '((uav OR drone OR aerial) AND (dataset OR benchmark OR simulator OR AirSim OR Flightmare OR Habitat OR "Isaac Sim"))',
    '("vision-language navigation" AND (evaluation OR metric OR SPL OR "success rate" OR "sim-to-real"))',
    '((uav OR drone OR aerial) AND (evaluation OR metric OR "success rate" OR collision OR "OOD generalization"))',
]

UAV_MARKERS = ["uav", "drone", "aerial", "unmanned aerial vehicle", "quadrotor", "multirotor", "flight"]

TOPIC_RULES: Dict[str, Dict[str, List[str]]] = {
    "Foundations": {
        "primary": [
            "vision-language navigation", "vision language navigation", "vln",
            "language-guided navigation", "instruction following", "navigation policy",
            "language grounding", "spatial grounding", "spatial language understanding",
            "spatial reasoning", "embodied navigation", "object navigation",
            "object-goal navigation", "point-goal navigation", "goal-oriented navigation",
        ],
        "secondary": [
            "reverie", "room-to-room", "r2r", "rxr", "navigation agent",
            "grounded instruction", "navigation benchmark", "language-conditioned navigation",
        ],
    },
    "Traditional UAV VLN": {
        "primary": [
            "slam", "visual slam", "vslam", "path planning", "trajectory planning",
            "motion planning", "obstacle avoidance", "collision avoidance",
            "semantic map", "semantic maps", "visual navigation", "autonomous navigation",
            "waypoint navigation", "target navigation", "localization and mapping",
        ],
        "secondary": [
            "map-based navigation", "mapless navigation", "topological navigation",
            "metric navigation", "frontier exploration", "route planning", "state estimation",
        ],
    },
    "UAV VLA": {
        "primary": [
            "vision-language-action", "vision language action", "vision-language-action model",
            "language-conditioned policy", "language conditioned policy", "vision-language policy",
            "action token", "action tokens", "action tokenizer", "action generation",
            "action prediction", "policy learning", "policy generation", "openvla",
            "rt-1", "rt-2", "rt-x", "octo", "diffusion policy", "act policy",
        ],
        "secondary": [
            "robot foundation model", "embodied foundation model", "generalist robot policy",
            "uav action", "drone action", "language-conditioned control", "closed-loop control",
        ],
    },
    "UAV WAM": {
        "primary": [
            "world action model", "action-conditioned world model", "video world model",
            "visual world model", "generative world model", "predictive world model",
            "latent world model", "future observation prediction", "future frame prediction",
            "next-state prediction", "video prediction", "learned dynamics model",
            "model-based reinforcement learning", "imagination-based planning",
        ],
        "secondary": [
            "dreamer", "dreamerv2", "dreamerv3", "genie", "gaia-1", "unisim",
            "action-conditioned video generation", "planning with world models",
        ],
    },
    "Datasets & Simulators": {
        "primary": [
            "airsim", "flightmare", "habitat", "isaac sim", "isaac gym", "gazebo",
            "unity", "unreal engine", "instruction-trajectory", "trajectory dataset",
            "instruction trajectory video", "vln dataset", "uav dataset", "drone dataset",
            "aerial dataset", "navigation benchmark", "robot navigation benchmark",
        ],
        "secondary": [
            "benchmark dataset", "navigation dataset", "synthetic data", "sim-to-real", "real-to-sim",
        ],
    },
    "Evaluation": {
        "primary": [
            "success rate", "spl", "success weighted by path length", "collision rate",
            "navigation error", "instruction following accuracy", "grounding accuracy",
            "action accuracy", "trajectory error", "path length", "completion rate",
            "sim-to-real", "ood generalization", "out-of-distribution generalization",
        ],
        "secondary": [
            "generalization", "zero-shot navigation", "zero shot navigation",
            "evaluation", "metric", "metrics", "ablation study",
        ],
    },
}

VENUE_RULES: Dict[str, List[str]] = {
    "CVPR": ["cvpr"],
    "ICCV": ["iccv"],
    "ECCV": ["eccv"],
    "NeurIPS": ["neurips", "neural information processing systems"],
    "ICLR": ["iclr"],
    "ICML": ["icml"],
    "CoRL": ["corl", "conference on robot learning"],
    "ICRA": ["icra"],
    "IROS": ["iros"],
    "RSS": ["robotics: science and systems", "rss"],
}


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]


def stable_id(title: str, published: str) -> str:
    raw = f"{title}|{published}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()[:12]


def count_hits(text: str, keywords: List[str]) -> int:
    count = 0
    for kw in keywords:
        if kw.lower() in text:
            count += 1
    return count


def score_topic(title: str, abstract: str, topic: str) -> float:
    rules = TOPIC_RULES[topic]
    title_text = title.lower()
    abstract_text = abstract.lower()
    full_text = f"{title_text} {abstract_text}"
    has_uav = any(marker in full_text for marker in UAV_MARKERS)

    primary_title_hits = count_hits(title_text, rules["primary"])
    primary_abstract_hits = count_hits(abstract_text, rules["primary"])
    secondary_title_hits = count_hits(title_text, rules["secondary"])
    secondary_abstract_hits = count_hits(abstract_text, rules["secondary"])

    score = 0.0
    score += primary_title_hits * 3.0
    score += primary_abstract_hits * 1.5
    score += secondary_title_hits * 1.5
    score += secondary_abstract_hits * 0.75

    if topic in {"Traditional UAV VLN", "UAV VLA", "UAV WAM"} and has_uav:
        score += 2.0
    if topic == "Traditional UAV VLN" and any(k in full_text for k in ["slam", "path planning", "visual navigation", "obstacle avoidance", "semantic map"]):
        score += 1.0
    if topic == "Foundations" and any(k in full_text for k in ["vision-language navigation", "language grounding", "spatial grounding", "instruction following"]):
        score += 1.0
    if topic == "Datasets & Simulators":
        if any(k in full_text for k in ["airsim", "flightmare", "habitat", "isaac sim", "isaac gym", "gazebo", "unity", "unreal engine"]):
            score += 2.0
        if has_uav and any(k in full_text for k in ["dataset", "benchmark", "simulator"]):
            score += 1.5
        if "vision-language navigation" in full_text and any(k in full_text for k in ["dataset", "benchmark"]):
            score += 1.5
    if topic == "Evaluation" and any(k in full_text for k in ["success rate", "spl", "collision rate", "sim-to-real", "ood generalization", "evaluation"]):
        score += 1.0

    # avoid weak false positives from generic terms in broad papers
    if topic == "Evaluation" and score < 3.0:
        return 0.0
    if topic == "Datasets & Simulators" and score < 2.5:
        return 0.0
    if topic == "Foundations" and score < 2.5:
        return 0.0
    if topic in {"Traditional UAV VLN", "UAV VLA", "UAV WAM"} and score < 3.0:
        return 0.0

    return score


def classify_topics(title: str, abstract: str, max_topics: int = 3) -> Tuple[List[str], Dict[str, float]]:
    scored = []
    for topic in TOPIC_ORDER:
        s = score_topic(title, abstract, topic)
        if s > 0:
            scored.append((topic, s))
    scored.sort(key=lambda x: (-x[1], TOPIC_ORDER.index(x[0])))
    top = scored[:max_topics]
    topics = [x[0] for x in top]
    score_map = {topic: round(score, 2) for topic, score in top}
    return topics, score_map


def compute_uav_relevance(title: str, abstract: str, topics: List[str]) -> str:
    text = f"{title} {abstract}".lower()
    has_uav = any(k in text for k in UAV_MARKERS)
    if has_uav and any(t in topics for t in ["Traditional UAV VLN", "UAV VLA", "UAV WAM"]):
        return "High"
    if has_uav or any(t in topics for t in ["Foundations", "Datasets & Simulators", "Evaluation"]):
        return "Medium"
    return "Low"


def guess_venue(comment: str, journal_ref: str) -> str:
    text = f"{comment} {journal_ref}".lower()
    for venue, keywords in VENUE_RULES.items():
        if any(k in text for k in keywords):
            return venue
    return "arXiv"


def bibtex_key(authors: List[str], published: str, title: str) -> str:
    first = "paper"
    if authors:
        first = re.sub(r"[^A-Za-z]", "", authors[0].split()[-1]).lower() or "paper"
    try:
        year = str(date_parser.parse(published).year)
    except Exception:
        year = "2026"
    word = slugify(title).split("-")[0] if title else "uav"
    return f"{first}{year}{word}"


def make_bibtex(paper: Dict) -> str:
    authors = " and ".join(paper.get("authors", []))
    title = paper.get("title", "")
    year = paper.get("year", "")
    url = paper.get("pdf_url") or paper.get("abs_url")
    key = paper.get("bibtex_key") or "paper"
    return (
        f"@article{{{key},\n"
        f"  title={{{title}}},\n"
        f"  author={{{authors}}},\n"
        f"  journal={{arXiv preprint}},\n"
        f"  year={{{year}}},\n"
        f"  url={{{url}}}\n"
        f"}}"
    )


def build_paper(entry, query: str) -> Dict:
    title = normalize_text(entry.get("title", ""))
    abstract = normalize_text(entry.get("summary", ""))
    authors = [a.name for a in entry.get("authors", [])]
    published = entry.get("published", "")
    updated = entry.get("updated", "")
    abs_url = entry.get("link", "")
    arxiv_id = abs_url.rstrip("/").split("/")[-1]
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}"
    year = ""
    date = ""
    try:
        dt = date_parser.parse(published)
        year = dt.year
        date = dt.date().isoformat()
    except Exception:
        pass

    comment = normalize_text(entry.get("arxiv_comment", ""))
    journal_ref = normalize_text(entry.get("arxiv_journal_ref", ""))
    topics, topic_scores = classify_topics(title, abstract)
    if not topics:
        return {}

    paper = {
        "id": stable_id(title, published),
        "arxiv_id": arxiv_id,
        "title": title,
        "authors": authors,
        "abstract": abstract,
        "published": published,
        "updated": updated,
        "date": date,
        "year": year,
        "venue": guess_venue(comment, journal_ref),
        "topics": topics,
        "tags": topics,
        "topic_scores": topic_scores,
        "query_source": query,
        "abs_url": abs_url,
        "pdf_url": pdf_url,
        "code_url": "",
        "project_url": "",
        "uav_relevance": compute_uav_relevance(title, abstract, topics),
        "comment": comment,
        "journal_ref": journal_ref,
    }
    paper["bibtex_key"] = bibtex_key(authors, published, title)
    paper["bibtex"] = make_bibtex(paper)
    return paper


def fetch_query(query: str, max_results: int, sleep: float = 2.0) -> List[Dict]:
    category_filter = "(cat:cs.CV OR cat:cs.AI OR cat:cs.RO OR cat:cs.LG OR cat:cs.CL)"
    search_query = f"all:{query} AND {category_filter}"
    url = (
        f"{ARXIV_API}?search_query={quote(search_query)}"
        f"&start=0&max_results={max_results}&sortBy=submittedDate&sortOrder=descending"
    )
    print(f"Fetching: {query}")
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    feed = feedparser.parse(response.text)
    papers = []
    for entry in feed.entries:
        paper = build_paper(entry, query)
        if paper:
            papers.append(paper)
    time.sleep(sleep)
    return papers


def merge_existing(existing_path: Path, new_papers: List[Dict]) -> List[Dict]:
    merged: Dict[str, Dict] = {}
    if existing_path.exists():
        with open(existing_path, "r", encoding="utf-8") as f:
            for p in json.load(f):
                topics, topic_scores = classify_topics(p.get("title", ""), p.get("abstract", ""))
                if not topics:
                    continue
                p["topics"] = topics
                p["tags"] = topics
                p["topic_scores"] = topic_scores
                p["uav_relevance"] = compute_uav_relevance(p.get("title", ""), p.get("abstract", ""), topics)
                key = p.get("arxiv_id") or p.get("id")
                merged[key] = p
    for p in new_papers:
        key = p.get("arxiv_id") or p.get("id")
        if key in merged:
            old = merged[key]
            p["code_url"] = old.get("code_url", p.get("code_url", ""))
            p["project_url"] = old.get("project_url", p.get("project_url", ""))
            p["notes"] = old.get("notes", p.get("notes", ""))
        merged[key] = p
    papers = list(merged.values())
    papers.sort(key=lambda x: x.get("date") or "", reverse=True)
    return papers


def write_outputs(papers: List[Dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    csv_path = output_path.with_suffix(".csv")
    fields = [
        "id", "arxiv_id", "title", "authors", "date", "year", "venue",
        "topics", "uav_relevance", "abs_url", "pdf_url", "code_url", "project_url", "query_source",
    ]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for p in papers:
            row = {k: p.get(k, "") for k in fields}
            row["authors"] = "; ".join(p.get("authors", []))
            row["topics"] = "; ".join(p.get("topics", []))
            writer.writerow(row)

    meta_path = output_path.parent / "meta.json"
    meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_papers": len(papers),
        "topics": TOPIC_ORDER,
        "source": "arXiv API + score-based six-topic classification",
        "tag_limit_per_paper": 3,
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-results", type=int, default=60, help="Max results for each query")
    parser.add_argument("--output", default="data/papers.json", help="Output JSON path")
    parser.add_argument("--sleep", type=float, default=2.0, help="Sleep seconds between arXiv API calls")
    args = parser.parse_args()

    output_path = Path(args.output)
    new_papers: List[Dict] = []
    for q in SEARCH_QUERIES:
        try:
            new_papers.extend(fetch_query(q, args.max_results, sleep=args.sleep))
        except Exception as e:
            print(f"[WARN] Failed query {q}: {e}")

    papers = merge_existing(output_path, new_papers)
    write_outputs(papers, output_path)
    print(f"Saved {len(papers)} papers to {output_path}")
    print(f"Saved CSV to {output_path.with_suffix('.csv')}")
    print(f"Saved metadata to {output_path.parent / 'meta.json'}")


if __name__ == "__main__":
    main()
