import json
import re
from datetime import datetime
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_file, url_for
import markdown

from labs import __main__ as labs_mod
from . import config, constants, gitops, intro, recommend, videos, xp
from .report import build_report, select_tasks
from .stats import compute_stats
from .storage import (
    DataDirError, atomic_write_bytes, check_data_dir, get_task, list_tasks, save_task,
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Oppvarmingskatalogen leses fra en lokal fil; ingen nettverkskall.
PRACTICE = {
    e["id"]: e
    for e in json.loads((Path(__file__).parent / "practice.json").read_text(encoding="utf-8"))
}


def render_markdown(text: str) -> str:
    """Markdown -> HTML. Rå HTML i teksten slås av og vises som ren tekst."""
    md = markdown.Markdown(extensions=["fenced_code", "tables", "sane_lists"])
    md.preprocessors.deregister("html_block")
    md.inlinePatterns.deregister("html")
    return md.convert(text or "")


def C_CAT(key: str) -> str:
    return constants.CATEGORIES.get(key, key)


def create_app(data_dir: str | None = None) -> Flask:
    app = Flask(__name__)
    app.config["TEMPLATES_AUTO_RELOAD"] = True   # lokal app: endrede maler vises uten restart
    # data_dir=None betyr: slå opp CTF_DATA_DIR / config.json for hver forespørsel.
    app.config["CTF_DATA_DIR_OVERRIDE"] = data_dir

    def current_dir():
        return app.config["CTF_DATA_DIR_OVERRIDE"] or config.get_data_dir()

    @app.context_processor
    def inject():
        try:
            check_data_dir(current_dir())
            problem = None
        except DataDirError as e:
            problem = str(e)
        # Liten profil til sidemenyen (nivå, XP, streak). Tåler at datamappen mangler.
        try:
            side = xp.compute_xp(list_tasks(current_dir())[0])
        except Exception:
            side = xp.compute_xp([])
        return {"data_problem": problem, "C": constants, "data_dir_path": current_dir(), "side": side}

    @app.errorhandler(DataDirError)
    def data_dir_error(e):
        if request.path.startswith("/api/"):
            return jsonify(error=str(e)), 503
        return render_template("error.html", message=str(e)), 503

    # --- sider -------------------------------------------------------------
    @app.get("/")
    def dashboard():
        try:
            tasks, _ = list_tasks(current_dir())
        except DataDirError:
            tasks = []
        logged = {tag for t in tasks for tag in t["tags"] if tag.startswith("practice-")}
        dl = config.get_downloads_dir()

        def ready(e):
            return intro.readiness(intro.file_info(dl, e.get("files") or [])) in ("ready", "nofiles")

        def nxt(diff):
            return next((e for e in PRACTICE.values()
                         if e["difficulty"] == diff and f"practice-{e['id']}" not in logged and ready(e)), None)
        done_ids = {t[len("practice-"):] for t in logged}
        missions = [{"kicker": "Start her", "title": "Oppvarming", "text": "Intro til kategoriene og to små oppgaver.",
                     "cta": "Start", "href": url_for("warmup_page")}]
        rec = recommend.recommend(tasks, list(PRACTICE.values()), done_ids, ready)
        if rec:
            e, w = rec["entry"], rec["category"]
            missions.append({"kicker": "Anbefalt for deg", "title": e["title"],
                             "text": f"{w['label']}: {w['reason']}", "cta": "Åpne",
                             "href": url_for("practice_page", diff=e["difficulty"], cat=e["category"])})
        e = nxt("easy")
        if e:
            missions.append({"kicker": "Neste lette oppgave", "title": e["title"],
                             "text": C_CAT(e["category"]) + " · " + e["source"].split(" · ")[0],
                             "cta": "Åpne", "href": url_for("practice_page", diff="easy", cat=e["category"])})
        missions.append({"kicker": "Vane", "title": "Påminnelse", "text": "Få et varsel på telefonen når du skal trene.",
                         "cta": "Sett opp", "href": url_for("reminder_page")})
        return render_template("dashboard.html", intros=intro.INTROS, missions=missions)

    @app.get("/tasks")
    def tasks_page():
        try:
            tasks, errors = list_tasks(current_dir())
        except DataDirError:
            tasks, errors = [], []
        return render_template("tasks.html", tasks=tasks, errors=errors)

    @app.get("/tasks/new")
    def new_task():
        prefill = None
        entry = PRACTICE.get(request.args.get("practice", ""))
        if entry:
            text = entry["no"] if request.args.get("lang") == "no" and entry.get("no") else entry
            body = constants.BODY_TEMPLATE.replace(
                "## Hva spurte oppgaven om\n\n",
                f"## Hva spurte oppgaven om\n\n{text['objective']}\n", 1)
            prefill = {
                "title": text["title"], "source": entry["source"], "category": entry["category"],
                "protocol": entry["protocol"], "difficulty": entry["difficulty"],
                "status": "unsolved", "tags": entry["tags"] + [f"practice-{entry['id']}"],
                "body": body,
            }
        return render_template("task_form.html", task=None, prefill=prefill,
                               sources=_sources(current_dir()))

    @app.get("/practice")
    def practice_page():
        try:
            tasks, _ = list_tasks(current_dir())
        except DataDirError:
            tasks = []
        logged = {tag for t in tasks for tag in t["tags"] if tag.startswith("practice-")}
        dl = config.get_downloads_dir()
        entries = []
        for e in PRACTICE.values():
            fi = intro.file_info(dl, e.get("files") or [])
            entries.append({**e, "done": f"practice-{e['id']}" in logged, "fileinfo": fi,
                            "ready": intro.readiness(fi), "steps": intro.start_steps(e, fi)})
        return render_template("practice.html", entries=entries, done=sum(e["done"] for e in entries),
                               intros=intro.INTROS, how_to_open=intro.HOW_TO_OPEN, downloads_dir=dl,
                               icons=intro.CATEGORY_ICONS, xp_base=xp.BASE, xp_factor=xp.FACTOR,
                               sources=sorted({e["source"].split(" · ")[0] for e in entries}))

    @app.get("/warmup")
    def warmup_page():
        try:
            tasks, _ = list_tasks(current_dir())
        except DataDirError:
            tasks = []
        logged = {tag for t in tasks for tag in t["tags"] if tag.startswith("practice-")}
        groups = []
        for key, ids in intro.WARMUP_TASKS.items():
            items = [{**PRACTICE[i], "done": f"practice-{i}" in logged, "steps": intro.start_steps(PRACTICE[i], [])}
                     for i in ids if i in PRACTICE]
            groups.append({"key": key, "info": intro.INTROS[key], "tasks": items,
                           "done": sum(1 for t in items if t["done"]), "total": len(items)})
        try:
            vids = videos.load(current_dir())
        except DataDirError:
            vids = {}
        for g in groups:
            g["videos"] = vids.get(g["key"], [])
        return render_template("warmup.html", intros=intro.INTROS, groups=groups, icons=intro.CATEGORY_ICONS,
                               xp_base=xp.BASE, xp_factor=xp.FACTOR)

    @app.post("/api/videos")
    def api_video_add():
        b = request.get_json(silent=True) or {}
        try:
            videos.add(current_dir(), str(b.get("category", "")), str(b.get("url", "")), str(b.get("title", "")),
                       b.get("minutes", ""))
        except ValueError as e:
            return jsonify(error=str(e)), 400
        return jsonify(ok=True)

    @app.post("/api/videos/remove")
    def api_video_remove():
        b = request.get_json(silent=True) or {}
        if str(b.get("category", "")) not in constants.CATEGORIES:
            return jsonify(error="Ukjent kategori."), 400
        videos.remove(current_dir(), str(b["category"]), str(b.get("id", "")))
        return jsonify(ok=True)

    @app.get("/reminder")
    def reminder_page():
        return render_template("reminder.html", days=intro.WEEKDAYS)

    @app.get("/reminder.ics")
    def reminder_ics():
        """Gjentakende kalenderhendelse med varsel. Importeres i telefonens kalender; appen sender ingenting selv."""
        text = intro.reminder_ics(request.args.get("time", "19:00"), request.args.getlist("day"),
                                  request.args.get("text", ""))
        if text is None:
            abort(400)
        return Response(text, mimetype="text/calendar",
                        headers={"Content-Disposition": 'attachment; filename="ctf-paminnelse.ics"'})

    @app.get("/dl/<path:rel>")
    def download_file(rel):
        """Last ned en PCAP fra nedlastingsmappen (kun innenfor mappen, kun hvis CTF_DOWNLOADS_DIR er satt)."""
        full = intro.safe_download_path(config.get_downloads_dir(), rel)
        if not full:
            abort(404)
        return send_file(full, as_attachment=True)

    @app.get("/tasks/<task_id>")
    def edit_task(task_id):
        try:
            task = get_task(current_dir(), task_id)
        except (FileNotFoundError, ValueError):
            abort(404)
        return render_template("task_form.html", task=task, prefill=None,
                               sources=_sources(current_dir()))

    @app.get("/report")
    def report_page():
        try:
            tasks, _ = list_tasks(current_dir())
        except DataDirError:
            tasks = []
        return render_template("report.html", tasks=sorted(tasks, key=lambda t: t["date"]))

    @app.get("/report.pdf")
    def report_pdf():
        data_dir = check_data_dir(current_dir())  # nekter hvis SSD-en mangler
        start, end = request.args.get("from") or None, request.args.get("to") or None
        for v in (start, end):
            if v and not DATE_RE.match(v):
                abort(400, "Ugyldig dato.")
        tasks, _ = list_tasks(data_dir)
        chosen = select_tasks(tasks, start, end, set(request.args.getlist("id")))
        if not chosen:
            return render_template("error.html", message="Ingen oppgaver i utvalget."), 400
        pdf = build_report(chosen, start, end)
        name = f"rapport-{datetime.now():%Y%m%d-%H%M%S}.pdf"
        (data_dir / "reports").mkdir(exist_ok=True)
        atomic_write_bytes(data_dir / "reports" / name, pdf)  # kopi på SSD (ikke i git)
        return Response(pdf, mimetype="application/pdf",
                        headers={"Content-Disposition": f'inline; filename="{name}"'})

    # --- API ---------------------------------------------------------------
    @app.get("/api/stats")
    def api_stats():
        tasks, errors = list_tasks(current_dir())
        flt = {k: request.args.get(k, "") for k in ("category", "difficulty", "protocol")}
        for k, allowed in (("category", constants.CATEGORIES), ("difficulty", constants.DIFFICULTIES),
                           ("protocol", constants.PROTOCOLS)):
            if flt[k] and flt[k] not in allowed:
                return jsonify(error=f"Ukjent {k}: {flt[k]}"), 400
            if flt[k]:
                tasks = [t for t in tasks if t.get(k) == flt[k]]
        return jsonify(stats=compute_stats(tasks), errors=errors, filter={k: v for k, v in flt.items() if v})

    @app.post("/api/check")
    def api_check():
        """Sjekk svaret på en av de egne øvelsene (lab-*). Fasiten ligger bare som hash i øvelsesmappen og skrives aldri ut."""
        body = request.get_json(silent=True) or {}
        pid, answer = body.get("id"), body.get("answer")
        if not isinstance(pid, str) or not isinstance(answer, str) or not answer.strip() or len(answer) > 300:
            return jsonify(error="Skriv inn et svar."), 400
        lab = pid[4:] if pid.startswith("lab-") and pid in PRACTICE else None
        if lab not in labs_mod.LABS:
            return jsonify(error="Denne oppgaven kan ikke sjekkes her. Lever svaret på oppgavens egen side."), 400
        try:
            ok = labs_mod.check(config.get_labs_dir(), lab, answer)
        except (OSError, ValueError, KeyError, SystemExit):
            return jsonify(error="Øvelsene er ikke laget ennå. Kjør: .venv/bin/python -m labs generate ~/ctf-labs"), 409
        return jsonify(correct=bool(ok), xp=xp.BASE.get(PRACTICE[pid]["difficulty"], 0) if ok else 0)

    @app.get("/api/xp")
    def api_xp():
        try:
            tasks, _ = list_tasks(current_dir())
        except DataDirError:
            tasks = []
        return jsonify(xp.compute_xp(tasks))

    @app.get("/api/catalog")
    def api_catalog():
        """Oppgavekatalogen (Oppvarming) i tall: totalt, klare (filer lastet ned), delvis, mangler, logget."""
        flt = {k: request.args.get(k, "") for k in ("category", "difficulty", "protocol")}
        try:
            tasks, _ = list_tasks(current_dir())
        except DataDirError:
            tasks = []
        logged = {tag for t in tasks for tag in t["tags"] if tag.startswith("practice-")}
        dl = config.get_downloads_dir()
        entries = [{**e, "ready": intro.readiness(intro.file_info(dl, e.get("files") or []))} for e in PRACTICE.values()]
        return jsonify(intro.catalog_summary(entries, {t[len("practice-"):] for t in logged}, flt)
                       | {"downloads_dir_set": bool(dl)})

    @app.post("/api/tasks")
    def api_create():
        return _save(None)

    @app.put("/api/tasks/<task_id>")
    def api_update(task_id):
        return _save(task_id)

    def _save(task_id):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify(error="Ugyldig JSON."), 400
        try:
            task = save_task(current_dir(), payload, task_id)
        except ValueError as e:
            return jsonify(error=str(e)), 400
        except FileNotFoundError:
            return jsonify(error="Oppgaven finnes ikke."), 404
        git = gitops.commit_task(current_dir(), task["id"], task["title"], created=task_id is None)
        return jsonify(task=task, git=git, url=url_for("edit_task", task_id=task["id"]))

    @app.get("/git")
    def git_page():
        return render_template("git.html")

    @app.get("/api/git/status")
    def api_git_status():
        return jsonify(gitops.status(current_dir()))

    @app.post("/api/git/push")
    def api_git_push():
        # Krever JSON: en annen nettside kan ikke sende det uten CORS-forespørsel først.
        if not request.is_json:
            return jsonify(error="Forventet JSON."), 400
        try:
            return jsonify(output=gitops.push(current_dir()))
        except gitops.GitError as e:
            return jsonify(error=str(e)), 400

    @app.post("/api/preview")
    def api_preview():
        payload = request.get_json(silent=True) or {}
        return jsonify(html=render_markdown(str(payload.get("text", ""))))

    return app


def _sources(data_dir) -> list[str]:
    try:
        tasks, _ = list_tasks(data_dir)
    except DataDirError:
        return []
    return sorted({t["source"] for t in tasks if t["source"]})
