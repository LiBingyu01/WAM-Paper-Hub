#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch and classify papers for WAM-Paper-Hub.

Usage:
    python scripts/fetch_arxiv.py --max-results 80
    python scripts/fetch_arxiv.py --max-results 200 --output data/papers.json
"""

import argparse
import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
from urllib.parse import quote

import feedparser
import requests
from dateutil import parser as date_parser

ARXIV_API = "https://export.arxiv.org/api/query"

SEARCH_QUERIES = [
    '"world model"',
    '"world models"',
    '"world action model"',
    '"action-conditioned" AND "video"',
    '"vision-language-action"',
    '"embodied ai"',
    '"embodied agent"',
    '"model-based reinforcement learning"',
    '"video prediction"',
    '"future frame prediction"',
    '"controllable video generation"',
    '"uav navigation"',
    '"drone navigation"',
    '"robot learning"',
    '"autonomous driving" AND "world model"',
]

TOPIC_RULES: Dict[str, List[str]] = {
    "World Model": [
        "world model", "world models", "neural world model", "generative world model",
        "latent dynamics", "learned dynamics", "model-based reinforcement learning",
        "model based reinforcement learning", "dreamer", "muzero",
    ],
    "WAM": [
        "world action model", "action-conditioned", "action conditioned", "action-controllable",
        "action controllable", "action-driven", "action driven", "observation-action",
        "trajectory-conditioned", "policy-conditioned", "visual action model",
        "vision-language-action", "vision language action", "vla",
    ],
    "Embodied AI": [
        "embodied ai", "embodied agent", "embodied intelligence", "vision-language navigation",
        "visual navigation", "object navigation", "language-guided navigation", "interactive agent",
        "sim-to-real", "habitat", "ai2-thor", "maniskill", "robosuite",
    ],
    "UAV": [
        "uav", "unmanned aerial vehicle", "drone", "quadrotor", "aerial robot",
        "aerial navigation", "drone navigation", "uav navigation", "flight policy",
        "aerial embodied", "aerial video",
    ],
    "Video Generation": [
        "video generation", "text-to-video", "image-to-video", "future prediction",
        "future frame", "future video", "video diffusion", "diffusion transformer",
        "dynamic scene generation", "4d generation", "video prediction",
    ],
    "Robotics": [
        "robot", "robotics", "robot learning", "manipulation", "mobile robot",
        "reinforcement learning", "policy learning", "control policy",
    ],
    "Autonomous Driving": [
        "autonomous driving", "self-driving", "driving world model", "occupancy prediction",
        "bev", "trajectory planning", "end-to-end driving",
    ],
    "Dataset / Benchmark": [
        "dataset", "benchmark", "evaluation", "leaderboard", "simulator", "simulation environment",
    ],
    "Survey": [
        "survey", "review", "a comprehensive study", "taxonomy", "overview",
    ],
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


def classify_topics(title: str, abstract: str) -> List[str]:
    haystack = f"{title} {abstract}".lower()
    topics = []
    for topic, keywords in TOPIC_RULES.items():
        if any(k.lower() in haystack for k in keywords):
            topics.append(topic)
    if not topics:
        topics.append("Other")
    return topics


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
    year = ""
    try:
        year = str(date_parser.parse(published).year)
    except Exception:
        year = "2026"
    word = slugify(title).split("-")[0] if title else "world"
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


def fetch_query(query: str, max_results: int, sleep: float = 2.5) -> List[Dict]:
    search_query = f"all:{query} AND (cat:cs.CV OR cat:cs.AI OR cat:cs.RO OR cat:cs.LG OR cat:cs.CL)"
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
        topics = classify_topics(title, abstract)
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
            "query_source": query,
            "abs_url": abs_url,
            "pdf_url": pdf_url,
            "code_url": "",
            "project_url": "",
            "uav_relevance": "High" if "UAV" in topics else "Medium" if any(t in topics for t in ["World Model", "WAM", "Embodied AI"]) else "Low",
            "comment": comment,
            "journal_ref": journal_ref,
        }
        paper["bibtex_key"] = bibtex_key(authors, published, title)
        paper["bibtex"] = make_bibtex(paper)
        papers.append(paper)

    time.sleep(sleep)
    return papers


def merge_existing(existing_path: Path, new_papers: List[Dict]) -> List[Dict]:
    merged: Dict[str, Dict] = {}
    if existing_path.exists():
        with open(existing_path, "r", encoding="utf-8") as f:
            for p in json.load(f):
                key = p.get("arxiv_id") or p.get("id")
                merged[key] = p
    for p in new_papers:
        key = p.get("arxiv_id") or p.get("id")
        if key in merged:
            old = merged[key]
            # Preserve manually added links.
            for field in ["code_url", "project_url", "note", "selected"]:
                if old.get(field) and not p.get(field):
                    p[field] = old[field]
        merged[key] = p
    papers = list(merged.values())
    papers.sort(key=lambda x: x.get("date", ""), reverse=True)
    return papers


def write_csv(papers: List[Dict], path: Path) -> None:
    fields = [
        "title", "authors", "date", "year", "venue", "topics", "uav_relevance",
        "abs_url", "pdf_url", "code_url", "project_url", "abstract"
    ]
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for p in papers:
            row = {k: p.get(k, "") for k in fields}
            row["authors"] = "; ".join(p.get("authors", []))
            row["topics"] = "; ".join(p.get("topics", []))
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-results", type=int, default=80, help="Max results per search query")
    parser.add_argument("--output", type=str, default="data/papers.json")
    parser.add_argument("--csv", type=str, default="data/papers.csv")
    parser.add_argument("--no-merge", action="store_true")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_new: List[Dict] = []
    for q in SEARCH_QUERIES:
        try:
            all_new.extend(fetch_query(q, args.max_results))
        except Exception as exc:
            print(f"[WARN] Failed query {q}: {exc}")

    papers = all_new if args.no_merge else merge_existing(output_path, all_new)

    meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "num_papers": len(papers),
        "source": "arXiv API",
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    write_csv(papers, Path(args.csv))

    with open(output_path.parent / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(papers)} papers to {output_path}")


if __name__ == "__main__":
    main()
