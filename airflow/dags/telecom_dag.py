from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from airflow import DAG
from airflow.operators.python import PythonOperator
from dotenv import load_dotenv

load_dotenv()

LANDING_DIR = Path(os.getenv("DATA_LANDING_DIR", "data/landing"))
RAW_DIR = Path(os.getenv("DATA_RAW_DIR", "data/raw"))
REJECTED_DIR = Path(os.getenv("DATA_REJECTED_DIR", "data/rejected"))
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from warehouse.load_warehouse import load_warehouse  # noqa: E402

PIPELINE_FILE = PROJECT_ROOT / "spark" / "telecom_pipeline.py"
EXPECTED_COLUMNS = {"timestamp", "grid_id", "call_count", "sms_count", "internet_usage"}


def detect_files(**context) -> None:
    csv_files = sorted(str(p) for p in LANDING_DIR.glob("*.csv"))
    print(f"Detected {len(csv_files)} files in landing zone.")
    context["ti"].xcom_push(key="landing_files", value=csv_files)


def validate_files(**context) -> None:
    landing_files = context["ti"].xcom_pull(key="landing_files", task_ids="detect_files") or []
    valid, invalid = [], []

    for file_path in landing_files:
        try:
            sample = pd.read_csv(file_path, nrows=200)
            has_columns = EXPECTED_COLUMNS.issubset(set(c.strip().lower() for c in sample.columns))
            required_not_null = True
            if has_columns:
                required_not_null = sample[list(EXPECTED_COLUMNS)].isnull().any().sum() == 0
            (valid if has_columns and required_not_null else invalid).append(file_path)
        except Exception:
            invalid.append(file_path)

    context["ti"].xcom_push(key="valid_files", value=valid)
    context["ti"].xcom_push(key="invalid_files", value=invalid)
    print(f"Valid files: {len(valid)}, invalid files: {len(invalid)}")


def move_files(**context) -> None:
    valid_files = context["ti"].xcom_pull(key="valid_files", task_ids="validate_files") or []
    invalid_files = context["ti"].xcom_pull(key="invalid_files", task_ids="validate_files") or []
    moved, rejected, duplicates = [], [], []

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    REJECTED_DIR.mkdir(parents=True, exist_ok=True)

    for src in valid_files:
        source = Path(src)
        target = RAW_DIR / source.name
        if target.exists():
            duplicates.append(source.name)
            shutil.move(str(source), str(REJECTED_DIR / f"duplicate_{source.name}"))
        else:
            shutil.move(str(source), str(target))
            moved.append(source.name)

    for src in invalid_files:
        source = Path(src)
        shutil.move(str(source), str(REJECTED_DIR / source.name))
        rejected.append(source.name)

    context["ti"].xcom_push(key="moved_files", value=moved)
    context["ti"].xcom_push(key="rejected_files", value=rejected)
    context["ti"].xcom_push(key="duplicate_files", value=duplicates)


def log_status(**context) -> None:
    moved = context["ti"].xcom_pull(key="moved_files", task_ids="move_files") or []
    rejected = context["ti"].xcom_pull(key="rejected_files", task_ids="move_files") or []
    duplicates = context["ti"].xcom_pull(key="duplicate_files", task_ids="move_files") or []
    print({"moved": moved, "rejected": rejected, "duplicates": duplicates})


def run_spark_job() -> None:
    try:
        subprocess.run(["python3", str(PIPELINE_FILE)], check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"Spark pipeline execution failed: {exc}") from exc


def load_warehouse_task() -> None:
    load_warehouse()


def notify(**context) -> None:
    moved = context["ti"].xcom_pull(key="moved_files", task_ids="move_files") or []
    print(f"Pipeline completed. Files ingested: {len(moved)}")


with DAG(
    dag_id="telecom_dag",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["telecom", "capstone"],
) as dag:
    detect_files_task = PythonOperator(task_id="detect_files", python_callable=detect_files)
    validate_files_task = PythonOperator(task_id="validate_files", python_callable=validate_files)
    move_files_task = PythonOperator(task_id="move_files", python_callable=move_files)
    log_status_task = PythonOperator(task_id="log_status", python_callable=log_status)
    run_spark_job_task = PythonOperator(task_id="run_spark_job", python_callable=run_spark_job)
    load_warehouse_operator = PythonOperator(task_id="load_warehouse", python_callable=load_warehouse_task)
    notify_task = PythonOperator(task_id="notify", python_callable=notify)

    (
        detect_files_task
        >> validate_files_task
        >> move_files_task
        >> log_status_task
        >> run_spark_job_task
        >> load_warehouse_operator
        >> notify_task
    )

