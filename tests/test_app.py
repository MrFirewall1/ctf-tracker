from datetime import date

import pytest

from app import storage
from app.stats import compute_stats, streaks
from app.storage import DataDirError, init_data_dir, list_tasks, parse_task_file, save_task
from app.web import create_app


def task(**kw):
    base = dict(
        title="Modbus coils", date="2026-03-02", source="ICS-PCAP-Challenges",
        category="pcap_ics", protocol="modbus", difficulty="easy", time_minutes=30,
        tools="wireshark, tshark", tags="coils", status="solved_alone", hints_used=0,
        resolved_later=False, body="## Hva jeg lærte\n\nFilter: `modbus.func_code == 5`\n",
    )
    base.update(kw)
    return base


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    return d


# --- filparsing ---------------------------------------------------------------

def test_roundtrip_preserves_text_exactly(data_dir):
    body = "## Kommandoer/filtre jeg brukte\n\n```\ntshark -r a.pcap -Y 'x: y'\n```\næøå ---\n"
    saved = save_task(data_dir, task(body=body, title="Tittel: med kolon # og æøå"))
    path = data_dir / "tasks" / f"{saved['id']}.md"
    assert path.read_text(encoding="utf-8").startswith("---\ntitle:")
    again = parse_task_file(path.read_text(encoding="utf-8"), saved["id"])
    assert again["body"].rstrip("\n") == body.rstrip("\n")
    assert again["title"] == "Tittel: med kolon # og æøå"
    assert again["tools"] == ["wireshark", "tshark"]
    assert again["date"] == "2026-03-02"


def test_parse_rejects_missing_frontmatter_and_bad_values():
    with pytest.raises(ValueError):
        parse_task_file("bare tekst", "x")
    with pytest.raises(ValueError):
        parse_task_file("---\ntitle: a\ndate: 2026-01-01\ncategory: nope\n---\n", "x")


def test_broken_file_is_reported_not_fatal(data_dir):
    save_task(data_dir, task())
    (data_dir / "tasks" / "ødelagt.md").write_text("ingen frontmatter", encoding="utf-8")
    tasks, errors = list_tasks(data_dir)
    assert len(tasks) == 1 and errors[0]["file"] == "ødelagt.md"


def test_ids_are_unique_and_safe(data_dir):
    a = save_task(data_dir, task())
    b = save_task(data_dir, task())
    assert a["id"] != b["id"]
    with pytest.raises(ValueError):
        save_task(data_dir, task(), task_id="../../etc/passwd")


def test_update_keeps_id(data_dir):
    a = save_task(data_dir, task())
    b = save_task(data_dir, task(title="Nytt navn", hints_used=2), task_id=a["id"])
    assert b["id"] == a["id"]
    assert len(list_tasks(data_dir)[0]) == 1


def test_atomic_write_leaves_no_tmp_and_cleans_up_on_failure(data_dir, monkeypatch):
    save_task(data_dir, task())
    assert not list((data_dir / "tasks").glob("*.tmp"))

    def boom(*a, **k):
        raise OSError("SSD trukket ut")

    monkeypatch.setattr(storage.os, "replace", boom)
    with pytest.raises(OSError):
        save_task(data_dir, task(title="Annen"))
    assert not list((data_dir / "tasks").glob("*.tmp"))
    assert len(list((data_dir / "tasks").glob("*.md"))) == 1


# --- statistikk ---------------------------------------------------------------

def mk(d, status="solved_alone", cat="pcap_ics", proto="modbus", diff="easy", minutes=10):
    return dict(id=f"id-{d}-{status}", title="t", date=d, category=cat, protocol=proto, difficulty=diff,
                time_minutes=minutes, status=status, hints_used=0, resolved_later=False,
                tools=[], tags=[], source="", body="")


