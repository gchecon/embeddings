from flask import Blueprint, jsonify, render_template, request

from database import qdrant_client
from services import embedder

bp = Blueprint("search", __name__)


@bp.get("/search")
def search():
    q = request.args.get("q", "").strip()
    limit = int(request.args.get("limit", 10))

    if not q:
        if request.accept_mimetypes.best == "application/json":
            return jsonify({"results": []})
        return render_template("search.html", query="", results=[])

    query_vector = embedder.embed_query(q)
    raw_results = qdrant_client.search(query_vector, limit=limit)

    results = []
    for r in raw_results:
        p = r["payload"]
        results.append({
            "score": round(r["score"], 4),
            "text": p.get("text", ""),
            "document_id": p.get("document_id", ""),
            "original_name": p.get("original_name", ""),
            "title": p.get("title", ""),
            "author": p.get("author", ""),
            "year": p.get("year", ""),
            "page_start": p.get("page_start", 1),
            "page_end": p.get("page_end", 1),
            "language": p.get("language", ""),
            "chunk_index": p.get("chunk_index", 0),
            "total_chunks": p.get("total_chunks", 0),
        })

    if request.accept_mimetypes.best == "application/json":
        return jsonify({"results": results})

    return render_template("search.html", query=q, results=results)
