"""
Tests for the AIOE to ISCO-08 crosswalk.

These exist so nobody has to take the README's numbers on faith. Running
`pytest` re-derives every headline figure from the committed source files and
fails if any of them has moved.

Three kinds of test are here:

  1. Source integrity. The inputs are what they claim to be.
  2. Reproduction. The pipeline still produces the published diagnostics.
  3. Method. The variance decomposition returns the right answer on cases
     whose answer is known in advance, so a passing reproduction test is not
     just reproducing the same bug.
"""

import json
import os
import subprocess
import sys

import numpy as np
import pandas as pd
import pytest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "src"))

import build_crosswalk as bc  # noqa: E402

DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "out")
TESTS = os.path.dirname(os.path.abspath(__file__))

# Published figures. A change here is a change to the README.
PUBLISHED = {
    "aioe_soc_codes": 774,
    "crosswalk_pairs": 1123,
    "pairs_full": 153,
    "pairs_partial": 970,
    "crosswalk_pairs_with_aioe": 1030,
    "isco_codes_covered": 422,
    "isco_codes_single_soc": 160,
    "isco_codes_multi_soc": 262,
    "aioe_soc_not_in_crosswalk": 3,
    "soc_codes_in_crosswalk": 838,
    "soc_per_isco_max": 35,
    "icc": 0.8299,
    "mean_within_isco_sd": 0.3448,
    "max_within_isco_range": 2.6383,
    "random_pick_spearman": 0.9599,
}


@pytest.fixture(scope="session")
def diagnostics():
    """Run the pipeline once and hand every test the result."""
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "src", "build_crosswalk.py")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, f"pipeline failed:\n{r.stderr}"
    with open(os.path.join(OUT, "diagnostics.json")) as f:
        return json.load(f)


# ---------------------------------------------------------------- integrity --

def test_aioe_is_standardised():
    a = pd.read_csv(os.path.join(DATA, "aioe_soc.csv"))
    assert len(a) == PUBLISHED["aioe_soc_codes"]
    assert a["aioe"].mean() == pytest.approx(0.0, abs=1e-6)
    assert a["aioe"].std(ddof=1) == pytest.approx(1.0, abs=1e-6)
    assert a["soc_code"].is_unique


def test_crosswalk_source_is_intact():
    c = pd.read_csv(os.path.join(DATA, "ISCO_SOC_Crosswalk.csv"), dtype=str)
    assert list(c.columns) == ["isco_08", "soc_2010", "match_type"]
    assert len(c) == PUBLISHED["crosswalk_pairs"]
    assert (c["match_type"] == "partial").sum() == PUBLISHED["pairs_partial"]
    assert (c["match_type"] == "full").sum() == PUBLISHED["pairs_full"]
    assert c["soc_2010"].nunique() == PUBLISHED["soc_codes_in_crosswalk"]
    assert not c.duplicated(["isco_08", "soc_2010"]).any()
    assert c["isco_08"].str.fullmatch(r"\d{4}").all()
    assert c["soc_2010"].str.fullmatch(r"\d{2}-\d{4}").all()


# ------------------------------------------------------------- reproduction --

def test_counts_match_published(diagnostics):
    c = diagnostics["counts"]
    m = diagnostics["match_type"]
    for key in ("aioe_soc_codes", "crosswalk_pairs", "crosswalk_pairs_with_aioe",
                "isco_codes_covered", "isco_codes_single_soc",
                "isco_codes_multi_soc", "aioe_soc_not_in_crosswalk",
                "soc_codes_in_crosswalk"):
        assert c[key] == PUBLISHED[key], key
    assert m["pairs_full"] == PUBLISHED["pairs_full"]
    assert m["pairs_partial"] == PUBLISHED["pairs_partial"]


def test_variance_decomposition_matches_published(diagnostics):
    vd = diagnostics["transfer_error"]["variance_decomposition"]
    assert vd["icc"] == pytest.approx(PUBLISHED["icc"], abs=5e-4)
    assert vd["var_between"] + vd["var_within"] == pytest.approx(
        vd["var_between"] / vd["icc"], rel=1e-9
    )
    assert vd["n_groups"] == PUBLISHED["isco_codes_covered"]
    assert vd["n_obs"] == PUBLISHED["crosswalk_pairs_with_aioe"]


def test_transfer_error_matches_published(diagnostics):
    te = diagnostics["transfer_error"]
    assert te["mean_within_isco_sd"] == pytest.approx(
        PUBLISHED["mean_within_isco_sd"], abs=5e-4)
    assert te["max_within_isco_range"] == pytest.approx(
        PUBLISHED["max_within_isco_range"], abs=5e-4)


