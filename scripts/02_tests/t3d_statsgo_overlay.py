"""Do the GIPL frozen-1 m cells follow USDA STATSGO2 (Alaska, 2016) soil map units?

Map units are rasterized on the GIPL 1 km grid (cell centres). Per unit: cells, frozen cells (any run, from
t3c_gipl_statewide.py), frozen share. If GIPL soil inputs came from these units, frozen shares should be near 0 or 1
and a few units should hold most of the frozen area. Units are described by their components (organic/peat soils,
drainage, landform).
Outputs: <data>/results/gipl_artifact/statsgo_units.csv, statsgo_mukey_1km.tif; docs/figures/t3d_statsgo_*.png
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

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

SG = C.DATA / "statsgo2/extracted/wss_gsmsoil_AK_2016-10-13"
OUT = C.DATA / "results/gipl_artifact"
FIG = C.REPO / "docs/figures"
INK, INK2, FROZEN_C, BORDER_C = "#0b0b0b", "#52514e", "#c2410c", "#f6b79d"


def table(name, physical):
    """Read a STATSGO2 pipe-delimited table with column names from mstabcol."""
    cols = pd.read_csv(SG / "tabular/mstabcol.txt", sep="|", header=None, quotechar='"', usecols=[0, 1, 2])
    names = cols[cols[0] == physical].sort_values(1)[2].tolist()
    return pd.read_csv(SG / f"tabular/{name}.txt", sep="|", header=None, names=names, quotechar='"',
                       dtype={"mukey": str, "cokey": str}, low_memory=False)


def describe_units():
    mu = table("mapunit", "mapunit")[["mukey", "musym", "muname"]]
    co = table("comp", "component")
    co["organic"] = co.taxorder.eq("Histosols") | co.taxsuborder.eq("Histels") | co.compname.str.contains(
        "organic", case=False, na=False)
    co["wet"] = co.drainagecl.isin(["Very poorly drained", "Poorly drained"])
    co["w"] = co.comppct_r.fillna(0)
    g = co.groupby("mukey")
    desc = pd.DataFrame({
        "pct_organic": g.apply(lambda d: d.w[d.organic].sum(), include_groups=False),
        "pct_poorly_drained": g.apply(lambda d: d.w[d.wet].sum(), include_groups=False),
        "dominant_component": g.apply(lambda d: d.sort_values("w").compname.iloc[-1], include_groups=False),
        "dominant_landform": g.apply(lambda d: d.sort_values("w").geomdesc.iloc[-1], include_groups=False),
    }).reset_index()
    return mu.merge(desc, on="mukey", how="left")


def main():
    with rasterio.open(OUT / "statewide_frozen_class.tif") as s:
        cls, prof = s.read(1), s.profile
    shp = gpd.read_file(SG / "spatial/gsmsoilmu_a_ak.shp").to_crs(C.CRS)
    shp["mukey"] = shp.MUKEY.astype(str)
    codes = {k: i + 1 for i, k in enumerate(sorted(shp.mukey.unique()))}
    mk = rasterize(((geom, codes[k]) for geom, k in zip(shp.geometry, shp.mukey)), out_shape=cls.shape,
                   transform=prof["transform"], fill=0, dtype="int32", all_touched=False)
    with rasterio.open(OUT / "statsgo_mukey_1km.tif", "w", **dict(prof, dtype="int32", nodata=0)) as d:
        d.write(mk, 1)
    inv = {v: k for k, v in codes.items()}

    valid = cls > 0
    frozen, border, pf = cls == 4, cls == 3, cls >= 2
    assert cls.max() == 4, "expects the 5-class frozen_class from the re-run of t3c"
    on = valid & (mk > 0)
    print(f"GIPL cells with a STATSGO2 unit: {on.sum()} / {valid.sum()}; frozen cells covered: "
          f"{(frozen & on).sum()} / {frozen.sum()}")
    df = pd.DataFrame({"code": mk[on], "frozen": frozen[on], "border": border[on], "pfr_pos": pf[on]})
    u = df.groupby("code").agg(cells=("frozen", "size"), frozen=("frozen", "sum"), border=("border", "sum"),
                               pfr_pos=("pfr_pos", "sum")).reset_index()
    u["mukey"] = u.code.map(inv)
    u["frozen_share"] = u.frozen / u.cells
    u = u.merge(describe_units(), on="mukey", how="left").sort_values("frozen", ascending=False)
    u.drop(columns="code").to_csv(OUT / "statsgo_units.csv", index=False)

    tot = u.frozen.sum()
    u["cum_frozen"] = u.frozen.cumsum() / tot
    n_any = int((u.frozen > 0).sum())
    print(f"units: {len(u)}; units with any frozen cell: {n_any}; units needed for 50/80/95 % of frozen area: "
          f"{int((u.cum_frozen < 0.5).sum()) + 1} / {int((u.cum_frozen < 0.8).sum()) + 1} / "
          f"{int((u.cum_frozen < 0.95).sum()) + 1}")
    for t in [0.5, 0.8, 0.9]:
        hi = u.frozen_share >= t
        print(f"units with frozen share >= {t}: {int(hi.sum())}, holding {u.frozen[hi].sum() / tot:.1%} of frozen "
              f"cells; precision if masked by unit: {u.frozen[hi].sum() / max(u.cells[hi].sum(), 1):.1%}")
    # best-case 'mask by unit' rule: flag units whose share >= 0.5
    pred = u.frozen_share >= 0.5
    rec, prec = u.frozen[pred].sum() / tot, u.frozen[pred].sum() / u.cells[pred].sum()
    print(f"mask-by-unit (share >= 0.5): recall {rec:.1%}, precision {prec:.1%}, cells flagged {u.cells[pred].sum()}")
    w = np.average(u.frozen_share, weights=u.frozen)
    print(f"frozen-weighted mean of unit frozen share: {w:.2f} (1 = frozen cells live in fully frozen units)")
    with pd.option_context("display.width", 250, "display.max_colwidth", 70):
        print(u.head(15)[["musym", "muname", "cells", "frozen", "frozen_share", "pct_organic",
                          "pct_poorly_drained", "dominant_landform"]].round(2).to_string(index=False))
        print("\nall units, organic % vs frozen share (cells-weighted correlation):",
              np.corrcoef(u.pct_organic.fillna(0), u.frozen_share)[0, 1].round(2),
              "| poorly drained:", np.corrcoef(u.pct_poorly_drained.fillna(0), u.frozen_share)[0, 1].round(2))

    # --- figure 1: distribution of unit frozen shares (area-weighted)
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.hist(u.frozen_share[u.frozen > 0], bins=np.linspace(0, 1, 21), weights=u.frozen[u.frozen > 0],
            color=FROZEN_C)
    ax.set_xlabel("share of the soil map unit that is frozen in GIPL")
    ax.set_ylabel("frozen cells (km²)")
    ax.set_title("Where do the frozen cells sit? (STATSGO2 map units)", loc="left", fontsize=10, color=INK)
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    fig.savefig(FIG / "t3d_statsgo_unit_share.png", dpi=150, bbox_inches="tight")

    # --- figure 2: eastern Interior zoom with unit boundaries
    t = prof["transform"]
    x0, x1, y0, y1 = 150_000, 650_000, 1_350_000, 1_900_000
    c0, c1 = int((x0 - t.c) / t.a), int((x1 - t.c) / t.a)
    r0, r1 = int((t.f - y1) / -t.e), int((t.f - y0) / -t.e)
    sub = cls[r0:r1, c0:c1]
    from matplotlib.colors import ListedColormap
    fig, ax = plt.subplots(figsize=(10, 11))
    ax.imshow(sub, extent=(x0, x1, y0, y1), cmap=ListedColormap(["#ffffff", "#f0efec", "#cfcdc6", BORDER_C, FROZEN_C]),
              vmin=-0.5, vmax=4.5, interpolation="nearest")
    shp.cx[x0:x1, y0:y1].boundary.plot(ax=ax, color=INK, linewidth=0.5)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_title("Eastern Interior: GIPL frozen cells (dark orange) vs STATSGO2 map-unit boundaries (black)",
                 loc="left", fontsize=10, color=INK)
    fig.savefig(FIG / "t3d_statsgo_east_interior.png", dpi=150, bbox_inches="tight")


if __name__ == "__main__":
    main()
