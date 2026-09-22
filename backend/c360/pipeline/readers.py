"""Raw ingestion (J-01, F-01): all-string read + lineage columns."""
from __future__ import annotations

from pathlib import Path

from pyspark.sql import DataFrame, SparkSession, Window
from pyspark.sql import functions as F

from c360.schema.datasets import ALL_CONTRACTS

DELIMITERS = {"loyalty_members": ";"}
FORMATS = {
    "customers_crm": "csv", "loyalty_members": "csv", "products": "csv",
    "order_items": "csv", "support_tickets": "csv",
    "app_users": "json", "orders": "json", "marketing_events": "json",
    "web_events": "json_gz",
}


def read_raw(spark: SparkSession, dataset: str, input_root: Path, run_id: int) -> DataFrame:
    fmt = FORMATS[dataset]
    if fmt == "csv":
        path = str(input_root / f"{dataset if dataset != 'customers_crm' else 'customers_crm'}.csv")
        df = (spark.read.option("header", True)
              .option("delimiter", DELIMITERS.get(dataset, ","))
              .option("mode", "PERMISSIVE")
              .csv(path))
    elif fmt == "json":
        path = str(input_root / f"{dataset}.jsonl")
        df = spark.read.option("primitivesAsString", "true").option("mode", "PERMISSIVE").json(path)
    else:  # json_gz, date-partitioned directory
        path = str(input_root / "web_events" / "dt=*" / "*.jsonl.gz")
        df = (spark.read.option("primitivesAsString", "true").option("mode", "PERMISSIVE")
              .json(path)
              .withColumn("_source_file", F.input_file_name()))

    df = df.withColumn("_source_file", F.coalesce(F.col("_source_file"), F.input_file_name())) \
        if "_source_file" in df.columns else df.withColumn("_source_file", F.input_file_name())
    df = df.withColumn("_ingested_at", F.current_timestamp())
    df = df.withColumn("_run_id", F.lit(run_id))
    df = df.withColumn(
        "_source_row_num",
        F.row_number().over(Window.partitionBy("_source_file").orderBy(F.monotonically_increasing_id())),
    )
    return df
