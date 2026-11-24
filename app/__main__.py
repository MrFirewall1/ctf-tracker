"""python -m app          -> start serveren på localhost
python -m app init     -> sett opp en eksisterende datamappe (én gang)
python -m app git-init [url] -> git-repo i datamappen, og remote origin hvis url gis
"""
import os
import sys

from . import config, gitops
from .storage import DataDirError, init_data_dir
from .web import create_app


def main(argv: list[str]) -> int:
    data_dir = config.get_data_dir()
    if argv[:1] == ["init"]:
        try:
            p = init_data_dir(data_dir)
        except DataDirError as e:
            print(f"FEIL: {e}", file=sys.stderr)
            return 1
        print(f"Datamappen er klar: {p}")
        return 0

    if argv[:1] == ["git-init"]:
        try:
            print(gitops.init_repo(data_dir, argv[1] if len(argv) > 1 else None))
        except (DataDirError, gitops.GitError) as e:
            print(f"FEIL: {e}", file=sys.stderr)
            return 1
        return 0

    app = create_app()
    # Kun localhost: dataene dine skal ikke ut på nettverket.
    app.run(host="127.0.0.1", port=int(os.environ.get("CTF_PORT", "5000")), debug=False)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
