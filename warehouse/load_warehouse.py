from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


load_dotenv()


def _safe_int_id(series: pd.Series) -> pd.Series:
    return pd.util.hash_pandas_object(series.astype(str), index=False).astype("int64")


def load_warehouse(
    processed_dir: str | None = None,
    db_url: str | None = None,
    cleaned_subdir: str = "cleaned_usage",
) -> None:
    processed_dir = processed_dir or os.getenv("DATA_PROCESSED_DIR", "data/processed")
    db_url = db_url or os.getenv("WAREHOUSE_DB_URL")
    if not db_url:
        raise ValueError("WAREHOUSE_DB_URL is not configured")

    cleaned_path = Path(processed_dir) / cleaned_subdir
    if not cleaned_path.exists():
        raise FileNotFoundError(f"Processed parquet path not found: {cleaned_path}")

    usage_df = pd.read_parquet(cleaned_path)
    if usage_df.empty:
        raise ValueError("Processed dataset is empty; nothing to load.")

    usage_df["event_timestamp"] = pd.to_datetime(usage_df["event_timestamp"], errors="coerce")
    usage_df["event_date"] = pd.to_datetime(usage_df["event_date"], errors="coerce")
    usage_df = usage_df.dropna(subset=["event_timestamp", "event_date", "grid_id"])

    usage_df["call_count"] = usage_df["call_count"].fillna(0).astype(int)
    usage_df["sms_count"] = usage_df["sms_count"].fillna(0).astype(int)
    usage_df["internet_usage"] = usage_df["internet_usage"].fillna(0.0).astype(float)
    usage_df["hour"] = usage_df["event_timestamp"].dt.hour.astype(int)

    if "region_name" not in usage_df.columns:
        usage_df["region_name"] = usage_df["grid_id"].astype(str)
    if "city" not in usage_df.columns:
        usage_df["city"] = "Unknown"

    dim_time = (
        usage_df[["event_date", "hour"]]
        .drop_duplicates()
        .rename(columns={"event_date": "date"})
        .assign(
            day=lambda x: x["date"].dt.day.astype(int),
            month=lambda x: x["date"].dt.month.astype(int),
            weekday=lambda x: x["date"].dt.day_name(),
        )
    )
    dim_time["time_id"] = _safe_int_id(dim_time["date"].astype(str) + "|" + dim_time["hour"].astype(str))
    dim_time_sql = dim_time.copy()
    dim_time_sql["date"] = dim_time_sql["date"].dt.date
    dim_time_sql["time_id"] = dim_time_sql["time_id"].astype("int64")

    dim_region = usage_df[["region_name", "city"]].drop_duplicates().reset_index(drop=True)
    dim_region["region_id"] = _safe_int_id(
        dim_region["region_name"].astype(str) + "|" + dim_region["city"].astype(str)
    )
    dim_region["region_id"] = dim_region["region_id"].astype("int64")

    fact = usage_df.merge(
        dim_time[["time_id", "date", "hour"]],
        left_on=["event_date", "hour"],
        right_on=["date", "hour"],
        how="left",
    ).merge(
        dim_region[["region_id", "region_name", "city"]],
        on=["region_name", "city"],
        how="left",
    )

    fact = fact[["time_id", "region_id", "call_count", "sms_count", "internet_usage"]].copy()
    fact = fact.dropna(subset=["time_id", "region_id"])
    fact["usage_id"] = _safe_int_id(
        fact["time_id"].astype(str)
        + "|"
        + fact["region_id"].astype(str)
        + "|"
        + fact["call_count"].astype(str)
        + "|"
        + fact["sms_count"].astype(str)
        + "|"
        + fact["internet_usage"].astype(str)
    )
    fact = fact.rename(columns={"internet_usage": "internet_mb"})
    fact["usage_id"] = fact["usage_id"].astype("int64")
    fact["time_id"] = fact["time_id"].astype("int64")
    fact["region_id"] = fact["region_id"].astype("int64")

    engine = create_engine(db_url)
    with engine.begin() as conn:
        schema_sql = Path(__file__).resolve().parent / "schema.sql"
        schema_text = schema_sql.read_text()
        for statement in [s.strip() for s in schema_text.split(";") if s.strip()]:
            conn.execute(text(statement))
        conn.execute(text("DELETE FROM fact_usage"))
        conn.execute(text("DELETE FROM dim_time"))
        conn.execute(text("DELETE FROM dim_region"))

    import sqlite3
    db_path = db_url.replace("sqlite:///", "")
    with sqlite3.connect(db_path) as conn_sqlite:
        dim_time_sql[["time_id", "date", "hour", "day", "month", "weekday"]].to_sql(
            "dim_time", conn_sqlite, if_exists="append", index=False
        )
        dim_region[["region_id", "region_name", "city"]].to_sql(
            "dim_region", conn_sqlite, if_exists="append", index=False
        )
        fact[["usage_id", "time_id", "region_id", "call_count", "sms_count", "internet_mb"]].to_sql(
            "fact_usage", conn_sqlite, if_exists="append", index=False
        )

    print("Warehouse load completed successfully.")


if __name__ == "__main__":
    load_warehouse()

