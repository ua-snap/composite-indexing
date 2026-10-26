"""T1 (Spearman correlation) + T2 (PCA, VIF) on the statewide feature cube (build_features.py). D19, D23.

Sets:
  state     - current state, domain = ESA PFR > 0 (2023) & GIPL-valid cell:
              pfr_2023, esa_gst_hist, esa_t1m_hist, esa_alt_hist, maat_hist, thaw_mean, lc_forest, lc_shrub,
              lc_herb_moss, lc_wetland (barren/other and water omitted: fractions sum to 1)
  <rcp>_<era> - projected (5ModelAvg), domain = PFR > 0 & GIPL class 2 (D17):
              maat, dmaat, gipl_sfc, dgipl_sfc (changes vs 2014-2023), pfr_2023, thaw_mean, lc_* (4).
              Eras are climate years (GIPL read from files labelled 20 years later, GIPL_ISSUE_3.md).
Regional: the same per region (features/regions_1km.tif: Arctic, Interior, West, South; make_regions.py).
PC signs are anchored (esa_gst_hist / maat loads positive on PC1) so PCs compare across sets and regions.
PCA = eigen-decomposition of the correlation matrix of z-scored variables (full domain). Loadings are
variable-PC correlations. Spearman = Pearson on ranks of a 200k random subsample (cells are spatially
autocorrelated: report effect sizes, not p-values). VIF = diagonal of the inverse correlation matrix.
Outputs: <data>/results/t2/{spearman,pca_variance,pca_loadings,vif}_<set>[_<region>].csv, regional_*.csv;
docs/figures/t2_corr_pca_<set>.png, t2_pca_maps_<set>.png, t2_scree_all.png, t2_regions_map.png,
t2_regional_pairs.png, t2_regional_pc1.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import rasterio
import pandas as pd
import xarray as xr
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import rankdata

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = C.DATA / "results/t2"
FIG = C.REPO / "docs/figures"
SUBSAMPLE = 200_000
NPC_SHOW = 4
ERAS = ["2026_2050", "2051_2080", "2081_2100"]
CHANGE_ERAS = ERAS  # base 2014-2023 overlaps no era
REGIONS = {1: "Arctic", 2: "Interior", 3: "West", 4: "South"}
REGION_C = {"Arctic": "#2a78d6", "Interior": "#eb6834", "West": "#1baf7a", "South": "#eda100"}
REGION_M = {"Arctic": "o", "Interior": "s", "West": "^", "South": "D"}
MIN_REGION_CELLS = 5000
SCENS = ["rcp45", "rcp85"]
MAP_SETS = ["state", "rcp85_2081_2100"]
LC = ["lc_forest", "lc_shrub", "lc_herb_moss", "lc_wetland"]
LABEL = {"pfr_2023": "Permafrost fraction (ESA 2023)", "esa_gst_hist": "Ground surface T (ESA GST)",
         "esa_t1m_hist": "1 m ground T (ESA T1m)", "esa_alt_hist": "Active layer (ESA ALT)",
         "maat_hist": "Air T (CRU MAAT)", "thaw_mean": "Terrain thaw score (TII)", "lc_forest": "Forest",
         "lc_shrub": "Shrub", "lc_herb_moss": "Herbaceous / moss", "lc_wetland": "Wetland",
         "maat": "Air T (MAAT)", "dmaat": "Air T change", "gipl_sfc": "Surface MAGT (GIPL)",
         "dgipl_sfc": "Surface MAGT change (GIPL)"}
SHORT = {"pfr_2023": "permafrost fraction", "esa_gst_hist": "surface T (ESA)", "esa_t1m_hist": "1 m T (ESA)",
         "maat_hist": "air T (CRU)", "thaw_mean": "terrain thaw score", "lc_forest": "forest", "maat": "air T",
         "gipl_sfc": "surface T (GIPL)", "dmaat": "air T change", "dgipl_sfc": "surface T change (GIPL)"}
INK, INK2 = "#0b0b0b", "#52514e"
DIV = LinearSegmentedColormap.from_list("div", ["#0d366b", "#2a78d6", "#9ec5f4", "#f0efec", "#f4a6a5", "#e34948",
                                                "#7a1d1c"])
DIV.set_bad("#ffffff")
RNG = np.random.default_rng(0)


def sets(f):
    cls, pos = f.gipl_class.values, f.pfr_pos.values == 1
    state = ["pfr_2023", "esa_gst_hist", "esa_t1m_hist", "esa_alt_hist", "maat_hist", "thaw_mean"] + LC
    out = {"state": ({v: f[v].values for v in state}, pos & (cls > 0))}
    for s in SCENS:
        for e in ERAS:
            cols = {"maat": f[f"maat_{s}_{e}"].values, "gipl_sfc": f[f"gipl_sfc_{s}_{e}"].values}
            if e in CHANGE_ERAS:
                cols.update(dmaat=f[f"dmaat_{s}_{e}"].values, dgipl_sfc=f[f"dgipl_sfc_{s}_{e}"].values)
            cols.update(pfr_2023=f.pfr_2023.values, thaw_mean=f.thaw_mean.values)
            cols.update({v: f[v].values for v in LC})
            out[f"{s}_{e}"] = (cols, pos & (cls == 2))
    return out


def analyse(name, cols, dom, verbose=True):
    names = list(cols)
    ok = dom & np.all([np.isfinite(cols[v]) for v in names], axis=0)
    X = np.column_stack([cols[v][ok] for v in names]).astype(np.float64)
    n = X.shape[0]
    Z = (X - X.mean(0)) / X.std(0)
    R = np.corrcoef(Z, rowvar=False)
    evals, evecs = np.linalg.eigh(R)
    order = np.argsort(evals)[::-1]
    evals, evecs = evals[order], evecs[:, order]
    anchor = names.index("esa_gst_hist" if "esa_gst_hist" in names else "maat")
    for k in range(evecs.shape[1]):  # sign: PC1 anchored on warmth; other PCs: largest |loading| positive
        ref = evecs[anchor, k] if k == 0 else evecs[np.argmax(np.abs(evecs[:, k])), k]
        if ref < 0:
            evecs[:, k] *= -1
    load = evecs * np.sqrt(np.maximum(evals, 0))
    vif = np.diag(np.linalg.inv(R))
    idx = RNG.choice(n, min(SUBSAMPLE, n), replace=False)
    S = np.corrcoef(np.column_stack([rankdata(X[idx, j]) for j in range(X.shape[1])]), rowvar=False)

    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(S, index=names, columns=names).to_csv(OUT / f"spearman_{name}.csv")
    var = pd.DataFrame(dict(pc=[f"PC{i + 1}" for i in range(len(evals))], eigenvalue=evals,
                            explained=evals / evals.sum(), cumulative=np.cumsum(evals) / evals.sum()))
    var.to_csv(OUT / f"pca_variance_{name}.csv", index=False)
    L = pd.DataFrame(load, index=names, columns=[f"PC{i + 1}" for i in range(len(evals))])
    L.to_csv(OUT / f"pca_loadings_{name}.csv")
    pd.DataFrame(dict(variable=names, vif=vif)).to_csv(OUT / f"vif_{name}.csv", index=False)
    if not verbose:
        return dict(names=names, S=S, load=load, evals=evals, evecs=evecs, ok=ok, n=n)
    print(f"\n== {name}: n = {n:,} cells")
    print("  explained:", " ".join(f"PC{i + 1} {v:.0%}" for i, v in enumerate(var.explained[:6])),
          f"| PCs with eigenvalue > 1: {(evals > 1).sum()}")
    print("  VIF:", ", ".join(f"{v} {x:.1f}" for v, x in zip(names, vif)))
    with pd.option_context("display.width", 200):
        print(L.iloc[:, :NPC_SHOW].round(2).to_string())
    return dict(names=names, S=S, load=load, evals=evals, evecs=evecs, ok=ok, Z=Z, n=n, X=X)


def plot_set(name, r, title):
    names, lab = r["names"], [LABEL[v] for v in r["names"]]
    plt.rcParams.update({"font.size": 9})
    fig, axs = plt.subplots(1, 2, figsize=(15, 6.2), gridspec_kw=dict(width_ratios=[1.05, 1]))
    ax = axs[0]
    im = ax.imshow(r["S"], cmap=DIV, vmin=-1, vmax=1)
    ax.set_xticks(range(len(names)), lab, rotation=45, ha="right")
    ax.set_yticks(range(len(names)), lab)
    for i in range(len(names)):
        for j in range(len(names)):
            v = r["S"][i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7, color="white" if abs(v) > 0.6 else INK)
    fig.colorbar(im, ax=ax, shrink=0.75, label="Spearman ρ")
    ax.set_title(f"Spearman correlation ({SUBSAMPLE // 1000}k-cell sample)", loc="left", fontsize=10, color=INK)
    ax = axs[1]
    k = NPC_SHOW
    L = r["load"][:, :k]
    im = ax.imshow(L, cmap=DIV, vmin=-1, vmax=1, aspect="auto")
    ex = r["evals"] / r["evals"].sum()
    ax.set_xticks(range(k), [f"PC{i + 1}\n{ex[i]:.0%}" for i in range(k)])
    ax.set_yticks(range(len(names)), lab)
    for i in range(len(names)):
        for j in range(k):
            ax.text(j, i, f"{L[i, j]:.2f}", ha="center", va="center", fontsize=8,
                    color="white" if abs(L[i, j]) > 0.6 else INK)
    fig.colorbar(im, ax=ax, shrink=0.75, label="loading (variable–PC correlation)")
    ax.set_title("PCA loadings (share of variance under each PC)", loc="left", fontsize=10, color=INK)
    fig.suptitle(f"{title}  (n = {r['n']:,} cells)", fontsize=11, color=INK)
    fig.tight_layout()
    fig.savefig(FIG / f"t2_corr_pca_{name}.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def plot_maps(name, r, shape, title):
    scores = r["Z"] @ r["evecs"][:, :3]
    fig, axs = plt.subplots(1, 3, figsize=(16, 4.8), constrained_layout=True)
    ex = r["evals"] / r["evals"].sum()
    for k, ax in enumerate(axs):
        g = np.full(shape, np.nan)
        g[r["ok"]] = scores[:, k]
        lim = np.nanpercentile(np.abs(scores[:, k]), 98)
        im = ax.imshow(g, cmap=DIV, vmin=-lim, vmax=lim, interpolation="nearest")
        top = np.argsort(-np.abs(r["load"][:, k]))[:3]
        ax.set_title(f"PC{k + 1} ({ex[k]:.0%}): " + ", ".join(
            f"{'+' if r['load'][i, k] > 0 else '−'}{LABEL[r['names'][i]]}" for i in top), loc="left", fontsize=8.5)
        ax.set_xticks([]); ax.set_yticks([])
        fig.colorbar(im, ax=ax, shrink=0.7)
    fig.suptitle(f"{title}: PC scores (white = outside domain)", fontsize=11)
    fig.savefig(FIG / f"t2_pca_maps_{name}.png", dpi=130, bbox_inches="tight")
    plt.close(fig)


def main():
    f = xr.open_dataset(C.DATA / "features/features_1km.nc")
    shape = f.pfr_2023.shape
    res = {}
    titles = {"state": "Current state (2000–2020, ESA PFR 2023, PFR > 0)"}
    titles.update({f"{s}_{e}": f"Projected {e.replace('_', '–')}, RCP {s[3]}.{s[4]} (5ModelAvg; GIPL good cells)"
                   for s in SCENS for e in ERAS})
    for name, (cols, dom) in sets(f).items():
        r = analyse(name, cols, dom)
        res[name] = r
        plot_set(name, r, titles[name])
        if name in MAP_SETS:
            plot_maps(name, r, shape, titles[name])

    # scree for all sets + stability of key correlations across eras
    fig, ax = plt.subplots(figsize=(7, 3.8))
    for name, r in res.items():
        ex = r["evals"] / r["evals"].sum()
        ax.plot(np.arange(1, len(ex) + 1), np.cumsum(ex), marker="o", ms=4, lw=1.4 if name != "state" else 2.4,
                color=INK if name == "state" else ("#eb6834" if "rcp85" in name else "#2a78d6"),
                alpha=1 if name == "state" else 0.4 + 0.2 * ERAS.index(name.split("_", 1)[1]), label=name)
    ax.set_xlabel("number of PCs"); ax.set_ylabel("cumulative variance explained")
    ax.grid(color="#e4e3df", lw=0.6)
    ax.legend(frameon=False, fontsize=7.5, ncol=2)
    ax.set_title("PCA scree (cumulative)", loc="left", fontsize=10)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.savefig(FIG / "t2_scree_all.png", dpi=150, bbox_inches="tight")

    rows = []
    for name, r in res.items():
        if name == "state":
            continue
        S, nm = r["S"], r["names"]
        g = lambda a, b: S[nm.index(a), nm.index(b)] if a in nm and b in nm else np.nan  # noqa: E731
        rows.append(dict(set=name, maat_vs_gipl_sfc=g("maat", "gipl_sfc"), dmaat_vs_dgipl_sfc=g("dmaat", "dgipl_sfc"),
                         gipl_sfc_vs_pfr=g("gipl_sfc", "pfr_2023"), dgipl_sfc_vs_pfr=g("dgipl_sfc", "pfr_2023"),
                         maat_vs_pfr=g("maat", "pfr_2023"), dmaat_vs_pfr=g("dmaat", "pfr_2023"),
                         thaw_vs_gipl_sfc=g("thaw_mean", "gipl_sfc")))
    key = pd.DataFrame(rows)
    key.to_csv(OUT / "spearman_key_pairs.csv", index=False)
    print("\nKey Spearman pairs by set:")
    print(key.round(2).to_string(index=False))
    regional(f, sets(f))


PAIRS_STATE = [("pfr_2023", "esa_gst_hist"), ("esa_gst_hist", "esa_t1m_hist"), ("maat_hist", "esa_gst_hist"),
               ("maat_hist", "pfr_2023"), ("thaw_mean", "esa_gst_hist"), ("lc_forest", "esa_gst_hist")]
PAIRS_PROJ = [("maat", "gipl_sfc"), ("dmaat", "dgipl_sfc"), ("gipl_sfc", "pfr_2023"), ("dgipl_sfc", "pfr_2023")]
REGIONAL_SETS = ["state", "rcp45_2081_2100", "rcp85_2051_2080", "rcp85_2081_2100"]


def regional(f, all_sets):
    with rasterio.open(C.DATA / "features/regions_1km.tif") as src:
        reg = src.read(1)
    rows, pc1 = [], []
    for name in REGIONAL_SETS:
        cols, dom = all_sets[name]
        pairs = PAIRS_STATE if name == "state" else PAIRS_PROJ
        for code, rname in REGIONS.items():
            m = dom & (reg == code)
            if m.sum() < MIN_REGION_CELLS:
                continue
            r = analyse(f"{name}_{rname}", cols, m, verbose=False)
            ex = r["evals"] / r["evals"].sum()
            nm = r["names"]
            for a, b in pairs:
                rows.append(dict(set=name, region=rname, n=r["n"], pair=f"{SHORT[a]} vs {SHORT[b]}",
                                 rho=r["S"][nm.index(a), nm.index(b)]))
            pc1.append(dict(set=name, region=rname, n=r["n"], pc1_explained=ex[0], pc2_explained=ex[1],
                            **{v: r["load"][i, 0] for i, v in enumerate(nm)}))
    rp, p1 = pd.DataFrame(rows), pd.DataFrame(pc1)
    rp.to_csv(OUT / "regional_pairs.csv", index=False)
    p1.to_csv(OUT / "regional_pc1.csv", index=False)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print("\nRegional Spearman pairs:")
        print(rp.pivot_table(index=["set", "pair"], columns="region", values="rho", sort=False).round(2).to_string())
        print("\nRegional PC1 (explained + loadings):")
        print(p1.round(2).to_string(index=False))
    plot_regions(reg, f, rp, p1)


def plot_regions(reg, f, rp, p1):
    dom = (f.pfr_pos.values == 1) & (f.gipl_class.values > 0)
    from matplotlib.colors import ListedColormap
    fig, ax = plt.subplots(figsize=(8, 6.5))
    g = np.where(reg > 0, reg.astype(float), np.nan)
    g_dom = np.where(dom, g, np.nan)
    cm = ListedColormap([REGION_C[REGIONS[k]] for k in REGIONS])
    ax.imshow(g, cmap=cm, vmin=0.5, vmax=4.5, alpha=0.25, interpolation="nearest")
    ax.imshow(g_dom, cmap=cm, vmin=0.5, vmax=4.5, interpolation="nearest")
    ax.legend([plt.Rectangle((0, 0), 1, 1, fc=REGION_C[r]) for r in REGION_C],
              [f"{r} ({int((dom & (reg == k)).sum()):,} permafrost cells)" for k, r in REGIONS.items()],
              loc="lower left", frameon=False, fontsize=9)
    ax.set_title("Regions (USDA STATSGO2 physiographic names); solid = permafrost cells analysed", loc="left",
                 fontsize=10)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.savefig(FIG / "t2_regions_map.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    blocks = [("state", "Today (ESA, CRU, 2000–2020)"), ("rcp85_2081_2100", "Projected 2081–2100, RCP 8.5"),
              ("rcp45_2081_2100", "Projected 2081–2100, RCP 4.5")]
    fig, axs = plt.subplots(1, len(blocks), figsize=(18, 4.2), gridspec_kw=dict(wspace=0.95))
    for ax, (st, title) in zip(axs, blocks):
        d = rp[rp.set == st]
        pairs = list(dict.fromkeys(d.pair))
        ax.axvline(0, color=INK2, lw=0.8)
        for k, rname in enumerate(REGIONS.values()):
            dd = d[d.region == rname]
            y = [pairs.index(p) + (k - 1.5) * 0.12 for p in dd.pair]
            ax.plot(dd.rho, y, REGION_M[rname], color=REGION_C[rname], ms=7, ls="none", label=rname)
        ax.set_yticks(range(len(pairs)), pairs, fontsize=8.5)
        ax.invert_yaxis()
        ax.set_xlim(-1, 1)
        ax.set_xlabel("Spearman ρ")
        ax.grid(axis="x", color="#e4e3df", lw=0.6)
        ax.set_title(title, loc="left", fontsize=10)
        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
    h, l = axs[0].get_legend_handles_labels()
    fig.legend(h, l, frameon=False, fontsize=9, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.08))
    fig.savefig(FIG / "t2_regional_pairs.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    st = p1[p1.set == "state"].set_index("region")
    var = [c for c in st.columns if c in LABEL and st[c].notna().all()]
    fig, ax = plt.subplots(figsize=(11, 3.4))
    im = ax.imshow(st[var].values, cmap=DIV, vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(var)), [LABEL[v] for v in var], rotation=35, ha="right")
    ax.set_yticks(range(len(st)), [f"{r}  (PC1 = {e:.0%})" for r, e in zip(st.index, st.pc1_explained)])
    for i in range(len(st)):
        for j in range(len(var)):
            v = st[var].values[i, j]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=8, color="white" if abs(v) > 0.6 else INK)
    fig.colorbar(im, ax=ax, shrink=0.9, label="PC1 loading")
    ax.set_title("Today: what the first principal component (PC1) is made of, by region", loc="left", fontsize=10)
    fig.savefig(FIG / "t2_regional_pc1.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
