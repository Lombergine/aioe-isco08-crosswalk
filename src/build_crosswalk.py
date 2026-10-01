"""
Carry AIOE occupational AI-exposure scores from the 2010 US SOC system onto
ISCO-08, and measure how much of the AIOE ranking survives the transfer.

Inputs
  data/aioe_soc.csv          AIOE scores by 6-digit 2010 SOC code.
                             Extracted from AIOE_DataAppendix.xlsx, Appendix A.
                             Felten, Raj and Seamans (2021).
  data/ISCO_SOC_Crosswalk.csv  BLS crosswalk, ISCO-08 to 2010 SOC, reduced to
                             three columns: isco_08, soc_2010, match_type.
                             Committed to this repository. Derived from
                             ISCO_SOC_Crosswalk.xls, August 2012 (updated
                             June 2015), sheet "ISCO-08 to 2010 SOC".
                             https://www.bls.gov/soc/soccrosswalks.htm
                             Dropping the original .xls into data/ also works;
                             the parser handles either.
  data/oes_soc_employment.csv  OPTIONAL. Two columns, soc_code and employment.
                             Enables the employment-weighted aggregation.

Outputs, all written to out/
  isco08_aioe.csv       the crosswalk itself, one row per ISCO-08 code
  soc_isco_pairs.csv    the exploded pair list with AIOE attached
  diagnostics.json      every number quoted in the write-up
  unmatched_soc.csv     AIOE occupations the crosswalk never reaches

The design question this answers:
  A SOC code can map to several ISCO codes and an ISCO code can draw on
  several SOC codes. Where an ISCO code draws on several SOC codes, their
  AIOE scores disagree. That disagreement is measurement error introduced by
  the transfer itself, and it is reported here rather than averaged away in
  silence.
"""

import json
import os
import re
import sys
from collections import defaultdict

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "out")

SOC_RE = re.compile(r"\b(\d{2}-\d{4})\b")
ISCO_RE = re.compile(r"\b(\d{4})\b")


def norm_soc(value):
    """Return a 6-digit SOC code as NN-NNNN, or None."""
    if value is None:
        return None
    s = str(value).strip()
    m = SOC_RE.search(s)
    if m:
        return m.group(1)
    digits = re.sub(r"\D", "", s)
    if len(digits) == 6:
        return digits[:2] + "-" + digits[2:]
    return None


def norm_isco(value):
    """Return a 4-digit ISCO-08 unit-group code as a string, or None."""
    if value is None:
        return None
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    digits = re.sub(r"\D", "", s)
    if len(digits) == 4:
        return digits
    # Some BLS rows carry 1-, 2- or 3-digit aggregate ISCO groups. Those are
    # not unit groups and are dropped rather than zero-padded into a code that
    # means something else.
    return None


def find_crosswalk_file():
    for name in os.listdir(DATA):
        low = name.lower()
        if "isco" in low and "soc" in low and low.endswith((".xls", ".xlsx", ".csv")):
            return os.path.join(DATA, name)
    return None


TIDY_COLUMNS = {"isco_08", "soc_2010", "match_type"}


def read_tidy(path):
    """
    Return the crosswalk as a tidy frame if the file already is one, else None.

    The reduced CSV committed to this repository carries an explicit header,
    so it is read straight rather than scanned cell by cell.
    """
    if not path.lower().endswith(".csv"):
        return None
    head = pd.read_csv(path, dtype=str, nrows=0)
    if not TIDY_COLUMNS.issubset(set(head.columns)):
        return None
    df = pd.read_csv(path, dtype=str)[["isco_08", "soc_2010", "match_type"]]
    df["isco_08"] = df["isco_08"].map(norm_isco)
    df["soc_2010"] = df["soc_2010"].map(norm_soc)
    df["match_type"] = (
        df["match_type"].fillna("unknown").str.strip().str.lower()
    )
    df = df.dropna(subset=["isco_08", "soc_2010"])
    return df.drop_duplicates(["isco_08", "soc_2010"]).reset_index(drop=True)


def read_any(path):
    """Read every sheet of a workbook, or a csv, into a list of DataFrames."""
    low = path.lower()
    if low.endswith(".csv"):
        return [pd.read_csv(path, dtype=str, header=None)]
    engine = "xlrd" if low.endswith(".xls") else "openpyxl"
    book = pd.read_excel(path, sheet_name=None, dtype=str, header=None, engine=engine)
    return list(book.values())


