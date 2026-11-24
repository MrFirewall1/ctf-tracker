from reportlab.platypus import Paragraph, Preformatted

from app.report import _styles, body_flowables, build_report, select_tasks
from app.storage import init_data_dir, save_task
from app.web import create_app

BODY = (
    "## Hva spurte oppgaven om\n\nFinn <flagget> & svar\nlinje to\n\n"
    "## Kommandoer/filtre jeg brukte\n\n```\ntshark -r a.pcap -Y 'modbus.func_code == 16'\n```\n\n"
    "## Hva jeg lærte\n\nÆØÅ og **rå markdown** beholdes\n"
)


def task(**kw):
    base = dict(title="Modbus æøå", date="2026-03-02", source="Egen", category="pcap_ics",
                protocol="modbus", difficulty="easy", time_minutes=0, tools="wireshark", tags="a, b",
                status="solved_alone", hints_used=1, resolved_later=True, body=BODY)
    base.update(kw)
    return base


def test_body_is_reproduced_verbatim():
    flow = body_flowables(BODY, _styles())
    paras = [f for f in flow if isinstance(f, Paragraph)]
    texts = [p.text for p in paras]
    assert "Finn &lt;flagget&gt; &amp; svar<br/>linje to" in texts  # kun XML-escape + linjeskift
    assert "ÆØÅ og **rå markdown** beholdes" in texts
    code = [f for f in flow if isinstance(f, Preformatted)]
    assert "\n".join(code[0].lines) == "tshark -r a.pcap -Y 'modbus.func_code == 16'"
    headings = ["Hva spurte oppgaven om", "Kommandoer/filtre jeg brukte", "Hva jeg lærte"]
    assert [t for t in texts if t in headings] == headings


def test_long_code_lines_are_wrapped_not_lost():
    long = "x" * 300
    flow = body_flowables(f"```\n{long}\n```", _styles())
    assert "".join(flow[0].lines).replace("  ", "") == long


def test_build_pdf_and_selection(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    a = save_task(d, task())
    b = save_task(d, task(title="Senere", date="2026-04-01", status="unsolved"))
    tasks = [a, b]
    assert [t["id"] for t in select_tasks(tasks, "2026-03-15", None)] == [b["id"]]
    assert [t["id"] for t in select_tasks(tasks, ids={a["id"]})] == [a["id"]]
    pdf = build_report(select_tasks(tasks))
    assert pdf.startswith(b"%PDF") and len(pdf) > 3000
    assert build_report([]).startswith(b"%PDF")  # tomt utvalg krasjer ikke


def test_report_route(tmp_path):
    d = tmp_path / "ssd"
    d.mkdir()
    init_data_dir(d)
    client = create_app(str(d)).test_client()
    assert client.get("/report.pdf").status_code == 400  # ingen oppgaver
    client.post("/api/tasks", json=task())
    r = client.get("/report.pdf?from=2026-01-01&to=2026-12-31")
    assert r.status_code == 200 and r.mimetype == "application/pdf" and r.data.startswith(b"%PDF")
    saved = list((d / "reports").glob("rapport-*.pdf"))
    assert len(saved) == 1 and not list((d / "reports").glob("*.tmp"))
    assert client.get("/report.pdf?from=abc").status_code == 400
    assert client.get("/report").status_code == 200


def test_report_refuses_without_ssd(tmp_path):
    missing = tmp_path / "ikke-montert"
    client = create_app(str(missing)).test_client()
    assert client.get("/report.pdf").status_code == 503
    assert not missing.exists()
