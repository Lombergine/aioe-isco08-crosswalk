"""
Draw the external validation figure.

Panel A is the test: crosswalked AIOE against the ILO's ISCO-native index,
which shares no inputs with AIOE and never went through a crosswalk.

Panel B is the result that was not expected. The within-code spread, which
looks like transfer error and which this repository originally told users to
filter on, does not predict disagreement with the independent measure.

Reads out/validation_pairs.csv and out/validation.json.
Writes docs/validation.png.
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
DOCS = os.path.join(HERE, "docs")

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
MUTED = "#52514e"
ACCENT = "#2a78d6"


def style():
    plt.rcParams.update({
        "figure.facecolor": SURFACE,
        "axes.facecolor": SURFACE,
        "savefig.facecolor": SURFACE,
        "axes.edgecolor": "#d8d7d2",
        "axes.labelcolor": MUTED,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
    })


def main():
    style()
    os.makedirs(DOCS, exist_ok=True)

    d = pd.read_csv(os.path.join(OUT, "validation_pairs.csv"), dtype={"isco_08": str})
    with open(os.path.join(OUT, "validation.json")) as f:
        v = json.load(f)

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(13.0, 5.2), gridspec_kw={"width_ratios": [1.25, 1]}
    )

    # ---- Panel A: does the crosswalk recover an independent measure? -------
    ax1.scatter(d["aioe_mean"], d["ilo_2025"], s=16, color=ACCENT,
                alpha=0.55, linewidths=0)

    z = np.polyfit(d["aioe_mean"], d["ilo_2025"], 1)
    xs = np.linspace(d["aioe_mean"].min(), d["aioe_mean"].max(), 50)
    ax1.plot(xs, np.polyval(z, xs), color=INK, linewidth=1.4,
             linestyle=(0, (5, 3)))

    ax1.set_title("The crosswalk recovers a measure it never saw")
    ax1.set_xlabel("AIOE carried onto ISCO-08 by this crosswalk\n(standard deviations)")
    ax1.set_ylabel("ILO ISCO-native GenAI exposure\n(Gmyrek et al. 2025)")
    ax1.text(
        0.03, 0.96,
        f"Spearman $\\rho$ = {v['agreement']['spearman']:.3f}\n"
        f"{v['coverage']['matched']} ISCO-08 unit groups\n"
        "no shared inputs, no shared crosswalk",
        transform=ax1.transAxes, fontsize=9, color=MUTED,
        va="top", linespacing=1.7,
    )

    # ---- Panel B: does the published spread predict disagreement? ----------
    s = v["does_the_spread_predict_disagreement"]
    t = s["multi_source_by_spread_tercile"]
    xs_b = [0.0] + [t[k]["mean_within_sd"] for k in ("cleanest", "middle", "messiest")]
    ys_b = [s["single_source"]["spearman"]] + [
        t[k]["spearman"] for k in ("cleanest", "middle", "messiest")
    ]
    ns_b = [s["single_source"]["n"]] + [t[k]["n"] for k in ("cleanest", "middle", "messiest")]
    labels = ["single\nsource", "cleanest\nthird", "middle\nthird", "messiest\nthird"]

    ax2.plot(xs_b, ys_b, color=ACCENT, linewidth=2.0, marker="o",
             markersize=9, markeredgecolor=SURFACE, markeredgewidth=1.5)
    for x, y, lab, n in zip(xs_b, ys_b, labels, ns_b):
        ax2.annotate(f"{lab}\nn={n}", xy=(x, y), xytext=(0, -34),
                     textcoords="offset points", ha="center", fontsize=8,
                     color=MUTED, linespacing=1.4)

    ax2.set_ylim(0, 1)
    ax2.set_xlim(-0.06, 0.72)
    ax2.set_title("The spread does not predict disagreement")
    ax2.set_xlabel("mean within-code standard deviation of AIOE")
    ax2.set_ylabel("Spearman $\\rho$ with the ILO measure")
    ax2.text(
        0.03, 0.17,
        "Within-code spread rises from 0 to 0.64 across these groups.\n"
        "Agreement with the independent measure does not move.\n"
        "The spread is occupational heterogeneity, which any\n"
        "ISCO-level measure inherits, not crosswalk error.",
        transform=ax2.transAxes, fontsize=8.5, color=MUTED,
        va="bottom", linespacing=1.7,
    )

    fig.tight_layout(pad=1.6, w_pad=3.0)
    path = os.path.join(DOCS, "validation.png")
    fig.savefig(path, dpi=170)
    print("wrote", path)


if __name__ == "__main__":
    main()
