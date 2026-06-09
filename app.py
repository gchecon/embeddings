from flask import Flask

from config import settings
from database.postgres import ensure_schema
from database.qdrant_client import ensure_collection
from routes.upload import bp as upload_bp
from routes.search import bp as search_bp
from routes.pdf_viewer import bp as pdf_viewer_bp
from routes.progress import bp as progress_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = settings.FLASK_SECRET_KEY

    ensure_schema()
    ensure_collection()

    app.register_blueprint(upload_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(pdf_viewer_bp)
    app.register_blueprint(progress_bp)

    @app.get("/")
    def index():
        from flask import render_template
        return render_template("index.html")

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=settings.FLASK_DEBUG)
