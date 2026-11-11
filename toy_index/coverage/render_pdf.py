"""Test helper: make the workbench's "Download PDF" file without a browser click, from a saved team record.

  python -I toy_index/coverage/render_pdf.py <team_record_dir> <out.pdf>

<team_record_dir> holds the page database as saved by the ArtifactData tool (decisions/<key>.json, notes/<id>.json).
Serves the local workbench build (toy_index/app/build/hosted/_local.html, identical to the published page), loads it
in headless Firefox, sets the page's team record to the saved one and calls the page's own buildPdf(), so the PDF is
the one the app would give for those decisions. Only for testing the coverage pipeline: the real input is the PDF a
person downloads from the app. Needs the WebDriver BiDi harness .claude/scratch/bidi.py and internet (the page loads
jsPDF from cdnjs).
"""
import base64
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HOSTED = REPO / "toy_index/app/build/hosted"
BIDI = REPO / ".claude/scratch/bidi.py"
PORT = 8767


def load_dir(d):
    return {p.stem: json.loads(p.read_text()) for p in sorted(d.glob("*.json"))} if d.is_dir() else {}


def main(record, out):
    record, out = Path(record), Path(out)
    team, notes = load_dir(record / "decisions"), load_dir(record / "notes")
    js = (f"(async () => {{ TEAM = {json.dumps(team)}; NOTES = {json.dumps(notes)}; teamChanged(); "
          "const d = await buildPdf(); return 'PDFDATA:' + d.output('datauristring'); })()")
    srv = subprocess.Popen([sys.executable, "-I", "-m", "http.server", str(PORT), "--bind", "127.0.0.1",
                            "--directory", str(HOSTED)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(3)
        r = subprocess.run([sys.executable, "-I", str(BIDI), f"http://127.0.0.1:{PORT}/_local.html#summary",
                            "--wait", "typeof landN !== 'undefined' && landN > 0 && !document.body.classList.contains('loading')",
                            "--eval", js, "--timeout", "120"], capture_output=True, text=True, timeout=300)
    finally:
        srv.terminate()
    line = next((x for x in r.stdout.splitlines() if x.startswith("PDFDATA:")), None)
    if not line:
        sys.exit(f"no PDF from the page:\n{r.stdout[-3000:]}\n{r.stderr[-2000:]}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(line.split("base64,", 1)[1]))
    print(f"wrote {out} ({out.stat().st_size / 1e6:.2f} MB)")


if __name__ == "__main__":
    main(*sys.argv[1:3])
