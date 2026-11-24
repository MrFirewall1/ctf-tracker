"""Git for datamappen. Alle kall er liste-argumenter (aldri shell), kjører i datamappen,
og kan aldri henge på passordspørsmål. Push skjer bare når du trykker på knappen."""
import os
import re
import subprocess
from pathlib import Path

from .storage import check_data_dir

BRANCH = "main"
# Bare ssh/https-URL-er. Alt som starter med '-' avvises (flagg-injeksjon).
REMOTE_RE = re.compile(
    r"^(git@[\w.-]+:[\w./~-]+|ssh://[\w@.:/~-]+|https://[\w.-]+(:\d+)?/[\w./~-]+)$"
)


class GitError(Exception):
    pass


def _run(data_dir, *args, timeout: int = 30, check: bool = True) -> subprocess.CompletedProcess:
    env = {
        **os.environ,
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_SSH_COMMAND": os.environ.get("GIT_SSH_COMMAND", "ssh -o BatchMode=yes -o ConnectTimeout=10"),
    }
    # safe.directory: SSD-er på /mnt/<stasjon> eier ofte ikke filene slik git forventer
    cmd = ["git", "-c", f"safe.directory={data_dir}", *args]
    try:
        p = subprocess.run(cmd, cwd=data_dir, capture_output=True, text=True,
                           timeout=timeout, env=env)
    except FileNotFoundError:
        raise GitError("git er ikke installert.") from None
    except subprocess.TimeoutExpired:
        raise GitError("git brukte for lang tid. Sjekk nett og SSH-nøkkel.") from None
    if check and p.returncode != 0:
        raise GitError((p.stderr or p.stdout).strip() or f"git {args[0]} feilet")
    return p


def is_repo(data_dir) -> bool:
    return (Path(data_dir) / ".git").exists()


def validate_remote(url: str) -> str:
    url = (url or "").strip()
    if not REMOTE_RE.match(url):
        raise GitError("Ugyldig repo-URL. Bruk f.eks. git@github.com:bruker/repo.git")
    return url


def init_repo(data_dir, remote: str | None = None) -> str:
    """Setter opp git i en eksisterende, initialisert datamappe. Trygg å kjøre flere ganger."""
    d = check_data_dir(data_dir)
    if remote:
        remote = validate_remote(remote)
    if not is_repo(d):
        _run(d, "init", "-b", BRANCH)
    # Egen identitet bare i dette repoet, og bare hvis du ikke har en fra før.
    if not _run(d, "config", "user.name", check=False).stdout.strip():
        _run(d, "config", "--local", "user.name", "CTF-tracker")
    if not _run(d, "config", "user.email", check=False).stdout.strip():
        _run(d, "config", "--local", "user.email", "ctf-tracker@localhost")
    if remote:
        has = _run(d, "remote", "get-url", "origin", check=False).returncode == 0
        _run(d, "remote", "set-url" if has else "add", "origin", remote)
    _run(d, "add", "--", ".gitignore", ".ctf-tracker", "tasks")
    if _run(d, "diff", "--cached", "--quiet", check=False).returncode == 1:
        _run(d, "commit", "-m", "Initialiser CTF-datamappe")
    return f"Git-repo klart i {d}" + (f", remote origin = {remote}" if remote else "")


def commit_task(data_dir, task_id: str, title: str, created: bool) -> dict:
    """Committer akkurat denne oppgavefilen. Feiler aldri høyt: lagringen er allerede gjort."""
    d = Path(data_dir)
    if not is_repo(d):
        return {"status": "no-repo",
                "message": "Ikke et git-repo ennå. Kjør: python -m app git-init <repo-url>"}
    rel = f"tasks/{task_id}.md"
    msg = f"{'Legg til' if created else 'Oppdater'} oppgave: {' '.join(title.split())[:120]}"
    try:
        _run(d, "add", "--", rel)
        if _run(d, "diff", "--cached", "--quiet", "--", rel, check=False).returncode == 0:
            return {"status": "unchanged", "message": "Ingen endringer å committe."}
        _run(d, "commit", "-m", msg, "--", rel)
    except GitError as e:
        return {"status": "error", "message": str(e)}
    return {"status": "committed", "message": msg}


def status(data_dir) -> dict:
    d = check_data_dir(data_dir, writable=False)
    if not is_repo(d):
        return {"repo": False}
    out = {"repo": True, "branch": None, "remote": None, "dirty": 0, "ahead": None, "log": []}
    try:
        b = _run(d, "rev-parse", "--abbrev-ref", "HEAD", check=False)
        out["branch"] = b.stdout.strip() if b.returncode == 0 else BRANCH
        r = _run(d, "remote", "get-url", "origin", check=False)
        out["remote"] = r.stdout.strip() if r.returncode == 0 else None
        out["dirty"] = len(_run(d, "status", "--porcelain").stdout.splitlines())
        has_commits = _run(d, "rev-parse", "--verify", "HEAD", check=False).returncode == 0
        if has_commits:
            up = _run(d, "rev-list", "--count", "@{u}..HEAD", check=False)
            if up.returncode == 0:
                out["ahead"] = int(up.stdout.strip() or 0)
            else:  # ingen upstream ennå: alt er upushet
                out["ahead"] = int(_run(d, "rev-list", "--count", "HEAD").stdout.strip() or 0)
            out["log"] = _run(d, "log", "-5", "--format=%h %s").stdout.splitlines()
        else:
            out["ahead"] = 0
    except GitError as e:
        out["error"] = str(e)
    return out


def push(data_dir) -> str:
    d = check_data_dir(data_dir)
    if not is_repo(d):
        raise GitError("Datamappen er ikke et git-repo. Kjør: python -m app git-init <repo-url>")
    if _run(d, "remote", "get-url", "origin", check=False).returncode != 0:
        raise GitError("Ingen remote 'origin'. Kjør: python -m app git-init <repo-url>")
    if _run(d, "rev-parse", "--verify", "HEAD", check=False).returncode != 0:
        raise GitError("Ingenting å pushe ennå: ingen commits.")
    p = _run(d, "push", "-u", "origin", "HEAD", timeout=90, check=False)
    text = (p.stderr + p.stdout).strip()
    if p.returncode != 0:
        hint = ""
        if "Permission denied" in text or "publickey" in text:
            hint = "\n\nSSH-nøkkelen er ikke godkjent av GitHub, eller krever passfrase (bruk ssh-agent)."
        raise GitError(text + hint)
    return text or "Pushet."
