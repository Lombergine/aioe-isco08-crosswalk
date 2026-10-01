# AIOE on ISCO-08

Carrying the AIOE measure of occupational AI exposure from the United States
SOC system onto ISCO-08, and reporting how much of the AIOE ranking survives
the transfer.

Aditya Garg. Built 1 October 2026.

## Why this exists

The AIOE score of Felten, Raj and Seamans (2021) is defined on six-digit 2010
SOC codes. European labour force surveys code occupations in ISCO-08. Any
cross-country study that wants an occupation-level measure of AI exposure has
to cross that boundary, and most do not say what the crossing costs them.

Chandar and Klein Teeselink (2026) sidestep the problem by using Revelio Labs
data, which carries its own occupation and seniority codes. Asked whether that
makes the public-data crosswalk route a dead end, Robert Seamans, one of the
authors of AIOE, replied on 30 September 2026:

> I don't think it is a dead end, as the Revelio data is expensive ($10K or
> more) and so it is still useful to build a crosswalk for public data.

That is the brief. Build the crosswalk, publish it, and be honest about where
it breaks.

## Headline results

| Quantity | Value |
|---|---|
| ISCO-SOC pairs in the BLS crosswalk | 1,123 |
| Pairs carrying an AIOE score | 1,030 |
| ISCO-08 unit groups covered | 422 |
| AIOE occupations with no ISCO counterpart | 3 of 774 |
| Pairs flagged partial rather than full | 970 (86.4%) |
| ISCO codes drawing on more than one SOC code | 262 (62.1%) |
| Mean SOC codes per ISCO code | 2.44 (max 35) |
| **Share of AIOE variance lying between ISCO codes** | **0.830** |
| Mean within-ISCO standard deviation | 0.345 |
| Widest within-ISCO spread | 2.638 |
| Spearman, mean-based vs random-single-pick ranking | 0.960 |

AIOE is standardised to unit variance across occupations, so the within-ISCO
figures are directly readable as fractions of the whole signal.

Two conclusions follow. The ISCO-level ranking is sound, because 83 percent of
the variance sits between codes and every aggregation rule tested produces
almost the same ordering. The individual scores are shakier than the ranking,
because most pairs are partial matches and some ISCO codes bundle occupations
that disagree sharply about their own exposure.

## The problem the crosswalk has to face

The SOC to ISCO-08 mapping is many-to-many. One SOC code can feed several ISCO
codes, and one ISCO code can draw on several SOC codes. Where an ISCO code
draws on several SOC codes, those SOC codes carry different AIOE scores, and
something has to be done about the disagreement.

The usual move is to take a mean and move on. The disagreement does not
disappear when you do that. It becomes measurement error in the resulting
ISCO-level score, invisible to anyone downstream who uses the number.

ISCO 3423, fitness and recreation instructors, shows the shape of it:

| SOC | Title | AIOE |
|---|---|---|
| 39-9031 | Fitness Trainers and Aerobics Instructors | −2.112 |
| 29-9091 | Athletic Trainers | −0.331 |
| 39-1021 | First-Line Supervisors of Personal Service Workers | +0.430 |
| 25-3021 | Self-Enrichment Education Teachers | +0.526 |

The mean of those four is −0.372, and no occupation in the group is anywhere
near it. A study that assigns −0.372 to everyone coded 3423 has introduced a
2.6 standard deviation spread and recorded none of it.

So every row of the output ships the spread beside the score, and anyone using
the crosswalk can drop the codes where the bundled occupations disagree badly.

## Method

1. Read AIOE scores for 774 six-digit SOC codes from Appendix A of the AIOE
   data appendix. The scores are standardised: mean 0, standard deviation 1.
2. Read the BLS crosswalk and keep every (ISCO-08 unit group, 2010 SOC) pair
   together with the partial-match flag. ISCO entries shorter than four digits
   are aggregate groups rather than unit groups, and are dropped rather than
   padded into a code that means something else.
3. Attach AIOE to the SOC side of every pair.
4. Aggregate to ISCO. For each ISCO code, report the mean, median, minimum,
   maximum, standard deviation and range of the contributing AIOE scores,
   how many SOC codes contributed, how many of those were partial matches, and
   which codes they were.
5. Report the diagnostics described below.

## What the diagnostics mean

**Coverage.** How many ISCO unit groups receive any AIOE score, and how many
AIOE occupations the crosswalk never reaches. A crosswalk covering half the
ISCO space is a different object from one covering all of it, and the
difference should be stated rather than discovered later.

