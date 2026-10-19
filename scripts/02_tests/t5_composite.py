"""T5: composite (0-1) Permafrost Thaw Index, "PTI-C" (docs/PTI_COMPOSITE.md; decisions Q22).
Question: "Does this cell contain permafrost that is susceptible to thaw?"

  PTI-C = 0.4 s_today + 0.4 s_warming + 0.1 s_flat + 0.1 s_cover        (weights sum to 1; additive)
  s_today   = clip((ESA GST 2014-2023 + 6) / 8, 0, 1)                   (-6 degC -> 0, +2 degC -> 1)
  s_warming = clip(warming / 6, 0, 1)                                   (0 -> 0, 6 degC -> 1); warming as in PTI.md:
              V1 air (T_N2 - today), V2 GIPL via the delta change method, air where GIPL is masked (T_G2 - today)
  s_flat    = share of the cell's land that is flat (32 m TII within +-0.1; 1 - sun_share - shade_share)
  s_cover   = share of the cell in permafrost-favourable NLCD 2016 classes {42, 90, 95, 72, 51, 74}
Classes on the score: Very low < 0.2 <= Low < 0.4 <= Moderate < 0.6 <= High < 0.8 <= Very high.
Domain = PTI.md's (ESA PFR 2023 > 0, GIPL grid); PFR is the gate only.
Outputs: <data>/results/t5/{ptic_area_summary,ptic_terms_corr,ptic_test_areas}.csv, ptic.nc;
docs/figures/ptic_{scaling,terms,class_shares,contrib,<area>}.png
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "03_report"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from matplotlib.colors import ListedColormap
from scipy.stats import spearmanr

from composite_indexing import config as C
from pti_draft_figures import ERAS, REGIONS, SCENS, load
from pti_results_figures import crop_of
from t4_index_variants import CLASS_C, CLASSES

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = C.DATA / "results/t5"
FIG = C.REPO / "docs/figures"
W = dict(today=0.4, warming=0.4, flat=0.1, cover=0.1)
BREAKS = [0.2, 0.4, 0.6, 0.8]
COVER = [42, 90, 95, 72, 51, 74]  # evergreen forest, woody + herbaceous wetland, sedge/herbaceous, dwarf scrub, moss
INK, INK2, GRID, CONTEXT = "#0b0b0b", "#52514e", "#e4e3df", "#e4e3df"
TERM_C = {"today": "#0d366b", "warming": "#3987e5", "flat": "#9ec5f4", "cover": "#c9c7c1"}
TERM_N = {"today": "today's surface temperature", "warming": "projected warming", "flat": "% flat",
          "cover": "% favourable cover"}
CMAP = ListedColormap(CLASS_C)
CMAP.set_bad((0, 0, 0, 0))
VERS = ["V1", "V2"]


def s_today(t):
    return np.clip((t + 6.0) / 8.0, 0, 1)


def s_warm(w):
    return np.clip(w / 6.0, 0, 1)


def classify(x):
    return np.where(np.isfinite(x), np.digitize(x, BREAKS), np.nan)


def era_txt(e):
    return e.replace("_", "–")


def off(ax):
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    today, warm, _, reg, dom = load()
    f = xr.open_dataset(C.DATA / "features/features_1km.nc")
    flat = 1.0 - f.sun_share.values - f.shade_share.values
    z = np.load(C.DATA / "landcover/agg/nlcd2016_counts.npz")
    cnt, codes = z["counts"].astype(np.float32), list(z["codes"])
    tot = cnt[..., :-1].sum(-1)
    cover = np.where(tot >= 0.9 * 1600, sum(cnt[..., codes.index(c)] for c in COVER) / np.maximum(tot, 1), np.nan)
    with rasterio.open(C.DATA / "results/gipl_artifact/statewide_frozen_class.tif") as s:
        gipl_ok = s.read(1) == 2
    ok = dom & np.isfinite(flat) & np.isfinite(cover)
    print(f"domain {dom.sum()}, with terrain + cover {ok.sum()} ({ok.sum() / dom.sum():.4%})", flush=True)
    st = s_today(today)
    terms_fixed = W["today"] * st + W["flat"] * flat + W["cover"] * cover
    score, cls = {}, {}
    for k, w in warm.items():
        sc = np.where(ok, terms_fixed + W["warming"] * s_warm(w), np.nan)
        score[k], cls[k] = sc, classify(sc)

    # correlations of the new terms with the others (for the doc)
    i = np.flatnonzero(ok)[::5]
    lay = {"ESA surface temp (today)": today, "PFR 2023": f.pfr_2023.values, "% flat": flat,
           "% favourable cover": cover, "warming V1 RCP 8.5 2051-2080": warm[("V1", "rcp85", "2051_2080")]}
    names = list(lay)
    corr = pd.DataFrame([[spearmanr(lay[a].ravel()[i], lay[b].ravel()[i], nan_policy="omit").statistic
                          for b in names] for a in names], index=names, columns=names)
    corr.to_csv(OUT / "ptic_terms_corr.csv")
    print(corr.round(2).to_string(), flush=True)

    # summary per area x version x scenario x era
    rows = []
    areas = [(0, "Statewide")] + list(REGIONS.items())
    for k, an in areas:
        a = ok & ((reg == k) if k else True)
        for (ver, scen, era), sc in score.items():
            c = cls[(ver, scen, era)][a]
            w = warm[(ver, scen, era)][a]
            rows.append(dict(area=an, version=ver, scen=scen, era=era, cells=int(a.sum()),
                             score_median=float(np.median(sc[a])), warming_median=float(np.median(w)),
                             today_median=float(np.median(today[a])), flat_median=float(np.median(flat[a])),
                             cover_median=float(np.median(cover[a])),
                             **{f"c_{t}": float(np.mean(v)) for t, v in
                                [("today", W["today"] * st[a]), ("warming", W["warming"] * s_warm(w)),
                                 ("flat", W["flat"] * flat[a]), ("cover", W["cover"] * cover[a])]},
                             **{cn: float(np.mean(c == q)) for q, cn in enumerate(CLASSES)}))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "ptic_area_summary.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_rows", 200):
        print(df.round(3).to_string(index=False), flush=True)

    # netCDF of scores and classes
    ds = xr.Dataset(coords=dict(y=f.y, x=f.x))
    for (ver, scen, era), sc in score.items():
        ds[f"score_{ver}_{scen}_{era}"] = (("y", "x"), sc.astype("float32"))
        ds[f"class_{ver}_{scen}_{era}"] = (("y", "x"), cls[(ver, scen, era)].astype("float32"))
    ds["s_today"] = (("y", "x"), np.where(ok, st, np.nan).astype("float32"))
    ds["flat_share"] = (("y", "x"), np.where(ok, flat, np.nan).astype("float32"))
    ds["cover_share"] = (("y", "x"), np.where(ok, cover, np.nan).astype("float32"))
    ds.to_netcdf(OUT / "ptic.nc")

    test_areas(f, today, warm, score, flat, cover, gipl_ok)
    fig_scaling()
    fig_terms(ok, today, warm, flat, cover)
    fig_class_shares(df)
    fig_contrib(df)
    for k, an in areas:
        fig_area(k, an, ok, reg, dom, cls)


def test_areas(f, today, warm, score, flat, cover, gipl_ok):
    wins = json.loads((C.DATA / "windows/pilot_windows.json").read_text())["windows"]
    rows = []
    for w in wins:
        cx, cy = (w["x0"] + w["x1"]) / 2, (w["y0"] + w["y1"]) / 2
        j, i = int(np.argmin(np.abs(f.x.values - cx))), int(np.argmin(np.abs(f.y.values - cy)))
        for ver in VERS:
            k = (ver, "rcp85", "2051_2080")
            rows.append(dict(area=w["label"], version=ver, score=score[k][i, j], cls=CLASSES[int(classify(score[k][i, j]))],
                             today=today[i, j], warming=warm[k][i, j], flat=flat[i, j], cover=cover[i, j],
                             pfr=f.pfr_2023.values[i, j], gipl_used=bool(gipl_ok[i, j])))
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "ptic_test_areas.csv", index=False)
    print(d.round(3).to_string(index=False), flush=True)


def fig_scaling():
    fig, axs = plt.subplots(1, 4, figsize=(15, 3.2))
    specs = [("today", np.linspace(-10, 5, 200), s_today, "ESA surface temperature, 2014–2023 (°C)", (-6, 2)),
             ("warming", np.linspace(0, 8, 200), s_warm, "projected warming (°C)", (0, 6)),
             ("flat", np.linspace(0, 100, 200), lambda x: x / 100, "% of cell flat", None),
             ("cover", np.linspace(0, 100, 200), lambda x: x / 100, "% of cell favourable cover", None)]
    for ax, (t, x, fn, xl, b) in zip(axs, specs):
        ax.plot(x, fn(x), color=INK, lw=2)
        if b:
            for v in b:
                ax.axvline(v, color=INK2, lw=0.8, ls=(0, (2, 2)))
        ax.set_ylim(-0.05, 1.05)
        ax.set_xlabel(xl)
        ax.set_title(f"{TERM_N[t]} (weight {W[t]})", loc="left", fontsize=10)
        ax.grid(color=GRID, lw=0.6)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
    axs[0].set_ylabel("term value (0–1)")
    fig.tight_layout()
    fig.savefig(FIG / "ptic_scaling.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_terms(ok, today, warm, flat, cover):
    r0, r1, c0, c1 = crop_of(ok)
    seq = plt.get_cmap("Blues").copy()
    seq.set_bad((0, 0, 0, 0))
    maps = [("a. today's surface temperature term", s_today(today)),
            ("b. projected warming term (V2, RCP 8.5, 2051–2080)", s_warm(warm[("V2", "rcp85", "2051_2080")])),
            ("c. % of cell flat", flat), ("d. % of cell favourable cover", cover)]
    fig, axs = plt.subplots(2, 2, figsize=(13, 10.5), constrained_layout=True)
    for ax, (t, v) in zip(axs.ravel(), maps):
        im = ax.imshow(np.where(ok, v, np.nan)[r0:r1, c0:c1], cmap=seq, vmin=0, vmax=1, interpolation="nearest")
        off(ax)
        ax.set_title(t, loc="left", fontsize=10.5)
    fig.colorbar(im, ax=axs, shrink=0.5, label="term value, 0–1 (before weighting)")
    fig.savefig(FIG / "ptic_terms.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def fig_class_shares(df):
    areas = ["Statewide"] + list(REGIONS.values())
    fig, axs = plt.subplots(1, len(areas), figsize=(17, 4.6), sharey=True)
    for ax, a in zip(axs, areas):
        d = df[df.area == a]
        labels, bottoms = [], None
        x = 0
        for scen in SCENS:
            for era in ERAS:
                for ver in VERS:
                    r = d[(d.scen == scen) & (d.era == era) & (d.version == ver)].iloc[0]
                    b = 0
                    for q, cn in enumerate(CLASSES):
                        ax.bar(x, 100 * r[cn], bottom=b, color=CLASS_C[q], width=0.8, edgecolor="white", lw=0.5)
                        b += 100 * r[cn]
                    labels.append(f"{ver}")
                    x += 1
                x += 0.5
        ticks, xt = [], 0
        for scen in SCENS:
            for era in ERAS:
                ticks.append((xt + 0.5, f"{era[:4]}–{era[-2:]}\nRCP {scen[3]}.{scen[4]}"))
                xt += 2.5
        ax.set_xticks([t for t, _ in ticks], [l for _, l in ticks], fontsize=7)
        ax.set_title(a, loc="left", fontsize=10)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
    axs[0].set_ylabel("% of permafrost cells")
    h = [plt.Rectangle((0, 0), 1, 1, fc=c) for c in CLASS_C]
    fig.legend(h, CLASSES, loc="upper center", ncol=5, frameon=False, bbox_to_anchor=(0.5, 1.04))
    fig.text(0.5, -0.04, "Each pair of bars: V1 (left), V2 (right).", ha="center", fontsize=8.5, color=INK2)
    fig.tight_layout()
    fig.savefig(FIG / "ptic_class_shares.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_contrib(df):
    areas = ["Statewide"] + list(REGIONS.values())
    fig, axs = plt.subplots(1, 2, figsize=(14, 4.2), sharey=True)
    for ax, era in zip(axs, ["2026_2050", "2081_2100"]):
        for n, a in enumerate(areas):
            r = df[(df.area == a) & (df.version == "V2") & (df.scen == "rcp85") & (df.era == era)].iloc[0]
            left = 0
            for t in ["today", "warming", "flat", "cover"]:
                ax.barh(n, r[f"c_{t}"], left=left, color=TERM_C[t], height=0.6, edgecolor="white", lw=1,
                        label=TERM_N[t] if n == 0 else None)
                left += r[f"c_{t}"]
            ax.text(left + 0.01, n, f"{left:.2f}", va="center", fontsize=9, color=INK)
        for b in BREAKS:
            ax.axvline(b, color=INK2, lw=0.7, ls=(0, (2, 2)))
        ax.set_yticks(range(len(areas)), areas)
        ax.set_xlim(0, 1)
        ax.set_xlabel("mean score (stacked: contribution of each weighted term)")
        ax.set_title(f"V2, RCP 8.5, {era_txt(era)}", loc="left", fontsize=10)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
    axs[0].invert_yaxis()  # shared y: invert once (Statewide on top)
    axs[0].legend(frameon=False, fontsize=8.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(FIG / "ptic_contrib.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


def fig_area(k, an, ok, reg, dom, cls):
    area = ok & ((reg == k) if k else True)
    r0, r1, c0, c1 = crop_of(area)
    fig, axs = plt.subplots(len(ERAS), 4, figsize=(18, 4.4 * len(ERAS)), constrained_layout=True)
    for a, era in enumerate(ERAS):
        for b, (scen, ver) in enumerate([(s, v) for s in SCENS for v in VERS]):
            ax = axs[a, b]
            if k:
                ax.imshow(np.where(dom & ~area, 1.0, np.nan)[r0:r1, c0:c1], cmap=ListedColormap([CONTEXT]), vmin=0,
                          vmax=2, interpolation="nearest")
            ax.imshow(np.where(area, cls[(ver, scen, era)], np.nan)[r0:r1, c0:c1], cmap=CMAP, vmin=-0.5, vmax=4.5,
                      interpolation="nearest")
            off(ax)
            ax.set_title(f"{ver}, RCP {scen[3]}.{scen[4]}, {era_txt(era)}", loc="left", fontsize=10)
    h = [plt.Rectangle((0, 0), 1, 1, fc=c) for c in CLASS_C] + [plt.Rectangle((0, 0), 1, 1, fc=CONTEXT)]
    lab = CLASSES + (["other permafrost cells"] if k else [])
    fig.legend(h[:len(lab)], lab, loc="upper center", ncol=6, frameon=False, bbox_to_anchor=(0.5, 1.035),
               fontsize=11)
    fig.suptitle(f"PTI-C, {an} ({int(area.sum()):,} permafrost cells)", fontsize=14, y=1.07)
    fig.savefig(FIG / f"ptic_{an.lower()}.png", dpi=100, bbox_inches="tight")
    plt.close(fig)
    print(an, "figure done", flush=True)


if __name__ == "__main__":
    main()
