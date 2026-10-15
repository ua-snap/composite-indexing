"""Do the GIPL frozen-1 m cells follow land cover (NLCD Alaska 2001/2011/2016)?

NALCMS 2015 was tried and dropped: its "USA" tile covers only the lower 48 (Alaska is only in the 3.6 GB North
America mosaic), and its US part is derived from NLCD 2016.

  aggregate <product>  - warp the 30 m map (nearest) onto a 25 m grid aligned with the GIPL 1 km cells (40 x 40
                         sub-pixels per cell), strip by strip, and count classes per cell
                         -> <data>/landcover/agg/<product>_counts.npz
  analyze              - on GIPL cells with ESA PFR > 0 (frozen vs good; 2 km border excluded), for two domains:
                         statewide, and "near" = within NEAR_KM of a frozen cell (a regional control, so interior
                         forest is not compared with North Slope tundra): frozen share by dominant class, AUC of
                         each class fraction, best one-class rules; plus maps.
Outputs: <data>/results/gipl_artifact/landcover_*.csv; docs/figures/t3f_landcover_*.png
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
from affine import Affine
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from scipy import ndimage
from scipy.stats import mannwhitneyu

from composite_indexing import config as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LC = C.DATA / "landcover"
OUT = C.DATA / "results/gipl_artifact"
FIG = C.REPO / "docs/figures"
SUB = 40  # 25 m sub-pixels per 1 km cell side
STRIP = 10  # GIPL rows per strip
NEAR_KM = 25

NLCD = {11: "Open water", 12: "Perennial ice/snow", 21: "Developed, open", 22: "Developed, low",
        23: "Developed, medium", 24: "Developed, high", 31: "Barren", 41: "Deciduous forest",
        42: "Evergreen forest", 43: "Mixed forest", 51: "Dwarf shrub", 52: "Shrub/scrub", 71: "Grassland/herbaceous",
        72: "Sedge/herbaceous", 74: "Moss", 81: "Pasture/hay", 82: "Cultivated crops", 90: "Woody wetlands",
        95: "Emergent herbaceous wetlands"}
PRODUCTS = {"nlcd2001": ("NLCD_2001_Land_Cover_AK_20200724", NLCD), "nlcd2011": ("NLCD_2011_Land_Cover_AK_20200724", NLCD),
            "nlcd2016": ("NLCD_2016_Land_Cover_AK_20200724", NLCD)}


def find_tif(product):
    d = LC / "extracted" / PRODUCTS[product][0]
    hits = sorted([p for p in d.rglob("*") if p.suffix.lower() in (".tif", ".img")], key=lambda p: -p.stat().st_size)
    if not hits:
        raise FileNotFoundError(d)
    return hits[0]


def aggregate(product):
    legend = PRODUCTS[product][1]
    codes = sorted(legend)
    lut = np.full(256, len(codes), np.int64)  # last index = nodata / other
    for i, c in enumerate(codes):
        lut[c] = i
    nc = len(codes) + 1
    src_path = find_tif(product)
    tr = Affine(1000 / SUB, 0, C.GIPL_X0, 0, -1000 / SUB, C.GIPL_Y0 + C.GIPL_NY * C.GIPL_RES)
    counts = np.zeros((C.GIPL_NY, C.GIPL_NX, nc), np.uint16)
    with rasterio.open(src_path) as src:
        print(src_path.name, src.crs, src.res, src.shape, src.nodata, flush=True)
        with WarpedVRT(src, crs=C.CRS, transform=tr, width=C.GIPL_NX * SUB, height=C.GIPL_NY * SUB,
                       resampling=Resampling.nearest, nodata=0) as vrt:
            for r0 in range(0, C.GIPL_NY, STRIP):
                nr = min(STRIP, C.GIPL_NY - r0)
                a = vrt.read(1, window=rasterio.windows.Window(0, r0 * SUB, C.GIPL_NX * SUB, nr * SUB))
                idx = lut[a]
                cell = (np.arange(nr * SUB)[:, None] // SUB) * C.GIPL_NX + (np.arange(C.GIPL_NX * SUB)[None, :] // SUB)
                bc = np.bincount((cell * nc + idx).ravel(), minlength=nr * C.GIPL_NX * nc)
                counts[r0:r0 + nr] = bc.reshape(nr, C.GIPL_NX, nc).astype(np.uint16)
                if r0 % 200 == 0:
                    print(f"  row {r0}/{C.GIPL_NY}", flush=True)
    out = LC / "agg" / f"{product}_counts.npz"
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(out, counts=counts, codes=np.array(codes))
    print("saved", out)


def auc(a, b):
    return mannwhitneyu(a, b).statistic / (len(a) * len(b))


def analyze():
    with rasterio.open(OUT / "statewide_frozen_class.tif") as s:
        cls = s.read(1)
    frozen, good = cls == 4, cls == 2
    near = ndimage.distance_transform_edt(~frozen) <= NEAR_KM
    dom_rows, auc_rows, rule_rows, doms = [], [], [], {}
    for product, domain, (_, legend) in [(p, d, v) for p, v in PRODUCTS.items() for d in ("statewide", "near")]:
        p = LC / "agg" / f"{product}_counts.npz"
        if not p.exists():
            print("missing", p)
            continue
        z = np.load(p)
        counts, codes = z["counts"].astype(np.float32), list(z["codes"])
        tot = counts[..., :-1].sum(-1)
        frac = counts[..., :-1] / np.maximum(tot, 1)[..., None]
        covered = tot >= 0.9 * SUB * SUB
        if not covered.any():
            print(f"\n== {product}: no coverage of the GIPL grid (skipped)")
            continue
        dom = np.where(covered, np.argmax(counts[..., :-1], -1), -1)
        doms[product] = (dom, codes, legend)
        dom_share = np.where(covered, frac.max(-1), np.nan)
        m = (frozen | good) & covered & (near if domain == "near" else True)
        print(f"\n== {product} [{domain}]: domain cells {m.sum()}, frozen {(frozen & m).sum()} (of {frozen.sum()})")
        nf = (frozen & m).sum()
        for i, c in enumerate(codes):
            sel = m & (dom == i)
            if sel.sum() == 0:
                continue
            dom_rows.append(dict(product=product, domain=domain, code=c, name=legend[c], cells=int(sel.sum()),
                                 frozen=int((sel & frozen).sum()), frozen_share=(sel & frozen).sum() / sel.sum(),
                                 share_of_all_frozen=(sel & frozen).sum() / nf))
            fa, fb = frac[..., i][m & frozen], frac[..., i][m & good]
            if fa.max() > 0 or fb.max() > 0:
                auc_rows.append(dict(product=product, domain=domain, code=c, name=legend[c], auc=auc(fa, fb),
                                     frozen_mean_frac=fa.mean(), good_mean_frac=fb.mean()))
            # one-class rule: flag cells where this class covers >= t of the cell
            for t in (0.25, 0.5, 0.75):
                flag = m & (frac[..., i] >= t)
                if flag.sum():
                    rule_rows.append(dict(product=product, domain=domain, name=legend[c], threshold=t, flagged=int(flag.sum()),
                                          recall=(flag & frozen).sum() / nf, precision=(flag & frozen).sum() / flag.sum()))
        a = auc(dom_share[m & frozen], dom_share[m & good])
        print(f"  dominant-class purity AUC (frozen vs good): {a:.3f}")
    dd, aa, rr = pd.DataFrame(dom_rows), pd.DataFrame(auc_rows), pd.DataFrame(rule_rows)
    dd.to_csv(OUT / "landcover_dominant.csv", index=False)
    aa.to_csv(OUT / "landcover_auc.csv", index=False)
    rr.to_csv(OUT / "landcover_rules.csv", index=False)
    with pd.option_context("display.width", 220, "display.max_colwidth", 45):
        for (product, domain), _ in dd.groupby(["product", "domain"], sort=False):
            k = lambda t: (t["product"] == product) & (t["domain"] == domain)  # noqa: E731
            print(f"\n== {product} [{domain}]: by dominant class (cells >= 1000)")
            print(dd[k(dd) & (dd.cells >= 1000)].sort_values("frozen_share", ascending=False)
                  .drop(columns=["product", "domain"]).round(3).to_string(index=False))
            print("  strongest class-fraction AUCs (|AUC-0.5| largest):")
            x = aa[k(aa)].assign(d=lambda t: (t.auc - 0.5).abs()).sort_values("d", ascending=False)
            print(x.head(6).drop(columns=["product", "domain", "d"]).round(3).to_string(index=False))
            print("  best one-class rules by F1:")
            y = rr[k(rr)].assign(f1=lambda t: 2 * t.recall * t.precision / (t.recall + t.precision))
            print(y.sort_values("f1", ascending=False).head(4).drop(columns=["product", "domain"]).round(3)
                  .to_string(index=False))
    plot(doms, cls)


def plot(doms, cls):
    """Dominant land cover (eastern Interior zoom) with frozen outlines, one panel per product."""
    x0, x1, y0, y1 = 150_000, 650_000, 1_350_000, 1_900_000
    c0, c1 = int((x0 - C.GIPL_X0) / 1000), int((x1 - C.GIPL_X0) / 1000)
    top = C.GIPL_Y0 + C.GIPL_NY * 1000
    r0, r1 = int((top - y1) / 1000), int((top - y0) / 1000)
    fz = (cls[r0:r1, c0:c1] == 4).astype(float)
    groups = {  # coarse display groups shared by both legends
        "Forest": ("#1c5cab", ["forest"]), "Shrub": ("#86b6ef", ["shrub", "scrub"]),
        "Herbaceous / grass / moss": ("#e9d8a6", ["grass", "herbaceous", "moss", "sedge"]),
        "Wetland": ("#1baf7a", ["wetland"]), "Barren / ice / developed": ("#cfcdc6", ["barren", "ice", "snow", "develop",
                                                                                      "urban", "crop", "pasture"]),
        "Water": ("#0d366b", ["water"])}
    names = list(groups)
    order = ["Wetland", "Water", "Forest", "Shrub", "Herbaceous / grass / moss", "Barren / ice / developed"]
    prods = [p for p in ["nlcd2001", "nlcd2016"] if p in doms]
    fig, axs = plt.subplots(1, len(prods), figsize=(6 * len(prods), 7), constrained_layout=True, squeeze=False)
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap([groups[n][0] for n in names])
    cmap.set_bad("#ffffff")
    for ax, p in zip(axs[0], prods):
        dom, codes, legend = doms[p]
        g = np.full(dom.shape, np.nan)
        for i, c in enumerate(codes):
            nm = legend[c].lower()
            for k in order:
                if any(w in nm for w in groups[k][1]):
                    g[dom == i] = names.index(k)
                    break
        ax.imshow(g[r0:r1, c0:c1], extent=(x0, x1, y0, y1), cmap=cmap, vmin=-0.5, vmax=len(names) - 0.5,
                  interpolation="nearest")
        ax.contour(fz, levels=[0.5], extent=(x0, x1, y0, y1), origin="upper", colors="#c2410c", linewidths=0.9)
        ax.set_title(f"{p.upper()} dominant class (1 km)", loc="left", fontsize=10)
        ax.set_xticks([]); ax.set_yticks([])
    handles = [plt.Rectangle((0, 0), 1, 1, fc=groups[n][0]) for n in names] + [
        plt.Line2D([], [], color="#c2410c", lw=1.2)]
    fig.legend(handles, names + ["GIPL stuck cells"], loc="lower center", ncol=7, frameon=False,
               bbox_to_anchor=(0.5, -0.05))
    fig.suptitle("Eastern Interior: GIPL stuck cells vs land cover", fontsize=11)
    fig.savefig(FIG / "t3f_landcover_east_interior.png", dpi=140, bbox_inches="tight")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["aggregate", "analyze"])
    ap.add_argument("product", nargs="?", choices=list(PRODUCTS))
    a = ap.parse_args()
    aggregate(a.product) if a.mode == "aggregate" else analyze()