def test_solve_rates_count_fasit_as_unsolved():
    tasks = [
        mk("2026-03-02", "solved_alone"),
        mk("2026-03-03", "solved_hint"),
        mk("2026-03-04", "solved_solution"),
        mk("2026-03-05", "unsolved", cat="web", proto=""),
    ]
    s = compute_stats(tasks, today=date(2026, 3, 5))
    assert s["totals"]["solved"] == 2 and s["totals"]["rate"] == 0.5
    cat = {r["key"]: r for r in s["by_category"]}
    assert cat["pcap_ics"]["rate"] == pytest.approx(2 / 3, abs=1e-3)
    assert cat["web"]["rate"] == 0.0
    assert [r["key"] for r in s["by_protocol"]] == ["modbus"]  # tom protokoll utelates
    assert {x["key"]: x["count"] for x in s["status_share"]}["solved_solution"] == 1


def test_weakest_needs_min_samples():
    tasks = [mk("2026-03-02", "unsolved", cat="web", proto="")]
    assert compute_stats(tasks, today=date(2026, 3, 2))["weakest"] == []
    tasks.append(mk("2026-03-03", "unsolved", cat="web", proto=""))
    w = compute_stats(tasks, today=date(2026, 3, 3))["weakest"]
    assert w and w[0]["key"] == "web"


def test_streaks():
    ds = {date(2026, 3, d) for d in (1, 2, 3, 7, 8)}
    assert streaks(ds, date(2026, 3, 8)) == (2, 3)
    assert streaks(ds, date(2026, 3, 9)) == (2, 3)   # i går teller fortsatt
    assert streaks(ds, date(2026, 3, 12)) == (0, 3)  # brutt
    assert streaks(set(), date(2026, 3, 1)) == (0, 0)


def test_hint_trend_learning_and_revisit():
    a = mk("2026-03-02", "solved_hint")
    a.update(hints_used=3, body="## Hva jeg lærte\n\nBruk filter\n\n## Annet\n")
    b = mk("2026-03-03", "solved_alone")
    b.update(hints_used=1, body="## Hva jeg lærte\n\n")  # tom seksjon teller ikke
    c = mk("2026-03-10", "unsolved")
    c.update(id="c", title="C", hints_used=0)
    a["id"], b["id"] = "a", "b"
    s = compute_stats([a, b, c], today=date(2026, 3, 10))
    assert s["totals"]["avg_hints"] == pytest.approx(1.33, abs=0.01)
    assert s["totals"]["explained"] == 1
    assert s["hints_over_time"]["avg_hints"] == [2.0, 0.0]
    assert [x["id"] for x in s["to_revisit"]] == ["a", "c"]
    c["resolved_later"] = True
    s = compute_stats([a, b, c], today=date(2026, 3, 10))
    assert [x["id"] for x in s["to_revisit"]] == ["a"]


def test_weekly_series_fill_gaps():
    tasks = [mk("2026-01-05", minutes=20), mk("2026-02-16", "unsolved", diff="hard", minutes=60)]
    s = compute_stats(tasks, today=date(2026, 2, 16))
    labels = s["solved_over_time"]["labels"]
    assert labels[0] == "2026-U02" and labels[-1] == "2026-U08" and len(labels) == 7
    assert s["solved_over_time"]["cumulative"][-1] == 1
    assert sum(s["sessions_per_week"]["days"]) == 2
    assert s["hints_over_time"]["avg_hints"][1] is None  # uke uten oppgaver


def test_empty_stats():
    s = compute_stats([])
    assert s["totals"]["tasks"] == 0 and s["weakest"] == []


# --- SSD-vakt -----------------------------------------------------------------

def test_refuses_to_write_when_path_missing(tmp_path):
    missing = tmp_path / "ikke-montert"
    with pytest.raises(DataDirError):
        save_task(missing, task())
    assert not missing.exists()  # ingenting opprettet i stillhet
    assert list(tmp_path.iterdir()) == []


def test_refuses_when_dir_exists_but_not_initialised(tmp_path):
    empty_mountpoint = tmp_path / "mnt"
    empty_mountpoint.mkdir()
    with pytest.raises(DataDirError):
        save_task(empty_mountpoint, task())
    assert list(empty_mountpoint.iterdir()) == []


def test_refuses_when_unset():
    with pytest.raises(DataDirError):
        save_task(None, task())


def test_init_does_not_create_root(tmp_path):
    with pytest.raises(DataDirError):
        init_data_dir(tmp_path / "finnes-ikke")
    assert list(tmp_path.iterdir()) == []


