import os

from flask import Blueprint, jsonify, request

bp = Blueprint("browse", __name__)


@bp.get("/browse")
def browse():
    path = request.args.get("path", "").strip()

    # Raiz: listar drives no Windows, / no Linux
    if not path:
        if os.name == "nt":
            import string
            drives = [
                f"{d}:\\"
                for d in string.ascii_uppercase
                if os.path.exists(f"{d}:\\")
            ]
            return jsonify({"path": "", "parent": None, "dirs": drives})
        path = "/"

    path = os.path.abspath(path)

    if not os.path.isdir(path):
        return jsonify({"error": "Caminho inválido"}), 400

    try:
        entries = sorted(
            e.name
            for e in os.scandir(path)
            if e.is_dir() and not e.name.startswith(".")
        )
    except PermissionError:
        return jsonify({"error": "Sem permissão para acessar este diretório"}), 403

    parent = str(os.path.dirname(path)) if path != os.path.dirname(path) else None

    return jsonify({"path": path, "parent": parent, "dirs": entries})
