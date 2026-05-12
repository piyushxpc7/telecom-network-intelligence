# Design Document: Telecom Network Intelligence System

## 1. Introduction
The Telecom Network Intelligence System is a scalable data platform designed to monitor, analyze, and predict telecommunications network usage. By processing millions of records from cell tower grids, the system identifies peak usage hours, regional hotspots, and potential congestion risks.

## 2. Design Goals
- **Scalability**: Handle datasets exceeding 10M+ records using distributed computing (Spark).
- **Automation**: Orchestrate the full ETL and ML lifecycle with minimal manual intervention (Airflow).
- **Insightfulness**: Provide actionable intelligence through interactive visualizations and predictive modeling.

## 3. Data Design
### 3.1 Medallion Architecture
- **Bronze (Raw)**: Original Kaggle CSV files (15M+ rows).
- **Silver (Processed)**: Cleaned, partitioned Parquet files with merged activity metrics.
- **Gold (Warehouse)**: SQLite tables optimized for dashboard queries.

### 3.2 Schema Design
- `fact_usage`: Stores individual usage events linked to region and time IDs.
- `dim_region`: Metadata for cell grids (Name, City).
- `dim_time`: Temporal dimensions (Hour, Date, Weekend flag).

## 4. Machine Learning Design
### 4.1 Feature Set
- `avg_call_count`: Rolling average of calls per hour.
- `avg_internet_usage`: Rolling average of data consumption.
- `peak_hour_flag`: Boolean indicator for high-traffic windows.

### 4.2 Model Performance
The Random Forest model is trained to classify congestion risk. The system prioritizes **Recall** for the "HIGH" risk class to ensure network administrators are alerted to potential issues early.

## 5. Frontend & UI/UX
The dashboard is designed using modern design principles:
- **Responsive Layout**: Works across mobile and desktop.
- **Real-time Filtering**: Users can drill down by region or specific dates.
- **Visual Clarity**: High-contrast charts highlighting anomalies and peak hours.

## 6. Deployment & Operations
- **Containerization**: Standardized environments for Spark and Airflow.
- **Monitoring**: Integrated logging for pipeline failures and data drift detection.
