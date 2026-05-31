# WAM-Paper-Hub

A lightweight, GitHub Pages-ready paper hub for **World Models**, **World Action Models (WAM)**, **Embodied AI**, **UAV Navigation**, **Robotics**, **Autonomous Driving**, and **Video Generation**.

This repo is designed to be easy to fork, debug, and extend. It includes:

- A static website: `index.html` + `assets/app.js` + `assets/style.css`
- A paper database: `data/papers.json`
- arXiv fetching script: `scripts/fetch_arxiv.py`
- Topic classification and BibTeX generation
- Search, topic filtering, tag filtering, sorting, local favorites, CSV export, BibTeX export
- GitHub Actions workflow for automatic daily update

## 1. Local quick start

```bash
pip install -r requirements.txt
python scripts/fetch_arxiv.py --max-results 80
python -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

## 2. GitHub Pages deployment

1. Create a new GitHub repo, e.g. `wam-paper-hub`.
2. Upload all files in this folder.
3. Go to `Settings -> Pages`.
4. Set `Source` to `Deploy from a branch`.
5. Select `main` branch and `/root`.
6. Visit:

```text
https://YOUR_GITHUB_USERNAME.github.io/wam-paper-hub/
```

## 3. Daily auto update

The workflow file is located at:

```text
.github/workflows/update.yml
```

It runs daily and updates `data/papers.json` automatically.

You can also manually trigger it from GitHub:

```text
Actions -> Update WAM Paper Hub -> Run workflow
```

## 4. Customize search topics

Edit this file:

```text
scripts/fetch_arxiv.py
```

Main places to customize:

- `SEARCH_QUERIES`
- `TOPIC_RULES`
- `VENUE_RULES`

## 5. Suggested repo name

```text
wam-paper-hub
world-model-paper-hub
uav-world-model-hub
```

## 6. Suggested domain

```text
wampaper.top
worldmodel.top
uavworldmodel.top
```

If you use a custom domain, create a `CNAME` file with your domain name.