def test_api_returns_503_and_writes_nothing_when_missing(tmp_path):
    missing = tmp_path / "ikke-montert"
    client = create_app(str(missing)).test_client()
    r = client.post("/api/tasks", json=task())
    assert r.status_code == 503 and "finnes ikke" in r.get_json()["error"]
    assert client.get("/api/stats").status_code == 503
    page = client.get("/")
    assert page.status_code == 200 and "Ingenting kan lagres" in page.get_data(as_text=True)
    assert not missing.exists() and list(tmp_path.iterdir()) == []


def test_api_end_to_end(data_dir):
    client = create_app(str(data_dir)).test_client()
    r = client.post("/api/tasks", json=task())
    assert r.status_code == 200
    tid = r.get_json()["task"]["id"]
    assert client.put(f"/api/tasks/{tid}", json=task(title="Endret")).status_code == 200
    assert client.put("/api/tasks/finnes-ikke", json=task()).status_code == 404
    assert client.post("/api/tasks", json=task(category="x")).status_code == 400
    stats = client.get("/api/stats").get_json()["stats"]
    assert stats["totals"]["tasks"] == 1
    assert client.get("/tasks").status_code == 200
    assert client.get(f"/tasks/{tid}").status_code == 200
    assert client.get("/tasks/ugyldig..id").status_code == 404


def test_preview_renders_code_and_escapes_html(data_dir):
    client = create_app(str(data_dir)).test_client()
    html = client.post("/api/preview", json={"text": "```\nx\n```\n<script>alert(1)</script>"}).get_json()["html"]
    assert "<pre><code>" in html and "<script>" not in html


def test_practice_catalog_is_valid():
    import json
    from pathlib import Path
    from app import constants
    entries = json.loads((Path(__file__).parent.parent / "app" / "practice.json").read_text(encoding="utf-8"))
    ids = [e["id"] for e in entries]
    assert len(ids) == len(set(ids))
    for e in entries:
        assert e["category"] in constants.CATEGORIES
        assert e["protocol"] in constants.PROTOCOLS
        assert e["difficulty"] in constants.DIFFICULTIES
        assert e["title"] and e["objective"] and isinstance(e["hints"], list)


def test_practice_page_renders_with_filters(tmp_path):
    from app.storage import init_data_dir
    d = tmp_path / "ssd"; d.mkdir(); init_data_dir(d)
    r = create_app(str(d)).test_client().get("/practice")
    assert r.status_code == 200
    html = r.get_data(as_text=True)
    assert 'id="f-diff"' in html and "scripts/fetch.py" in html


def test_practice_is_bilingual_and_prefill_follows_language(tmp_path):
    import json
    from pathlib import Path
    from app.storage import init_data_dir
    entries = json.loads((Path(__file__).parent.parent / "app" / "practice.json").read_text(encoding="utf-8"))
    for e in entries:
        assert e["no"]["title"] and e["no"]["objective"] and len(e["no"]["hints"]) == len(e["hints"])
    e = next(x for x in entries if x["id"] == "ics-ot-coimbra-clean")
    assert "Characterize the traffic" in e["objective"] and "Karakteriser trafikken" in e["no"]["objective"]
    d = tmp_path / "ssd"; d.mkdir(); init_data_dir(d)
    c = create_app(str(d)).test_client()
    en = c.get("/tasks/new?practice=ics-ot-coimbra-clean&lang=en").get_data(as_text=True)
    no = c.get("/tasks/new?practice=ics-ot-coimbra-clean&lang=no").get_data(as_text=True)
    assert "Characterize the traffic" in en and "Karakteriser trafikken" in no
    page = c.get("/practice").get_data(as_text=True)
    assert 'class="t-en"' in page and 'class="t-no"' in page and "langbtn" in page


def _mk(c, title, category, difficulty, status="solved_alone", protocol=""):
    r = c.post("/api/tasks", json={"title": title, "date": "2026-03-02", "category": category, "protocol": protocol,
                                   "difficulty": difficulty, "status": status})
    assert r.status_code == 200


