from __future__ import annotations

import os
from typing import Any, Dict

import joblib
import numpy as np
import pandas as pd
from dotenv import load_dotenv


load_dotenv()


_MODEL_CACHE = None

def predict_usage_risk(features: Dict[str, Any]) -> Dict[str, Any]:
    global _MODEL_CACHE
    if _MODEL_CACHE is None:
        model_path = os.getenv("MODEL_PATH", "ml/model.pkl")
        _MODEL_CACHE = joblib.load(model_path)
    
    artifact = _MODEL_CACHE
    model = artifact["model"]
    cols = artifact["feature_columns"]

    for col in cols:
        if col not in features:
            raise ValueError(f"Missing feature: {col}")

    x = pd.DataFrame([[float(features[col]) for col in cols]], columns=cols)
    pred = model.predict(x)[0]
    proba = model.predict_proba(x)[0]
    score = float(np.max(proba))
    anomaly_flag = bool(pred == "HIGH" and score > 0.75)

    return {
        "congestion_risk": str(pred),
        "anomaly_flag": anomaly_flag,
        "score": round(score, 4),
    }

