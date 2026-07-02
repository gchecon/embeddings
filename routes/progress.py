import json
import queue
import threading

from flask import Blueprint, Response, stream_with_context

bp = Blueprint("progress", __name__)

_queues: dict[str, queue.Queue] = {}
_lock = threading.Lock()

SESSION_KEY = "default"


def get_queue(session_id: str = SESSION_KEY) -> queue.Queue:
    with _lock:
        if session_id not in _queues:
            _queues[session_id] = queue.Queue()
        return _queues[session_id]


def push_event(event: dict, session_id: str = SESSION_KEY):
    q = get_queue(session_id)
    q.put(json.dumps(event))


def push_done(session_id: str = SESSION_KEY):
    q = get_queue(session_id)
    q.put(None)  # sentinel


@bp.get("/progress")
def progress_stream():
    q = get_queue()

    def generate():
        while True:
            try:
                event = q.get(timeout=10)
            except queue.Empty:
                # Keepalive: comentário SSE não dispara onmessage, só mantém a conexão
                yield ": keepalive\n\n"
                continue
            if event is None:
                yield f"data: {json.dumps({'status': 'done'})}\n\n"
                break
            yield f"data: {event}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
