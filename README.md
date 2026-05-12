# Telecom Network Intelligence System

End-to-end capstone project covering data engineering, analytics, APIs, dashboarding, and ML for telecom activity data.

## Documentation
- [Design Document](docs/design-document.md): Detailed project scope and technical specifications.
- [Architecture Overview](docs/architecture.md): Data flow and component interaction.
- [Architecture Diagram](docs/architecture-diagram.png): Visual representation of the system.

## Implemented phases

- Phase 1: EDA notebook template + complete `UsageProcessor` class + API enrichment stub
- Phase 2: end-to-end PySpark ETL with schema, cleaning, normalization, join, aggregations, parquet output
- Phase 3: Airflow ingestion DAG + star schema + parquet-to-warehouse loader
- Phase 4: FastAPI with 5 endpoints, Pydantic models, structured error responses
- Phase 5: React (Vite) dashboard with 4 pages consuming backend APIs
- Phase 6: Feature engineering, model training, real prediction API integration, batch scoring

## Setup

1. Python environment
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`
2. Create environment file
   - `cp .env.example .env`
   - update `WAREHOUSE_DB_URL` and paths
3. Prepare data
   - Place incoming files in `data/landing/`
   - Add region map CSV in `data/raw/region_mapping.csv` with columns:
     - `grid_id,region_name,city`

## Run order (end-to-end)

1. Run Spark ETL directly
   - `python3 spark/telecom_pipeline.py`
2. Load warehouse tables
   - `python3 warehouse/load_warehouse.py`
3. Train model
   - `python3 ml/train_model.py`
4. Batch scoring
   - `python3 ml/batch_score.py`
5. Start FastAPI
   - `uvicorn api.main:app --reload --host 0.0.0.0 --port 8000`
6. Start React app
   - `cd react-app && npm install && npm run dev`
7. Airflow orchestration (optional run path)
   - deploy `airflow/dags/telecom_dag.py` in Airflow and trigger `telecom_dag`

## Required SQL validation query

```sql
SELECT r.region_name, t.hour, SUM(f.call_count) AS total_calls
FROM fact_usage f
JOIN dim_time t ON f.time_id = t.time_id
JOIN dim_region r ON f.region_id = r.region_id
GROUP BY r.region_name, t.hour
ORDER BY total_calls DESC
LIMIT 10;
```

## API endpoints

- `GET /usage/summary`
- `GET /usage/region/{region}`
- `GET /usage/peak`
- `GET /usage/features/{region}`
- `POST /predict-usage-risk`

Swagger docs: `http://localhost:8000/docs`
