# UAV-VLN-AWESOME-Paper-Hub

A focused survey-oriented paper hub for **UAV Vision-Language Navigation (UAV VLN)**.

This version is intentionally strict:
- only **6 topics** are used;
- each paper can have **up to 3 tags**;
- the homepage provides **6 jump buttons** that scroll to the corresponding topic sections.

## Six Fixed Topics

1. **Foundations**  
   VLN formulation, spatial grounding, navigation policy, instruction following.

2. **Traditional UAV VLN**  
   SLAM, path planning, semantic maps, obstacle avoidance, visual navigation.

3. **UAV VLA**  
   Vision + language → action, action tokens, language-conditioned policy learning.

4. **UAV WAM**  
   Observation + action → future observation/state for imagination-based planning.

5. **Datasets & Simulators**  
   AirSim, Flightmare, Habitat, Isaac Sim, instruction-trajectory-video data.

6. **Evaluation**  
   SR, SPL, collision rate, instruction accuracy, sim-to-real and OOD generalization.


## Time Index

The web interface now supports a calendar-style year-month filter:

- use the `Year-Month` picker in the toolbar to filter papers by month;
- each topic section shows month chips such as `2026.05`;
- clicking a month chip jumps to that topic and filters the corresponding month;
- papers inside each month are sorted by day.

## Features

- arXiv-based update script
- stricter score-based six-topic classification
- at most 3 tags per paper
- grouped topic sections on the webpage
- search, filter, sort, favorites, CSV/BibTeX export

## Quick Start

```bash
pip install -r requirements.txt
python scripts/fetch_arxiv.py --max-results 60
python -m http.server 8000
```

Then open:

```text
http://127.0.0.1:8000
```

## Update Data

```bash
python scripts/fetch_arxiv.py --max-results 60
```

The script updates:
- `data/papers.json`
- `data/papers.csv`
- `data/meta.json`

## Notes

- Retrieval is more precise than the previous broad version, but you should still manually curate highly important papers.
- Existing manually added `code_url` and `project_url` are preserved when possible.
