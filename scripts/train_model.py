import pandas as pd
import numpy as np
from xgboost import XGBRegressor
import joblib
import os

def train():
    df = pd.read_csv("dataset.csv")

    # Fallback to synthetic data if the database doesn't have enough rows yet
    if len(df) < 10:
        print("Not enough real data. Generating synthetic bootstrap data...")
        np.random.seed(42)
        synthetic_data = {
            "slant_std": np.random.uniform(0, 20, 100),
            "spacing_std": np.random.uniform(0, 30, 100),
            "baseline_var": np.random.uniform(0, 15, 100),
            "stroke_var": np.random.uniform(0, 10, 100),
        }
        # Create a synthetic score based loosely on the rules
        # Higher variance = lower score
        synthetic_score = 100 - (synthetic_data["slant_std"] * 1.5 + synthetic_data["spacing_std"] * 1.2 + synthetic_data["baseline_var"] * 2.0)
        synthetic_score = np.clip(synthetic_score, 0, 100)
        synthetic_data["score"] = synthetic_score
        
        df = pd.concat([df, pd.DataFrame(synthetic_data)])

    X = df.drop(columns=["score"])
    y = df["score"]

    model = XGBRegressor(n_estimators=100)
    model.fit(X, y)

    joblib.dump(model, "model.pkl")
    print("Model trained and saved to model.pkl successfully.")

if __name__ == "__main__":
    train()