def test_ranking_is_robust_to_the_aggregation_rule(diagnostics):
    rs = diagnostics["rank_stability"]
    for key in ("mean_vs_median", "mean_vs_min", "mean_vs_max"):
        assert rs[key] > 0.95, f"{key} fell to {rs[key]}"
    assert rs["random_single_pick_spearman"]["mean"] == pytest.approx(
        PUBLISHED["random_pick_spearman"], abs=5e-3)


def test_outputs_are_well_formed(diagnostics):
    isco = pd.read_csv(os.path.join(OUT, "isco08_aioe.csv"), dtype={"isco_08": str})
    assert len(isco) == PUBLISHED["isco_codes_covered"]
    assert isco["isco_08"].is_unique
    # Every row must carry the spread beside the score. That is the point.
    for col in ("aioe_mean", "aioe_min", "aioe_max", "aioe_sd", "aioe_range",
                "n_soc", "n_partial", "soc_codes"):
        assert col in isco.columns
    assert (isco["aioe_min"] <= isco["aioe_mean"]).all()
    assert (isco["aioe_mean"] <= isco["aioe_max"]).all()
    assert (isco["n_soc"] >= 1).all()
    assert (isco["n_partial"] <= isco["n_soc"]).all()
    assert isco.loc[isco["n_soc"] == 1, "aioe_sd"].eq(0).all()
    assert isco["n_soc"].max() == PUBLISHED["soc_per_isco_max"]
    counted = isco["soc_codes"].str.split("|").str.len()
    assert (counted.to_numpy() == isco["n_soc"].to_numpy()).all()


def test_pipeline_is_deterministic(diagnostics):
    first = json.dumps(diagnostics, sort_keys=True)
    r = subprocess.run(
        [sys.executable, os.path.join(HERE, "src", "build_crosswalk.py")],
        capture_output=True, text=True,
    )
    assert r.returncode == 0
    with open(os.path.join(OUT, "diagnostics.json")) as f:
        second = json.dumps(json.load(f), sort_keys=True)
    assert first == second


# -------------------------------------------------------------------- method --

def test_icc_is_one_when_groups_do_not_disagree_internally():
    """Zero within-group variance means the grouping explains everything."""
    groups = [[1.0, 1.0, 1.0], [5.0, 5.0, 5.0], [9.0, 9.0, 9.0]]
    r = bc.icc_one_way(groups)
    assert r["icc"] == pytest.approx(1.0)
    assert r["var_within"] == pytest.approx(0.0)


def test_icc_is_zero_when_group_means_are_identical():
    """Identical means mean the grouping explains nothing."""
    groups = [[0.0, 2.0], [2.0, 0.0], [0.0, 2.0], [2.0, 0.0]]
    r = bc.icc_one_way(groups)
    assert r["icc"] == pytest.approx(0.0, abs=1e-9)


def test_icc_recovers_a_known_variance_ratio():
    """
    Build data with a between-group variance of 4 and a within-group variance
    of 1 and check the decomposition finds the 0.8 ratio back.
    """
    rng = np.random.default_rng(11)
    means = rng.normal(0, 2.0, 400)
    groups = [list(m + rng.normal(0, 1.0, 12)) for m in means]
    r = bc.icc_one_way(groups)
    assert r["icc"] == pytest.approx(4.0 / 5.0, abs=0.05)


def test_icc_declines_to_answer_on_degenerate_input():
    assert bc.icc_one_way([[1.0, 2.0]]) is None
    assert bc.icc_one_way([]) is None


def test_isco_aggregate_groups_are_dropped_not_padded():
    """A 2-digit ISCO major group is not a unit group and must not become one."""
    assert bc.norm_isco("25") is None
    assert bc.norm_isco("251") is None
    assert bc.norm_isco("2511") == "2511"
    assert bc.norm_isco("0110") == "0110"
    assert bc.norm_isco("2511.0") == "2511"


def test_soc_normalisation():
    assert bc.norm_soc("15-1121") == "15-1121"
    assert bc.norm_soc("151121") == "15-1121"
    assert bc.norm_soc(" 15-1121 ") == "15-1121"
    assert bc.norm_soc("not a code") is None


def test_workbook_parser_still_reads_the_bls_layout():
    """
    The committed CSV is a reduction of the BLS workbook. This checks the
    other branch, the one that reads an .xls/.xlsx directly, still works, so
    anyone who downloads the original file from BLS gets the same object.
    """
    fixture = os.path.join(TESTS, "FIXTURE_ISCO_SOC_Crosswalk.xlsx")
    pairs = bc.extract_pairs(bc.read_any(fixture))
    assert list(pairs.columns) == ["isco_08", "soc_2010", "match_type"]
    assert len(pairs) > 0
    assert pairs["isco_08"].str.fullmatch(r"\d{4}").all()
    assert pairs["soc_2010"].str.fullmatch(r"\d{2}-\d{4}").all()
    assert set(pairs["match_type"]) <= {"full", "partial"}
    # The tidy reader must refuse a workbook rather than mangle it.
    assert bc.read_tidy(fixture) is None


