# Results

First build, 1 October 2026. Sources: AIOE Data Appendix A (774 six-digit 2010
SOC codes, standardised to mean 0 and standard deviation 1) joined to the BLS
"ISCO-08 to 2010 SOC" crosswalk, August 2012, updated June 2015.

## Coverage

| | |
|---|---|
| ISCO-SOC pairs in the BLS crosswalk | 1,123 |
| of which flagged as partial matches | 970 (86.4%) |
| of which full matches | 153 (13.6%) |
| pairs carrying an AIOE score | 1,030 |
| ISCO-08 unit groups receiving a score | 422 |
| distinct SOC codes in the crosswalk | 838 |
| AIOE occupations the crosswalk never reaches | 3 |

Coverage of AIOE is almost complete. Three of 774 scored occupations have no
ISCO counterpart in the BLS mapping.

## How messy the mapping is

| | |
|---|---|
| ISCO codes drawing on exactly one SOC code | 160 (37.9%) |
| ISCO codes drawing on several SOC codes | 262 (62.1%) |
| mean SOC codes per ISCO code | 2.44 |
| most SOC codes feeding a single ISCO code | 35 |

Nearly two thirds of ISCO unit groups are built from more than one SOC
occupation, so for most of the crosswalk there is a genuine aggregation
choice to make.

## What the transfer costs

AIOE has a standard deviation of 1 across all occupations, which makes the
numbers below directly interpretable as a fraction of the whole signal.

| | |
|---|---|
| mean within-ISCO standard deviation of AIOE | 0.345 |
| median within-ISCO range | 0.551 |
| largest within-ISCO range | 2.638 |

So a typical multi-source ISCO code bundles occupations whose exposure scores
differ by about a third of the entire cross-occupational spread. At the
extreme, one ISCO code contains occupations 2.64 standard deviations apart,
which is most of the range of the measure.

## The headline number

A one-way random-effects decomposition of SOC-level AIOE across ISCO groups:

| | |
|---|---|
| variance between ISCO codes | 0.794 |
| variance within ISCO codes | 0.163 |
| **share of AIOE variance surviving the transfer** | **0.830** |

Eighty-three percent of the variation in AIOE lies between ISCO codes rather
than within them. The crosswalk preserves most of the signal.

## Does the aggregation rule matter

Spearman rank correlations between ISCO-level rankings built different ways:

| | |
|---|---|
| mean against median | 0.997 |
| mean against minimum | 0.968 |
| mean against maximum | 0.958 |

And a resampling check. Draw one contributing SOC code at random for each
ISCO code, rank on that single draw, and correlate with the mean-based
ranking. Over 1,000 draws:

| | |
|---|---|
| mean Spearman | 0.960 |
| 5th percentile | 0.956 |
| 95th percentile | 0.964 |

The choice of aggregation rule is close to irrelevant to the ranking. Even
picking one occupation at random per ISCO code reproduces the mean-based
ordering at 0.96.

## What this means

The crosswalk route is usable, and now it is usable with a number attached.
Anyone carrying AIOE into ISCO-08 is keeping 83 percent of the variation and
can stop worrying about which aggregation rule to use.

That also answers the employment-weighting question before it was asked.
Weighting is a choice among aggregation rules, and every rule tested lands
within 0.04 Spearman of every other. It is a second-order concern.

The first-order concern is different, and it is the one to report loudly.
Eighty-six percent of the BLS pairs are flagged as **partial** matches rather
than full correspondences, and 62 percent of ISCO codes draw on several SOC
occupations. The crosswalk therefore ships the within-ISCO spread
alongside every score. The 2.64 case is not a number anyone should use without
knowing what is inside it.

It does not follow that those codes should be dropped, which is what an earlier
version of this document recommended. See the validation section below.

## Reproducing this

Every figure above was produced twice by separate implementations.

The first pass parsed `ISCO_SOC_Crosswalk.xls` directly in a browser session,
because the build environment could not reach bls.gov. The second pass ran the
Python pipeline in this repository against `data/ISCO_SOC_Crosswalk.csv`, the
same BLS sheet reduced to three columns. The two agree on every number here,
including the variance decomposition and the thousand-draw resampling check.

To regenerate:

```
pip install -r requirements.txt
python src/build_crosswalk.py
```

Dropping the original `ISCO_SOC_Crosswalk.xls` into `data/` also works. The
parser reads either the workbook or the reduced CSV, and takes the
partial-match flag from the asterisk in the column headed "part".

## Validation against an ISCO-native measure

Every figure above is internal to AIOE. Gmyrek et al. (2025), ILO Working Paper
140, built an occupational exposure index directly on ISCO-08 from Polish task
descriptions scored by 1,640 workers and then by two language models. It shares
no inputs with AIOE and never goes through a crosswalk.

| | |
|---|---|
| ISCO-08 unit groups covered by both | 416 |
| Spearman, crosswalked AIOE vs ILO index | 0.818 |
| Pearson | 0.796 |

The constructs differ. AIOE scores exposure to AI capability, the ILO index
scores automation potential of tasks under generative AI, so part of the gap is
construct rather than transfer loss.

### The within-code spread does not predict disagreement

| group | n | mean within-code sd | Spearman vs ILO |
|---|---|---|---|
| single-source codes | 155 | 0.000 | 0.790 |
| multi-source, cleanest third | 87 | 0.105 | 0.810 |
| multi-source, middle third | 91 | 0.301 | 0.819 |
| multi-source, messiest third | 83 | 0.645 | 0.798 |

Spread rises from zero to 0.645. Agreement is flat. Filtering the full set at
0.75, 0.50, 0.35 and 0.25 gives 0.821, 0.825, 0.811 and 0.805 against a
baseline of 0.818.

When one ISCO code bundles disparate occupations, the ILO's own score for that
code averages over the same disparate jobs. Both measures inherit the
heterogeneity, so it cancels rather than accumulating. The within-code spread
describes the occupational category, not damage done by the crossing.

Reproduce with `make validate`.
