import csv
import sys
import os

# Add the project root to sys.path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.models.result import Result

def build():
    db = SessionLocal()
    rows = db.query(Result).all()

    with open("dataset.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "slant_std", "spacing_std", "baseline_var", "stroke_var", "score"
        ])

        for r in rows:
            fts = r.features or {}
            scr = r.scores.get("overall_score", r.scores.get("overall", 0)) if r.scores else 0

            writer.writerow([
                fts.get("slant_std", 0),
                fts.get("spacing_std", 0),
                fts.get("baseline_var", 0),
                fts.get("stroke_var", 0),
                scr
            ])
            
    print(f"Exported {len(rows)} records to dataset.csv")

if __name__ == "__main__":
    build()
