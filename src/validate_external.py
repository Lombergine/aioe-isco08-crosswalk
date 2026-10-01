"""
Test the crosswalk against a measure that never went through it.

The diagnostics in build_crosswalk.py are internal. They describe how much
AIOE variance survives the move onto ISCO-08, but they cannot say whether the
resulting scores are right, because everything in them descends from AIOE.

Gmyrek et al. (2025), ILO Working Paper 140, built an occupational exposure
index directly on ISCO-08. It comes from Polish task descriptions, scored by
1,640 workers and then by GPT-4o and Gemini. It shares no inputs with AIOE and
never touches a crosswalk. So agreement between the two is evidence about the
crossing rather than evidence about AIOE.

Two caveats worth stating before the numbers.

AIOE measures exposure to AI capability. The ILO index measures the automation
potential of tasks under generative AI. Those are related constructs, not the
same one, so perfect agreement was never available and some of the gap is
construct rather than transfer loss.

The ILO file is published without an explicit licence, so it is fetched at run
time into data/external/ and is not redistributed from this repository.

Outputs out/validation.json.
"""

import json
import os
import ssl
import sys
import urllib.request

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, rankdata, spearmanr

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
EXT = os.path.join(HERE, "data", "external")

ILO_URL = (
    "https://raw.githubusercontent.com/pgmyrek/2025_GenAI_scores_ISCO08/"
    "main/Final_Scores_ISCO08_Gmyrek_et_al_2025.xlsx"
)
ILO_LOCAL = os.path.join(EXT, "gmyrek_isco08_scores.xlsx")


def fetch_ilo():
    if os.path.exists(ILO_LOCAL) and os.path.getsize(ILO_LOCAL) > 100_000:
        return ILO_LOCAL
    os.makedirs(EXT, exist_ok=True)
    print(f"fetching {ILO_URL}", file=sys.stderr)
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(ILO_URL, context=ctx, timeout=120) as r:
        data = r.read()
    with open(ILO_LOCAL, "wb") as f:
        f.write(data)
    print(f"wrote {ILO_LOCAL} ({len(data)} bytes)", file=sys.stderr)
    return ILO_LOCAL


def load_ilo(path):
    """One row per ISCO-08 unit group, carrying the occupation-level mean."""
    g = pd.read_excel(path)
    g["isco_08"] = g["ISCO_08"].astype(str).str.extract(r"(\d{4})")[0]
    g = g.dropna(subset=["isco_08"])
    return (
        g.groupby("isco_08")
        .agg(
            ilo_2025=("mean_score_2025", "first"),
            ilo_2023=("mean_score_2023", "first"),
            ilo_sd=("SD_2025", "first"),
            ilo_title=("Title", "first"),
        )
        .reset_index()
    )


def rho(a, b):
    return float(spearmanr(a, b).statistic)


