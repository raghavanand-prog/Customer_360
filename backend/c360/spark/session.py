"""SparkSession factory with the runtime configuration from §8.1."""
from __future__ import annotations

import math

from pyspark.sql import SparkSession


def build_spark(app_name: str, input_bytes_hint: int | None = None, master: str = "local[*]") -> SparkSession:
    shuffle_partitions = 8
    if input_bytes_hint:
        shuffle_partitions = max(8, math.ceil(input_bytes_hint / (128 * 1024 * 1024)))

    builder = (
        SparkSession.builder.appName(app_name)
        .master(master)
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions))
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.skewJoin.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.autoBroadcastJoinThreshold", str(32 * 1024 * 1024))
        .config("spark.sql.sources.partitionOverwriteMode", "dynamic")
        .config("spark.sql.parquet.compression.codec", "snappy")
        .config("spark.sql.session.timeZone", "UTC")
        .config("spark.ui.showConsoleProgress", "false")
    )
    spark = builder.getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    return spark
