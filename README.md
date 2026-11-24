# CTF-tracker

A small **local, offline** web app that helps you get better at CTFs: log every challenge you try, write your own explanation,
see where you are weak, and get a nudge toward what to practice next.

- **No AI features, no external APIs, no CDN, no telemetry.** It runs on `127.0.0.1` and your notes stay on your disk.
- One Markdown file per logged challenge, kept in a folder you choose (put it in a private git repo if you like).
- Works on Linux and on Windows via WSL. Python 3.10+. macOS should work for the app itself but is untested (the `run.sh` helper that stops an old copy uses Linux tools).

> The user interface is currently in **Norwegian** (the catalog texts also have an English/Norwegian toggle).
> Translating the UI is a welcome contribution, see [CONTRIBUTING.md](CONTRIBUTING.md). Norwegian docs: [README.no.md](README.no.md).

## Quick start

```bash
git clone https://github.com/<you>/ctf-tracker.git
cd ctf-tracker
./setup.sh          # creates .venv, installs dependencies, makes ~/ctf-tracker-data
./run.sh            # starts the app and opens http://127.0.0.1:5000
```

Stop it with **Ctrl+C**. `run.sh` also stops an old copy of the app that is still holding the port.
Use another data folder with `CTF_DATA_DIR=/path ./setup.sh`, or edit `config.json` (see `config.example.json`).

## Tailor it to what you struggle with

| What | Where |
|---|---|
| **Weakest areas** by category and protocol (needs at least 2 logged tasks) | Dashboard |
| **Recommended for you**: the next unlogged task in your weakest area, easy before medium before hard | Dashboard, "Next missions" |
| Filter the dashboard by category, difficulty and protocol | Dashboard |
| Tasks to **revisit** (solved with a hint or the solution, and not solved cleanly later) | Dashboard |
| A guided **warm-up**: intro to every category and two small tasks in each | Warm-up |
| ~255 practice tasks with search, filters, XP per task and step-by-step "how to start" | Tasks |
| **Answer checking** for the built-in labs (random flags generated on your machine) | Tasks / Warm-up |
| Your own **video links** per category (YouTube, click-to-play, max 30 min each) | Warm-up |
| A **phone reminder** as a calendar file (`.ics`) | Reminder |
| A **PDF report** of what you logged, with your own words | Report |

XP: easy 10, medium 25, hard 50. Solved alone gives full XP, with a hint 70 %, with the solution 20 %.
"Solved" in the statistics means solved alone or with a hint. Solved with the solution counts as *not* solved, so weak spots are not hidden.

### Add your own tasks

`app/practice.json` is a plain list. Add an entry and it shows up under **Tasks**:

```json
{
  "id": "my-first-task", "kind": "custom", "title": "Login bypass", "source": "My CTF · Team practice",
  "url": "", "category": "web", "protocol": "", "difficulty": "easy",
  "objective": "Get into the admin page.", "hints": ["Look at the cookies."], "tags": ["web"],
  "no": {"title": "Innloggingsomgåelse", "objective": "Kom deg inn på admin-siden.", "hints": ["Se på cookies."]}
}
```

Categories: `pcap_ics`, `web`, `crypto`, `reversing`, `forensics`, `other`. Difficulties: `easy`, `medium`, `hard`.
Edit `INTROS` in `app/intro.py` to change the category introductions, and `WARMUP_TASKS` to pick the two warm-up tasks per category.

## Where your data lives

- `<data_dir>/tasks/YYYY-MM-DD-title.md`: one file per logged task, YAML front matter plus your Markdown explanation.
- `<data_dir>/videos.json`: your video links. `<data_dir>/reports/`: generated PDFs (ignored by git).
- Writes are atomic (temp file, `fsync`, rename). If the folder is missing or the drive is not mounted, the app shows a red banner and refuses to save.

**Do not log real company data, passwords, tokens or real network traffic.** If you push your data folder to GitHub, treat it as shared.

## Optional: git backup of your notes

```bash
.venv/bin/python -m app git-init git@github.com:<you>/ctf-data.git   # once, repo must be empty
```

Each logged task is committed. Pushing is manual (button on the **Git** page). Only ssh and https remotes are accepted.

## Built-in practice labs

```bash
.venv/bin/python -m labs generate ~/ctf-labs          # random flags, only hashes are stored
.venv/bin/python -m labs check ~/ctf-labs hidden-file 'CTF{...}'
```

Labs: `hidden-file`, `log-secret`, `env-leak`, `modbus-flag` (a small PCAP with synthetic addresses). The warm-up and task pages can check your answer too.

## About the task catalog

The catalog only **points** to practice material (titles, categories, links, short generic hints). It contains no solutions, flags or challenge files.
Sources and licenses are listed in [NOTICE.md](NOTICE.md). Open each challenge on its own platform; some need a free account.
Optional PCAP datasets (ICS-PCAP-Challenges) are downloaded separately; set `downloads_dir` to show which files you already have.

## Development

```bash
.venv/bin/python -m pytest
```

Templates reload automatically, so you only need to refresh the browser after editing a template. Restart after changing Python code.
Please use practice targets you own or are allowed to test.

## License

MIT, see [LICENSE](LICENSE). Third-party notices are in [NOTICE.md](NOTICE.md).
