from __future__ import annotations

import os

from dotenv import load_dotenv

from ml.feature_engineering import build_features
from ml.predict import predict_usage_risk


load_dotenv()


def run_batch_scoring(output_path: str | None = None) -> str:
    output_path = output_path or "ml/batch_predictions.csv"
    features_df = build_features()
    
    import joblib
    import numpy as np
    import pandas as pd
    
    model_path = os.getenv("MODEL_PATH", "ml/model.pkl")
    artifact = joblib.load(model_path)
    model = artifact["model"]
    cols = artifact["feature_columns"]
    
    # Predict on the entire dataframe
    X = features_df[cols]
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)
    scores = np.max(probabilities, axis=1)
    
    out_df = features_df.copy()
    out_df["congestion_risk"] = predictions
    out_df["score"] = np.round(scores, 4)
    out_df["anomaly_flag"] = (out_df["congestion_risk"] == "HIGH") & (out_df["score"] > 0.75)
    
    out_df.to_csv(output_path, index=False)
    return output_path


if __name__ == "__main__":
    path = run_batch_scoring()
    print(f"Batch predictions saved to {path}")

