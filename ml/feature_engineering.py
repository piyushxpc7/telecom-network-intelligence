from __future__ import annotations

import os
import sqlite3

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()


def build_features(db_url: str | None = None) -> pd.DataFrame:
    db_url = db_url or os.getenv("WAREHOUSE_DB_URL")
    if not db_url:
        raise ValueError("WAREHOUSE_DB_URL is not configured.")

    query = """
    SELECT
      r.region_name,
      t.date,
      t.hour,
      f.call_count,
      f.sms_count,
      f.internet_mb
    FROM fact_usage f
    JOIN dim_time t ON f.time_id = t.time_id
    JOIN dim_region r ON f.region_id = r.region_id
    """

    if db_url.startswith("sqlite:///"):
        sqlite_path = db_url.replace("sqlite:///", "", 1)
        with sqlite3.connect(sqlite_path) as conn:
            df = pd.read_sql_query(query, conn)
    else:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            df = pd.read_sql_query(query, conn)
    if df.empty:
        raise ValueError("No warehouse data available for feature engineering.")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["total_usage"] = df["call_count"] + df["sms_count"] + df["internet_mb"]

    daily = (
        df.groupby(["region_name", "date"], as_index=False)["total_usage"].sum().sort_values(["region_name", "date"])
    )
    daily["prev_usage"] = daily.groupby("region_name")["total_usage"].shift(1)
    daily["growth_rate"] = np.where(
        daily["prev_usage"].fillna(0) > 0,
        (daily["total_usage"] - daily["prev_usage"]) / daily["prev_usage"],
        0.0,
    )

    per_region = daily.groupby("region_name", as_index=False).agg(
        avg_usage=("total_usage", "mean"),
        growth_rate=("growth_rate", "mean"),
        variability=("total_usage", "std"),
    )
    per_region["variability"] = per_region["variability"].fillna(0.0)

    peak = df.groupby(["region_name", "hour"], as_index=False)["total_usage"].sum()
    peak_ratio = peak.groupby("region_name", as_index=False).agg(
        peak_usage=("total_usage", "max"),
        avg_hourly_usage=("total_usage", "mean"),
    )
    peak_ratio["peak_ratio"] = np.where(
        peak_ratio["avg_hourly_usage"] > 0,
        peak_ratio["peak_usage"] / peak_ratio["avg_hourly_usage"],
        0.0,
    )

    features = per_region.merge(peak_ratio[["region_name", "peak_ratio"]], on="region_name", how="left")
    return features.fillna(0.0)


if __name__ == "__main__":
    out = build_features()
    print(out.head())

