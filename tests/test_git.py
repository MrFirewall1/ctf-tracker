import subprocess

import pytest

from app import gitops
from app.storage import init_data_dir
from app.web import create_app


@pytest.fixture(autouse=True)
def isolated_git(tmp_path, monkeypatch):
    """Ingen global git-konfig: testen skal ikke avhenge av (eller endre) din egen."""
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "nonexistent"))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout


def task(**kw):
    base = dict(title="Modbus æøå", date="2026-03-02", category="pcap_ics", protocol="modbus",
                difficulty="easy", status="solved_alone", body="## Hva jeg lærte\n\nnoe\n")
    base.update(kw)
    return base


@pytest.fixture
def data(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    return d


@pytest.fixture
def remote(tmp_path):
    r = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(r)], check=True)
    return r


def test_init_repo_commits_base_files_and_sets_identity(data):
    gitops.init_repo(data)
    files = git(data, "ls-files").split()
    assert ".gitignore" in files and ".ctf-tracker" in files
    assert git(data, "log", "--format=%s").strip() == "Initialiser CTF-datamappe"
    assert git(data, "config", "--local", "user.email").strip() == "ctf-tracker@localhost"
    gitops.init_repo(data)  # idempotent
    assert len(git(data, "log", "--format=%s").splitlines()) == 1


def test_save_autocommits_with_message_template(data):
    gitops.init_repo(data)
    client = create_app(str(data)).test_client()
    r = client.post("/api/tasks", json=task())
    assert r.get_json()["git"]["status"] == "committed"
    tid = r.get_json()["task"]["id"]
    assert git(data, "log", "-1", "--format=%s").strip() == "Legg til oppgave: Modbus æøå"
    assert git(data, "status", "--porcelain").strip() == ""
    # uendret lagring: ingen ny commit
    assert client.put(f"/api/tasks/{tid}", json=task()).get_json()["git"]["status"] == "unchanged"
    r = client.put(f"/api/tasks/{tid}", json=task(hints_used=2))
    assert r.get_json()["git"]["status"] == "committed"
    assert git(data, "log", "-1", "--format=%s").strip() == "Oppdater oppgave: Modbus æøå"


def test_gitignore_excludes_pdf_tmp_and_sqlite(data):
    gitops.init_repo(data)
    (data / "reports").mkdir()
    for name in ("reports/r.pdf", "x.pdf", ".task.md.123.tmp", "index.sqlite", "index.db"):
        (data / name).write_text("x")
    assert git(data, "status", "--porcelain").strip() == ""


def test_title_with_newlines_cannot_break_message(data):
    gitops.init_repo(data)
    client = create_app(str(data)).test_client()
    client.post("/api/tasks", json=task(title="Linje1\nLinje2 -rf"))
    assert git(data, "log", "-1", "--format=%s").strip() == "Legg til oppgave: Linje1 Linje2 -rf"


def test_save_works_without_repo_and_when_git_fails(data, monkeypatch):
    client = create_app(str(data)).test_client()
    r = client.post("/api/tasks", json=task())
    assert r.status_code == 200 and r.get_json()["git"]["status"] == "no-repo"
    gitops.init_repo(data)

    def boom(*a, **k):
        raise gitops.GitError("disk full")

    monkeypatch.setattr(gitops, "_run", boom)
    r = client.post("/api/tasks", json=task(title="Ny"))
    assert r.status_code == 200 and r.get_json()["git"] == {"status": "error", "message": "disk full"}
    assert list((data / "tasks").glob("*-ny.md"))  # filen er lagret uansett


def test_push_is_manual_and_works(data, remote):
    gitops.init_repo(data)
    git(data, "remote", "add", "origin", str(remote))  # lokal sti: bare i test, valideringen krever ssh/https
    client = create_app(str(data)).test_client()
    client.post("/api/tasks", json=task())
    # auto-commit pusher ikke
    assert subprocess.run(["git", "--git-dir", str(remote), "log"], capture_output=True).returncode != 0
    st = client.get("/api/git/status").get_json()
    assert st["repo"] and st["ahead"] == 2 and st["remote"] == str(remote) and st["dirty"] == 0
    r = client.post("/api/git/push", json={})
    assert r.status_code == 200
    log = git(data, "--git-dir", str(remote), "log", "--format=%s").splitlines()
    assert log[0] == "Legg til oppgave: Modbus æøå" and len(log) == 2
    assert client.get("/api/git/status").get_json()["ahead"] == 0


def test_push_errors_are_clean(data):
    client = create_app(str(data)).test_client()
    assert client.post("/api/git/push", json={}).status_code == 400  # ikke repo
    gitops.init_repo(data)
    r = client.post("/api/git/push", json={})
    assert r.status_code == 400 and "origin" in r.get_json()["error"]
    assert client.post("/api/git/push", data="x=1").status_code == 400  # ikke JSON


def test_push_refused_without_ssd(tmp_path):
    client = create_app(str(tmp_path / "ikke-montert")).test_client()
    assert client.post("/api/git/push", json={}).status_code == 503
    assert client.get("/api/git/status").status_code == 503


@pytest.mark.parametrize("url", ["--upload-pack=touch /tmp/x", "-oProxyCommand=x", "file:///etc",
                                 "git@github.com:a/b.git; rm -rf ~", "http://x/y", "/tmp/lokal"])
def test_bad_remote_urls_rejected(data, url):
    with pytest.raises(gitops.GitError):
        gitops.init_repo(data, url)
    assert not (data / ".git").exists()


def test_good_remote_urls_accepted():
    for u in ("git@github.com:bruker/ctf-data.git", "https://github.com/bruker/ctf-data.git",
              "ssh://git@github.com/bruker/ctf-data.git"):
        assert gitops.validate_remote(u) == u
