"""T-07/T-07b: DQ engine classification invariants (§9.8)."""
from pathlib import Path

from c360.dq.engine import evaluate, load_ruleset, rules_for_dataset
from c360.pipeline.readers import read_raw
from c360.pipeline.typing_clean import apply_cleaning, apply_contract_typing
from c360.schema.datasets import ALL_CONTRACTS

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "dq_rules.yaml"


def _evaluate(spark, dataset, input_root):
    contract = ALL_CONTRACTS[dataset]
    df = read_raw(spark, dataset, input_root, run_id=1)
    df = apply_contract_typing(df, contract)
    df = apply_cleaning(df)
    config = load_ruleset(CONFIG_PATH)
    rules = rules_for_dataset(config, dataset)
    return evaluate(df, dataset, rules)


def test_record_conservation_invariant(spark, generated_tiny_dataset):
    """accepted + accepted_with_warning + quarantined + rejected == ingested."""
    result = _evaluate(spark, "customers_crm", generated_tiny_dataset)
    s = result["scores"]
    total = s["records_accepted"] + s["records_warned"] + s["records_quarantined"] + s["records_rejected"]
    assert total == s["records_ingested"]


def test_at_least_30_rules_across_six_dimensions():
    config = load_ruleset(CONFIG_PATH)
    all_rules = []
    for ds in config["datasets"].values():
        all_rules.extend(ds["rules"])
    assert len(all_rules) >= 30
    dimensions = {r["dimension"] for r in all_rules}
    assert dimensions == {"completeness", "validity", "uniqueness", "consistency", "integrity", "timeliness"}


def test_quarantine_never_empty_denominator(spark, generated_tiny_dataset):
    result = _evaluate(spark, "orders", generated_tiny_dataset)
    assert result["scores"]["score_overall"] is not None
    assert 0 <= result["scores"]["score_overall"] <= 100


def test_defect_free_data_scores_100_on_every_active_rule(spark, generated_tiny_clean_dataset):
    result = _evaluate(spark, "customers_crm", generated_tiny_clean_dataset)
    for rule in result["rule_results"]:
        assert rule["records_failed"] == 0, rule
