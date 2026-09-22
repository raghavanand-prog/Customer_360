"""Iterative connected components: transitive closure over the identity graph.

No GraphFrames dependency (ADR-12): this is small-to-large / min-label
propagation, checkpointed every iteration so the query plan does not grow
with the number of iterations (§10.6). Non-convergence within
``max_iterations`` fails loudly rather than emitting a half-merged result.
"""
from __future__ import annotations

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


class IdentityResolutionNonConvergence(RuntimeError):
    pass


def connected_components(
    spark: SparkSession,
    vertices: DataFrame,   # column: source_record_key
    edges: DataFrame,      # columns: record_a, record_b
    max_iterations: int = 20,
    checkpoint_dir: str | None = None,
) -> DataFrame:
    """Returns (source_record_key, cluster_key) where cluster_key is the
    deterministic minimum vertex key in the connected component."""
    if checkpoint_dir:
        spark.sparkContext.setCheckpointDir(checkpoint_dir)

    labels = vertices.select(F.col("source_record_key").alias("v")).distinct() \
        .withColumn("label", F.col("v"))

    und_edges = (
        edges.select(F.col("record_a").alias("a"), F.col("record_b").alias("b"))
        .filter(F.col("a").isNotNull() & F.col("b").isNotNull() & (F.col("a") != F.col("b")))
        .distinct()
        .cache()
    )
    und_edges.count()  # materialise the cache before the loop (§8.3 caching discipline)

    converged = False
    for iteration in range(max_iterations):
        msgs_fwd = und_edges.join(labels, und_edges.a == labels.v).select(
            F.col("b").alias("v"), F.col("label"))
        msgs_bwd = und_edges.join(labels, und_edges.b == labels.v).select(
            F.col("a").alias("v"), F.col("label"))
        incoming_min = msgs_fwd.unionByName(msgs_bwd).groupBy("v").agg(F.min("label").alias("incoming_min"))

        new_labels = (
            labels.join(incoming_min, on="v", how="left")
            .withColumn("new_label", F.least(F.col("label"), F.coalesce(F.col("incoming_min"), F.col("label"))))
        )
        changed_count = new_labels.filter(F.col("new_label") != F.col("label")).count()
        new_labels = new_labels.select("v", F.col("new_label").alias("label"))
        new_labels = new_labels.localCheckpoint(eager=True)

        labels = new_labels
        if changed_count == 0:
            converged = True
            break

    und_edges.unpersist()

    if not converged:
        raise IdentityResolutionNonConvergence(
            f"Connected components did not converge within {max_iterations} iterations")

    return labels.withColumnRenamed("v", "source_record_key").withColumnRenamed("label", "cluster_key")
