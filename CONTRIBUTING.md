# Contributing

Thanks for helping people get better at CTFs. Small, focused pull requests are easiest to review.

## Ground rules

- **Keep it offline.** No AI features, no external API calls, no CDN, no telemetry. The only network use is links the user clicks, and the optional click-to-play video, which loads nothing until the user presses play.
- **No solutions, flags or challenge files** in the catalog. Titles, categories, difficulty, links and short generic hints only. Respect each platform's rules.
- **Never commit personal data**: no `config.json`, no data folders, no tokens, usernames or paths from your own machine.
- Add or update **tests** for what you change: `.venv/bin/python -m pytest` must pass.

## Good first contributions

- Translate the UI (templates in `app/templates/`, text in `app/intro.py`) or add an English UI.
- More practice entries in `app/practice.json` (see the format in the README) with accurate difficulty and a working link.
- Better category introductions and "how to start" steps.
- Packaging for Windows without WSL, and macOS testing.

## Setup

```bash
./setup.sh && .venv/bin/python -m pytest
```

Use only targets you own or have permission to test.
