"""AgriScope entry point.  Development:  python app.py     Production:  waitress-serve --call app:create_app"""
import os

from agriscope import create_app

if __name__ == "__main__":
    app = create_app()
    app.run(
        host=os.environ.get("AGRISCOPE_HOST", "127.0.0.1"),
        port=int(os.environ.get("AGRISCOPE_PORT", "5000")),
        debug=os.environ.get("AGRISCOPE_DEBUG", "").lower() in {"1", "true", "yes"},
    )
