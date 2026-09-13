"""CR-001: fragemotor."""
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import kompass as K  # noqa: E402

VALDA3 = ["klimat-energi-miljo", "skola-utbildning", "valfard-halsa"]


def test_femtio_fragor_vid_tre_domaner():
    f, _ = K.valj_fragor(VALDA3)
    assert len(f) == K.ANTAL_FRAGOR


def test_fordelning_trettio_tjugo():
    f, _ = K.valj_fragor(VALDA3)
    c = Counter(x["doman"] for x in f)
    riktade = sum(c[d] for d in VALDA3)
    assert riktade == 30
    assert len(f) - riktade == 20


def test_en_doman_ger_tio_riktade():
    f, _ = K.valj_fragor(["ekonomi-skatt"])
    c = Counter(x["doman"] for x in f)
    assert c["ekonomi-skatt"] == K.PER_VALD_DOMAN
    assert len(f) == K.ANTAL_FRAGOR


def test_deterministiskt_urval():
    a, _ = K.valj_fragor(VALDA3)
    b, _ = K.valj_fragor(VALDA3)
    assert [x["id"] for x in a] == [x["id"] for x in b]


def test_inga_dubbletter():
    f, _ = K.valj_fragor(VALDA3)
    ids = [x["id"] for x in f]
    assert len(ids) == len(set(ids))


def test_otillrackliga_domaner_ej_valbara():
    """Bostad och landsbygd har for fa pastaenden - far inte kunna valjas."""
    import yaml
    tax = yaml.safe_load((ROOT / "domains" / "taxonomi.yaml").read_text(encoding="utf-8"))
    domaner = K.tillgangliga_domaner(tax)
    for d in domaner:
        if d["antal"] < K.PER_VALD_DOMAN:
            assert not d["valbar"], f"{d['id']} har {d['antal']} men är valbar"


def test_tom_bank_ger_varning():
    """Motorn ska varna, inte krascha, nar banken saknas."""
    orig = K.las_pastaenden
    K.las_pastaenden = lambda: []
    try:
        f, v = K.valj_fragor(VALDA3)
        assert f == []
        assert v
    finally:
        K.las_pastaenden = orig