def test_stats_filter_by_category_difficulty_protocol(tmp_path):
    d = tmp_path / "ssd"; d.mkdir(); init_data_dir(d)
    c = create_app(str(d)).test_client()
    _mk(c, "a", "pcap_ics", "easy", protocol="modbus")
    _mk(c, "b", "pcap_ics", "hard", status="unsolved", protocol="dnp3")
    _mk(c, "c", "web", "easy")
    tot = lambda q: c.get("/api/stats" + q).get_json()["stats"]["totals"]["tasks"]
    assert tot("") == 3 and tot("?category=pcap_ics") == 2 and tot("?category=web") == 1
    assert tot("?difficulty=easy") == 2 and tot("?category=pcap_ics&difficulty=easy") == 1
    assert tot("?protocol=dnp3") == 1 and tot("?category=reversing") == 0
    assert c.get("/api/stats?category=ukjent").status_code == 400


def test_dashboard_and_tasks_have_filters_and_intros(tmp_path):
    d = tmp_path / "ssd"; d.mkdir(); init_data_dir(d)
    c = create_app(str(d)).test_client()
    dash = c.get("/").get_data(as_text=True)
    assert 'id="f-category"' in dash and 'id="f-difficulty"' in dash and "Nøkkelbegreper" in dash or "intros-data" in dash
    from app.intro import INTROS
    from app import constants
    assert set(INTROS) == set(constants.CATEGORIES)
    for i in INTROS.values():
        assert i["summary"] and i["terms"] and i["start"] and i["tools"]
    tasks = c.get("/tasks").get_data(as_text=True)
    assert 'id="f-difficulty"' in tasks and 'id="f-protocol"' in tasks


def test_practice_shows_file_status_and_windows_path(tmp_path, monkeypatch):
    from app import intro
    assert intro._windows_path("/mnt/d/ctf-downloads/x/y.pcap") == "D:\\ctf-downloads\\x\\y.pcap"
    assert intro._windows_path("/home/bruker/x") is None
    dl = tmp_path / "dl"; (dl / "ds").mkdir(parents=True); (dl / "ds" / "a.pcap").write_text("x")
    info = intro.file_info(str(dl), ["data/ds/a.pcap", "data/ds/b.pcap"])
    assert info[0]["exists"] is True and info[1]["exists"] is False and info[0]["rel"] == "ds/a.pcap"
    assert intro.file_info(None, ["data/ds/a.pcap"])[0]["exists"] is None
    d = tmp_path / "ssd"; d.mkdir(); init_data_dir(d)
    monkeypatch.setenv("CTF_DOWNLOADS_DIR", str(dl))
    page = create_app(str(d)).test_client().get("/practice").get_data(as_text=True)
    assert "Åpne oppgaven (filer)" in page and "Hvordan åpner jeg en oppgave?" in page and 'id="f-cat"' in page


def test_download_route_is_confined_to_downloads_dir(tmp_path, monkeypatch):
    dl = tmp_path / "dl"; (dl / "ds").mkdir(parents=True)
    (dl / "ds" / "a.pcap").write_bytes(b"PCAP")
    (tmp_path / "secret.txt").write_text("hemmelig")
    (dl / "ds" / "lenke").symlink_to(tmp_path / "secret.txt")
    d = tmp_path / "ssd"; d.mkdir(); init_data_dir(d)
    c = create_app(str(d)).test_client()
    assert c.get("/dl/ds/a.pcap").status_code == 404          # ingen nedlastingsmappe satt
    monkeypatch.setenv("CTF_DOWNLOADS_DIR", str(dl))
    r = c.get("/dl/ds/a.pcap")
    assert r.status_code == 200 and r.data == b"PCAP" and "attachment" in r.headers["Content-Disposition"]
    for bad in ("ds/lenke", "../secret.txt", "ds/../../secret.txt", "ds", "finnes-ikke"):
        assert c.get("/dl/" + bad).status_code == 404, bad
    page = c.get("/practice").get_data(as_text=True)
    assert "Last ned" not in page or "/dl/" in page


