import threading

from flask import Blueprint, jsonify, request

from routes.progress import push_event, push_done, get_queue
from services import indexer

bp = Blueprint("upload", __name__)


@bp.post("/scan")
def scan():
    data = request.get_json(silent=True) or {}
    directory = (data.get("directory") or "").strip()

    if not directory:
        return jsonify({"error": "Campo 'directory' é obrigatório"}), 400

    import os
    if not os.path.isdir(directory):
        return jsonify({"error": f"Diretório não encontrado: {directory}"}), 400

    # Flush old queue
    q = get_queue()
    while not q.empty():
        try:
            q.get_nowait()
        except Exception:
            break

    def run():
        def on_progress(event):
            push_event(event)

        summary = indexer.index_directory(directory, on_progress=on_progress)
        push_event({"status": "summary", **summary})
        push_done()

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    return jsonify({"status": "started", "directory": directory})
