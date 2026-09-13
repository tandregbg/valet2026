#!/usr/bin/env python3
"""
CR-003: matchningsalgoritm.

Beraknar overensstammelse mellan anvandarens svar och vad kallorna faktiskt
foreslar.

KARNPRINCIP: franvaro far ALDRIG tolkas som motstand. Om ett dokument saknar
ett forslag kan det betyda motstand, lag prioritet, eller att extraktionen
missade det (2-21% bortfall, 40% svaga traffar). Algoritmen kan inte skilja
dem at. Darfor ar 'saknas' ett eget tillstand som utesluts ur berakningen -
aldrig 0, som skulle dra ned matchningen.

Konsekvens: algoritmen mater overensstammelse dar det finns belagg, aldrig
avstand baserat pa tystnad.
"""
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOMAINS = ROOT / "domains"

MIN_TACKNING = 15          # CR-003 beslut 2: under detta gramarkeras kallan


def las_pastaenden():
    f = DOMAINS / "pastaenden.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def _dedup_nyckel(p):
    """CR-003 beslut 4: skyddsnat om CR-002:s dubblettfilter missar nagot."""
    t = unicodedata.normalize("NFKD", p["text"].lower())
    t = re.sub(r"[^\w\s]", " ", t)
    ord_ = sorted({o for o in t.split() if len(o) > 3})[:10]
    return (p["subdoman"], " ".join(ord_))


def normalisera_svar(varde):
    """1-5 -> -1..+1. En trea ger 0: neutralt svar paverkar inte matchningen."""
    return (varde - 3) / 2


def berakna(svar, pastaenden=None):
    """svar: lista av {pastaende_id, varde, hoppad?}

    Returnerar lista per kalla, sorterad fallande pa matchning:
      {parti, matchning (-1..1), procent (0..100), tackning, av_totalt,
       under_troskel, traffar[]}
    """
    pastaenden = pastaenden if pastaenden is not None else las_pastaenden()

    # Deduplicera pastaenden fore berakning
    sedda, rena = set(), []
    for p in pastaenden:
        n = _dedup_nyckel(p)
        if n not in sedda:
            sedda.add(n)
            rena.append(p)
    index = {p["id"]: p for p in rena}

    # Bara besvarade fragor raknas. Overhoppade utesluts helt (CR-001).
    besvarade = [s for s in svar
                 if not s.get("hoppad") and s.get("varde") is not None
                 and s["pastaende_id"] in index]

    per_kalla = defaultdict(lambda: {"summa": 0.0, "n": 0, "traffar": []})

    for s in besvarade:
        p = index[s["pastaende_id"]]
        anvandarvarde = normalisera_svar(s["varde"])
        for kalla in p["kallor"]:
            hallning = kalla.get("hallning", "for")
            if hallning == "saknas":
                continue                      # utesluts, blir aldrig 0
            riktning = 1 if hallning == "for" else -1
            poang = anvandarvarde * riktning
            d = per_kalla[kalla["parti"]]
            d["summa"] += poang
            d["n"] += 1
            d["traffar"].append({
                "pastaende_id": p["id"],
                "text": p["text"],
                "doman": p["doman"],
                "svar": s["varde"],
                "hallning": hallning,
                "poang": round(poang, 3),
                "originaltext": p.get("originaltext"),
                "forslag_id": kalla.get("forslag_id"),
                "svag_traff": p.get("svag_traff", False),
            })

    ut = []
    for parti, d in per_kalla.items():
        if d["n"] == 0:
            continue
        # Normalisering mot antal belagg, inte summa - annars ger langre
        # dokument hogre poang bara pa volym
        matchning = d["summa"] / d["n"]
        ut.append({
            "parti": parti,
            "matchning": round(matchning, 4),
            "procent": round((matchning + 1) / 2 * 100, 1),
            "tackning": d["n"],
            "av_totalt": len(besvarade),
            "under_troskel": d["n"] < MIN_TACKNING,
            "traffar": sorted(d["traffar"], key=lambda t: -t["poang"]),
        })

    ut.sort(key=lambda x: -x["matchning"])
    return ut


def per_doman(kallresultat):
    """Bryter ned en kallas traffar per doman, for CR-004 niva 2."""
    grupper = defaultdict(lambda: {"summa": 0.0, "n": 0, "traffar": []})
    for t in kallresultat["traffar"]:
        g = grupper[t["doman"]]
        g["summa"] += t["poang"]
        g["n"] += 1
        g["traffar"].append(t)

    ut = []
    for doman, g in grupper.items():
        m = g["summa"] / g["n"] if g["n"] else 0
        ut.append({
            "doman": doman,
            "matchning": round(m, 4),
            "procent": round((m + 1) / 2 * 100, 1),
            "n": g["n"],
            "traffar": sorted(g["traffar"], key=lambda t: -t["poang"]),
        })
    ut.sort(key=lambda x: -x["n"])
    return ut


def oenighet(kallresultat, grans=-0.25):
    """Dar anvandaren och kallan drar at olika hall. Ett verktyg som bara
    visar overensstammelse ar en bekraftelsemaskin."""
    return [t for t in kallresultat["traffar"] if t["poang"] <= grans]
