# UAV-VLN-WAM-Paper-Hub

A survey-oriented paper hub for **UAV Vision-Language Navigation (UAV VLN)**, covering traditional UAV navigation, instruction following, Vision-Language-Action (VLA) models, World Action Models (WAM), embodied AI, multimodal perception, datasets, simulators, and evaluation metrics.

This repository is designed for building a UAV VLN survey such as:

> UAV Vision-Language Navigation: From Traditional Navigation to Vision-Language-Action Models and World Action Models

## Main Topics

The paper hub uses the following topic taxonomy:

1. **UAV VLN**: UAV / drone / aerial vision-language navigation.
2. **Navigation Foundation**: VLN formulation, spatial reasoning, language grounding, navigation policy.
3. **Traditional Navigation**: SLAM, path planning, semantic navigation, obstacle avoidance, visual navigation.
4. **Instruction Following**: language-guided UAV control and grounded instruction following.
5. **Vision-Language-Action**: VLA, action tokens, language-conditioned policy, robot foundation models.
6. **World Action Model**: action-conditioned world models, visual world models, future observation prediction, imagination-based planning.
7. **Embodied AI**: embodied agents, aerial embodied intelligence, physical agents.
8. **Multimodal Perception**: visual grounding, panoramic perception, GPS/IMU/LiDAR fusion, semantic maps.
9. **Dataset / Simulator**: UAV datasets, VLN benchmarks, AirSim, Flightmare, Habitat, Isaac Sim, Gazebo, CARLA.
10. **Evaluation**: SR, SPL, navigation error, collision rate, instruction-following accuracy, sim-to-real, OOD generalization.
11. **Survey**: survey, review, taxonomy, overview papers.

## Features

- Static GitHub Pages website.
- Search by title, abstract, author, topic, or venue.
- Filter by topic and UAV relevance.
- Sort by date, title, or favorites.
- Local favorites stored in browser local storage.
- Export current filtered results as CSV or BibTeX.
- Fetch and classify papers from arXiv.
- GitHub Actions workflow for daily automatic updates.

## Local Usage

```bash
pip install -r requirements.txt
python scripts/fetch_arxiv.py --max-results 100
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

## Update Data from arXiv

```bash
python scripts/fetch_arxiv.py --max-results 100

git add data/papers.json data/papers.csv data/meta.json
git commit -m "Update papers from arXiv"
git push
```

## GitHub Pages

After uploading this repository to GitHub:

```text
Settings -> Pages -> Deploy from a branch -> main -> /root
```

The site will be available at:

```text
https://<username>.github.io/<repo-name>/
```

For example:

```text
https://LiBingyu01.github.io/WAM-Paper-Hub/
```

## Recommended Survey Outline

1. Introduction
2. Foundations of UAV Vision-Language Navigation
3. Traditional UAV VLN and Aerial Navigation
4. Vision-Language-Action Models for UAV Navigation
5. World Action Models for UAV Navigation
6. Datasets, Simulators, and Benchmarks
7. Evaluation Protocols
8. Challenges and Future Directions

## Notes

You can manually edit `data/papers.json` to add project links, code links, or notes. The fetch script preserves manually curated `code_url`, `project_url`, and `notes` fields when the same arXiv paper is updated.