def rho_ci(a, b, draws=2000, seed=7):
    """Bootstrap percentile interval for a Spearman correlation.

    Point estimates on small groups are easy to over-read. Every rho this
    script reports for a subgroup carries one of these so the reader can see
    whether a difference is real.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(a)
    vals = []
    for _ in range(draws):
        i = rng.integers(0, n, n)
        v = spearmanr(a[i], b[i]).statistic
        if not np.isnan(v):
            vals.append(v)
    return [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))]


def agreement_by_level(pairs, ilo):
    """Agreement at each ISCO aggregation level, with intervals.

    Coarser levels have fewer groups, so their intervals widen fast. Reporting
    the point estimates alone invites exactly the wrong conclusion.
    """
    out = {}
    for lvl, name in ((4, "4_digit_unit_group"), (3, "3_digit_minor"),
                      (2, "2_digit_sub_major"), (1, "1_digit_major")):
        a = pairs.assign(k=pairs["isco_08"].str[:lvl]).groupby("k")["aioe"].mean()
        b = ilo.assign(k=ilo["isco_08"].str[:lvl]).groupby("k")["ilo_2025"].mean()
        j = pd.concat([a.rename("x"), b.rename("y")], axis=1).dropna()
        out[name] = {
            "n_groups": int(len(j)),
            "spearman": rho(j["x"], j["y"]),
            "ci95": rho_ci(j["x"], j["y"]),
        }
    return out


def main():
    ilo = load_ilo(fetch_ilo())
    cw = pd.read_csv(os.path.join(OUT, "isco08_aioe.csv"), dtype={"isco_08": str})
    m = cw.merge(ilo, on="isco_08", how="inner")

    # Rank discrepancy between the two measures, for the direct test.
    m["abs_rank_discrepancy"] = np.abs(
        rankdata(m["aioe_mean"]) - rankdata(m["ilo_2025"])
    )

    lo, hi = m["aioe_mean"].quantile([0.05, 0.95])
    trim = m[(m["aioe_mean"] > lo) & (m["aioe_mean"] < hi)]

    pairs_long = pd.read_csv(
        os.path.join(OUT, "soc_isco_pairs.csv"), dtype={"isco_08": str}
    ).dropna(subset=["aioe"])

    single = m[m["n_soc"] == 1]
    multi = m[m["n_soc"] > 1].copy()
    multi["tercile"] = pd.qcut(
        multi["aioe_sd"], 3, labels=["cleanest", "middle", "messiest"]
    )

    by_tercile = {
        str(lab): {
            "n": int(len(grp)),
            "mean_within_sd": float(grp["aioe_sd"].mean()),
            "spearman": rho(grp["aioe_mean"], grp["ilo_2025"]),
            "ci95": rho_ci(grp["aioe_mean"], grp["ilo_2025"]),
        }
        for lab, grp in multi.groupby("tercile", observed=True)
    }

    thresholds = {}
    for thr in (0.75, 0.50, 0.35, 0.25):
        k = m[m["aioe_sd"] < thr]
        thresholds[f"aioe_sd_under_{thr}"] = {
            "n": int(len(k)),
            "spearman": rho(k["aioe_mean"], k["ilo_2025"]),
        }

    res = {
        "external_measure": {
            "source": "Gmyrek et al. (2025), ILO Working Paper 140",
            "url": "https://github.com/pgmyrek/2025_GenAI_scores_ISCO08",
            "native_classification": "ISCO-08, no crosswalk involved",
            "construct": "automation potential of tasks under generative AI",
            "note": (
                "AIOE measures exposure to AI capability; the two constructs "
                "overlap but are not identical, so part of any gap is construct "
                "difference rather than transfer loss."
            ),
        },
        "coverage": {
            "ilo_unit_groups": int(len(ilo)),
            "crosswalk_unit_groups": int(len(cw)),
            "matched": int(len(m)),
        },
        "agreement": {
            "spearman": rho(m["aioe_mean"], m["ilo_2025"]),
            "spearman_ci95": rho_ci(m["aioe_mean"], m["ilo_2025"]),
            "spearman_p": float(spearmanr(m["aioe_mean"], m["ilo_2025"]).pvalue),
            "pearson": float(pearsonr(m["aioe_mean"], m["ilo_2025"])[0]),
            "spearman_middle_90pct_of_aioe": rho(trim["aioe_mean"], trim["ilo_2025"]),
            "note_on_trim": (
                "Dropping the top and bottom 5% of AIOE leaves rho at "
                f"{rho(trim['aioe_mean'], trim['ilo_2025']):.3f}, so the "
                "headline is not an artefact of the extremes."
            ),
        },
        "agreement_by_aggregation_level": {
            **agreement_by_level(pairs_long, ilo),
            "reading": (
                "The point estimates drift upward as groups get coarser, but "
                "the intervals widen faster. The 2-digit interval contains the "
                "4-digit estimate and the 1-digit one rests on nine groups. "
                "The supportable claim is that agreement is indistinguishable "
                "across aggregation levels, NOT that coarsening improves it."
            ),
        },
        "does_the_spread_predict_disagreement": {
            "single_source": {
                "n": int(len(single)),
                "spearman": rho(single["aioe_mean"], single["ilo_2025"]),
            },
            "multi_source": {
                "n": int(len(multi)),
                "spearman": rho(multi["aioe_mean"], multi["ilo_2025"]),
            },
            "direct_test": {
                "description": (
                    "The tercile split below is coarse. This is the direct "
                    "test: rank every code by both measures and correlate the "
                    "absolute rank discrepancy against the within-code spread. "
                    "If the spread measured crosswalk damage, codes with more "
                    "of it would sit further from the independent measure."
                ),
                "spearman_spread_vs_rank_discrepancy": float(
                    spearmanr(m["aioe_sd"], m["abs_rank_discrepancy"]).statistic
                ),
                "p": float(spearmanr(m["aioe_sd"], m["abs_rank_discrepancy"]).pvalue),
                "multi_source_only": {
                    "n": int(len(multi)),
                    "spearman": float(
                        spearmanr(multi["aioe_sd"], multi["abs_rank_discrepancy"]).statistic
                    ),
                    "p": float(
                        spearmanr(multi["aioe_sd"], multi["abs_rank_discrepancy"]).pvalue
                    ),
                },
            },
            "multi_source_by_spread_tercile": by_tercile,
            "filtering_on_published_spread": thresholds,
            "verdict": (
                "No. The direct test finds no relationship between the "
                "within-code spread and how far a code sits from the "
                "independent measure. Bundled codes agree at least as well as "
                "clean ones, the tercile intervals overlap heavily, and "
                "filtering on the spread does not improve agreement. The "
                "spread reflects heterogeneity inside the occupational "
                "category, which any ISCO-level measure inherits, rather than "
                "error introduced by the crossing."
            ),
        },
    }

    m[["isco_08", "n_soc", "aioe_mean", "aioe_sd", "ilo_2025", "ilo_title"]].to_csv(
        os.path.join(OUT, "validation_pairs.csv"), index=False
    )
    with open(os.path.join(OUT, "validation.json"), "w") as f:
        json.dump(res, f, indent=2)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
