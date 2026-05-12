# Telecom Network Intelligence System Design Document

## 1. Problem Statement
This project predicts telecom congestion risk at region level using historical call, SMS, and internet activity. The model labels congestion risk as LOW/MEDIUM/HIGH based on usage distribution percentiles. This helps operations teams identify overloaded zones, schedule proactive capacity planning, and flag anomalous spikes before service degradation.

## 2. End-to-End Data Flow
1. Raw CSV telecom logs arrive in `data/landing/`.
2. Airflow validates schema and routes files to `data/raw/` or `data/rejected/`.
3. Spark job cleans and enriches data, then writes partitioned Parquet to `data/processed/`.
4. Warehouse loader builds star schema tables (`dim_time`, `dim_region`, `fact_usage`).
5. FastAPI exposes analytics and prediction endpoints.
6. React dashboard consumes APIs for operational visibility.

## 3. Batch vs Streaming Decisions
| Data Flow | Type | Why |
|---|---|---|
| Network activity logs from cell towers | Streaming | Near-real-time events from network edges |
| Daily usage summary | Batch | Aggregated once per day |
| Monthly billing reports | Batch | Financial cycle-based generation |
| Network congestion alerts | Streaming | Requires immediate operational response |
| Customer dashboard data | Hybrid (batch + near real-time) | Batch baseline plus periodic refresh |

## 4. Storage Strategy
- Raw layer uses CSV because source systems commonly deliver flat files and CSV preserves original structure for traceability.
- Processed layer uses Parquet because it is columnar, compressed, and query-efficient for analytics.
- Partitioning by date improves read performance for time-windowed queries and incremental loads.
- Warehouse uses star schema for performance and cleaner analytical joins; dimensions reduce repetition and support reusable BI queries.

## 5. Warehouse Model
- `dim_time(time_id, date, hour, day, month, weekday)`
- `dim_region(region_id, region_name, city)`
- `fact_usage(usage_id, time_id, region_id, call_count, sms_count, internet_mb)`

The required analytical query is supported by this model:
```sql
SELECT r.region_name, t.hour, SUM(f.call_count) AS total_calls
FROM fact_usage f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_region r ON f.region_id = r.region_id
GROUP BY r.region_name, t.hour
ORDER BY total_calls DESC
LIMIT 10;
```

## 6. Failure Handling Scenarios
1. Missing input file: `detect_files` returns zero; DAG logs and safely exits without Spark failure.
2. Corrupt CSV rows / null required fields: `validate_files` marks file invalid; moved to `data/rejected/`.
3. Duplicate file in landing: `move_files` detects existing name in raw zone; sends duplicate to rejected with `duplicate_` prefix.

## 7. ML Method
- Features: average usage, growth rate, variability, peak ratio.
- Labeling rule:
  - `HIGH`: average usage >= 90th percentile
  - `MEDIUM`: >= 50th percentile and < 90th percentile
  - `LOW`: < 50th percentile
- Model: RandomForestClassifier, 80/20 train-test split.
- Metrics: accuracy and confusion matrix (plus class metrics).
