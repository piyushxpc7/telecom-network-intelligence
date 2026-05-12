from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict

import pandas as pd


@dataclass
class UsageProcessor:
    """Reusable processor for telecom usage data."""

    df: pd.DataFrame = field(default_factory=pd.DataFrame)

    def load_data(self, path: str) -> pd.DataFrame:
        """Load telecom CSV data into a DataFrame."""
        self.df = pd.read_csv(path)
        return self.df

    def clean_data(self) -> pd.DataFrame:
        """Clean and standardize core columns."""
        if self.df.empty:
            raise ValueError("DataFrame is empty. Call load_data() first.")

        df = self.df.copy()
        df.columns = [c.strip().lower() for c in df.columns]

        required_cols = ["timestamp", "grid_id", "call_count", "sms_count", "internet_usage"]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
        df["call_count"] = pd.to_numeric(df["call_count"], errors="coerce")
        df["sms_count"] = pd.to_numeric(df["sms_count"], errors="coerce")
        df["internet_usage"] = pd.to_numeric(df["internet_usage"], errors="coerce")

        df = df.dropna(subset=["timestamp", "grid_id", "call_count", "sms_count", "internet_usage"])
        df = df[
            (df["call_count"] >= 0)
            & (df["sms_count"] >= 0)
            & (df["internet_usage"] >= 0)
        ]

        df["hour"] = df["timestamp"].dt.hour
        df["day"] = df["timestamp"].dt.date
        df = df.drop_duplicates()

        self.df = df.reset_index(drop=True)
        return self.df

    def compute_daily_usage(self) -> pd.DataFrame:
        """Compute total activity by day."""
        if self.df.empty:
            raise ValueError("No cleaned data available.")

        return (
            self.df.groupby("day", as_index=False)[["call_count", "sms_count", "internet_usage"]]
            .sum()
            .rename(
                columns={
                    "call_count": "total_calls",
                    "sms_count": "total_sms",
                    "internet_usage": "total_internet_usage",
                }
            )
        )

    def compute_kpis(self) -> Dict[str, Any]:
        """Compute region totals, avg usage by hour, and peak usage hour."""
        if self.df.empty:
            raise ValueError("No cleaned data available.")

        region_usage = (
            self.df.groupby("grid_id", as_index=False)[["call_count", "sms_count", "internet_usage"]]
            .sum()
            .sort_values("internet_usage", ascending=False)
        )

        hourly_avg = (
            self.df.groupby("hour", as_index=False)[["call_count", "sms_count", "internet_usage"]]
            .mean()
            .rename(
                columns={
                    "call_count": "avg_calls",
                    "sms_count": "avg_sms",
                    "internet_usage": "avg_internet_usage",
                }
            )
        )

        hourly_totals = (
            self.df.assign(total_usage=self.df["call_count"] + self.df["sms_count"] + self.df["internet_usage"])
            .groupby("hour", as_index=False)["total_usage"]
            .sum()
        )
        peak_hour = int(hourly_totals.sort_values("total_usage", ascending=False).iloc[0]["hour"])

        return {
            "total_rows": int(len(self.df)),
            "peak_usage_hour": peak_hour,
            "usage_per_region": region_usage.to_dict(orient="records"),
            "avg_usage_per_hour": hourly_avg.to_dict(orient="records"),
        }


def call_plan_api(customer_id: str) -> Dict[str, Any]:
    """Mock API response for customer plan enrichment."""
    return {
        "customer_id": customer_id,
        "plan_name": "Premium Plus",
        "data_limit_mb": 25000,
        "voice_limit_minutes": 1200,
        "sms_limit": 1000,
        "status": "ACTIVE",
    }