def extract_pairs(frames):
    """
    Pull (isco_08, soc_2010) pairs out of the crosswalk without assuming where
    the header sits. Every cell is scanned; a row contributes a pair when it
    holds at least one ISCO unit-group code and at least one SOC code.
    """
    pairs = []
    for df in frames:
        for _, row in df.iterrows():
            cells = [c for c in row.tolist() if c is not None and str(c).strip() != ""]
            if not cells:
                continue
            iscos, socs = [], []
            # The BLS sheet flags a partial match with a bare asterisk in the
            # column headed "part". A blank there means a full match.
            partial = any(str(c).strip() == "*" for c in cells)
            for c in cells:
                s = norm_soc(c)
                if s:
                    socs.append(s)
                    continue
                i = norm_isco(c)
                if i:
                    iscos.append(i)
            for i in iscos:
                for s in socs:
                    pairs.append((i, s, "partial" if partial else "full"))
    seen = set()
    uniq = []
    for p in pairs:
        if p[:2] not in seen:
            seen.add(p[:2])
            uniq.append(p)
    return pd.DataFrame(uniq, columns=["isco_08", "soc_2010", "match_type"])


def icc_one_way(groups):
    """
    One-way random-effects decomposition of SOC-level AIOE across ISCO groups.

    Returns the share of total AIOE variance that lies BETWEEN ISCO codes.
    Groups of size one carry no within-group information and are included in
    the between term only, which is how a one-way ANOVA treats them.

    A value near 1 means the transfer preserves the ordering: occupations that
    land in the same ISCO code agree about their exposure. A value near 0
    means an ISCO code's score is mostly an artefact of which SOC codes
    happened to be folded into it.
    """
    groups = [np.asarray(g, dtype=float) for g in groups if len(g) > 0]
    k = len(groups)
    if k < 2:
        return None
    all_vals = np.concatenate(groups)
    n_total = all_vals.size
    grand = all_vals.mean()
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_within = sum(((g - g.mean()) ** 2).sum() for g in groups)
    df_between = k - 1
    df_within = n_total - k
    if df_within <= 0:
        return None
    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    sizes = np.array([len(g) for g in groups], dtype=float)
    n0 = (sizes.sum() - (sizes ** 2).sum() / sizes.sum()) / (k - 1)
    var_between = max((ms_between - ms_within) / n0, 0.0)
    var_within = ms_within
    if var_between + var_within == 0:
        return None
    return {
        "icc": float(var_between / (var_between + var_within)),
        "var_between": float(var_between),
        "var_within": float(var_within),
        "ms_between": float(ms_between),
        "ms_within": float(ms_within),
        "n_groups": int(k),
        "n_obs": int(n_total),
    }


def spearman(a, b):
    from scipy.stats import spearmanr

    r = spearmanr(a, b)
    return float(r.statistic), float(r.pvalue)


