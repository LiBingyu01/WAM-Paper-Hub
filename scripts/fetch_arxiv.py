#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fetch and classify papers for UAV-VLN-WAM-Paper-Hub.

This script is designed for a survey-oriented paper hub on:
- UAV Vision-Language Navigation (UAV VLN)
- Traditional UAV Navigation and VLN foundations
- Vision-Language-Action (VLA) models
- World Action Models (WAM) / World Models
- Embodied AI, multimodal perception, datasets, simulators, and evaluation

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

# Survey-oriented arXiv queries. You can add project/model names here later.
SEARCH_QUERIES = [
    '"uav navigation"',
    '"drone navigation"',
    '"aerial navigation"',
    '"vision-language navigation"',
    '"vision language navigation"',
    '"language-guided navigation"',
    '"instruction following navigation"',
    '"uav vision-language navigation"',
    '"drone vision-language navigation"',
    '"aerial vision-language navigation"',
    '"vision-language-action"',
    '"vision language action"',
    '"language-conditioned policy"',
    '"vision-language policy"',
    '"uav foundation model"',
    '"drone foundation model"',
    '"world action model"',
    '"action-conditioned world model"',
    '"visual world model"',
    '"generative world model"',
    '"uav world model"',
    '"drone world model"',
    '"action-conditioned video generation"',
    '"future observation prediction"',
    '"video prediction"',
    '"model-based reinforcement learning"',
    '"embodied navigation"',
    '"embodied ai"',
    '"aerial embodied intelligence"',
    '"uav simulator"',
    '"drone simulator"',
    '"vision-language navigation" survey',
    '"world model" survey',
    '"vision-language-action" survey',
    '"uav navigation" survey',
]

TOPIC_ORDER = [
    "UAV VLN",
    "Navigation Foundation",
    "Traditional Navigation",
    "Instruction Following",
    "Vision-Language-Action",
    "World Action Model",
    "Embodied AI",
    "Multimodal Perception",
    "Dataset / Simulator",
    "Evaluation",
    "Survey",
    "Other",
]

UAV_VLN_KEYWORDS = [
    "uav vision-language navigation", "aerial vision-language navigation", "drone vision-language navigation",
    "vision language navigation for uav", "vision-language navigation", "vision language navigation",
    "vln", "aerial navigation", "uav navigation", "drone navigation", "language-guided navigation",
    "language guided navigation", "instruction-guided navigation", "instruction following navigation",
    "natural language navigation", "embodied navigation", "goal-oriented navigation", "target-driven navigation",
    "object-goal navigation", "object navigation", "remote embodied navigation",
]

NAVIGATION_FOUNDATION_KEYWORDS = [
    "vision-language navigation", "embodied navigation", "visual navigation", "semantic navigation",
    "object navigation", "object-goal navigation", "point-goal navigation", "room-to-room", "r2r", "rxr",
    "reverie", "so-on", "habitat", "matterport3d", "ai2-thor", "minigrid", "instruction following",
    "language grounding", "spatial reasoning", "spatial language understanding", "navigation policy",
    "planning policy", "reinforcement learning for navigation", "imitation learning for navigation",
    "exploration policy",
]

TRADITIONAL_UAV_VLN_KEYWORDS = [
    "visual navigation", "vision-based navigation", "vision based navigation", "uav visual navigation",
    "drone visual navigation", "aerial robot navigation", "autonomous navigation", "autonomous uav navigation",
    "path planning", "trajectory planning", "motion planning", "route planning", "waypoint navigation",
    "goal navigation", "target navigation", "object goal navigation", "object-goal navigation",
    "semantic navigation", "map-based navigation", "mapless navigation", "topological navigation",
    "metric navigation", "slam", "visual slam", "semantic slam", "vslam", "localization and mapping",
    "obstacle avoidance", "collision avoidance", "exploration", "active perception",
]

UAV_INSTRUCTION_FOLLOWING_KEYWORDS = [
    "uav instruction following", "drone instruction following", "aerial instruction following",
    "language-guided uav", "language guided uav", "language-guided drone", "natural language instruction",
    "instruction-conditioned policy", "instruction conditioned policy", "language-conditioned control",
    "language conditioned control", "language-conditioned navigation", "language conditioned navigation",
    "text-guided navigation", "text conditioned navigation", "grounded instruction following",
    "spatial instruction following", "aerial language grounding", "language grounding for uav",
    "human-drone interaction", "human uav interaction",
]

UAV_VLA_KEYWORDS = [
    "vision-language-action", "vision language action", "vla", "vision-language-action model",
    "vision language action model", "visual language action", "multimodal action model",
    "language-conditioned policy", "language conditioned policy", "vision-language policy",
    "vision language policy", "robotic foundation model", "robot foundation model",
    "embodied foundation model", "generalist robot policy", "generalist agent", "action token",
    "action tokenizer", "action prediction", "action generation", "policy learning", "policy generation",
    "end-to-end control", "closed-loop control", "openvla", "rt-1", "rt-2", "rt-x",
    "octo", "pi-zero", "pizero", "diffusion policy", "act policy", "uav vla", "drone vla",
    "aerial vla", "vision-language-action for uav", "vision language action for uav",
    "uav foundation model", "drone foundation model", "aerial robot foundation model",
    "uav language action model", "drone language action model", "language-conditioned drone control",
    "vision-language drone control", "uav action prediction", "drone action prediction",
]

