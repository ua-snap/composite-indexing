"""T4: index variants on a fixed scale (D26-D28). The index answers: "How susceptible to thaw is the permafrost in this
cell, if it is there?" Domain: ESA PFR > 0 (2023) & GIPL-valid cell. Context (extent, terrain, land cover) is reported
beside the index in a "data sentence", not inside it (except variant X1, for comparison).

Fixed scale (D27; archive, 5 tiers, PTI_EXPERIMENTS.md): susceptibility class from projected mean annual ground
SURFACE temperature T (deg C), anchored on how ESA CCI permafrost fraction varies with ESA ground surface temperature
today:
  Very low < -4 <= Low < -2 <= Moderate < 0 <= High < +1.5 <= Very high
Variants (T per cell, per RCP and era 2026-2050 / 2051-2080 / 2081-2100):
  N1 today only        T = ESA GST 2014-2023
  N2 ESA + air warming  T = ESA GST 2014-2023 + [model MAAT(era) - model MAAT(2014-2023)]        (no GIPL)
  N3 weighted blend     score = 0.5 s(T_N2) + 0.25 s(MAAT) + 0.25 (1 - PFR/100) (fixed linear s(); classes by score)
  G1 ESA + GIPL change  T = ESA GST 2014-2023 + [GIPL(era) - GIPL(2014-2023)]                    (delta change method;
                        climate years, GIPL files + 20, GIPL_ISSUE_3.md); NoData where GIPL is masked (D17)
  G2 = G1, masked cells filled with N2 (flagged)
  G3 GIPL as delivered  T = GIPL surface MAGT (era)                                              (NoData where masked)
  X1 context inside     score = 0.8 s(T_N2) + 0.1 terrain + 0.1 (1 - insulating cover)           (illustration)
  CN / CG two-way table class = TABLE[today band, warming band]; today = ESA GST 2014-2023 (bands at -4/-2/0 degC);
                        warming = projected T - today (bands at 2/3/4/5 degC); CN warming from air (N2), CG warming from
                        GIPL via the delta change method, air where GIPL is masked (G2, flagged). No PFR anywhere.
                        PTI.md uses the 3-tier TABLE (Low / Moderate / High; class_CN / class_CG in the netCDF, data
                        sentences, t4_table.png); the archive outputs (CSVs, class shares) keep the 5-tier TABLE5.
Outputs: <data>/results/t4/{class_shares,agreement,regional,sentences}.csv, index_variants.nc;
docs/figures/t4_*.png (class maps: t4_class_maps_<rcp>.png, all variants x eras)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
import xarray as xr
from matplotlib.colors import ListedColormap

from composite_indexing import config as C
from t1_maat_vs_magt import cell_centres, maat_mean, to_gipl

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = C.DATA / "results/t4"
FIG = C.REPO / "docs/figures"
SCENS = ["rcp45", "rcp85"]
ERAS = {"2026_2050": (2026, 2050), "2051_2080": (2051, 2080), "2081_2100": (2081, 2100)}
EDGES = [-4.0, -2.0, 0.0, 1.5]  # degC: archive single-scale class edges on projected surface temperature (5 tiers)
CLASSES5 = ["Very low", "Low", "Moderate", "High", "Very high"]  # archive variants (PTI_EXPERIMENTS.md)
CLASS_C5 = ["#1f7a3d", "#8fcf86", "#f2b134", "#e34948", "#7a1d1c"]  # traffic light, lightness-stepped for CVD
CLASSES = ["Low", "Moderate", "High"]  # PTI classes (two-way table V1/V2 and PTI-C)
CLASS_C = ["#0072B2", "#F0E442", "#D55E00"]  # Okabe-Ito blue / yellow / vermillion (colour-blind safe)
T_COLD, T_WARM = -6.0, 2.0  # fixed linear score s(T) = clip((T - T_COLD) / (T_WARM - T_COLD), 0, 1)
SCORE_EDGES = [(e - T_COLD) / (T_WARM - T_COLD) for e in EDGES]  # same edges on the 0-1 score
MAAT_COLD, MAAT_WARM = -10.0, 0.0  # fixed scale for the MAAT term of N3
REGIONS = {1: "Arctic", 2: "Interior", 3: "West", 4: "South"}
VARIANTS = ["N1", "N2", "N3", "G1", "G2", "G3", "X1", "CN", "CG"]
TODAY_EDGES, WARM_EDGES = [-4.0, -2.0, 0.0], [2.0, 3.0, 4.0, 5.0]
TODAY_NAMES = ["Cold (below −4 °C)", "Cool (−4 to −2 °C)", "Near 0 (−2 to 0 °C)", "Warm surface (above 0 °C)"]
TODAY_WORDS = ["cold", "cool", "near 0 °C", "above 0 °C"]
WARM_NAMES = ["under 2 °C", "2–3 °C", "3–4 °C", "4–5 °C", "over 5 °C"]
TABLE5 = np.array([[0, 0, 1, 2, 3],   # rows: today's state (cold .. warm surface); columns: projected warming
                   [1, 2, 2, 3, 4],   # (under 2, 2-3, 3-4, 4-5, over 5 degC); values: class 0..4 = Very low ..
                   [2, 3, 3, 4, 4],   # Very high (archive). "Over 5" = "4-5" plus one class.
                   [2, 3, 4, 4, 4]])
TABLE = np.array([[0, 0, 0, 1, 2],   # = TABLE5 collapsed to 3 tiers (Very low + Low -> Low, Moderate, High + Very
                  [0, 1, 1, 2, 2],   # high -> High); values: class 0..2 = Low .. High (draft, team-editable).
                  [1, 2, 2, 2, 2],
                  [1, 2, 2, 2, 2]])
VNAME = {"N1": "N1 today only", "N2": "N2 ESA + air warming", "N3": "N3 weighted blend",
         "G1": "G1 ESA + GIPL change (delta)", "G2": "G2 = G1, gaps filled with N2", "G3": "G3 GIPL as delivered",
         "X1": "X1 context inside the index", "CN": "V1: today × air warming",
         "CG": "V2: today × GIPL warming (air where GIPL is masked)"}  # PTI.md calls the table versions V1 / V2
INK, INK2 = "#0b0b0b", "#52514e"
CLASS_INK = ["#ffffff", INK, INK]  # text on each PTI class colour (white on blue; dark on yellow / vermillion)


def s_of(T):
    return np.clip((T - T_COLD) / (T_WARM - T_COLD), 0, 1)


def classify_T(T):
    c = np.digitize(T, EDGES).astype(float)
    c[~np.isfinite(T)] = np.nan
    return c


def classify_score(s):
    c = np.digitize(s, SCORE_EDGES).astype(float)
    c[~np.isfinite(s)] = np.nan
    return c


def table_class(today, warming, table=TABLE):
    i = np.digitize(today, TODAY_EDGES)
    j = np.digitize(warming, WARM_EDGES)
    c = table[np.clip(i, 0, table.shape[0] - 1), np.clip(j, 0, table.shape[1] - 1)].astype(float)
    c[~(np.isfinite(today) & np.isfinite(warming))] = np.nan
    return c


def load():
    f = xr.open_dataset(C.DATA / "features/features_1km.nc")
    with rasterio.open(C.DATA / "features/regions_1km.tif") as s:
        reg, prof = s.read(1), s.profile
    z = np.load(C.DATA / "landcover/agg/nlcd2016_counts.npz")
    counts, codes = z["counts"].astype("float32"), list(z["codes"])
    tot = np.maximum(counts[..., :-1].sum(-1), 1)
    insul = (counts[..., codes.index(42)] + counts[..., codes.index(90)] + counts[..., codes.index(95)]) / tot
    insul[counts[..., :-1].sum(-1) < 0.9 * 1600] = np.nan
    return f, reg, prof, insul


def variants(f, prof, insul, scen, era):
    X, Y = cell_centres(prof)
    y0, y1 = ERAS[era]
    m_ref = to_gipl(maat_mean(scen, 2014, 2023), X, Y)
    m_era = f[f"maat_{scen}_{era}"].values
    esa = f.esa_gst_recent.values
    good = f.gipl_class.values == 2
    g_era, g_base = f[f"gipl_sfc_{scen}_{era}"].values, f[f"gipl_sfc_{scen}_base"].values  # base = 2014-2023, as ESA
    T = {}
    T["N1"] = esa
    T["N2"] = esa + (m_era - m_ref)
    T["G1"] = np.where(good, esa + (g_era - g_base), np.nan)
    T["G2"] = np.where(good, T["G1"], T["N2"])
    T["G3"] = np.where(good, g_era, np.nan)
    terrain = np.clip(f.thaw_mean.values / 0.5, 0, 1)
    s = {v: s_of(T[v]) for v in T}
    s["N3"] = 0.5 * s_of(T["N2"]) + 0.25 * np.clip((m_era - MAAT_COLD) / (MAAT_WARM - MAAT_COLD), 0, 1) + \
        0.25 * (1 - f.pfr_2023.values / 100)
    s["X1"] = 0.8 * s_of(T["N2"]) + 0.1 * terrain + 0.1 * (1 - insul)
    cls = {v: classify_T(T[v]) for v in T}
    cls["N3"], cls["X1"] = classify_score(s["N3"]), classify_score(s["X1"])
    T["W_CN"], T["W_CG"] = T["N2"] - esa, T["G2"] - esa  # projected warming vs today
    cls["CN"], cls["CG"] = table_class(esa, T["W_CN"], TABLE5), table_class(esa, T["W_CG"], TABLE5)  # archive
    s["CN"], s["CG"] = cls["CN"], cls["CG"]
    cls["V1"], cls["V2"] = table_class(esa, T["W_CN"]), table_class(esa, T["W_CG"])  # PTI, 3 tiers
    return T, s, cls, ~good


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f, reg, prof, insul = load()
    dom = (f.pfr_pos.values == 1) & (f.gipl_class.values > 0)
    n_dom = int(dom.sum())
    shares, agree, regional, store = [], [], [], {}
    for scen in SCENS:
        for era in ERAS:
            T, s, cls, masked = variants(f, prof, insul, scen, era)
            store[(scen, era)] = (T, s, cls, masked)
            ref = cls["N2"]
            for v in VARIANTS:
                c = cls[v][dom]
                ok = np.isfinite(c)
                row = dict(scen=scen, era=era, variant=v, coverage=ok.mean())
                row.update({k: np.mean(c[ok] == i) for i, k in enumerate(CLASSES5)})
                shares.append(row)
                both = ok & np.isfinite(ref[dom])
                rs = pd.Series(s[v][dom][both]).rank().corr(pd.Series(s["N2"][dom][both]).rank())
                agree.append(dict(scen=scen, era=era, variant=v, same_class_as_N2=np.mean(c[both] == ref[dom][both]),
                                  differ_2plus=np.mean(np.abs(c[both] - ref[dom][both]) >= 2), spearman_vs_N2=rs))
                for k, rn in REGIONS.items():
                    m = dom & (reg == k)
                    cc = cls[v][m]
                    okr = np.isfinite(cc)
                    regional.append(dict(scen=scen, era=era, variant=v, region=rn, coverage=okr.mean(),
                                         high_or_very_high=np.mean(cc[okr] >= 3) if okr.any() else np.nan,
                                         median_T=np.nanmedian(T[v][m]) if v in T else np.nan))
            print(scen, era, "done", flush=True)
    sh, ag, rg = pd.DataFrame(shares), pd.DataFrame(agree), pd.DataFrame(regional)
    sh.to_csv(OUT / "class_shares.csv", index=False)
    ag.to_csv(OUT / "agreement.csv", index=False)
    rg.to_csv(OUT / "regional.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_rows", 200):
        print(f"\ndomain cells: {n_dom:,}")
        print(sh.round(3).to_string(index=False))
        print(ag.round(3).to_string(index=False))
        print(rg[rg.era == "2051_2080"].pivot_table(index=["scen", "variant"], columns="region",
                                                    values="high_or_very_high", sort=False).round(2).to_string())
    save_nc(f, store, dom)
    sentences(f, store, dom, insul, reg)
    figures(f, store, dom, reg, sh, ag)


def save_nc(f, store, dom):
    v = {}
    pti = {"CN": "V1", "CG": "V2"}  # the netCDF's table classes are the 3-tier PTI ones
    for (scen, era), (T, s, cls, masked) in store.items():
        for k in VARIANTS:
            v[f"class_{k}_{scen}_{era}"] = (("y", "x"), np.where(dom, cls[pti.get(k, k)], np.nan).astype("float32"))
            if k in T:
                v[f"T_{k}_{scen}_{era}"] = (("y", "x"), np.where(dom, T[k], np.nan).astype("float32"))
    ds = xr.Dataset(v, coords=dict(x=f.x, y=f.y))
    ds.attrs.update(classes=",".join(CLASSES5), edges_degC=str(EDGES), pti_classes=",".join(CLASSES),
                    note="class_<N1..X1>: 0..4 = Very low..Very high (archive); class_CN / class_CG: PTI V1 / V2, "
                         "0..2 = Low..High")
    ds.to_netcdf(OUT / "index_variants.nc", encoding={k: {"zlib": True, "complevel": 4} for k in v})


def extent_words(pfr):
    if pfr >= 100:
        return "continuous"
    if pfr >= 71:
        return "extensive"
    if pfr >= 43:
        return "patchy"
    return "sparse"


def sentence(cls_now, cls_fut, T_fut, era, scen, pfr, sun, shade, insul, flag=""):
    era_txt = era.replace("_", "–")
    parts = [f"Susceptibility: {CLASSES5[int(cls_fut)]} (projected {era_txt}, RCP {scen[3]}.{scen[4]}; "
             f"today: {CLASSES5[int(cls_now)]}; projected surface temperature {T_fut:+.1f} °C)."]
    parts.append(f"Permafrost extent: {extent_words(pfr)} (PFR {pfr:.0f} %).")
    if sun >= 0.4:
        parts.append(f"Terrain: {sun:.0%} sun-facing slopes, so permafrost is likely limited to shaded and flat ground.")
    elif shade >= 0.4:
        parts.append(f"Terrain: {shade:.0%} shaded slopes, which favour permafrost.")
    else:
        parts.append(f"Terrain: mostly flat or gentle ({sun:.0%} sun-facing, {shade:.0%} shaded).")
    if np.isfinite(insul) and insul >= 0.5:
        parts.append(f"Land cover: {insul:.0%} black spruce / wetland (insulating organic layer).")
    elif np.isfinite(insul):
        parts.append(f"Land cover: {insul:.0%} black spruce / wetland; mostly shrub, tundra or open ground.")
    if flag:
        parts.append(flag)
    return " ".join(parts)


def sentence_c(cls_fut, today, warm, era, scen, pfr, sun, shade, insul, flag=""):
    era_txt = era.replace("_", "–")
    band = TODAY_WORDS[int(np.clip(np.digitize(today, TODAY_EDGES), 0, 3))]
    parts = [f"PTI: {CLASSES[int(cls_fut)]} ({era_txt}, RCP {scen[3]}.{scen[4]}): surface {band} today "
             f"({today:+.1f} °C), projected to warm {warm:+.1f} °C."]
    parts.append(f"Permafrost extent: {extent_words(pfr)} (PFR {pfr:.0f} %).")
    if sun >= 0.4:
        parts.append(f"Terrain: {sun:.0%} sun-facing slopes, so permafrost is likely limited to shaded and flat ground.")
    elif shade >= 0.4:
        parts.append(f"Terrain: {shade:.0%} shaded slopes, which favour permafrost.")
    else:
        parts.append(f"Terrain: mostly flat or gentle ({sun:.0%} sun-facing, {shade:.0%} shaded).")
    if np.isfinite(insul) and insul >= 0.5:
        parts.append(f"Land cover: {insul:.0%} black spruce / wetland (insulating organic layer).")
    elif np.isfinite(insul):
        parts.append(f"Land cover: {insul:.0%} black spruce / wetland; mostly shrub, tundra or open ground.")
    if flag:
        parts.append(flag)
    return " ".join(parts)


def sentences(f, store, dom, insul, reg):
    """Example data sentences (variant CG, RCP 8.5, 2051-2080): pilot-window centres + one random cell per region."""
    scen, era = "rcp85", "2051_2080"
    T, s, cls, masked = store[(scen, era)]
    picks = []
    with open(C.DATA / "windows/pilot_windows.json") as fh:
        import json
        for w in json.load(fh)["windows"]:
            cx, cy = (w["x0"] + w["x1"]) / 2, (w["y0"] + w["y1"]) / 2
            j = int(np.argmin(np.abs(f.x.values - cx)))
            i = int(np.argmin(np.abs(f.y.values - cy)))
            picks.append((f"{w['label']} test area", i, j))
    rng = np.random.default_rng(3)
    for k, rn in REGIONS.items():
        ii, jj = np.nonzero(dom & (reg == k))
        n = rng.integers(len(ii))
        picks.append((f"random {rn} cell", ii[n], jj[n]))
    rows = []
    for name, i, j in picks:
        flag = "Note: GIPL unavailable here; air-temperature warming used instead." if masked[i, j] else ""
        txt = sentence_c(cls["V2"][i, j], T["N1"][i, j], T["W_CG"][i, j], era, scen, f.pfr_2023.values[i, j],
                         f.sun_share.values[i, j], f.shade_share.values[i, j], insul[i, j], flag)
        rows.append(dict(cell=name, x=float(f.x.values[j]), y=float(f.y.values[i]), sentence=txt))
        print(f"\n[{name}] {txt}")
    pd.DataFrame(rows).to_csv(OUT / "sentences.csv", index=False)


def figures(f, store, dom, reg, sh, ag):
    plt.rcParams.update({"font.size": 9, "axes.spines.top": False, "axes.spines.right": False})
    # 1. fixed-scale anchor: ESA PFR vs ESA GST today
    v = (f.gipl_class.values > 0) & np.isfinite(f.esa_gst_recent.values)
    g, p = f.esa_gst_recent.values[v], f.pfr_2023.values[v]
    xs = np.arange(-8, 4.01, 0.25)
    mp = [p[(g >= x - 0.125) & (g < x + 0.125)].mean() if ((g >= x - 0.125) & (g < x + 0.125)).sum() > 200 else np.nan
          for x in xs]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    lo = [-8] + EDGES
    hi = EDGES + [4]
    for k in range(5):
        ax.axvspan(lo[k], hi[k], color=CLASS_C5[k], alpha=0.18, lw=0)
        ax.text((lo[k] + hi[k]) / 2, 104, CLASSES5[k], ha="center", fontsize=8.5, color=INK)
    ax.plot(xs, mp, color=INK, lw=2.2)
    ax.set_xlim(-8, 4); ax.set_ylim(0, 110)
    ax.set_xlabel("ESA CCI ground surface temperature, 2014–2023 (°C)")
    ax.set_ylabel("mean permafrost fraction (%)")
    ax.set_title("Fixed scale: how permafrost fraction varies with surface temperature today (all GIPL-valid cells)",
                 loc="left", fontsize=10)
    fig.savefig(FIG / "t4_fixed_scale.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 2. class maps: one figure per RCP; rows = variants (N1 today on top), columns = eras
    cmap = ListedColormap(CLASS_C5)
    cmap.set_bad((0, 0, 0, 0))
    rr, cc = np.nonzero(dom)
    r0, r1 = max(rr.min() - 10, 0), min(rr.max() + 10, dom.shape[0])
    c0, c1 = max(cc.min() - 10, 0), min(cc.max() + 10, dom.shape[1])
    rows = ["N1", "N2", "N3", "G1", "G2", "G3", "X1"]  # the two-way table variants have their own figure
    r0, r1 = int(np.percentile(rr, 0.2)) - 10, int(np.percentile(rr, 99.8)) + 10  # zoom past far outlying specks
    c0, c1 = int(np.percentile(cc, 0.2)) - 10, int(np.percentile(cc, 99.8)) + 10
    r0, c0 = max(r0, 0), max(c0, 0)
    for scen in SCENS:
        h = 13 / len(ERAS) * (r1 - r0) / (c1 - c0) + 0.45
        fig, axs = plt.subplots(len(rows), len(ERAS), figsize=(13, h * len(rows)), constrained_layout=True)
        for i, v in enumerate(rows):
            for j, era in enumerate(ERAS):
                ax = axs[i, j]
                ax.set_xticks([]); ax.set_yticks([])
                for sp in ax.spines.values():
                    sp.set_visible(False)
                if v == "N1" and j > 0:
                    ax.axis("off")
                    continue
                c = np.where(dom, store[(scen, era)][2][v], np.nan)[r0:r1, c0:c1]
                gap = np.where(dom[r0:r1, c0:c1] & ~np.isfinite(c), 1.0, np.nan)
                ax.imshow(gap, cmap=ListedColormap(["#a3a19b"]), vmin=0, vmax=2, interpolation="nearest")
                ax.imshow(c, cmap=cmap, vmin=-0.5, vmax=4.5, interpolation="nearest")
                ax.set_title(VNAME[v] if v == "N1" else f"{VNAME[v]}\n{era.replace('_', '–')}", loc="left",
                             fontsize=9)
        handles = [plt.Rectangle((0, 0), 1, 1, fc=c) for c in CLASS_C5] + [plt.Rectangle((0, 0), 1, 1, fc="#a3a19b")]
        axs[0, 1].legend(handles, CLASSES5 + ["no value (GIPL masked)"], loc="center", ncol=2, frameon=False,
                         fontsize=11, title=f"Susceptibility class, RCP {scen[3]}.{scen[4]}", title_fontsize=12)
        fig.savefig(FIG / f"t4_class_maps_{scen}.png", dpi=90, bbox_inches="tight")
        plt.close(fig)
    T, s, cls, masked = store[("rcp85", "2051_2080")]

    table_figures()

    # 3. class shares by variant, era, RCP (stacked bars)
    fig, axs = plt.subplots(1, 2, figsize=(15, 5.2), sharey=True)
    for ax, scen in zip(axs, SCENS):
        d = sh[sh.scen == scen]
        labels, lefts = [], []
        ypos = 0
        yt, yl = [], []
        for era in ERAS:
            for v in VARIANTS:
                if v == "N1" and era != "2026_2050":
                    continue
                r = d[(d.era == era) & (d.variant == v)].iloc[0]
                left = 0
                for k, cname in enumerate(CLASSES5):
                    w = r[cname] * 100
                    ax.barh(ypos, w, left=left, color=CLASS_C5[k], height=0.8, edgecolor="white", lw=0.6)
                    left += w
                yt.append(ypos)
                yl.append(("today: " if v == "N1" else f"{era.replace('_', '–')}: ") + VNAME[v])
                ypos += 1
            ypos += 0.6
        ax.set_yticks(yt, yl, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlim(0, 100)
        ax.set_xlabel("% of permafrost cells with a value")
        ax.set_title(f"RCP {scen[3]}.{scen[4]}", loc="left", fontsize=10)
    axs[0].legend([plt.Rectangle((0, 0), 1, 1, fc=c) for c in CLASS_C5], CLASSES5, ncol=5, frameon=False,
                  loc="upper center", bbox_to_anchor=(1.0, 1.1), fontsize=9)
    fig.tight_layout()
    fig.savefig(FIG / "t4_class_shares.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # 4. GIPL vs air-warming trajectory: G1 - N2 (degC), RCP 8.5 2051-2080
    from matplotlib.colors import LinearSegmentedColormap
    div = LinearSegmentedColormap.from_list("div", ["#0d366b", "#2a78d6", "#9ec5f4", "#f0efec", "#f4a6a5", "#e34948",
                                                    "#7a1d1c"])
    div.set_bad("#ffffff")
    fig, ax = plt.subplots(figsize=(8.5, 6.5))
    d = np.where(dom, T["G1"] - T["N2"], np.nan)[r0:r1, c0:c1]
    im = ax.imshow(d, cmap=div, vmin=-2, vmax=2, interpolation="nearest")
    fig.colorbar(im, ax=ax, shrink=0.7, label="V2 − V1 projected warming (°C): GIPL minus air temperature")
    ax.set_title("Where GIPL's surface warming differs from air warming (2051–2080, RCP 8.5)", loc="left", fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.savefig(FIG / "t4_gipl_minus_air.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def table_figures():
    """The two-way table itself (class names only). Per-area results figures: scripts/03_report/pti_results_figures.py."""
    fig, ax = plt.subplots(figsize=(11.5, 4.4))
    ax.imshow(TABLE, cmap=ListedColormap(CLASS_C), vmin=-0.5, vmax=len(CLASSES) - 0.5, aspect="auto")
    for a in range(TABLE.shape[0]):
        for b in range(TABLE.shape[1]):
            ax.text(b, a, CLASSES[TABLE[a, b]], ha="center", va="center", fontsize=11, weight="bold",
                    color=CLASS_INK[TABLE[a, b]])
    for k in range(1, TABLE.shape[1]):
        ax.axvline(k - 0.5, color="white", lw=2)
    for k in range(1, TABLE.shape[0]):
        ax.axhline(k - 0.5, color="white", lw=2)
    ax.set_xticks(range(TABLE.shape[1]), WARM_NAMES)
    ax.set_yticks(range(TABLE.shape[0]), TODAY_NAMES)
    ax.set_xlabel("Projected warming of the ground surface")
    ax.set_ylabel("Ground surface temperature today")
    ax.xaxis.set_label_position("top"); ax.xaxis.tick_top()
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.savefig(FIG / "t4_table.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

if __name__ == "__main__":
    main()
