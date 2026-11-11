# Team decisions → Rasdaman coverage

Turns the PDF the team workbench downloads ("Download PDF" on its Summary page) into a Rasdaman coverage with four
bands, plus its `wcst_import` ingest recipe. Each band holds one class per 1 km cell:

| Band | Holds |
|---|---|
| `wildfire` | Wildfire index class |
| `erosion` | Erosion index class |
| `permafrost` | Permafrost index class |
| `hazard` | Environmental Hazard: the three classes combined by the team's rule |

Values: **0 Low, 1 Medium, 2 High, 255 no data**. 255 means outside the land mask, or a land cell where that index
has no value (e.g. stuck GIPL cells in `permafrost`). When the rule counts a missing index as Low, the `hazard` band
has a class on every land cell. Cells a variant puts in a fixed class are 0 (Low): for example, wildfire outside
the boreal area, or permafrost outside the ESA permafrost zone.

**Status: test.** The decisions aren't final. The coverage ID is `environmental_hazard_index_test` until the team
settles.

## Workflow

```
E=/home/jdpaul3/micromamba/envs/arcticdem-pisr; PY="env PROJ_DATA=$E/share/proj $E/bin/python -I"
$PY toy_index/coverage/build_coverage.py <workbench.pdf>        # -> <data>/coverage/<id>/exported_<UTC time>/
$PY toy_index/coverage/check_coverage.py <that dir> --server    # file + recipe checks; spot checks vs SNAP servers
# ... ingest on the server, then:
$PY toy_index/coverage/check_coverage.py <that dir> --ingested  # the coverage on Zeus vs this build (~20 requests)
```

Then copy `<id>.nc` to the Rasdaman server at the recipe's input path. The default is
`/opt/rasdaman-storage/coverage_data/environmental_hazard_index/`; set `--server-dir` to change it. Run the ingest
with `ingest.json`. The same recipe is also written to `toy_index/coverage/ingest/ingest.json`.

The rasdaman-audit tiling guide says not to re-run `wcst_import` on a coverage that already exists, because it
duplicates tile index entries. To update, delete the coverage first, or ingest under a new ID and swap.

1. **`read_pdf.py`** reads the PDF without a PDF library (the file is made by jsPDF in the browser). It returns:
   - the decision record (the JSON block at the end of the PDF), and
   - the numbers the PDF prints, used as test values.
2. **`build_coverage.py`** checks the record against the repo: each variant exists and isn't retired, its letter
   matches, the boundaries are in order, and the rule is complete. It then:
   - classes every cell the way the app does (`classify.py`),
   - **stops if any number differs from the PDF**: shares of land per index and for the hazard, the hazard by region,
     the 11 named places, all 27 rule combinations,
   - writes `<id>.nc`, `ingest.json`, `metadata.json`, `decisions.json`, `build_checks.txt` and a copy of the PDF.
3. **`check_coverage.py`** checks the written files on their own:
   - grid and envelope equal to Rasdaman `crrel_gipl_outputs_nc`,
   - band types and fill value,
   - the hazard band recomputed from the other three,
   - recipe band names, nilValue, gridOrder, tiling bytes and metadata format.

   With `--server` it also spot-checks the named places against SNAP's services: about 33 small requests, run one at
   a time at least 1.5 s apart, and cached so a re-run sends none:

   | Index | Checked against |
   |---|---|
   | Permafrost | Rasdaman `crrel_gipl_outputs_nc_wcs` (GIPL magt1m) |
   | Wildfire | `earthmaps.io/fire_weather` (summer fire danger days) |
   | Erosion | `earthmaps.io/precipitation/frequency`, compared with NOAA Atlas 14 |
4. **`render_pdf.py`** (testing only) makes the app's PDF from a saved team record. It runs the published page's own
   code in headless Firefox.

## Choices

- **Same classes as the app, cell for cell.** The app classes each variant's value after rounding it for the page:
  0.01 for the three variants in use now, 1/scale in `variant.json`. The coverage uses the same rounded values, so it
  matches what the team saw and the PDF's numbers. Without the rounding, 340 to 825 cells per index (0.02 to 0.06 %
  of land) would fall on the other side of a boundary.
- **Grid**: the GIPL 2.0 1 km grid, EPSG:3338, 2471 × 1941. These are the same cells as Rasdaman
  `crrel_gipl_outputs_nc`; the envelope and first cell centre are checked against its DescribeCoverage. In the
  netCDF, `x` and `y` are cell centres and the recipe sets `pixelIsPoint: true`, as SNAP's GIPL recipe does.