def test_tidy_reader_accepts_the_committed_csv():
    t = bc.read_tidy(os.path.join(DATA, "ISCO_SOC_Crosswalk.csv"))
    assert t is not None
    assert len(t) == PUBLISHED["crosswalk_pairs"]

# --------------------------------------------------- external validation --
#
# These depend on out/validation.json, which needs the ILO file and therefore
# a network fetch. They skip rather than fail when it is absent, so the core
# suite still runs offline.

VALIDATION = os.path.join(OUT, "validation.json")
needs_validation = pytest.mark.skipif(
    not os.path.exists(VALIDATION),
    reason="run `make validate` first; it fetches the ILO file over the network",
)


@pytest.fixture(scope="session")
def validation():
    with open(VALIDATION) as f:
        return json.load(f)


@needs_validation
def test_crosswalk_recovers_an_independent_isco_native_measure(validation):
    """
    The ILO index is built directly on ISCO-08 from Polish task data. It shares
    no inputs with AIOE and never goes through a crosswalk, so agreement is
    evidence about the crossing rather than about AIOE.
    """
    assert validation["coverage"]["matched"] >= 400
    assert validation["agreement"]["spearman"] == pytest.approx(0.8185, abs=5e-3)
    assert validation["agreement"]["pearson"] == pytest.approx(0.7959, abs=5e-3)
    assert validation["agreement"]["spearman_p"] < 1e-50


@needs_validation
def test_within_code_spread_does_not_predict_disagreement(validation):
    """
    This pins a negative result, and it is the reason the README no longer
    tells anyone to filter on aioe_sd.

    If the within-code spread measured crosswalk error, bundled codes would
    agree with the independent measure less well than clean ones. They do not.
    """
    s = validation["does_the_spread_predict_disagreement"]
    single = s["single_source"]["spearman"]
    multi = s["multi_source"]["spearman"]
    assert multi >= single, (
        "multi-source codes stopped agreeing at least as well as single-source "
        "ones; the README's reasoning would need revisiting"
    )

    terciles = s["multi_source_by_spread_tercile"]
    spreads = [terciles[k]["mean_within_sd"] for k in ("cleanest", "middle", "messiest")]
    rhos = [terciles[k]["spearman"] for k in ("cleanest", "middle", "messiest")]
    assert spreads[0] < spreads[1] < spreads[2], "terciles are not ordered by spread"
    # Spread rises roughly six-fold across the terciles. Agreement should stay flat.
    assert max(rhos) - min(rhos) < 0.05, f"agreement moved with spread: {rhos}"


@needs_validation
def test_the_direct_spread_test_finds_nothing(validation):
    """
    The sharpest form of the negative result, and the one the README leads on.

    Rank every code by both measures, take the absolute rank discrepancy, and
    correlate it against the within-code spread. If the spread measured damage
    done by the crossing, this would be clearly positive. It is not.
    """
    t = validation["does_the_spread_predict_disagreement"]["direct_test"]
    assert abs(t["spearman_spread_vs_rank_discrepancy"]) < 0.15
    assert t["p"] > 0.05, "the spread started predicting discrepancy; revisit the README"
    assert abs(t["multi_source_only"]["spearman"]) < 0.15
    assert t["multi_source_only"]["p"] > 0.05


@needs_validation
def test_aggregation_claim_is_not_overread(validation):
    """
    Point estimates rise as ISCO groups get coarser. The intervals widen
    faster. This pins the honest reading: the levels are not distinguishable,
    so nobody should claim aggregation improves agreement.
    """
    lv = validation["agreement_by_aggregation_level"]
    four = lv["4_digit_unit_group"]
    two = lv["2_digit_sub_major"]
    one = lv["1_digit_major"]

    assert two["n_groups"] < 50 and one["n_groups"] < 15
    # The coarse estimates must not be treated as separate from the fine one.
    assert two["ci95"][0] <= four["spearman"] <= two["ci95"][1], (
        "the 2-digit interval no longer contains the 4-digit estimate, so the "
        "claim that the levels are indistinguishable would need rechecking"
    )
    assert one["ci95"][1] - one["ci95"][0] > 0.3, (
        "the 1-digit interval got narrow enough to be worth quoting, which "
        "nine groups should not allow"
    )


@needs_validation
def test_filtering_on_the_spread_does_not_help(validation):
    """Dropping high-spread codes should not buy a meaningfully better ranking."""
    base = validation["agreement"]["spearman"]
    for key, row in validation["does_the_spread_predict_disagreement"][
        "filtering_on_published_spread"
    ].items():
        assert abs(row["spearman"] - base) < 0.05, (
            f"{key} changed agreement by more than 0.05, which would mean "
            "filtering does something after all"
        )
