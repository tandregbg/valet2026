#!/usr/bin/env python3
"""
CR-002 steg 1: kandidatgenerering.

Filtrerar forslag.jsonl till kandidater som kan bli graderbara pastaenden,
och genererar ett forslag till omskrivning som UTGANGSPUNKT for manuell
granskning - aldrig som fardigt pastaende.

Filternivan ar beslutad 2026-09-13: traffsakerhet=1 slapps in, eftersom det
strama filtret lamnade 8 av 12 domaner under CR-001:s minimum. Priset ar att
underlaget innehaller de minst tillforlitliga raderna. Dessa markeras med
svag_traff=true och MASTE granskas manuellt.
"""
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOMAINS = ROOT / "domains"

MAX_ORD = 60
MIN_PER_DOMAN = 10          # CR-001:s krav

# Fraser som avslojar avsandaren eller bar vardering. Tas bort i utkastet,
# men granskaren ser alltid originalet bredvid.
ROSTMARKORER = re.compile(
    r"\b(vi vill|vi föreslår|vi ska|vi kommer att|vi tycker|vårt förslag|"
    r"[a-zåäö]+erna vill|partiet vill|vi anser|vi kräver|vi lovar)\b",
    re.IGNORECASE)

VARDEORD = re.compile(
    r"\b(rättvis\w*|ansvarsfull\w*|kraftfull\w*|modig\w*|historisk\w*|"
    r"katastrofal\w*|misslyckad\w*|skandalös\w*|orimlig\w*)\b",
    re.IGNORECASE)


def normalisera_for_dubblett(text):
    """Nyckel for dubblettdetektering over kallor."""
    t = unicodedata.normalize("NFKD", text.lower())
    t = re.sub(r"[^\w\s]", " ", t)
    ord_ = [o for o in t.split() if len(o) > 3]
    return " ".join(sorted(set(ord_))[:12])


def forsta_meningen(text):
    """Forslagets karna star nastan alltid i forsta meningen; resten ar
    motivering. Se CR-002 problemanalys."""
    m = re.split(r"(?<=[.!?])\s+", text.strip())
    return m[0] if m else text


def utkast(text):
    """Genererar ett forslag till pastaende. Heuristisk och medvetet
    konservativ - granskaren forvantas skriva om de flesta."""
    t = forsta_meningen(text)
    t = ROSTMARKORER.sub("", t)
    t = VARDEORD.sub("", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" ,.;:-–—")
    if not t:
        return None
    # Imperativ -> pastaende: "Öka antalet läkare" -> "Antalet läkare bör öka"
    if len(t) > 1:
        t = t[0].upper() + t[1:]
    if not t.endswith("."):
        t += "."
    return t


def generera():
    rader = [json.loads(l) for l in
             (DOMAINS / "forslag.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]

    # Filter enligt CR-002 (beslutad niva)
    kandidater = [
        r for r in rader
        if r["typ"] in ("reform", "mal")
        and len(r["text"].split()) <= MAX_ORD
    ]

    # Slå ihop dubbletter over kallor - samma sakfraga fran flera avsandare
    grupper = defaultdict(list)
    for r in kandidater:
        nyckel = (r["subdoman"], normalisera_for_dubblett(r["text"]))
        grupper[nyckel].append(r)

    ut = []
    for i, ((subdoman, _), grupp) in enumerate(sorted(grupper.items()), start=1):
        forsta = grupp[0]
        text = utkast(forsta["text"])
        if not text or len(text.split()) < 3:
            continue
        svag = any(r["traffsakerhet"] <= 1 for r in grupp)
        ut.append({
            "id": f"K-{i:04d}",
            "utkast": text,
            "doman": forsta["doman"],
            "subdoman": subdoman,
            "svag_traff": svag,
            "kallor": [
                {"parti": r["parti"], "forslag_id": r["id"], "hallning": "for"}
                for r in grupp
            ],
            "originaltext": forsta["text"],
            "status": "kandidat",        # kandidat | godkand | forkastad
            "granskad_av": [],
            "granskad_datum": None,
            "anmarkning": None,
        })

    (DOMAINS / "kandidater.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in ut) + "\n",
        encoding="utf-8")

    per_doman = Counter(r["doman"] for r in ut)
    svaga = sum(1 for r in ut if r["svag_traff"])
    otillrackliga = sorted(d for d, n in per_doman.items() if n < MIN_PER_DOMAN)

    print(f"Skrev {len(ut)} kandidater till domains/kandidater.jsonl")
    print(f"Varav svag träff (kräver manuell granskning): {svaga}\n")
    print(f"{'Domän':<28} {'Antal':>6}")
    for d, n in sorted(per_doman.items(), key=lambda x: -x[1]):
        flagga = "  UNDER MINIMUM" if n < MIN_PER_DOMAN else ""
        print(f"{d:<28} {n:>6}{flagga}")

    if otillrackliga:
        print(f"\nDomäner under {MIN_PER_DOMAN} kandidater: {', '.join(otillrackliga)}")
        print("Dessa markeras som otillgängliga för domänval (CR-001).")
        (DOMAINS / "otillgangliga_domaner.json").write_text(
            json.dumps(otillrackliga, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        (DOMAINS / "otillgangliga_domaner.json").write_text("[]", encoding="utf-8")

    return ut


if __name__ == "__main__":
    generera()
