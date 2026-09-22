"""Parquet/DataFrame -> PostgreSQL loader (C-08): COPY into staging, then
upsert into the serving table inside one transaction per table (§6.2).
"""
from __future__ import annotations

import io
import json

import pandas as pd
import psycopg


def _to_copy_buffer(df: pd.DataFrame) -> io.StringIO:
    buf = io.StringIO()
    df.to_csv(buf, index=False, header=False, na_rep="\\N")
    buf.seek(0)
    return buf


def upsert_dataframe(conn: psycopg.Connection, df: pd.DataFrame, table: str, pk_cols: list[str]) -> int:
    if df.empty:
        return 0
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].map(lambda v: json.dumps(v) if isinstance(v, (dict, list)) else v)

    columns = list(df.columns)
    update_cols = [c for c in columns if c not in pk_cols]
    staging_table = f"stg_{table}"

    with conn.cursor() as cur:
        cur.execute(f"CREATE TEMP TABLE {staging_table} (LIKE {table} INCLUDING DEFAULTS) ON COMMIT DROP")
        col_list = ", ".join(f'"{c}"' for c in columns)
        with cur.copy(f"COPY {staging_table} ({col_list}) FROM STDIN WITH (FORMAT csv, NULL '\\N')") as copy:
            copy.write(_to_copy_buffer(df).read())

        pk_list = ", ".join(f'"{c}"' for c in pk_cols)
        if update_cols:
            set_clause = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in update_cols)
            conflict_clause = f"ON CONFLICT ({pk_list}) DO UPDATE SET {set_clause}"
        else:
            conflict_clause = f"ON CONFLICT ({pk_list}) DO NOTHING"

        cur.execute(
            f'INSERT INTO {table} ({col_list}) SELECT {col_list} FROM {staging_table} {conflict_clause}'
        )
        return cur.rowcount


def load_spark_df(conn: psycopg.Connection, spark_df, table: str, pk_cols: list[str]) -> int:
    pdf = spark_df.toPandas()
    return upsert_dataframe(conn, pdf, table, pk_cols)