def test_catalog_summary_counts_ready_partial_missing(tmp_path, monkeypatch):
    from app import intro
    assert intro.readiness([]) == "nofiles"
    assert intro.readiness([{"exists": True}, {"exists": True}]) == "ready"
    assert intro.readiness([{"exists": True}, {"exists": False}]) == "partial"
    assert intro.readiness([{"exists": False}]) == "missing"
    assert intro.readiness([{"exists": None}]) == "unknown"
    entries = [{"id": "a", "difficulty": "easy", "category": "pcap_ics", "protocol": "modbus", "ready": "ready"},
               {"id": "b", "difficulty": "easy", "category": "pcap_ics", "protocol": "dnp3", "ready": "missing"},
               {"id": "c", "difficulty": "hard", "category": "web", "protocol": "", "ready": "partial"}]
    s = intro.catalog_summary(entries, {"a"}, {})
    assert s["total"] == {"total": 3, "ready": 1, "partial": 1, "missing": 1, "logged": 1}
    assert intro.catalog_summary(entries, set(), {"category": "pcap_ics"})["total"]["total"] == 2
    d = tmp_path / "ssd"; d.mkdir(); init_data_dir(d)
    c = create_app(str(d)).test_client()
    r = c.get("/api/catalog?difficulty=easy")
    assert r.status_code == 200 and r.get_json()["total"]["total"] > 20
    assert 'id="catalog"' in c.get("/").get_data(as_text=True)


def test_xp_levels_and_heatmap():
    from datetime import date
    from app import xp
    today = date(2026, 11, 24)
    tasks = [
        {"date": "2026-11-24", "difficulty": "easy", "status": "solved_alone", "category": "web"},
        {"date": "2026-11-23", "difficulty": "medium", "status": "solved_hint", "category": "web"},
        {"date": "2026-11-23", "difficulty": "hard", "status": "solved_solution", "category": "crypto"},
        {"date": "2026-11-20", "difficulty": "hard", "status": "unsolved", "category": "crypto"},
    ]
    r = xp.compute_xp(tasks, today)
    assert r["xp"] == 10 + round(25 * 0.7) + round(50 * 0.2)   # 10 + 18 + 10
    assert r["level"]["name"] == "Nybegynner" and r["level"]["to_next"] == 100 - r["xp"]
    assert r["streak"]["current"] == 2 and r["week_xp"] == r["xp"]
    assert r["heatmap"][-1] == {"date": "2026-11-24", "n": 1}
    assert {s["key"]: s["xp"] for s in r["skills"]}["web"] == 28
    assert xp.level_for(100)["name"] == "Lærling" and xp.level_for(99999)["next_name"] is None
    assert xp.compute_xp([], today)["xp"] == 0


