"""CR-005: om-sidan. Kallor och siffror ska harledas ur data, ej hardkodas."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import app as A  # noqa: E402


def hamta():
    return A.app.test_client().get("/om").data.decode()


def test_alla_sektioner():
    h = hamta()
    for sid in ["kallor", "process", "varfor-inte-chatgpt",
                "arbetsdelning", "data", "brister"]:
        assert f'id="{sid}"' in h, f"sektion {sid} saknas"


def test_varje_kalla_har_lank_och_checksumma():
    import yaml
    k = yaml.safe_load((ROOT / "domains" / "kallor.yaml").read_text(encoding="utf-8"))
    h = hamta()
    for d in k["dokument"]:
        assert d["utgivare"] in h
        assert d["url"] in h, f"{d['kod']} saknar länk"
        assert d["sha256"][:16] in h, f"{d['kod']} saknar checksumma"


def test_siffror_harleds_ur_data():
    """Om banken andras ska sidan folja med - inga hardkodade tal."""
    import json
    h = hamta()
    pf = ROOT / "domains" / "pastaenden.jsonl"
    n = len([l for l in pf.read_text(encoding="utf-8").splitlines() if l.strip()])
    assert f"{n} granskade påståenden" in h


def test_arbetsdelningen_skiljer_fyra_lager():
    h = hamta()
    for t in ["Rent innehåll", "AI-assisterad kod", "Språkmodell",
              "Mänskligt omdöme"]:
        assert t in h


def test_isk_felet_dokumenteras():
    """Det konkreta exemplet pa varfor granskning behovs far inte tappas."""
    h = hamta()
    assert "investeringssparkonto" in h
    assert "214 av 221" in h
