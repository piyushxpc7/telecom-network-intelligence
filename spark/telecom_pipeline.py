from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Dict

# Set JAVA_HOME before any PySpark imports
os.environ.setdefault(
    "JAVA_HOME",
    "/opt/homebrew/Cellar/openjdk@17/17.0.19/libexec/openjdk.jdk/Contents/Home",
)

from dotenv import load_dotenv
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F
from pyspark.sql.functions import broadcast
from pyspark.sql.types import DoubleType, StringType, StructField, StructType


load_dotenv()


def create_session() -> SparkSession:
    app_name = os.getenv("SPARK_APP_NAME", "TelecomIntelligencePipeline")
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def usage_schema() -> StructType:
    return StructType(
        [
            StructField("datetime", StringType(), True),
            StructField("CellID", StringType(), True),
            StructField("countrycode", StringType(), True),
            StructField("smsin", DoubleType(), True),
            StructField("smsout", DoubleType(), True),
            StructField("callin", DoubleType(), True),
            StructField("callout", DoubleType(), True),
            StructField("internet", DoubleType(), True),
        ]
    )


def load_data(spark: SparkSession, raw_dir: str) -> DataFrame:
    df = (
        spark.read.format("csv")
        .option("header", True)
        .schema(usage_schema())
        .load(f"{raw_dir}/sms-call-internet-mi-2013-11-0*.csv")
    )

    # Required in assessment: print record count per file.
    per_file = (
        df.withColumn("_source_file", F.input_file_name())
        .groupBy("_source_file")
        .count()
        .orderBy("_source_file")
    )
    print("Record counts by file:")
    per_file.show(truncate=False)
    return df


def clean_data(df: DataFrame) -> DataFrame:
    cleaned = (
        df.select(
            F.col("datetime").alias("timestamp"),
            F.col("CellID").alias("grid_id"),
            (F.coalesce(F.col("callin"), F.lit(0)) + F.coalesce(F.col("callout"), F.lit(0))).alias("call_count"),
            (F.coalesce(F.col("smsin"), F.lit(0)) + F.coalesce(F.col("smsout"), F.lit(0))).alias("sms_count"),
            F.coalesce(F.col("internet"), F.lit(0)).alias("internet_usage"),
        )
        .withColumn("event_timestamp", F.to_timestamp("timestamp"))
        .withColumn("event_date", F.to_date("event_timestamp"))
        .withColumn("hour", F.hour("event_timestamp"))
        .drop("timestamp")
        .filter(F.col("event_timestamp").isNotNull())
        .filter(F.col("grid_id").isNotNull())
    )
    return cleaned


def normalize_activity_types(df: DataFrame) -> DataFrame:
    stacked = (
        df.select(
            "grid_id",
            "event_timestamp",
            "event_date",
            "hour",
            F.array(
                F.struct(F.lit("call").alias("activity_type"), F.col("call_count").alias("activity_value")),
                F.struct(F.lit("sms").alias("activity_type"), F.col("sms_count").alias("activity_value")),
                F.struct(
                    F.lit("internet").alias("activity_type"),
                    F.col("internet_usage").alias("activity_value"),
                ),
            ).alias("activity_array"),
        )
        .withColumn("activity", F.explode("activity_array"))
        .select(
            "grid_id",
            "event_timestamp",
            "event_date",
            "hour",
            F.col("activity.activity_type").alias("activity_type"),
            F.col("activity.activity_value").alias("activity_value"),
        )
    )
    return stacked


def enrich_with_region(cleaned_df: DataFrame, mapping_path: str) -> DataFrame:
    if not Path(mapping_path).exists():
        print(f"region mapping not found at {mapping_path}; continuing without enrichment")
        return cleaned_df

    mapping_schema = StructType(
        [
            StructField("grid_id", StringType(), True),
            StructField("region_name", StringType(), True),
            StructField("city", StringType(), True),
        ]
    )

    mapping_df = (
        cleaned_df.sparkSession.read.format("csv")
        .option("header", True)
        .schema(mapping_schema)
        .load(mapping_path)
        .dropDuplicates(["grid_id"])
    )

    # Broadcast join is appropriate because mapping is a small lookup table.
    return cleaned_df.join(broadcast(mapping_df), on="grid_id", how="left")


def compute_aggregates(df: DataFrame) -> Dict[str, DataFrame]:
    calls_per_hour = df.groupBy("hour").agg(F.sum("call_count").alias("total_calls")).orderBy("hour")
    sms_per_region_day = (
        df.groupBy("event_date", "grid_id")
        .agg(F.sum("sms_count").alias("total_sms"))
        .orderBy("event_date", "grid_id")
    )
    internet_per_day = (
        df.groupBy("event_date")
        .agg(F.sum("internet_usage").alias("total_internet_usage"))
        .orderBy("event_date")
    )
    top_5_peak_hours = (
        df.withColumn("total_usage", F.col("call_count") + F.col("sms_count") + F.col("internet_usage"))
        .groupBy("hour")
        .agg(F.sum("total_usage").alias("total_usage"))
        .orderBy(F.desc("total_usage"))
        .limit(5)
    )

    return {
        "calls_per_hour": calls_per_hour,
        "sms_per_region_day": sms_per_region_day,
        "internet_per_day": internet_per_day,
        "top_5_peak_hours": top_5_peak_hours,
    }


def write_outputs(df: DataFrame, summary: Dict[str, DataFrame], processed_dir: str) -> None:
    cleaned_out = f"{processed_dir}/cleaned_usage"
    summary_out = f"{processed_dir}/summary"

    (
        df.repartition("event_date")
        .write.mode("overwrite")
        .partitionBy("event_date")
        .parquet(cleaned_out)
    )

    for name, summary_df in summary.items():
        summary_df.write.mode("overwrite").parquet(f"{summary_out}/{name}")

    print(f"cleaned data written to: {cleaned_out}")
    print(f"aggregates written to: {summary_out}")


def main() -> None:
    raw_dir = os.getenv("DATA_RAW_DIR", "data/raw")
    processed_dir = os.getenv("DATA_PROCESSED_DIR", "data/processed")
    mapping_path = os.getenv("REGION_MAPPING_PATH", "data/raw/region_mapping.csv")

    spark = create_session()
    try:
        start = time.time()
        raw_df = load_data(spark, raw_dir)
        cleaned_df = clean_data(raw_df)
        normalized_df = normalize_activity_types(cleaned_df)
        normalized_df.cache()
        _ = normalized_df.count()
        cleaned_df = cleaned_df.repartition("grid_id").cache()
        _ = cleaned_df.count()
        enriched_df = enrich_with_region(cleaned_df, mapping_path)

        # Show execution plan for optimization evidence.
        enriched_df.explain(mode="formatted")

        summary = compute_aggregates(enriched_df)
        write_outputs(enriched_df, summary, processed_dir)
        print(f"End-to-end pipeline execution time (seconds): {round(time.time() - start, 2)}")
    finally:
        spark.stop()


if __name__ == "__main__":
    main()

