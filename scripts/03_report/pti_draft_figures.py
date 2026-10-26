"""DRAFT figures to help the team judge the PTI two-way table by region (not referenced by any doc yet).

Reads <data>/results/t4/index_variants.nc (from t4_index_variants.py) and features/regions_1km.tif.
today = ESA surface temperature 2014-2023 (T_N1); warming V1 = T_N2 - today, V2 = T_G2 - today.
Writes docs/figures/drafts/:
  d1_table_marginals_statewide.png  - table drawn on continuous axes + cell density + marginal histograms
  d2_table_marginals_regions.png    - the same per region, boxes labelled with the region's share of cells
  d3_regional_class_shares.png      - class shares per region x scenario x era, V1 and V2
  d4_region_positions.png           - where each region's middle 50 % of cells sits in the table, by era
  d5_warming_by_region.png          - projected warming by region and era vs the warming band edges
  d6_edge_sensitivity.png           - share of cells changing class if a band edge moves +/- 0.5 degC
and <data>/results/t4/drafts_box_shares.csv (share of each region's cells in each table box, all eras/scenarios).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "02_tests"))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from matplotlib.colors import ListedColormap
from mpl_toolkits.axes_grid1 import make_axes_locatable

from composite_indexing import config as C
from t4_index_variants import CLASS_C, CLASSES, TABLE, TODAY_EDGES, WARM_EDGES

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

RES = C.DATA / "results/t4"
OUT = C.REPO / "docs/figures/drafts"
SCENS = ["rcp45", "rcp85"]
ERAS = ["2026_2050", "2051_2080", "2081_2100"]
REGIONS = {1: "Arctic", 2: "Interior", 3: "West", 4: "South"}
MARKERS = {"Arctic": "o", "Interior": "s", "West": "^", "South": "D"}
T_LIM, W_LIM = (-10.0, 4.0), (0.0, 7.5)  # display limits (today, warming)
T_BANDS = [T_LIM[0]] + TODAY_EDGES + [T_LIM[1]]
W_BANDS = [W_LIM[0]] + WARM_EDGES + [W_LIM[1]]
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})


def load():
    v = xr.open_dataset(RES / "index_variants.nc")
    with rasterio.open(C.DATA / "features/regions_1km.tif") as s:
        reg = s.read(1)
    today = v["T_N1_rcp85_2051_2080"].values
    warm, cls = {}, {}
    for scen in SCENS:
        for era in ERAS:
            warm[("V1", scen, era)] = v[f"T_N2_{scen}_{era}"].values - today
            warm[("V2", scen, era)] = v[f"T_G2_{scen}_{era}"].values - today
            cls[("V1", scen, era)] = v[f"class_CN_{scen}_{era}"].values
            cls[("V2", scen, era)] = v[f"class_CG_{scen}_{era}"].values
    dom = np.isfinite(today)
    return today, warm, cls, reg, dom


NR, NC = TABLE.shape


def boxes(t, w, t_edges=TODAY_EDGES, w_edges=WARM_EDGES):
    return np.clip(np.digitize(t, t_edges), 0, NR - 1), np.clip(np.digitize(w, w_edges), 0, NC - 1)


def draw_table(ax, alpha=0.32, labels=True):
    for a in range(NR):
        for b in range(NC):
            ax.add_patch(plt.Rectangle((W_BANDS[b], T_BANDS[a]), W_BANDS[b + 1] - W_BANDS[b],
                                       T_BANDS[a + 1] - T_BANDS[a], fc=CLASS_C[TABLE[a, b]], alpha=alpha, lw=0))
            if labels:
                ax.text((W_BANDS[b] + W_BANDS[b + 1]) / 2, T_BANDS[a] + 0.35, CLASSES[TABLE[a, b]], ha="center",
                        va="top", fontsize=7, color=INK2)
    for e in TODAY_EDGES:
        ax.axhline(e, color="white", lw=1.2)
    for e in WARM_EDGES:
        ax.axvline(e, color="white", lw=1.2)
    ax.set_xlim(*W_LIM)
    ax.set_ylim(T_LIM[1], T_LIM[0])  # cold at the top, as in the table


def table_with_marginals(ax, t, w, title, annotate=None):
    draw_table(ax, labels=annotate is None)
    ok = np.isfinite(t) & np.isfinite(w)
    ax.hexbin(np.clip(w[ok], *W_LIM), np.clip(t[ok], *T_LIM), gridsize=55, bins="log", cmap="Greys", mincnt=3,
              extent=(*W_LIM, *T_LIM), alpha=0.75, linewidths=0)
    if annotate is not None:
        for a in range(NR):
            for b in range(NC):
                ax.text((W_BANDS[b] + W_BANDS[b + 1]) / 2, (T_BANDS[a] + T_BANDS[a + 1]) / 2,
                        f"{CLASSES[TABLE[a, b]]}\n{annotate[a, b]:.0%}", ha="center", va="center", fontsize=6.3,
                        linespacing=1.1, color=INK, bbox=dict(fc="white", ec="none", alpha=0.6, pad=0.4))
    ax.set_xlabel("projected warming (°C)")
    ax.set_ylabel("today's surface temperature (°C)")
    div = make_axes_locatable(ax)
    top = div.append_axes("top", 0.55, pad=0.05, sharex=ax)
    right = div.append_axes("right", 0.55, pad=0.05, sharey=ax)
    top.hist(np.clip(w[ok], *W_LIM), bins=np.linspace(*W_LIM, 61), color=INK2, weights=np.full(ok.sum(), 100 / ok.sum()))
    right.hist(np.clip(t[ok], *T_LIM), bins=np.linspace(*T_LIM, 57), color=INK2, orientation="horizontal",
               weights=np.full(ok.sum(), 100 / ok.sum()))
    for e in WARM_EDGES:
        top.axvline(e, color=INK, lw=0.8, ls=(0, (2, 2)))
    for e in TODAY_EDGES:
        right.axhline(e, color=INK, lw=0.8, ls=(0, (2, 2)))
    top.tick_params(labelbottom=False)
    right.tick_params(labelleft=False)
    top.set_ylabel("% cells", fontsize=7.5)
    right.set_xlabel("% cells", fontsize=7.5)
    top.set_title(title, loc="left", fontsize=10, color=INK)


def box_share(t, w):
    ok = np.isfinite(t) & np.isfinite(w)
    i, j = boxes(t[ok], w[ok])
    sh = np.zeros((NR, NC))
    np.add.at(sh, (i, j), 1)
    return sh / max(ok.sum(), 1)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    today, warm, cls, reg, dom = load()
    key = ("V1", "rcp85", "2051_2080")

    # d1 statewide
    fig, ax = plt.subplots(figsize=(8, 6.5))
    table_with_marginals(ax, today[dom], warm[key][dom], "Statewide: V1, 2051–2080, RCP 8.5 (grey = density of cells)")
    fig.savefig(OUT / "d1_table_marginals_statewide.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # d2 per region
    fig, axs = plt.subplots(2, 2, figsize=(13, 11))
    for ax, (k, rn) in zip(axs.flat, REGIONS.items()):
        m = dom & (reg == k)
        table_with_marginals(ax, today[m], warm[key][m], f"{rn} ({m.sum():,} cells)",
                             annotate=box_share(today[m], warm[key][m]))
    fig.suptitle("Two-way table by region: share of each region's permafrost cells per box (V1, 2051–2080, RCP 8.5)",
                 fontsize=11, y=1.0)
    fig.tight_layout()
    fig.savefig(OUT / "d2_table_marginals_regions.png", dpi=120, bbox_inches="tight")
    plt.close(fig)

    # box shares csv (all versions / scenarios / eras / regions)
    rows = []
    for (ver, scen, era), w in warm.items():
        for k, rn in [(0, "Statewide")] + list(REGIONS.items()):
            m = dom & ((reg == k) if k else True)
            sh = box_share(today[m], w[m])
            for a in range(NR):
                for b in range(NC):
                    rows.append(dict(version=ver, scen=scen, era=era, region=rn, today_band=a, warming_band=b,
                                     cls=CLASSES[TABLE[a, b]], share=sh[a, b]))
    pd.DataFrame(rows).to_csv(RES / "drafts_box_shares.csv", index=False)

    # d3 class shares per region x scenario x era (V1, V2)
    fig, axs = plt.subplots(len(REGIONS), 2, figsize=(13, 10), sharex=True)
    for a, (k, rn) in enumerate(REGIONS.items()):
        m = dom & (reg == k)
        for b, scen in enumerate(SCENS):
            ax = axs[a, b]
            labels = []
            for y, (era, ver) in enumerate([(e, v) for e in ERAS for v in ["V1", "V2"]]):
                c = cls[(ver, scen, era)][m]
                c = c[np.isfinite(c)]
                left = 0
                for q in range(len(CLASSES)):
                    wdt = 100 * np.mean(c == q)
                    ax.barh(y, wdt, left=left, color=CLASS_C[q], height=0.78, edgecolor="white", lw=0.6)
                    left += wdt
                labels.append(f"{era.replace('_', '–')}  {ver}")
            ax.set_yticks(range(len(labels)), labels, fontsize=8)
            ax.invert_yaxis()
            ax.set_xlim(0, 100)
            ax.set_title(f"{rn}, RCP {scen[3]}.{scen[4]}", loc="left", fontsize=10)
    for ax in axs[-1]:
        ax.set_xlabel("% of the region's permafrost cells")
    fig.legend([plt.Rectangle((0, 0), 1, 1, fc=c) for c in CLASS_C], CLASSES, ncol=len(CLASSES), frameon=False,
               loc="upper center", bbox_to_anchor=(0.5, 1.03))
    fig.tight_layout()
    fig.savefig(OUT / "d3_regional_class_shares.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    # d4 where each region's middle 50 % sits, by era
    fig, axs = plt.subplots(1, 2, figsize=(14, 6), sharey=True)
    for ax, scen in zip(axs, SCENS):
        draw_table(ax, alpha=0.45)
        for k, rn in REGIONS.items():
            m = dom & (reg == k)
            t = today[m]
            tq = np.nanpercentile(t, [25, 50, 75])
            pts = []
            for era in ERAS:
                w = warm[("V1", scen, era)][m]
                wq = np.nanpercentile(w, [25, 50, 75])
                ax.add_patch(plt.Rectangle((wq[0], tq[0]), wq[2] - wq[0], tq[2] - tq[0], fill=False, ec=INK, lw=0.9,
                                           ls=(0, (3, 2))))
                pts.append((wq[1], tq[1]))
            xs, ys = zip(*pts)
            ax.plot(xs, ys, "-", color=INK, lw=1.2)
            ax.plot(xs, ys, MARKERS[rn], color=INK, mfc="white", ms=8, mew=1.4)
            dy = {"Arctic": 0, "Interior": 0, "West": 12, "South": -12}[rn]
            ax.annotate(rn, pts[-1], xytext=(10, dy), textcoords="offset points", va="center", fontsize=9, weight="bold",
                        bbox=dict(fc="white", ec="none", alpha=0.7, pad=1))
        ax.set_xlabel("projected warming (°C)")
        ax.set_title(f"RCP {scen[3]}.{scen[4]}, V1: region medians for 2026–2050 → 2051–2080 → 2081–2100\n"
                     "(dashed boxes = middle 50 % of the region's cells)", loc="left", fontsize=9.5)
    axs[0].set_ylabel("today's surface temperature (°C)")
    fig.tight_layout()
    fig.savefig(OUT / "d4_region_positions.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # d5 projected warming by region and era
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.8), sharey=True)
    for ax, scen in zip(axs, SCENS):
        pos, data, labs = [], [], []
        for a, (k, rn) in enumerate(REGIONS.items()):
            m = dom & (reg == k)
            for e, era in enumerate(ERAS):
                w = warm[("V1", scen, era)][m]
                data.append(w[np.isfinite(w)])
                pos.append(a * 4 + e)
                labs.append(era[:4] + "–\n" + era[-4:])
        bp = ax.boxplot(data, positions=pos, widths=0.7, whis=(5, 95), showfliers=False, patch_artist=True,
                        medianprops=dict(color=INK), boxprops=dict(fc="#e4e3df", ec=INK2),
                        whiskerprops=dict(color=INK2), capprops=dict(color=INK2))
        for e in WARM_EDGES:
            ax.axhline(e, color=INK, lw=0.8, ls=(0, (2, 2)))
        ax.set_xticks(pos, labs, fontsize=7)
        for a, rn in enumerate(REGIONS.values()):
            ax.text(a * 4 + 1, 7.4, rn, ha="center", fontsize=9.5, weight="bold")
        ax.set_ylim(0, 8)
        ax.set_title(f"Projected warming, V1, RCP {scen[3]}.{scen[4]} (box = middle 50 %, whiskers = 5–95 %)",
                     loc="left", fontsize=10)
        ax.grid(axis="y", color=GRID, lw=0.6)
    axs[0].set_ylabel("projected warming (°C); dashed = band edges 2 / 3 / 4 °C")
    fig.tight_layout()
    fig.savefig(OUT / "d5_warming_by_region.png", dpi=140, bbox_inches="tight")
    plt.close(fig)

    # d6 edge sensitivity: share of cells changing class if edges move by +/- 0.5 degC (V1, 2051-2080, RCP 8.5)
    rows = []
    for k, rn in REGIONS.items():
        m = dom & (reg == k)
        t, w = today[m], warm[key][m]
        ok = np.isfinite(t) & np.isfinite(w)
        t, w = t[ok], w[ok]
        i0, j0 = boxes(t, w)
        c0 = TABLE[i0, j0]
        for name, de_t, de_w in [("today edges −0.5", -0.5, 0), ("today edges +0.5", 0.5, 0),
                                 ("warming edges −0.5", 0, -0.5), ("warming edges +0.5", 0, 0.5)]:
            i1, j1 = boxes(t, w, [e + de_t for e in TODAY_EDGES], [e + de_w for e in WARM_EDGES])
            rows.append(dict(region=rn, shift=name, changed=np.mean(TABLE[i1, j1] != c0)))
    d6 = pd.DataFrame(rows)
    d6.to_csv(RES / "drafts_edge_sensitivity.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 4))
    shifts = list(dict.fromkeys(d6["shift"]))
    shades = ["#86b6ef", "#1c5cab", "#cfcdc6", "#52514e"]
    for s_i, sh in enumerate(shifts):
        d = d6[d6["shift"] == sh]
        ax.bar(np.arange(4) + (s_i - 1.5) * 0.2, 100 * d.changed, width=0.19, color=shades[s_i], label=sh)
    ax.set_xticks(range(4), list(REGIONS.values()))
    ax.set_ylabel("% of the region's cells changing class")
    ax.set_title("Edge sensitivity: V1, 2051–2080, RCP 8.5", loc="left", fontsize=10)
    ax.legend(frameon=False, fontsize=8.5, ncol=2)
    ax.grid(axis="y", color=GRID, lw=0.6)
    fig.savefig(OUT / "d6_edge_sensitivity.png", dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(d6.pivot_table(index="region", columns="shift", values="changed", sort=False).round(3).to_string())


if __name__ == "__main__":
    main()