def main():
    os.makedirs(OUT, exist_ok=True)

    aioe = pd.read_csv(os.path.join(DATA, "aioe_soc.csv"), dtype={"soc_code": str})
    aioe["soc_code"] = aioe["soc_code"].map(norm_soc)
    aioe = aioe.dropna(subset=["soc_code"]).drop_duplicates("soc_code")

    cw_path = find_crosswalk_file()
    if cw_path is None:
        print(
            "MISSING: no ISCO-SOC crosswalk in data/.\n"
            "Download ISCO_SOC_Crosswalk.xls from\n"
            "  https://www.bls.gov/soc/soccrosswalks.htm\n"
            "and place it in data/. Nothing below can run without it, and no\n"
            "substitute will be invented.",
            file=sys.stderr,
        )
        return 2

    pairs = read_tidy(cw_path)
    if pairs is None:
        pairs = extract_pairs(read_any(cw_path))
    pairs = pairs.merge(
        aioe, left_on="soc_2010", right_on="soc_code", how="left"
    ).drop(columns=["soc_code"])

    matched = pairs.dropna(subset=["aioe"]).copy()

    # ---- employment weights, if the OES extract is present -----------------
    oes_path = os.path.join(DATA, "oes_soc_employment.csv")
    have_weights = os.path.exists(oes_path)
    if have_weights:
        oes = pd.read_csv(oes_path, dtype={"soc_code": str})
        oes["soc_code"] = oes["soc_code"].map(norm_soc)
        oes = oes.dropna(subset=["soc_code"]).drop_duplicates("soc_code")
        matched = matched.merge(
            oes.rename(columns={"soc_code": "soc_2010"}), on="soc_2010", how="left"
        )
        matched["employment"] = pd.to_numeric(
            matched["employment"], errors="coerce"
        ).fillna(0.0)

    # ---- aggregate to ISCO -------------------------------------------------
    rows = []
    for isco, g in matched.groupby("isco_08"):
        vals = g["aioe"].to_numpy(dtype=float)
        rec = {
            "isco_08": isco,
            "n_soc": int(len(vals)),
            "aioe_mean": float(vals.mean()),
            "aioe_median": float(np.median(vals)),
            "aioe_min": float(vals.min()),
            "aioe_max": float(vals.max()),
            "aioe_sd": float(vals.std(ddof=1)) if len(vals) > 1 else 0.0,
            "aioe_range": float(vals.max() - vals.min()),
            "n_partial": int((g["match_type"] == "partial").sum()),
            "soc_codes": "|".join(sorted(g["soc_2010"])),
        }
        if have_weights:
            w = g["employment"].to_numpy(dtype=float)
            rec["aioe_empwt"] = (
                float(np.average(vals, weights=w)) if w.sum() > 0 else float(vals.mean())
            )
            rec["employment_total"] = float(w.sum())
        rows.append(rec)
    isco = pd.DataFrame(rows).sort_values("isco_08").reset_index(drop=True)

    # ---- diagnostics -------------------------------------------------------
    multi = isco[isco["n_soc"] > 1]
    groups = [g["aioe"].to_numpy(dtype=float) for _, g in matched.groupby("isco_08")]
    icc = icc_one_way(groups)

    rng = np.random.default_rng(20261001)
    draws = []
    by_isco = {k: v["aioe"].to_numpy(dtype=float) for k, v in matched.groupby("isco_08")}
    order = isco["isco_08"].tolist()
    base = isco["aioe_mean"].to_numpy(dtype=float)
    for _ in range(1000):
        pick = np.array([rng.choice(by_isco[i]) for i in order])
        draws.append(spearman(base, pick)[0])
    draws = np.array(draws)

    soc_degree = pairs.groupby("soc_2010")["isco_08"].nunique()
    aioe_socs = set(aioe["soc_code"])
    cw_socs = set(pairs["soc_2010"])
    unmatched = sorted(aioe_socs - cw_socs)

    diag = {
        "sources": {
            "aioe": "Felten, Raj and Seamans (2021), AIOE_DataAppendix.xlsx, Appendix A",
            "crosswalk": os.path.basename(cw_path),
            "employment_weights": "present" if have_weights else "absent",
        },
        "counts": {
            "aioe_soc_codes": int(len(aioe)),
            "crosswalk_pairs": int(len(pairs)),
            "crosswalk_pairs_with_aioe": int(len(matched)),
            "isco_codes_covered": int(len(isco)),
            "isco_codes_single_soc": int((isco["n_soc"] == 1).sum()),
            "isco_codes_multi_soc": int(len(multi)),
            "aioe_soc_not_in_crosswalk": int(len(unmatched)),
            "soc_codes_in_crosswalk": int(pairs["soc_2010"].nunique()),
        },
        "match_type": {
            "pairs_full": int((pairs["match_type"] == "full").sum()),
            "pairs_partial": int((pairs["match_type"] == "partial").sum()),
            "share_pairs_partial": float(
                (pairs["match_type"] == "partial").mean()
            ),
        },
        "mapping_degree": {
            "soc_per_isco_mean": float(isco["n_soc"].mean()),
            "soc_per_isco_max": int(isco["n_soc"].max()),
            "isco_per_soc_mean": float(soc_degree.mean()),
            "isco_per_soc_max": int(soc_degree.max()),
            "share_isco_multi_soc": float(len(multi) / len(isco)) if len(isco) else None,
        },
        "transfer_error": {
            "mean_within_isco_sd": float(multi["aioe_sd"].mean()) if len(multi) else None,
            "median_within_isco_range": float(multi["aioe_range"].median())
            if len(multi)
            else None,
            "max_within_isco_range": float(multi["aioe_range"].max())
            if len(multi)
            else None,
            "aioe_sd_overall": float(aioe["aioe"].std(ddof=1)),
            "variance_decomposition": icc,
        },
        "rank_stability": {
            "mean_vs_median": spearman(isco["aioe_mean"], isco["aioe_median"])[0],
            "mean_vs_min": spearman(isco["aioe_mean"], isco["aioe_min"])[0],
            "mean_vs_max": spearman(isco["aioe_mean"], isco["aioe_max"])[0],
            "random_single_pick_spearman": {
                "mean": float(draws.mean()),
                "p05": float(np.percentile(draws, 5)),
                "p95": float(np.percentile(draws, 95)),
                "n_draws": int(draws.size),
            },
        },
    }
    if have_weights:
        diag["rank_stability"]["mean_vs_employment_weighted"] = spearman(
            isco["aioe_mean"], isco["aioe_empwt"]
        )[0]

    isco.to_csv(os.path.join(OUT, "isco08_aioe.csv"), index=False)
    matched.to_csv(os.path.join(OUT, "soc_isco_pairs.csv"), index=False)
    pd.DataFrame({"soc_2010": unmatched}).merge(
        aioe.rename(columns={"soc_code": "soc_2010"}), on="soc_2010", how="left"
    ).to_csv(os.path.join(OUT, "unmatched_soc.csv"), index=False)
    with open(os.path.join(OUT, "diagnostics.json"), "w") as f:
        json.dump(diag, f, indent=2)

    print(json.dumps(diag, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
