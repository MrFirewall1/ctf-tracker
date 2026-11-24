import json
import struct

import pytest

from app.constants import CATEGORIES, DIFFICULTIES, PROTOCOLS
from app.storage import init_data_dir
from app.web import PRACTICE, create_app
from labs import __main__ as labs


def test_catalog_is_valid():
    assert len(PRACTICE) >= 10
    for e in PRACTICE.values():
        assert e["category"] in CATEGORIES and e["protocol"] in PROTOCOLS
        assert e["difficulty"] in DIFFICULTIES and e["objective"] and e["hints"]
        assert e["url"] == "" or e["url"].startswith("https://")


def test_generate_and_check(tmp_path):
    flags = labs.generate(tmp_path / "L")
    assert set(flags) == set(labs.LABS)
    for lab, flag in flags.items():
        assert labs.check(tmp_path / "L", lab, flag)
        assert not labs.check(tmp_path / "L", lab, "CTF{feil}")
    manifest = (tmp_path / "L" / labs.MANIFEST).read_text()
    assert not any(f in manifest for f in flags.values())  # kun hash, aldri klartekst
    # flaggene er tilfeldige fra gang til gang
    assert labs.generate(tmp_path / "M") != flags


def test_hidden_and_log_flags_are_findable(tmp_path):
    flags = labs.generate(tmp_path)
    hidden = [p for p in (tmp_path / "hidden-file").rglob("*")
              if p.is_file() and p.name.startswith(".")]
    assert [p.read_text().strip() for p in hidden] == [flags["hidden-file"]]
    log = (tmp_path / "log-secret" / "server.log").read_text()
    assert log.count(flags["log-secret"]) == 1
    assert flags["env-leak"] in (tmp_path / "env-leak" / "start_service.sh").read_text()


def test_pcap_is_wellformed_and_holds_flag(tmp_path):
    flags = labs.generate(tmp_path)
    raw = (tmp_path / "modbus-flag" / "capture.pcap").read_bytes()
    magic, vmaj, vmin, _, _, _, link = struct.unpack("<IHHiIII", raw[:24])
    assert (magic, vmaj, vmin, link) == (0xA1B2C3D4, 2, 4, 1)
    pos, frames = 24, []
    while pos < len(raw):
        _, _, caplen, origlen = struct.unpack("<IIII", raw[pos:pos + 16])
        assert caplen == origlen
        frames.append(raw[pos + 16:pos + 16 + caplen])
        pos += 16 + caplen
    assert pos == len(raw) and len(frames) > 10
    assert all(f[12:14] == b"\x08\x00" and f[14] == 0x45 for f in frames)
    # IPv4-lengde stemmer med rammen
    assert all(struct.unpack("!H", f[16:18])[0] == len(f) - 14 for f in frames)
    # Flagget ligger i en FC16-forespørsel til port 502
    hits = [f for f in frames if flags["modbus-flag"].encode() in f]
    assert len(hits) == 1 and struct.unpack("!H", hits[0][36:38])[0] == 502
    assert hits[0][14 + 20 + 20 + 7] == 16


def test_generate_refuses_nonempty_and_data_dir(tmp_path, monkeypatch):
    (tmp_path / "x").mkdir()
    (tmp_path / "x" / "fil").write_text("a")
    with pytest.raises(SystemExit):
        labs.generate(tmp_path / "x")
    data = tmp_path / "ssd"
    data.mkdir()
    init_data_dir(data)
    monkeypatch.setenv("CTF_DATA_DIR", str(data))
    with pytest.raises(SystemExit):
        labs.generate(data / "labs")
    assert not (data / "labs").exists()


def test_practice_pages_and_prefill(tmp_path):
    data = tmp_path / "ssd"
    data.mkdir()
    init_data_dir(data)
    client = create_app(str(data)).test_client()
    page = client.get("/practice").get_data(as_text=True)
    assert "0 / " in page and "Hidden File Hunt" in page
    form = client.get("/tasks/new?practice=lab-modbus-flag").get_data(as_text=True)
    assert "Own exercise: flag in Modbus traffic" in form and "practice-lab-modbus-flag" in form
    form_no = client.get("/tasks/new?practice=lab-modbus-flag&lang=no").get_data(as_text=True)
    assert "Egen øvelse: flagg i Modbus-trafikk" in form_no
    assert client.get("/tasks/new?practice=finnes-ikke").status_code == 200
    r = client.post("/api/tasks", json={
        "title": "Egen øvelse: skjult fil", "date": "2026-03-02", "category": "other",
        "difficulty": "easy", "status": "solved_alone", "tags": "linux, practice-lab-hidden-file",
    })
    assert r.status_code == 200
    assert "1 / " in client.get("/practice").get_data(as_text=True)


def test_answer_check_endpoint(tmp_path, monkeypatch):
    data = tmp_path / "ssd"
    data.mkdir()
    init_data_dir(data)
    labs_dir = tmp_path / "L"
    flags = labs.generate(labs_dir)
    monkeypatch.setenv("CTF_LABS_DIR", str(labs_dir))
    c = create_app(str(data)).test_client()
    ok = c.post("/api/check", json={"id": "lab-modbus-flag", "answer": flags["modbus-flag"]}).get_json()
    assert ok["correct"] is True and ok["xp"] == 25
    bad = c.post("/api/check", json={"id": "lab-modbus-flag", "answer": "CTF{feil}"}).get_json()
    assert bad == {"correct": False, "xp": 0}
    assert flags["modbus-flag"] not in c.post("/api/check", json={"id": "lab-modbus-flag", "answer": "x"}).get_data(as_text=True)
    # kan ikke sjekke eksterne oppgaver, tomt svar, ukjent id
    assert c.post("/api/check", json={"id": "pico-mod-26", "answer": "x"}).status_code == 400
    assert c.post("/api/check", json={"id": "lab-modbus-flag", "answer": " "}).status_code == 400
    assert c.post("/api/check", json={"id": "lab-finnes-ikke", "answer": "x"}).status_code == 400
    # øvelsene er ikke laget
    monkeypatch.setenv("CTF_LABS_DIR", str(tmp_path / "ingen"))
    assert c.post("/api/check", json={"id": "lab-modbus-flag", "answer": "x"}).status_code == 409
    page = c.get("/practice").get_data(as_text=True)
    assert "Sjekk svar" in page and "+25 XP" in page