**Mapping degree.** The distribution of how many SOC codes feed each ISCO
code. Single-source ISCO codes carry a clean transfer. Multi-source ones
carry a blend.

**Transfer error.** For every multi-source ISCO code, the spread of the
contributing AIOE scores. Since AIOE has a standard deviation of 1 across all
occupations, a within-ISCO standard deviation of 0.5 means the transfer
introduces noise half as large as the entire signal.

**Variance decomposition.** A one-way random-effects decomposition of
SOC-level AIOE across ISCO groups, with

    n0 = (Σn − Σn² / Σn) / (k − 1)

as the effective group size. The reported ICC is the share of total AIOE
variance lying between ISCO codes rather than within them. This is the
headline number. Near 1 means occupations folded into the same ISCO code agree
about their exposure and the ranking transfers. Near 0 means an ISCO code's
score is mostly an artefact of which SOC codes happened to land in it.

**Rank stability.** Spearman correlations between the ISCO-level rankings
produced by different aggregation rules, plus a resampling check: draw one
contributing SOC at random for each ISCO code, rank on that, and correlate
with the mean-based ranking, repeated a thousand times. A high correlation
means the choice of aggregation rule does not matter much. A low one would
mean anyone using this crosswalk is partly measuring their own arbitrary
choice.

## The weighting question, and why it is closed

Where one SOC code maps to several ISCO codes, the aggregation can be
unweighted or weighted by employment in the destination country. Weighting
needs employment counts by occupation, which differ by country, so a single
weighted crosswalk does not exist.

The data makes the question close to moot. Rankings by mean, median, minimum
and maximum correlate above 0.95 with one another, and drawing a single
contributing SOC at random for each ISCO code still reproduces the mean-based
ranking at 0.960 across a thousand draws. The aggregation rule barely moves
the ordering.

The code still supports weights through an optional
`data/oes_soc_employment.csv` with columns `soc_code` and `employment`, and
reports the weighted ranking alongside the unweighted one so the difference
stays visible.

## Data

| File | Source | Status |
|---|---|---|
| `data/aioe_soc.csv` | Appendix A of `AIOE_DataAppendix.xlsx` | committed |
| `data/AIOE_DataAppendix.xlsx` | https://github.com/AIOE-Data/AIOE | committed |
| `data/ISCO_SOC_Crosswalk.csv` | BLS, reduced to three columns | committed |
| `data/oes_soc_employment.csv` | BLS OES | optional, absent |

`data/ISCO_SOC_Crosswalk.csv` is the BLS crosswalk reduced to `isco_08`,
`soc_2010` and `match_type`. It was taken from the sheet "ISCO-08 to 2010 SOC"
of `ISCO_SOC_Crosswalk.xls`, dated August 2012 and updated June 2015, at
https://www.bls.gov/soc/soccrosswalks.htm. Dropping that original `.xls` into
`data/` also works, because the parser handles either and reads the
partial-match asterisk directly from the sheet.

The reduced CSV was produced by parsing the BLS workbook, and the figures it
yields were then reproduced independently by this Python pipeline. The two
implementations agree on every number in the table above, which is the reason
the reduced file is trusted rather than the original being required.

## Running it

```
pip install -r requirements.txt
python src/build_crosswalk.py
```

Outputs land in `out/` and are committed, so the crosswalk can be used without
running anything:

- `isco08_aioe.csv` the crosswalk, one row per ISCO-08 unit group
- `soc_isco_pairs.csv` the exploded pair list with AIOE and match type attached
- `diagnostics.json` every number quoted above
- `unmatched_soc.csv` the three AIOE occupations the crosswalk never reaches

`tests/FIXTURE_ISCO_SOC_Crosswalk.xlsx` holds invented rows in the BLS layout.
It exists to exercise the parser and is never used as data.

## Citation

If this crosswalk is useful, please cite the underlying measure and the BLS
crosswalk. This repository is a derivation of both.

## References

Felten, E., M. Raj and R. Seamans (2021). "Occupational, industry, and
geographic exposure to artificial intelligence: A novel dataset and its
potential uses." *Strategic Management Journal* 42(12).

Chandar, B. and B. Klein Teeselink (2026). "How Does AI Change Labor Demand?
Evidence from 41 Countries." Stanford Digital Economy Lab working paper,
21 September 2026.

Bureau of Labor Statistics. "Crosswalk between the 2008 International
Standard Classification of Occupations and the 2010 SOC."
https://www.bls.gov/soc/soccrosswalks.htm
