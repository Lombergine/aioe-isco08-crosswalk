"""
Draw the repository figure: what the SOC to ISCO-08 transfer costs.

Reads out/isco08_aioe.csv and writes docs/transfer_error.png.

Panel A sorts all 422 ISCO-08 unit groups by their mean AIOE and draws the
range of the SOC occupations folded into each one. The rising line is the
ranking that survives the transfer. The grey bars are what the mean hides.

Panel B is the distribution of within-code standard deviation across the
multi-source codes, against the standard deviation of AIOE over all
occupations, which is 1 by construction.
"""

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
WHISKER = "#cfcec9"


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
        "xtick.direction": "out",
        "ytick.direction": "out",
    })


def main():
    style()
    os.makedirs(DOCS, exist_ok=True)

    d = pd.read_csv(os.path.join(OUT, "isco08_aioe.csv"), dtype={"isco_08": str})
    d = d.sort_values("aioe_mean").reset_index(drop=True)
    x = np.arange(len(d))

    fig, (ax1, ax2) = plt.subplots(
        1, 2, figsize=(13.5, 5.2), gridspec_kw={"width_ratios": [2.1, 1]}
    )

    # ---- Panel A: the ranking, and the spread it conceals -------------------
    ax1.vlines(x, d["aioe_min"], d["aioe_max"], color=WHISKER, linewidth=0.9)
    ax1.plot(x, d["aioe_mean"], color=ACCENT, linewidth=2.0, solid_capstyle="round")
    ax1.axhline(0, color="#d8d7d2", linewidth=1.0, zorder=0)

    worst = d["aioe_range"].idxmax()
    ax1.annotate(
        f"ISCO {d.loc[worst, 'isco_08']} spans {d.loc[worst, 'aioe_range']:.2f}\n"
        "from Fitness Trainers to\nSelf-Enrichment Teachers",
        xy=(worst, d.loc[worst, "aioe_min"]),
        xytext=(worst + 28, d.loc[worst, "aioe_min"] - 0.55),
        fontsize=8.5, color=MUTED, linespacing=1.45,
        arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=0.9,
                        shrinkA=0, shrinkB=3),
    )

    ax1.set_title("The ranking transfers. The individual scores carry baggage.")
    ax1.set_xlabel("422 ISCO-08 unit groups, ranked by mean AIOE\n ")
    ax1.set_ylabel("AIOE (standard deviations)")
    ax1.set_xlim(-6, len(d) + 5)
    ax1.text(
        0.015, 0.955,
        "blue line  mean AIOE of the code\ngrey bar   range of the SOC occupations inside it",
        transform=ax1.transAxes, fontsize=8.5, color=MUTED,
        va="top", linespacing=1.6,
    )

    # ---- Panel B: how far apart the bundled occupations sit -----------------
    multi = d[d["n_soc"] > 1]
    ax2.hist(multi["aioe_sd"], bins=28, color=ACCENT, alpha=0.9,
             edgecolor=SURFACE, linewidth=0.8)

    mean_sd = multi["aioe_sd"].mean()
    ax2.axvline(mean_sd, color=INK, linewidth=1.4, linestyle=(0, (4, 3)))
    ax2.axvline(1.0, color=MUTED, linewidth=1.2, linestyle=(0, (1, 2.5)))

    ax2.set_ylim(0, ax2.get_ylim()[1] * 1.18)
    top = ax2.get_ylim()[1]
    ax2.text(mean_sd + 0.045, top * 0.97, f"mean {mean_sd:.2f}",
             fontsize=8.5, color=INK, va="top")
    ax2.text(1.0 - 0.045, top * 0.70, "AIOE sd across\nall occupations = 1",
             fontsize=8.5, color=MUTED, ha="right", va="top", linespacing=1.5)

    ax2.set_title("Within-code disagreement")
    ax2.set_xlabel(f"standard deviation of AIOE inside one ISCO code\n"
                   f"({len(multi)} codes drawing on more than one SOC occupation)")
    ax2.set_ylabel("ISCO codes")

    fig.tight_layout(pad=1.6, w_pad=3.0)
    path = os.path.join(DOCS, "transfer_error.png")
    fig.savefig(path, dpi=170)
    print("wrote", path)

    print(f"codes plotted            {len(d)}")
    print(f"multi-source codes       {len(multi)}")
    print(f"mean within-code sd      {mean_sd:.4f}")
    print(f"widest code              ISCO {d.loc[worst, 'isco_08']} "
          f"range {d.loc[worst, 'aioe_range']:.4f}")


if __name__ == "__main__":
    main()
