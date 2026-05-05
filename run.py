"""
run.py — Entry point for Smart HORECA AI Web App
Run: python run.py
Then open: http://localhost:5000
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5000, host="0.0.0.0")
