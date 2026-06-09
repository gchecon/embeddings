from flask import Blueprint, Response, abort, render_template, request

from database.postgres import get_pdf_data

bp = Blueprint("pdf_viewer", __name__)


@bp.get("/pdf/<doc_id>")
def serve_pdf(doc_id: str):
    data = get_pdf_data(doc_id)
    if data is None:
        abort(404)

    page = request.args.get("page", "")
    view = request.args.get("view", "inline")

    if view == "download":
        return Response(
            data,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={doc_id}.pdf"},
        )

    if view == "raw":
        return Response(
            data,
            mimetype="application/pdf",
            headers={"Content-Disposition": "inline"},
        )

    # Default: render viewer template with embedded PDF
    return render_template("viewer.html", doc_id=doc_id, page=page)
