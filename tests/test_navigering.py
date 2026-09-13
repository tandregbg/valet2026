"""CR-006: navigering. Varje publik vy ska ga att na fran menyn."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import app as A  # noqa: E402


def meny():
    return A.app.test_client().get("/").data.decode()


def test_alla_vyer_i_menyn():
    h = meny()
    for t in ["Täckning", "Konfliktaxlar", "Inramning",
              "Valkompass", "Granskning", "Om &amp; källor"]:
        assert t in h, f"{t} saknas i menyn"


def test_menylankar_svarar():
    c = A.app.test_client()
    for rt in ["/", "/axlar", "/inramning", "/kompass", "/granskning", "/om"]:
        assert c.get(rt).status_code == 200, f"{rt} svarar inte"


def test_aktiv_markering():
    c = A.app.test_client()
    for rt in ["/", "/axlar", "/inramning", "/kompass", "/granskning", "/om"]:
        assert 'class="aktiv"' in c.get(rt).data.decode() or "aktiv" in c.get(rt).data.decode(), \
            f"{rt} markerar inte aktiv vy"


def test_sidfoten_beskriver_lagen_korrekt():
    """Pastaendena ar granskade - foten far inte saga 'oreviderad'."""
    h = meny()
    assert "oreviderad" not in h
    assert "redaktionellt granskade" in h
