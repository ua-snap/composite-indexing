"""Is GIPL MAGT at 0.5 m also "stuck"? Statewide, same rule as 1 m (t3c): max - min of annual MAGT over 2021-2120
< 0.1 degC, per run (3 models x 2 RCPs). Compared with the 1 m stuck cells (any run).
Outputs: <data>/results/gipl_artifact/statewide_0p5m_{counts.csv,class.tif}; docs/figures/t3g_0p5m_vs_1m_map.png
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib
import numpy as np
import pandas as pd
import rasterio
from matplotlib.colors import ListedColormap
from pyproj import Transformer

from composite_indexing import config as C
from t3c_gipl_statewide import FROZEN, MODELS, SCENS, YEARS, esa_pfr_on_grid, read

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

TIF = C.DATA / "gipl_tif"
OUT = C.DATA / "results/gipl_artifact"
FIG = C.REPO / "docs/figures"
VAR = "magt0.5m"


def magt_range(model, scen):
    lo = hi = None
    for y in YEARS:
        a, prof = read(TIF / VAR / f"gipl_{model}_{scen}_{VAR}_degC_{y}.tif")
        lo = a if lo is None else np.fmin(lo, a)
        hi = a if hi is None else np.fmax(hi, a)
    return hi - lo, prof


def main():
    with rasterio.open(OUT / "statewide_frozen_class.tif") as s:
        cls1, prof = s.read(1), s.profile
    stuck1 = cls1 == 4  # 1 m, any run
    valid = cls1 > 0
    stuck, rows = {}, []
    for m in MODELS:
        for sc in SCENS:
            r, _ = magt_range(m, sc)
            stuck[(m, sc)] = r < FROZEN
            if (m, sc) == ("5ModelAvg", "rcp85"):
                r_ref = r
            print(f"{m} {sc}: 0.5 m stuck {stuck[(m, sc)].sum()}", flush=True)
    any05 = np.logical_or.reduce(list(stuck.values()))
    all05 = np.logical_and.reduce(list(stuck.values()))
    pfr = esa_pfr_on_grid(prof)
    pf = valid & (pfr > 0) & (pfr <= 100)
    n_pf = pf.sum()
    for (m, sc), f in stuck.items():
        rows.append(dict(run=f"{m} {sc}", stuck_0p5m=int(f.sum()), share_pfr_domain=(f & pf).sum() / n_pf,
                         also_stuck_1m=int((f & stuck1).sum())))
    for name, f in [("0.5 m stuck in ANY run", any05), ("0.5 m stuck in ALL runs", all05),
                    ("1 m stuck in ANY run", stuck1), ("both depths (any run)", any05 & stuck1),
                    ("0.5 m only", any05 & ~stuck1), ("1 m only", stuck1 & ~any05)]:
        rows.append(dict(run=name, stuck_0p5m=int(f.sum()), share_pfr_domain=(f & pf).sum() / n_pf))
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "statewide_0p5m_counts.csv", index=False)
    print(df.round(4).to_string(index=False))
    v05 = read(TIF / VAR / f"gipl_5ModelAvg_rcp85_{VAR}_degC_2021.tif")[0]
    s = stuck[("5ModelAvg", "rcp85")]
    if s.any():
        print("0.5 m stuck values (5ModelAvg rcp85, 2021) 1/10/50/90/99 %:",
              np.nanpercentile(v05[s], [1, 10, 50, 90, 99]).round(2))
    print("0.5 m range (5ModelAvg rcp85) in 1 m-stuck cells, 1/50/99 %:",
          np.nanpercentile(r_ref[stuck1], [1, 50, 99]).round(3))

    c = np.zeros(cls1.shape, "uint8")  # 0 nodata, 1 other, 2 1 m only, 3 0.5 m only, 4 both
    c[valid] = 1
    c[stuck1 & ~any05], c[any05 & ~stuck1], c[any05 & stuck1] = 2, 3, 4
    with rasterio.open(OUT / "statewide_0p5m_class.tif", "w", **dict(prof, dtype="uint8", nodata=0, compress="lzw")) as d:
        d.write(c, 1)

    t = prof["transform"]
    ext = (t.c, t.c + prof["width"] * t.a, t.f + prof["height"] * t.e, t.f)
    fig, ax = plt.subplots(figsize=(14, 11))
    ax.imshow(c, extent=ext, interpolation="nearest", vmin=-0.5, vmax=4.5,
              cmap=ListedColormap(["#ffffff", "#e4e3df", "#eb6834", "#2a78d6", "#7a1d1c"]))
    to = Transformer.from_crs("EPSG:4326", C.CRS, always_xy=True)
    for _, label, lon, lat in C.REGIONS:
        x, y = to.transform(lon, lat)
        ax.plot(x, y, "s", mfc="none", mec="#0b0b0b", ms=8, mew=1.2)
        ax.annotate(label, (x, y), xytext=(6, 6), textcoords="offset points", fontsize=9)
    n = {k: int(v.sum()) for k, v in [("both", any05 & stuck1), ("1m", stuck1 & ~any05), ("05", any05 & ~stuck1)]}
    handles = [plt.Rectangle((0, 0), 1, 1, fc=col) for col in ["#7a1d1c", "#eb6834", "#2a78d6", "#e4e3df"]]
    ax.legend(handles, [f"stuck at 0.5 m and 1 m ({n['both']:,} km²)", f"1 m only ({n['1m']:,} km²)",
                        f"0.5 m only ({n['05']:,} km²)", "other GIPL cells"], loc="lower left", frameon=False, fontsize=9)
    ax.set_title("GIPL 2.0 stuck cells at 0.5 m vs 1 m (MAGT change < 0.1 °C over 2021–2120, any run)", loc="left",
                 fontsize=12)
    ax.set_xticks([]); ax.set_yticks([])
    for sp in ax.spines.values():
        sp.set_visible(False)
    fig.savefig(FIG / "t3g_0p5m_vs_1m_map.png", dpi=170, bbox_inches="tight")


if __name__ == "__main__":
    main()
