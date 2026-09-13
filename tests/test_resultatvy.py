"""CR-004: resultatvy. Guardrail-tester - procent far aldrig visas naken."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import app as A          # noqa: E402
import kompass as K      # noqa: E402

A.app.config["SECRET_KEY"] = "test"
VALDA = ["klimat-energi-miljo", "skola-utbildning", "valfard-halsa"]


def _omgang(client, varde=5):
    f, _ = K.valj_fragor(VALDA)
    svar = [{"pastaende_id": x["id"], "varde": varde} for x in f]
    client.post("/kompass/svar", json={"svar": svar, "valda_domaner": VALDA})
    return f


def test_resultat_visar_tackning():
    c = A.app.test_client()
    _omgang(c)
    body = c.get("/kompass/resultat").data.decode()
    assert "belägg för" in body, "täckningssiffran är obligatorisk"


def test_forbehall_syns():
    c = A.app.test_client()
    _omgang(c)
    body = c.get("/kompass/resultat").data.decode()
    assert "ingång till materialet" in body
    assert "mäter inte avstånd" in body


def test_utan_svar_omdirigeras():
    c = A.app.test_client()
    r = c.get("/kompass/resultat")
    assert r.status_code == 302


def test_kallvy_har_originaltext():
    """Sparbarhet till kalltext ar ett guardrail."""
    c = A.app.test_client()
    _omgang(c)
    body = c.get("/kompass/resultat").data.decode()
    import re
    m = re.search(r"/kompass/resultat/(\w+)", body)
    assert m
    detalj = c.get(f"/kompass/resultat/{m.group(1)}").data.decode()
    assert "Originaltext ur källan" in detalj


def test_oenighet_visas():
    """Ett verktyg som bara visar overensstammelse ar en bekraftelsemaskin."""
    c = A.app.test_client()
    _omgang(c, varde=1)          # ta avstand fran allt
    body = c.get("/kompass/resultat").data.decode()
    import re
    m = re.search(r"/kompass/resultat/(\w+)", body)
    detalj = c.get(f"/kompass/resultat/{m.group(1)}").data.decode()
    assert "Där ni skiljer er åt" in detalj
