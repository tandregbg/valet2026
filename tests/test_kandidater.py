"""CR-002: kandidatgenerering.

VIKTIGT: dessa tester far ALDRIG kora kandidater.py mot projektets
datafiler. Skriptet skriver over kandidater.jsonl och nollstaller darmed
all granskningsstatus - det hande i praktiken och raderade 122 granskade
rader. Generering testas i en temporar katalog i stallet.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def las():
    f = ROOT / "domains" / "kandidater.jsonl"
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_generering_fungerar_i_sandlada():
    """Kor kandidater.py mot en kopia, aldrig mot riktiga filer."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "domains").mkdir()
        (tmp / "manifest").mkdir()
        for f in ["taxonomi.yaml", "forslag.jsonl", "kandidater.py"]:
            shutil.copy(ROOT / "domains" / f, tmp / "domains" / f)
        r = subprocess.run([sys.executable, str(tmp / "domains" / "kandidater.py")],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        ut = tmp / "domains" / "kandidater.jsonl"
        assert ut.exists()
        rader = [json.loads(l) for l in ut.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(rader) > 100


def test_varje_kandidat_har_originaltext():
    """Sparbarhet bakat ar ett guardrail - far aldrig tappas."""
    for k in las():
        assert k["originaltext"], f"{k['id']} saknar originaltext"
        assert k["kallor"], f"{k['id']} saknar kallhanvisning"


def test_svag_traff_markeras():
    assert any(k["svag_traff"] for k in las()), "svag_traff satts aldrig"


def test_granskningsstatus_bevaras():
    """Regressionstest: granskningen far inte forsvinna. Den raderades en
    gang av ett test som korde om genereringen."""
    rader = las()
    godkanda = [k for k in rader if k["status"] == "godkand"]
    assert godkanda, "inga godkanda kandidater - har granskningen nollstallts?"
    for k in godkanda:
        assert k["granskad_av"], f"{k['id']} godkand utan granskare"
        assert k.get("slutlig_text"), f"{k['id']} godkand utan text"


def test_pastaenden_speglar_godkanda():
    """pastaenden.jsonl ska innehalla exakt de godkanda kandidaterna."""
    godkanda = [k for k in las() if k["status"] == "godkand"]
    pf = ROOT / "domains" / "pastaenden.jsonl"
    past = [json.loads(l) for l in pf.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(past) == len(godkanda), \
        f"{len(past)} påståenden men {len(godkanda)} godkända kandidater"


def test_otillgangliga_domaner_stammer():
    """Filen ska lista exakt de domaner som har under 10 pastaenden."""
    from collections import Counter
    pf = ROOT / "domains" / "pastaenden.jsonl"
    past = [json.loads(l) for l in pf.read_text(encoding="utf-8").splitlines() if l.strip()]
    c = Counter(p["doman"] for p in past)

    import yaml
    tax = yaml.safe_load((ROOT / "domains" / "taxonomi.yaml").read_text(encoding="utf-8"))
    alla = [d["id"] for d in tax["domaner"]]
    forvantat = sorted(d for d in alla if c.get(d, 0) < 10)

    faktiskt = json.loads((ROOT / "domains" / "otillgangliga_domaner.json").read_text(encoding="utf-8"))
    assert sorted(faktiskt) == forvantat, \
        f"otillgangliga_domaner.json är ur synk: {faktiskt} != {forvantat}"
