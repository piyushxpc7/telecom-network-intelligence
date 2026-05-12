from __future__ import annotations

import os

import joblib
import numpy as np
from dotenv import load_dotenv
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split

from ml.feature_engineering import build_features


load_dotenv()


def _label_risk(avg_usage_series) -> np.ndarray:
    p50 = np.percentile(avg_usage_series, 50)
    p90 = np.percentile(avg_usage_series, 90)
    labels = []
    for value in avg_usage_series:
        if value >= p90:
            labels.append("HIGH")
        elif value >= p50:
            labels.append("MEDIUM")
        else:
            labels.append("LOW")
    return np.array(labels)


def train_and_save(model_path: str | None = None) -> dict:
    model_path = model_path or os.getenv("MODEL_PATH", "ml/model.pkl")
    features = build_features()
    features["label"] = _label_risk(features["avg_usage"].values)

    x = features[["avg_usage", "growth_rate", "variability", "peak_ratio"]]
    y = features["label"]

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.2, random_state=42, stratify=y
    )

    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(x_train, y_train)

    y_pred = model.predict(x_test)
    accuracy = accuracy_score(y_test, y_pred)
    conf = confusion_matrix(y_test, y_pred)
    report = classification_report(y_test, y_pred, output_dict=True)

    artifact = {
        "model": model,
        "feature_columns": ["avg_usage", "growth_rate", "variability", "peak_ratio"],
        "labels": ["LOW", "MEDIUM", "HIGH"],
    }
    joblib.dump(artifact, model_path)

    metrics = {"accuracy": float(accuracy), "confusion_matrix": conf.tolist(), "report": report}
    print(metrics)
    return metrics


if __name__ == "__main__":
    train_and_save()

