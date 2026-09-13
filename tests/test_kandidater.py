"""CR-002: kandidatgenerering."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "domains"))


def las():
    f = ROOT / "domains" / "kandidater.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_kandidater_genereras():
    subprocess.run([sys.executable, str(ROOT / "domains" / "kandidater.py")],
                   check=True, capture_output=True)
    assert len(las()) > 100


def test_varje_kandidat_har_originaltext():
    """Sparbarhet bakat ar ett guardrail - far aldrig tappas."""
    for k in las():
        assert k["originaltext"], f"{k['id']} saknar originaltext"
        assert k["kallor"], f"{k['id']} saknar kallhanvisning"


def test_svag_traff_markeras():
    rader = las()
    assert any(k["svag_traff"] for k in rader), "svag_traff satts aldrig"


def test_ingen_kandidat_ar_godkand_fran_start():
    """Manniskan ar grinden. Ingenting slinker igenom automatiskt."""
    for k in las():
        assert k["status"] == "kandidat"
        assert k["granskad_av"] == []


def test_otillgangliga_domaner_skrivs():
    f = ROOT / "domains" / "otillgangliga_domaner.json"
    assert f.exists()
    json.loads(f.read_text(encoding="utf-8"))