- **One byte per band.** Four bands make 19.2 MB uncompressed for the whole state; the netCDF is 0.5 MB.
- **Tiling**: `ALIGNED [0:511, 0:511] tile size 1048576`, which makes 20 square tiles of 1 MiB:
  512 × 512 cells × 4 bands × 1 byte. There are no time or model axes, so one square tiling serves both point queries
  (one 1 MiB tile per point) and map tiles. That's why there's no `_wcs` / `_wms` pair. The guide's 1–4 MB range
  allows up to 1024 × 1024 tiles, but smaller tiles mean less data read per point. The netCDF dimensions are
  `(y, x)`, so Y has gridOrder 0 and X has gridOrder 1. `ALIGNED` is used because 1941 and 2471 aren't divisible
  by 512.
- **Metadata** follows the GIPL recipe's style: plain-text `Title`, and JSON text for structured values, which
  DescribeCoverage returns as JSON on SNAP's server.
  - **GetCoverage came back empty after the first two ingests.** Every GetCoverage in JSON, GeoTIFF or netCDF, and
    WCPS `encode()` of the coverage, returned an empty HTTP 200. GML output, scalar WCPS and WMS worked. GetCoverage
    on GIPL worked, and constructed WCPS coverages (`coverage ... over`) encoded fine. Petascope copies the coverage
    metadata into the rasql query of every `encode()`, so the metadata is the suspect.
    - **Most likely cause: the word "into"**, which rasql uses for writing (`SELECT … INTO`, `INSERT INTO … VALUES`).
      Both ingests had it in the Abstract ("turns the three classes into the hazard class"). SNAP saw the same with
      the CMIP6 `evspsbl` and fire weather `isi` coverages, which worked after their descriptions were reworded
      (rasdaman-ingest 3378ac427a, ardac d924132e43, 2025-10). Both old descriptions contained "into" ("flux of water
      into the atmosphere", "does not take fuel type into account"); the new ones, and every working description
      checked (other FWI codes, GIPL, DOT, ALFRESCO), don't.
    - Now: `build_coverage.py` rewords "into" to "to" and "values" to "data" in all metadata text, and refuses any
      of into / insert / update / delete / drop / create / alter / values / commit. `check_coverage.py` checks the
      recipe and, after ingest, the stored metadata.
    - Also, from the same search: band attributes are only `long_name`, `flag_values`, `flag_meanings`,
      `grid_mapping` (wcst_import copies every netCDF band attribute into the band metadata; the recipe only sets
      the global metadata). The per-band comment and JSON are netCDF global attributes (`<band>_comment`,
      `<band>_metadata_json`), which wcst_import doesn't copy.
    - Ingest 1 also had `\uXXXX` escapes; removing them alone (ingest 2) didn't help.
  - **Plain ASCII, with no backslashes, double quotes or `< > &` inside text.** `build_coverage.py` transliterates all
    text (– to -, ° to deg, ≥ to "at least", and so on) and refuses unsafe values; `check_coverage.py` checks this,
    and that band attributes are plain.
  - Structured values are ASCII JSON with no `true`, `false` or `null`. wcst_import may evaluate a value as a Python
    literal, and `check_coverage.py` checks that both readings agree.
  - Free notes stay out: they're development chatter.
  - The netCDF carries the same information as CF attributes: `flag_values` and `flag_meanings` per band, a `crs`
    grid mapping, and per-band `<band>_comment` and `<band>_metadata_json` as global attributes.

  | Key | Holds |
  |---|---|
  | `Title`, `Abstract`, `Status` (`test`), `Version` (build time), `Institution` | Plain text |
  | `Encoding` | Class codes per band, SNAP's usual key |
  | `Bands` | Per band: variant, method, unit, boundaries, the fixed-class rule, what High and Low mean, sources. For `hazard`: the rule, its parameters and all 27 combinations |
  | `Grid` | The grid |
  | `Source` | PDF file name and SHA-256, export time, the code version |

  The netCDF also holds `Decisions` (the PDF's decision record, without free notes) and the variant grids' SHA-256.
  They're left out of the recipe to keep the server-side metadata small (about 8 KB).
- **WMS styles**: one `after_import` hook per band. Each uses a `values` colour table in the app's palette (blue,
  yellow, vermillion; 255 transparent), in the same format as the hooks in rasdaman-ingest.

## After the ingest: `check_coverage.py --ingested`

About 20 small requests to Zeus, compared with the build:

- **DescribeCoverage**: envelope and offset vectors equal the GIPL grid; every metadata key is present and has no
  backslashes.
- **Stored array** (WCPS type-error probe): `[D0(0:1940), D1(0:2470)]`, rows then columns.
- **Class counts**: cells per class in each band equal the netCDF's.
- **Six single cells**, read by map coordinate, equal the netCDF. They're picked so that a north–south or east–west
  flip would give a different value.
- **GetCoverage**: a 9 × 9 window at Fairbanks, as GeoTIFF (compared cell by cell) and JSON (must not be empty).
- **WMS in EPSG:3338**: a 100 × 100 px map around Fairbanks must equal the netCDF pixel for pixel.
- **WMS in EPSG:3857** (reported, not pass/fail): compared with PROJ's reprojection of the netCDF.

## Map projection (2026-11-10 findings)

The first ingest looked "off against the basemap" in the front end. Tested on Zeus:

| Test | Result |
|---|---|
| WCS reads at 6 cells picked so a flip would show | All equal the netCDF |
| Class counts | Equal (e.g. hazard High 308,863) |
| WMS `crs=EPSG:3338` | 100 % of pixels equal the netCDF |
| WMS `crs=EPSG:3857` (Web Mercator) | 62 % of pixels agree with PROJ's reprojection |
| `crrel_gipl_outputs_nc_wms` (production GIPL layer) in EPSG:3857 | 57 % agree |

The coverage and its georeferencing are right, but Zeus's Web Mercator output is displaced and warped by several km.
For scale, two correct renderings half a pixel apart agree 89 %, and 3 pixels apart 71 %. The GIPL layer behaves the
same, so this is the server's reprojection, not this coverage. No simple flip, shift or EPSG:3395 mix-up explains it.

So the map should request EPSG:3338 with a 3338 basemap, as SNAP's other map apps do. Otherwise someone needs to look
at the server's reprojection to 3857.

**EPSG:4326 (2026-11-11, after the re-ingest).** A statewide 800 × 600 GetMap with `crs=EPSG:4326` came back as
600 × 800 (width and height swapped), with Alaska's shape distorted. Only 55 % of its land pixels overlap a PROJ
rendering of the netCDF. The production GIPL layer does the same, so this is the server's reprojection again.

**Always pass `styles`.** With `styles=` empty, Rasdaman uses the first style added, which is
`environmental_hazard_index_test_wildfire`, so the map shows the wildfire band. Use
`styles=environmental_hazard_index_test_hazard` for the hazard, or `_erosion` / `_permafrost` for the others.
The default style can also be set on the server (planned: hazard as the default, set by hand after each ingest).

**GetCoverage output (ingest 3, 2026-11-11).**
- **JSON** works. A point is one string, bands separated by spaces in band order: `"1 0 0 0"`. A window is rows
  (north to south) of such strings. A band with no data reads `null` inside the string (`"2 1 null 1"`), and a cell
  with no data in any band reads `"null null null null"`, not 255. So split on spaces and treat `null` as no data.
- **GeoTIFF** comes back transposed: the values are right, but rows hold X while the file's georeferencing says rows
  hold Y. `crrel_gipl_outputs_nc_wcs` does the same (9 × 9 test), so this is Zeus's GeoTIFF output for coverages
  stored Y first. SNAP's CMIP6 prep scripts transpose their data to X first before ingest; doing that here would
  likely fix GeoTIFF (not yet tried).

**Front-end gotcha:** a WCPS point read of all bands at a cell where one band is null prints garbled. For example,
`$c[X(560708.291), Y(1550979.751)]` returns `{ 1, 2, NULL, 255 }` for wildfire 1, erosion 2, permafrost null,
hazard 1: the hazard value is lost. Read one band per query (`(short) $c.hazard[...]`), or use GetCoverage, which
works once the metadata is clean.

Before the real ingest, run `wcst_import.sh ingest.json --analyze` (dry run) on the server. Fairbanks (downtown) is
row 708, col 1277, cell centre X 297708.291, Y 1666979.751. It should read wildfire 2, erosion 1, permafrost 0
(outside the ESA permafrost zone, so fixed Low) and hazard 1.