UAV_WAM_KEYWORDS = [
    "world action model", "world-action model", "wam", "action-conditioned world model",
    "action conditioned world model", "action-controllable world model", "controllable world model",
    "visual world model", "video world model", "generative world model", "predictive world model",
    "latent world model", "neural world model", "embodied world model", "robot world model",
    "uav world model", "drone world model", "aerial world model", "action-conditioned video generation",
    "action conditioned video generation", "action-driven video generation", "action driven video generation",
    "future observation prediction", "future frame prediction", "video prediction", "next-state prediction",
    "next state prediction", "dynamics model", "learned dynamics model", "model-based reinforcement learning",
    "model based reinforcement learning", "planning with world models", "imagination-based planning",
    "imagination based planning", "general world model", "generalist world model", "general-purpose world model",
    "general purpose world model", "universal world model", "foundation world model", "world foundation model",
    "scalable world model", "multimodal world model", "unified world model", "universal action model",
    "general action model", "action foundation model", "policy foundation model", "dreamer", "dreamerv2",
    "dreamerv3", "genie", "gaia-1", "unisim", "cosmos",
]

UAV_EMBODIED_KEYWORDS = [
    "embodied ai", "embodied intelligence", "embodied agent", "embodied foundation model",
    "embodied perception", "embodied planning", "embodied navigation", "aerial embodied intelligence",
    "aerial embodied agent", "uav embodied intelligence", "drone embodied intelligence", "robotic agent",
    "autonomous agent", "interactive agent", "multimodal agent", "vision-language agent",
    "language-guided agent", "physical agent", "situated agent", "agentic navigation",
]

UAV_MULTIMODAL_PERCEPTION_KEYWORDS = [
    "multimodal perception", "uav perception", "drone perception", "aerial perception",
    "vision-language perception", "visual grounding", "language grounding", "referring expression",
    "object grounding", "spatial grounding", "scene understanding", "semantic scene understanding",
    "aerial scene understanding", "panoramic perception", "egocentric perception", "first-person view",
    "fpv", "depth estimation", "lidar", "imu", "gps", "visual inertial odometry", "vio",
    "multisensor fusion", "sensor fusion", "occupancy prediction", "semantic map", "topological map",
]

UAV_VLN_DATASET_KEYWORDS = [
    "uav dataset", "drone dataset", "aerial dataset", "uav benchmark", "drone benchmark",
    "aerial benchmark", "vision-language navigation dataset", "vln dataset", "embodied navigation dataset",
    "instruction following dataset", "language-guided navigation dataset", "robot navigation benchmark",
    "uav simulator", "drone simulator", "aerial simulator", "flight simulator", "airsim",
    "flightmare", "habitat", "ai2-thor", "isaac sim", "isaac gym", "gazebo", "carla",
    "unreal engine", "unity", "sim-to-real", "real-to-sim", "synthetic data",
]

UAV_VLN_EVALUATION_KEYWORDS = [
    "success rate", "spl", "success weighted by path length", "navigation error", "trajectory error",
    "path length", "collision rate", "completion rate", "goal success", "instruction following accuracy",
    "grounding accuracy", "action accuracy", "control error", "tracking error", "planning success",
    "generalization", "zero-shot navigation", "sim-to-real transfer", "out-of-distribution generalization",
    "ood generalization",
]

SURVEY_KEYWORDS = [
    "survey", "review", "taxonomy", "overview", "comprehensive study", "systematic review",
]

TOPIC_RULES: Dict[str, List[str]] = {
    "UAV VLN": UAV_VLN_KEYWORDS,
    "Navigation Foundation": NAVIGATION_FOUNDATION_KEYWORDS,
    "Traditional Navigation": TRADITIONAL_UAV_VLN_KEYWORDS,
    "Instruction Following": UAV_INSTRUCTION_FOLLOWING_KEYWORDS,
    "Vision-Language-Action": UAV_VLA_KEYWORDS,
    "World Action Model": UAV_WAM_KEYWORDS,
    "Embodied AI": UAV_EMBODIED_KEYWORDS,
    "Multimodal Perception": UAV_MULTIMODAL_PERCEPTION_KEYWORDS,
    "Dataset / Simulator": UAV_VLN_DATASET_KEYWORDS,
    "Evaluation": UAV_VLN_EVALUATION_KEYWORDS,
    "Survey": SURVEY_KEYWORDS,
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

UAV_MARKERS = ["uav", "drone", "aerial", "unmanned aerial vehicle", "quadrotor", "flight"]


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
    for topic in TOPIC_ORDER:
        if topic in ("Other",):
            continue
        keywords = TOPIC_RULES.get(topic, [])
        if any(k.lower() in haystack for k in keywords):
            topics.append(topic)
    if not topics:
        topics.append("Other")
    return topics


def compute_uav_relevance(title: str, abstract: str, topics: List[str]) -> str:
    text = f"{title} {abstract}".lower()
    has_uav = any(k in text for k in UAV_MARKERS)
    if "UAV VLN" in topics or (has_uav and any(t in topics for t in ["Vision-Language-Action", "World Action Model", "Instruction Following"])):
        return "High"
    if has_uav or any(t in topics for t in ["Navigation Foundation", "Traditional Navigation", "Embodied AI", "Dataset / Simulator"]):
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


def fetch_query(query: str, max_results: int, sleep: float = 2.5) -> List[Dict]:
    # arXiv API supports fielded search. We use all:<query> and restrict to CV/AI/RO/LG/CL.
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
            "uav_relevance": compute_uav_relevance(title, abstract, topics),
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
            # Preserve manually curated links while refreshing metadata/topics.
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
        "source": "arXiv API + manual JSON curation",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-results", type=int, default=80, help="Max results for each query")
    parser.add_argument("--output", default="data/papers.json", help="Output JSON path")
    parser.add_argument("--sleep", type=float, default=2.5, help="Sleep seconds between arXiv API calls")
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
