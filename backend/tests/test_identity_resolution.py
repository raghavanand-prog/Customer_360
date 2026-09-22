"""T-09/T-10: identity resolution against the hand-built worked examples (§10.8)."""
from pathlib import Path

import pytest
import yaml

from c360.identity.resolve import resolve_identities

CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config"


@pytest.fixture(scope="module")
def rules_cfg():
    return yaml.safe_load((CONFIG_ROOT / "identity_rules.yaml").read_text())


@pytest.fixture(scope="module")
def denylist_cfg():
    return yaml.safe_load((CONFIG_ROOT / "identity_denylist.yaml").read_text())


def _edges_df(spark, rows):
    return spark.createDataFrame(rows, ["source_system", "source_record_id", "identity_namespace", "identity_value_norm"])


def _attrs_df(spark, rows):
    return spark.createDataFrame(rows, ["source_system", "source_record_id", "first_name_norm", "last_name_norm", "full_name_norm"])


def test_example1_canonical_case(spark, rules_cfg, denylist_cfg):
    edges = _edges_df(spark, [
        ("crm", "C102", "email", "user@example.com"),
        ("crm", "C102", "crm_id", "C102"),
        ("app", "W883", "email", "user@example.com"),
        ("app", "W883", "app_user_id", "W883"),
        ("orders", "O5001", "crm_id", "C102"),
    ])
    result = resolve_identities(spark, edges, None, denylist_cfg, rules_cfg, run_id=1)
    ids = {r["source_record_key"]: r["canonical_customer_id"] for r in result.customer_identities.collect()}
    assert ids["crm:C102"] == ids["app:W883"] == ids["orders:O5001"]


def test_example2_transitive_three_hop_chain(spark, rules_cfg, denylist_cfg):
    edges = _edges_df(spark, [
        ("crm", "C500", "email", "a@example.com"),
        ("crm", "C500", "phone", "+919000000001"),
        ("loyalty", "L900", "phone", "+919000000001"),
        ("app", "U700", "email", "a@example.com"),
        ("support", "T44", "email", "b@example.com"),
    ])
    result = resolve_identities(spark, edges, None, denylist_cfg, rules_cfg, run_id=1)
    ids = {r["source_record_key"]: r["canonical_customer_id"] for r in result.customer_identities.collect()}
    assert ids["crm:C500"] == ids["loyalty:L900"] == ids["app:U700"]
    assert ids["support:T44"] != ids["crm:C500"]


def test_example3_shared_phone_must_not_merge(spark, rules_cfg, denylist_cfg):
    edges = _edges_df(spark, [
        ("crm", "C610", "phone", "+919111111111"),
        ("crm", "C610", "email", "ravi.kumar@example.com"),
        ("crm", "C611", "phone", "+919111111111"),
        ("crm", "C611", "email", "sunita.kumar@example.com"),
    ])
    attrs = _attrs_df(spark, [
        ("crm", "C610", "ravi", "kumar", "ravi kumar"),
        ("crm", "C611", "sunita", "kumar", "sunita kumar"),
    ])
    result = resolve_identities(spark, edges, attrs, denylist_cfg, rules_cfg, run_id=1)
    ids = {r["source_record_key"]: r["canonical_customer_id"] for r in result.customer_identities.collect()}
    assert ids["crm:C610"] != ids["crm:C611"]
    assert any(r["reason"] == "attribute_conflict" for r in result.review_queue_rows)


def test_example4_switchboard_frequency_screen(spark, rules_cfg, denylist_cfg):
    rows = [("crm", f"C{i}", "phone", "+911234500000") for i in range(12)] + \
           [("app", f"U{i}", "phone", "+911234500000") for i in range(12)]
    edges = _edges_df(spark, rows)
    result = resolve_identities(spark, edges, None, denylist_cfg, rules_cfg, run_id=1)
    ids = {r["source_record_key"]: r["canonical_customer_id"] for r in result.customer_identities.collect()}
    # the switchboard number must not link anyone: every record is its own cluster
    assert len(set(ids.values())) == len(ids)
    screened = [r["screen_reason"] for r in result.screened_log.collect()]
    assert any(r == "S3_frequency_threshold" for r in screened)


def test_singleton_with_no_usable_identifier(spark, rules_cfg, denylist_cfg):
    from pyspark.sql.types import StringType, StructField, StructType
    schema = StructType([
        StructField("source_system", StringType()), StructField("source_record_id", StringType()),
        StructField("identity_namespace", StringType()), StructField("identity_value_norm", StringType()),
    ])
    edges = spark.createDataFrame([("orders", "O9999", "email", None)], schema)
    result = resolve_identities(spark, edges, None, denylist_cfg, rules_cfg, run_id=1)
    ids = {r["source_record_key"]: r["canonical_customer_id"] for r in result.customer_identities.collect()}
    assert "orders:O9999" in ids


def test_generic_email_does_not_link(spark, rules_cfg, denylist_cfg):
    edges = _edges_df(spark, [
        ("crm", "C1", "email", "info@partner-example.com"),
        ("app", "U1", "email", "info@partner-example.com"),
    ])
    result = resolve_identities(spark, edges, None, denylist_cfg, rules_cfg, run_id=1)
    ids = {r["source_record_key"]: r["canonical_customer_id"] for r in result.customer_identities.collect()}
    assert ids["crm:C1"] != ids["app:U1"]


def test_two_runs_on_unchanged_input_produce_identical_canonical_ids(spark, rules_cfg, denylist_cfg):
    edges = _edges_df(spark, [
        ("crm", "C102", "email", "user@example.com"),
        ("app", "W883", "email", "user@example.com"),
    ])
    r1 = resolve_identities(spark, edges, None, denylist_cfg, rules_cfg, run_id=1)
    ids1 = {r["source_record_key"]: r["canonical_customer_id"] for r in r1.customer_identities.collect()}
    r2 = resolve_identities(spark, edges, None, denylist_cfg, rules_cfg, run_id=2)
    ids2 = {r["source_record_key"]: r["canonical_customer_id"] for r in r2.customer_identities.collect()}
    assert ids1 == ids2
