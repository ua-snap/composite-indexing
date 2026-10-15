"""Do the GIPL frozen-1 m cells around Fairbanks follow SSURGO soils?

Six SSURGO survey areas intersecting the Fairbanks 100 x 100 km box (AK610, AK642, AK650, AK655, AK657, AK686;
found with Soil Data Access) are rasterized at 50 m and summarized per GIPL 1 km cell:
  - dominant map unit (mukey and map-unit name) and its area share (purity);
  - area-weighted soil properties from the component tables (component % weights): organic surface thickness,
    share of organic soils (Histosols/Histels), share poorly/very poorly drained, share with permafrost restriction,
    depth to permafrost, hydric share.
Tests: (1) per map unit (by name, so a series spanning surveys counts once), frozen share of the cells it
dominates - near 0/1 if GIPL used these units; (2) per property, AUC of separating frozen from normal cells.
Outputs: <data>/results/gipl_artifact/ssurgo_fbx_{cells,units,auc}.csv; docs/figures/t3e_ssurgo_*.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import rasterio
from rasterio.features import rasterize
from rasterio.transform import from_origin
from scipy.stats import mannwhitneyu

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SS = C.DATA / "ssurgo/extracted"
AREAS = ["AK610", "AK642", "AK650", "AK655", "AK657", "AK686"]
OUT = C.DATA / "results/gipl_artifact"
FIG = C.REPO / "docs/figures"
BOX = (272208.291, 1642479.751, 372208.291, 1742479.751)  # Fairbanks 100 x 100 km (t3b), GIPL cell edges
FINE = 50.0
K = int(1000 / FINE)  # fine pixels per GIPL cell side
INK, INK2, FROZEN_C = "#0b0b0b", "#52514e", "#c2410c"


def table(area, name, physical):
    t = SS / area / "tabular"
    cols = pd.read_csv(t / "mstabcol.txt", sep="|", header=None, quotechar='"', usecols=[0, 1, 2])
    names = cols[cols[0] == physical].sort_values(1)[2].tolist()
    p = t / f"{name}.txt"
    if p.stat().st_size == 0:
        return pd.DataFrame(columns=names)
    return pd.read_csv(p, sep="|", header=None, names=names, quotechar='"',
                       dtype={"mukey": str, "cokey": str, "chkey": str}, low_memory=False)


def organic_thickness(hz):
    """Thickness (cm) of the contiguous organic layer from the surface (O horizons or om_r >= 20 %)."""
    hz = hz.sort_values("hzdept_r")
    tot = 0.0
    for r in hz.itertuples():
        org = (isinstance(r.hzname, str) and r.hzname.strip().upper().startswith("O")) or (
            pd.notna(r.om_r) and r.om_r >= 20)
        if not org:
            break
        tot += (r.hzdepb_r - r.hzdept_r) if pd.notna(r.hzdepb_r) and pd.notna(r.hzdept_r) else 0
    return tot


def unit_properties():
    rows = []
    for a in AREAS:
        mu = table(a, "mapunit", "mapunit")[["mukey", "musym", "muname"]]
        co = table(a, "comp", "component")
        ch = table(a, "chorizon", "chorizon")
        rs = table(a, "crstrcts", "corestrictions")
        co["w"] = co.comppct_r.fillna(0)
        orgt = ch.groupby("cokey").apply(organic_thickness, include_groups=False).rename("org_cm")
        pf = rs[rs.reskind.astype(str).str.contains("ermafrost", na=False)].groupby("cokey").resdept_r.min().rename(
            "pf_depth_cm")
        co = co.join(orgt, on="cokey").join(pf, on="cokey")
        co["organic_soil"] = co.taxorder.eq("Histosols") | co.taxsuborder.eq("Histels")
        co["poorly"] = co.drainagecl.isin(["Very poorly drained", "Poorly drained"])
        co["has_pf"] = co.pf_depth_cm.notna() | co.taxorder.eq("Gelisols")
        co["hydric"] = co.hydricrating.eq("Yes")

        def agg(d):
            w = d.w.values
            sw = w.sum() if w.sum() > 0 else np.nan
            wa = lambda v: np.nansum(w * np.nan_to_num(v.astype(float))) / sw  # noqa: E731
            pfd = d.pf_depth_cm.astype(float)
            return pd.Series(dict(
                org_cm=wa(d.org_cm.fillna(0)), pct_organic_soil=100 * wa(d.organic_soil),
                pct_poorly=100 * wa(d.poorly), pct_permafrost=100 * wa(d.has_pf), pct_hydric=100 * wa(d.hydric),
                pf_depth_cm=np.nansum(w * pfd.fillna(0)) / max(w[pfd.notna().values].sum(), 1e-9)
                if pfd.notna().any() else np.nan,
                dominant_component=d.sort_values("w").compname.iloc[-1]))
        p = co.groupby("mukey").apply(agg, include_groups=False).reset_index()
        rows.append(mu.merge(p, on="mukey", how="left").assign(area=a))
    return pd.concat(rows, ignore_index=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    props = unit_properties()
    shp = pd.concat([gpd.read_file(SS / a / "spatial" / f"soilmu_a_{a.lower()}.shp").to_crs(C.CRS) for a in AREAS],
                    ignore_index=True)
    shp["mukey"] = shp.MUKEY.astype(str)
    codes = {k: i + 1 for i, k in enumerate(sorted(shp.mukey.unique()))}
    n = int((BOX[2] - BOX[0]) / FINE)
    tr = from_origin(BOX[0], BOX[3], FINE, FINE)
    fine = rasterize(((g, codes[k]) for g, k in zip(shp.geometry, shp.mukey)), out_shape=(n, n), transform=tr,
                     fill=0, dtype="int32")

    with rasterio.open(OUT / "statewide_frozen_class.tif") as s:
        win = rasterio.windows.from_bounds(*BOX, s.transform).round_offsets().round_lengths()
        cls = s.read(1, window=win)
    nc = cls.shape[0]
    assert nc * K == n

    # per-cell: dominant mukey, purity, coverage, area-weighted properties
    blocks = fine.reshape(nc, K, nc, K).transpose(0, 2, 1, 3).reshape(nc, nc, K * K)
    pcols = ["org_cm", "pct_organic_soil", "pct_poorly", "pct_permafrost", "pct_hydric", "pf_depth_cm"]
    lut = props.set_index("mukey")
    code_props = np.full((len(codes) + 1, len(pcols)), np.nan)
    code_name = np.array([""] * (len(codes) + 1), dtype=object)
    for k, c in codes.items():
        if k in lut.index:
            r = lut.loc[k]
            r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
            code_props[c] = r[pcols].astype(float).values
            code_name[c] = f"{r.muname}"
    recs = []
    for i in range(nc):
        for j in range(nc):
            b = blocks[i, j]
            cov = np.mean(b > 0)
            if cov == 0:
                recs.append(dict(row=i, col=j, cls=cls[i, j], coverage=0.0))
                continue
            vals, cnt = np.unique(b[b > 0], return_counts=True)
            dom = vals[np.argmax(cnt)]
            pv = code_props[b[b > 0]]
            rec = dict(row=i, col=j, cls=cls[i, j], coverage=cov, dom_code=dom, dom_name=code_name[dom],
                       purity=cnt.max() / cnt.sum())
            rec.update({c: np.nanmean(pv[:, q]) if np.isfinite(pv[:, q]).any() else np.nan for q, c in enumerate(pcols)})
            recs.append(rec)
    cells = pd.DataFrame(recs)
    cells["frozen"] = cells.cls == 4
    cells["normal"] = cells.cls == 2  # PFR>0, not frozen, not border
    cells.to_csv(OUT / "ssurgo_fbx_cells.csv", index=False)
    cov = cells.coverage >= 0.9
    print(f"box cells {len(cells)}; SSURGO coverage >= 90 %: {cov.sum()}; frozen cells {cells.frozen.sum()}, "
          f"of which covered {(cells.frozen & cov).sum()}")

    c = cells[cov & (cells.frozen | cells.normal)]
    u = c.groupby("dom_name").agg(cells=("frozen", "size"), frozen=("frozen", "sum"),
                                  purity=("purity", "median")).reset_index()
    u["frozen_share"] = u.frozen / u.cells
    u = u.merge(props.drop_duplicates("muname").rename(columns={"muname": "dom_name"})[
        ["dom_name"] + pcols], on="dom_name", how="left").sort_values("frozen", ascending=False)
    u.to_csv(OUT / "ssurgo_fbx_units.csv", index=False)
    tot = u.frozen.sum()
    w = np.average(u.frozen_share, weights=u.frozen) if tot else np.nan
    print(f"map-unit names dominating covered cells: {len(u)}; with any frozen cell: {(u.frozen > 0).sum()}; "
          f"frozen-weighted mean frozen share of the unit: {w:.2f}")
    for t in [0.5, 0.8]:
        hi = u.frozen_share >= t
        print(f"  units with frozen share >= {t}: {hi.sum()}, holding {u.frozen[hi].sum() / tot:.1%} of frozen cells")
    with pd.option_context("display.width", 250, "display.max_colwidth", 60):
        print(u[u.cells >= 10].head(20)[["dom_name", "cells", "frozen", "frozen_share", "purity", "org_cm",
                                          "pct_organic_soil", "pct_poorly", "pct_permafrost"]].round(2).to_string(index=False))

    aucs = []
    for col in pcols + ["purity"]:
        a, b = c.loc[c.frozen, col].dropna(), c.loc[~c.frozen, col].dropna()
        if len(a) > 5 and len(b) > 5:
            auc = mannwhitneyu(a, b).statistic / (len(a) * len(b))
            aucs.append(dict(property=col, auc=auc, frozen_median=a.median(), normal_median=b.median(),
                             n_frozen=len(a), n_normal=len(b)))
    aucs = pd.DataFrame(aucs)
    aucs.to_csv(OUT / "ssurgo_fbx_auc.csv", index=False)
    print("\nseparation of frozen vs normal cells (AUC 0.5 = none, 1 or 0 = perfect):")
    print(aucs.round(3).to_string(index=False))

    # --- figures: frozen outline over SSURGO organic thickness and permafrost share
    ext = (BOX[0], BOX[2], BOX[1], BOX[3])
    fz = (cls == 4).astype(float)
    fig, axs = plt.subplots(1, 2, figsize=(14, 7), constrained_layout=True)
    for ax, (col, title, vmax) in zip(axs, [("org_cm", "SSURGO organic surface layer (cm, area-weighted)", 40),
                                            ("pct_poorly", "SSURGO poorly / very poorly drained (% of cell)", 100)]):
        g = np.full((nc, nc), np.nan)
        g[cells.row, cells.col] = cells[col]
        g[(cells.coverage < 0.9).values.reshape(nc, nc)] = np.nan
        cm = plt.get_cmap("Blues").copy(); cm.set_bad("#f0efec")
        im = ax.imshow(g, extent=ext, cmap=cm, vmin=0, vmax=vmax)
        ax.contour(fz, levels=[0.5], extent=ext, origin="upper", colors=FROZEN_C, linewidths=1.2)
        fig.colorbar(im, ax=ax, shrink=0.75)
        ax.set_title(title, loc="left", fontsize=10, color=INK)
        ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Fairbanks 100 × 100 km: GIPL frozen cells (orange outline) vs SSURGO soils (light grey = no SSURGO)",
                 fontsize=11, color=INK)
    fig.savefig(FIG / "t3e_ssurgo_fairbanks.png", dpi=140, bbox_inches="tight")

    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.hist(u.frozen_share[u.frozen > 0], bins=np.linspace(0, 1, 21), weights=u.frozen[u.frozen > 0], color=FROZEN_C)
    ax.set_xlabel("share of the cells dominated by this SSURGO map unit that are frozen in GIPL")
    ax.set_ylabel("frozen cells")
    ax.set_title("Fairbanks: do frozen cells sit in fully frozen soil units?", loc="left", fontsize=10, color=INK)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.savefig(FIG / "t3e_ssurgo_unit_share.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
