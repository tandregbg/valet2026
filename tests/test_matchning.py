"""CR-003: matchningsalgoritm. Testfallen kommer fran CR:ns Testing Plan."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

import matchning as M  # noqa: E402


def pastaende(pid, kallor, doman="x", subdoman=None, text=None):
    return {"id": pid, "text": text or f"Påstående {pid}", "doman": doman,
            "subdoman": subdoman or f"sub-{pid}",
            "kallor": [{"parti": p, "hallning": h, "forslag_id": f"{p}-1"}
                       for p, h in kallor],
            "originaltext": "orig", "svag_traff": False}


def test_franvaro_drar_inte_ned():
    """Karnprincipen: en kalla utan belagg ska inte straffas."""
    past = [pastaende(f"P-{i}", [("A", "for")] if i < 10 else [("B", "for")])
            for i in range(50)]
    svar = [{"pastaende_id": f"P-{i}", "varde": 5} for i in range(50)]
    r = M.berakna(svar, past)
    a = next(x for x in r if x["parti"] == "A")
    assert a["procent"] == 100.0, "belägg-träffar ska ge full match"
    assert a["tackning"] == 10, "täckningen ska spegla antal belägg"
    assert a["under_troskel"] is True


def test_volymneutralitet():
    """Tva kallor med identisk hallning far samma procent oavsett volym."""
    past = ([pastaende(f"P-{i}", [("A", "for"), ("B", "for")]) for i in range(10)]
            + [pastaende(f"Q-{i}", [("B", "for")]) for i in range(10)])
    svar = ([{"pastaende_id": f"P-{i}", "varde": 5} for i in range(10)]
            + [{"pastaende_id": f"Q-{i}", "varde": 5} for i in range(10)])
    r = M.berakna(svar, past)
    a = next(x for x in r if x["parti"] == "A")
    b = next(x for x in r if x["parti"] == "B")
    assert a["procent"] == b["procent"]
    assert b["tackning"] == 2 * a["tackning"]


def test_neutrala_svar_ger_noll():
    """Alla treor -> 50% (mittpunkten), inte 100."""
    past = [pastaende(f"P-{i}", [("A", "for")]) for i in range(20)]
    svar = [{"pastaende_id": f"P-{i}", "varde": 3} for i in range(20)]
    r = M.berakna(svar, past)
    assert r[0]["matchning"] == 0.0
    assert r[0]["procent"] == 50.0


def test_overhoppade_utesluts():
    past = [pastaende(f"P-{i}", [("A", "for")]) for i in range(20)]
    svar = ([{"pastaende_id": f"P-{i}", "varde": 5} for i in range(10)]
            + [{"pastaende_id": f"P-{i}", "varde": None, "hoppad": True}
               for i in range(10, 20)])
    r = M.berakna(svar, past)
    assert r[0]["tackning"] == 10
    assert r[0]["av_totalt"] == 10


def test_saknas_blir_aldrig_noll():
    """Explicit: hallning 'saknas' utesluts, den far inte rakna som neutral."""
    past = [pastaende("P-1", [("A", "for"), ("B", "saknas")])]
    svar = [{"pastaende_id": "P-1", "varde": 5}]
    r = M.berakna(svar, past)
    assert [x["parti"] for x in r] == ["A"], "B har inget belägg och ska utebli"


def test_emot_vander_riktning():
    past = [pastaende("P-1", [("A", "for"), ("B", "emot")])]
    svar = [{"pastaende_id": "P-1", "varde": 5}]
    r = M.berakna(svar, past)
    a = next(x for x in r if x["parti"] == "A")
    b = next(x for x in r if x["parti"] == "B")
    assert a["matchning"] == 1.0
    assert b["matchning"] == -1.0


def test_dubbletter_dedupliceras():
    past = [pastaende("P-1", [("A", "for")], subdoman="s", text="Skatten bör sänkas nu"),
            pastaende("P-2", [("A", "for")], subdoman="s", text="Skatten bör sänkas nu")]
    svar = [{"pastaende_id": "P-1", "varde": 5}, {"pastaende_id": "P-2", "varde": 5}]
    r = M.berakna(svar, past)
    assert r[0]["tackning"] == 1, "samma sakfråga får inte räknas dubbelt"


def test_oenighet_fangas():
    past = [pastaende("P-1", [("A", "for")]), pastaende("P-2", [("A", "for")])]
    svar = [{"pastaende_id": "P-1", "varde": 5}, {"pastaende_id": "P-2", "varde": 1}]
    r = M.berakna(svar, past)
    o = M.oenighet(r[0])
    assert len(o) == 1
    assert o[0]["pastaende_id"] == "P-2"
