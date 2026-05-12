from __future__ import annotations

import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from ml.predict import predict_usage_risk


from fastapi.middleware.cors import CORSMiddleware

load_dotenv()
DB_URL = os.getenv("WAREHOUSE_DB_URL")
if not DB_URL:
    raise RuntimeError("WAREHOUSE_DB_URL must be set in environment.")
engine = create_engine(DB_URL)

app = FastAPI(title="Telecom Network Intelligence API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ErrorResponse(BaseModel):
    detail: str
    status_code: int


class UsageSummaryResponse(BaseModel):
    total_calls: int
    total_sms: int
    total_internet_mb: float
    top_peak_hours: List[int]
    top_busiest_regions: List[str]


class HourlyUsagePoint(BaseModel):
    hour: int
    calls: float
    sms: float
    internet_mb: float


class RegionUsageResponse(BaseModel):
    region: str
    hourly_distribution: List[HourlyUsagePoint]
    trend: List[HourlyUsagePoint]


class TopUsageItem(BaseModel):
    hour: int | None = None
    region: str | None = None
    total_usage: float


class PeakTrafficResponse(BaseModel):
    top_hours: List[TopUsageItem]
    top_regions: List[TopUsageItem]


class FeatureResponse(BaseModel):
    region: str
    avg_usage: float
    growth_rate: float
    variability: float
    peak_ratio: float


class PredictRequest(BaseModel):
    region: str
    avg_usage: float = Field(ge=0)
    growth_rate: float
    variability: float = Field(ge=0)
    peak_ratio: float = Field(default=1.0, ge=0)


class PredictResponse(BaseModel):
    congestion_risk: str
    anomaly_flag: bool
    score: float


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(detail=str(exc), status_code=422).model_dump(),
    )


@app.exception_handler(Exception)
async def generic_exception_handler(_, exc: Exception):
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(detail=str(exc), status_code=500).model_dump(),
    )


@app.get("/usage/summary", response_model=UsageSummaryResponse)
def usage_summary():
    query = """
    SELECT
      COALESCE(SUM(call_count), 0) AS total_calls,
      COALESCE(SUM(sms_count), 0) AS total_sms,
      COALESCE(SUM(internet_mb), 0) AS total_internet_mb
    FROM fact_usage;
    """
    peak_hour_query = """
    SELECT t.hour, SUM(f.call_count + f.sms_count + f.internet_mb) AS total_usage
    FROM fact_usage f JOIN dim_time t ON f.time_id = t.time_id
    GROUP BY t.hour ORDER BY total_usage DESC LIMIT 3;
    """
    busiest_region_query = """
    SELECT r.region_name, SUM(f.call_count + f.sms_count + f.internet_mb) AS total_usage
    FROM fact_usage f JOIN dim_region r ON f.region_id = r.region_id
    GROUP BY r.region_name ORDER BY total_usage DESC LIMIT 3;
    """
    with engine.begin() as conn:
        totals = conn.execute(text(query)).mappings().first()
        peaks = conn.execute(text(peak_hour_query)).mappings().all()
        regions = conn.execute(text(busiest_region_query)).mappings().all()
    return UsageSummaryResponse(
        total_calls=int(totals["total_calls"]),
        total_sms=int(totals["total_sms"]),
        total_internet_mb=float(totals["total_internet_mb"]),
        top_peak_hours=[int(p["hour"]) for p in peaks],
        top_busiest_regions=[r["region_name"] for r in regions],
    )