def test_new_pages_render_and_nav(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    c = create_app(str(d)).test_client()
    assert "ctf" in c.get("/").get_data(as_text=True) and c.get("/api/xp").get_json()["xp"] == 0
    w = c.get("/warmup").get_data(as_text=True)
    assert "Oppvarming" in w and "Slik starter du" in w and "Log Hunt" in w and w.count('class="cat-icon"') == 12
    p = c.get("/practice").get_data(as_text=True)
    assert "<h1>Oppgaver" in p and "Slik starter du" in p
    assert "Påminnelse" in c.get("/reminder").get_data(as_text=True)


def test_reminder_ics_is_valid_and_rejects_bad_input(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    c = create_app(str(d)).test_client()
    r = c.get("/reminder.ics?time=18:30&day=MO&day=FR&text=Tid%20for%20CTF")
    assert r.status_code == 200 and r.mimetype == "text/calendar"
    body = r.get_data(as_text=True)
    assert "RRULE:FREQ=WEEKLY;BYDAY=MO,FR" in body and "TRIGGER:PT0M" in body and "T183000" in body
    assert c.get("/reminder.ics?time=25:99").status_code == 400
    assert c.get("/reminder.ics?time=18:30&day=XX").status_code == 400
    inj = c.get("/reminder.ics?time=18:30&text=a%0D%0AEND:VEVENT%0D%0AX:y").get_data(as_text=True)
    assert inj.split("\r\n").count("END:VEVENT") == 1   # linjeskift i teksten fjernes, ingen ekte ny linje


def test_task_cards_have_illustrations(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    c = create_app(str(d)).test_client()
    assert c.get("/practice").get_data(as_text=True).count('class="thumb"') >= 190
    assert c.get("/warmup").get_data(as_text=True).count('class="thumb"') == 12


def test_picoctf_entries_are_valid_and_link_only():
    import json
    from pathlib import Path
    from app import constants, intro
    entries = [e for e in json.loads((Path(__file__).parent.parent / "app" / "practice.json").read_text(encoding="utf-8"))
               if e["id"].startswith("pico-")]
    assert len(entries) >= 55
    for e in entries:
        assert e["url"].startswith("https://") and e["no"]["objective"] and len(e["hints"]) == len(e["no"]["hints"])
        assert e["category"] in constants.CATEGORIES and e["difficulty"] in ("easy", "medium")
    cyl = next(e for e in entries if "cylabacademy" in e["url"])
    assert "Challenge Library" in intro.start_steps(cyl, [])[0]
    web = [e for e in entries if e["category"] == "web"]
    assert {e["id"] for e in web} == {"pico-insp3ct0r", "pico-cookies"} and all("play.picoctf.org" in e["url"] for e in web)
    assert "picoGym" in intro.start_steps(web[0], [])[0]
    assert all(" · ·" not in e["source"] and not e["source"].endswith(" ·") for e in entries)


def test_dashboard_has_next_missions_and_library_layout(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    c = create_app(str(d)).test_client()
    dash = c.get("/").get_data(as_text=True)
    assert "Neste oppdrag" in dash and "Oppvarming" in dash and "Neste lette oppgave" in dash
    page = c.get("/practice").get_data(as_text=True)
    assert 'id="f-text"' in page and 'id="pager"' in page and page.count('class="card lib-card"') >= 250


def test_sidebar_profile_shows_level_and_streak(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    c = create_app(str(d)).test_client()
    page = c.get("/practice").get_data(as_text=True)
    assert "Nybegynner" in page and "Nivå 1" in page and 'class="profile"' in page and "Daglig påminnelse" in page
    assert ">Learn<" in page and ">Resources<" in page and ">Play<" in page


def test_warmup_has_two_tasks_per_category_and_ready_state(tmp_path):
    from app import constants, intro
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    c = create_app(str(d)).test_client()
    assert set(intro.WARMUP_TASKS) == set(constants.CATEGORIES)
    from app.web import PRACTICE
    assert all(len(v) == 2 and all(i in PRACTICE for i in v) for v in intro.WARMUP_TASKS.values())
    for key, ids in intro.WARMUP_TASKS.items():
        assert all(PRACTICE[i]["category"] == key for i in ids), key
    page = c.get("/warmup").get_data(as_text=True)
    assert "0 / 2 gjort" in page and "Du er klar!" not in page
    for i in intro.WARMUP_TASKS["web"]:
        c.post("/api/tasks", json={"title": "t", "date": "2026-03-02", "category": "web", "difficulty": "easy",
                                   "status": "solved_alone", "tags": f"practice-{i}"})
    page = c.get("/warmup").get_data(as_text=True)
    assert "2 / 2 gjort" in page and "Du er klar!" in page


def test_templates_reload_without_restart(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    app = create_app(str(d))
    assert app.config["TEMPLATES_AUTO_RELOAD"] is True and app.jinja_env.auto_reload is True


def test_video_links_parse_store_and_render(tmp_path):
    from app import videos
    ok = "dQw4w9WgXcQ"
    for url in (f"https://www.youtube.com/watch?v={ok}&t=3", f"https://youtu.be/{ok}?si=x", f"https://youtube.com/embed/{ok}",
                f"https://m.youtube.com/shorts/{ok}"):
        assert videos.parse_youtube(url) == ok, url
    for bad in ("https://evil.com/watch?v=" + ok, "javascript:alert(1)", "https://youtube.com.evil.com/watch?v=" + ok,
                "https://www.youtube.com/watch?v=kort", "https://www.youtube.com/watch?v=" + ok + "<script>", "", "ftp://youtu.be/" + ok):
        assert videos.parse_youtube(bad) is None, bad
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    c = create_app(str(d)).test_client()
    r = c.post("/api/videos", json={"category": "web", "url": f"https://youtu.be/{ok}", "title": "Intro <b>web</b>", "minutes": 12})
    assert r.status_code == 200
    assert c.post("/api/videos", json={"category": "web", "url": f"https://youtu.be/{ok}", "minutes": 5}).status_code == 400   # duplikat
    other = "abcdefghijk"
    for bad in (31, 0, -4, "", "tolv", None, 99999):
        assert c.post("/api/videos", json={"category": "web", "url": f"https://youtu.be/{other}", "minutes": bad}).status_code == 400, bad
    assert c.post("/api/videos", json={"category": "web", "url": f"https://youtu.be/{other}", "minutes": 30}).status_code == 200
    assert c.post("/api/videos/remove", json={"category": "web", "id": other}).status_code == 200
    assert c.post("/api/videos", json={"category": "ukjent", "url": f"https://youtu.be/{ok}", "minutes": 5}).status_code == 400
    assert c.post("/api/videos", json={"category": "web", "url": "https://evil.com/x", "minutes": 5}).status_code == 400
    page = c.get("/warmup").get_data(as_text=True)
    assert ok in page and "12 min" in page and "Spill av" in page and "<b>web</b>" not in page and "&lt;b&gt;web" in page
    assert "vid-modal" in page and "strict-origin-when-cross-origin" in page and "no-referrer" not in page.replace("noreferrer", "")  # feil 153: YouTube krever avsender
    assert "youtube-nocookie.com/embed" in page and f'src="https://www.youtube-nocookie.com/embed/{ok}' not in page  # ingenting lastes før klikk
    assert c.post("/api/videos/remove", json={"category": "web", "id": ok}).status_code == 200
    assert ok not in c.get("/warmup").get_data(as_text=True).replace("youtube-nocookie", "")


def test_videos_unknown_length_only_when_seeded_not_via_api(tmp_path):
    from app import videos
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    videos.add(d, "web", "https://youtu.be/dQw4w9WgXcQ", "Ukjent lengde", None, allow_unknown=True)
    with pytest.raises(ValueError):
        videos.add(d, "web", "https://youtu.be/abcdefghijk", "x", None)       # uten allow_unknown
    c = create_app(str(d)).test_client()
    assert c.post("/api/videos", json={"category": "web", "url": "https://youtu.be/abcdefghijk", "minutes": None}).status_code == 400
    assert "lengde ikke sjekket" in c.get("/warmup").get_data(as_text=True)


def test_run_script_exists_and_port_is_configurable():
    import os
    from pathlib import Path
    root = Path(__file__).parent.parent
    sh = root / "run.sh"
    assert sh.is_file() and os.access(sh, os.X_OK)
    text = sh.read_text(encoding="utf-8")
    assert "kill -9" in text and "-m app" in text and "CTF_PORT" in text      # stopper kun egen app
    assert 'CTF_PORT' in (root / "app" / "__main__.py").read_text(encoding="utf-8")


def test_recommendation_targets_weakest_area():
    from app import recommend
    tasks = [{"category": "web", "status": "unsolved"}, {"category": "web", "status": "solved_alone"},
             {"category": "crypto", "status": "solved_alone"}, {"category": "crypto", "status": "solved_hint"},
             {"category": "forensics", "status": "solved_solution"}, {"category": "forensics", "status": "unsolved"}]
    order = [w["key"] for w in recommend.weak_categories(tasks)]
    assert order[:2] == ["forensics", "web"]                      # 0 % før 50 %; crypto (100 %) er ikke «svak»
    assert set(order) == {"forensics", "web", "pcap_ics", "reversing", "other"}   # crypto (2/2 løst) er ikke svak og ikke uprøvd
    entries = [{"id": "a", "category": "web", "difficulty": "medium"}, {"id": "b", "category": "web", "difficulty": "easy"},
               {"id": "c", "category": "forensics", "difficulty": "easy"}]
    r = recommend.recommend(tasks, entries, set())
    assert r["category"]["key"] == "forensics" and r["entry"]["id"] == "c"
    r = recommend.recommend(tasks, entries, {"c"})                 # forensics tomt -> neste svake: web, lett før middels
    assert r["category"]["key"] == "web" and r["entry"]["id"] == "b"
    assert recommend.recommend(tasks, entries, {"a", "b", "c"}) is None
    assert recommend.weak_categories([])[0]["reason"] == "ikke prøvd ennå"