@app.get("/usage/region/{region}", response_model=RegionUsageResponse)
def usage_region(region: str):
    hourly_query = """
    SELECT t.hour, SUM(f.call_count) AS calls, SUM(f.sms_count) AS sms, SUM(f.internet_mb) AS internet_mb
    FROM fact_usage f
    JOIN dim_time t ON f.time_id = t.time_id
    JOIN dim_region r ON f.region_id = r.region_id
    WHERE LOWER(r.region_name) = LOWER(:region)
    GROUP BY t.hour
    ORDER BY t.hour;
    """
    trend_query = """
    SELECT t.hour, AVG(f.call_count) AS calls, AVG(f.sms_count) AS sms, AVG(f.internet_mb) AS internet_mb
    FROM fact_usage f
    JOIN dim_time t ON f.time_id = t.time_id
    JOIN dim_region r ON f.region_id = r.region_id
    WHERE LOWER(r.region_name) = LOWER(:region)
    GROUP BY t.hour
    ORDER BY t.hour;
    """
    with engine.begin() as conn:
        hourly = [dict(row) for row in conn.execute(text(hourly_query), {"region": region}).mappings().all()]
        trend = [dict(row) for row in conn.execute(text(trend_query), {"region": region}).mappings().all()]
    if not hourly:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found")
    return RegionUsageResponse(region=region, hourly_distribution=hourly, trend=trend)


@app.get("/usage/peak", response_model=PeakTrafficResponse)
def usage_peak():
    hours_query = """
    SELECT t.hour, SUM(f.call_count + f.sms_count + f.internet_mb) AS total_usage
    FROM fact_usage f JOIN dim_time t ON f.time_id = t.time_id
    GROUP BY t.hour ORDER BY total_usage DESC LIMIT 5;
    """
    regions_query = """
    SELECT r.region_name AS region, SUM(f.call_count + f.sms_count + f.internet_mb) AS total_usage
    FROM fact_usage f JOIN dim_region r ON f.region_id = r.region_id
    GROUP BY r.region_name ORDER BY total_usage DESC LIMIT 5;
    """
    with engine.begin() as conn:
        top_hours = [dict(row) for row in conn.execute(text(hours_query)).mappings().all()]
        top_regions = [dict(row) for row in conn.execute(text(regions_query)).mappings().all()]
    return PeakTrafficResponse(top_hours=top_hours, top_regions=top_regions)


@app.get("/usage/features/{region}", response_model=FeatureResponse)
def usage_features(region: str):
    q = """
    SELECT t.date, t.hour, f.call_count, f.sms_count, f.internet_mb
    FROM fact_usage f
    JOIN dim_time t ON f.time_id = t.time_id
    JOIN dim_region r ON f.region_id = r.region_id
    WHERE LOWER(r.region_name) = LOWER(:region)
    ORDER BY t.date, t.hour;
    """
    with engine.begin() as conn:
        rows = [dict(r) for r in conn.execute(text(q), {"region": region}).mappings().all()]
    if not rows:
        raise HTTPException(status_code=404, detail=f"Region '{region}' not found")

    import pandas as pd

    df = pd.DataFrame(rows)
    df["total_usage"] = df["call_count"] + df["sms_count"] + df["internet_mb"]
    daily = df.groupby("date", as_index=False)["total_usage"].sum().sort_values("date")
    daily["prev"] = daily["total_usage"].shift(1)
    growth = ((daily["total_usage"] - daily["prev"]) / daily["prev"]).replace([float("inf"), -float("inf")], 0).fillna(0)

    avg_usage = float(daily["total_usage"].mean())
    growth_rate = float(growth.mean())
    variability = float(daily["total_usage"].std() or 0.0)
    peak_ratio = float(df.groupby("hour")["total_usage"].sum().max() / (df.groupby("hour")["total_usage"].sum().mean() or 1))
    return FeatureResponse(
        region=region,
        avg_usage=avg_usage,
        growth_rate=growth_rate,
        variability=variability,
        peak_ratio=peak_ratio,
    )


@app.post("/predict-usage-risk", response_model=PredictResponse)
def predict_usage(req: PredictRequest):
    prediction = predict_usage_risk(
        {
            "avg_usage": req.avg_usage,
            "growth_rate": req.growth_rate,
            "variability": req.variability,
            "peak_ratio": req.peak_ratio,
        }
    )
    return PredictResponse(**prediction)

