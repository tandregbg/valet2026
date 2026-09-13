#!/usr/bin/env python3
"""
CR-001: valkompassens domanval och fragemotor.

Flode: valj max 3 domaner -> 50 pastaenden att gradera 1-5 -> resultat (CR-004).

Fordelning enligt CR-001: 10 fragor per vald doman, resten blandade fran
ovriga domaner. De blandade finns for att resultatet inte ska bli
sjalvuppfyllande - valjer man bara klimat och bara far klimatfragor blir
matchningen cirkular.
"""
import hashlib
import json
import random
from collections import defaultdict
from pathlib import Path

from flask import (Blueprint, jsonify, redirect, render_template, request,
                   session, url_for)

ROOT = Path(__file__).resolve().parent.parent
DOMAINS = ROOT / "domains"

bp = Blueprint("kompass", __name__)

ANTAL_FRAGOR = 50
PER_VALD_DOMAN = 10
MAX_VALDA = 3

SKALA = [
    (1, "Tar helt avstånd"),
    (2, "Tveksam"),
    (3, "Neutral / kan fungera"),
    (4, "Positiv"),
    (5, "Instämmer helt"),
]


def las_pastaenden():
    f = DOMAINS / "pastaenden.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def otillgangliga():
    f = DOMAINS / "otillgangliga_domaner.json"
    if not f.exists():
        return []
    return json.loads(f.read_text(encoding="utf-8"))


def tillgangliga_domaner(tax):
    """En doman kan valjas bara om den har minst PER_VALD_DOMAN godkanda
    pastaenden. Att markera den otillganglig ar arligare an att fylla ut
    med daliga pastaenden (CR-002)."""
    pastaenden = las_pastaenden()
    per_doman = defaultdict(int)
    for p in pastaenden:
        per_doman[p["doman"]] += 1
    blockerade = set(otillgangliga())

    ut = []
    for d in tax["domaner"]:
        n = per_doman.get(d["id"], 0)
        ut.append({
            "id": d["id"], "namn": d["namn"], "farg": d["farg"],
            "antal": n,
            "valbar": n >= PER_VALD_DOMAN and d["id"] not in blockerade,
        })
    return ut


def valj_fragor(valda_domaner, seed=None):
    """Deterministiskt urval: samma domanval ger samma fragor. Viktigt for
    felsokning och for att tva personer ska kunna jamfora resultat.

    Returnerar (fragor, varningar). Varningar nar en doman inte kunde
    leverera sin kvot - da fylls det ut, och det ska synas."""
    pastaenden = las_pastaenden()
    if not pastaenden:
        return [], ["Påståendebanken är tom. Granska kandidater först."]

    per_doman = defaultdict(list)
    for p in pastaenden:
        per_doman[p["doman"]].append(p)

    if seed is None:
        seed = hashlib.sha256("|".join(sorted(valda_domaner)).encode()).hexdigest()
    rnd = random.Random(seed)

    valda, varningar = [], []
    anvanda = set()

    # Riktade fragor fran valda domaner
    for d in valda_domaner:
        pool = [p for p in per_doman.get(d, []) if p["id"] not in anvanda]
        rnd.shuffle(pool)
        tagna = pool[:PER_VALD_DOMAN]
        if len(tagna) < PER_VALD_DOMAN:
            varningar.append(
                f"{d}: bara {len(tagna)} påståenden tillgängliga av {PER_VALD_DOMAN}")
        for p in tagna:
            anvanda.add(p["id"])
        valda.extend(tagna)

    # Blandade fran ovriga domaner
    ovriga = [p for p in pastaenden
              if p["doman"] not in valda_domaner and p["id"] not in anvanda]
    rnd.shuffle(ovriga)
    behovs = ANTAL_FRAGOR - len(valda)
    blandade = ovriga[:behovs]
    if len(blandade) < behovs:
        # Fyll ut med det som finns kvar oavsett doman hellre an att
        # leverera farre an 50
        rest = [p for p in pastaenden if p["id"] not in anvanda
                and p["id"] not in {b["id"] for b in blandade}]
        rnd.shuffle(rest)
        blandade.extend(rest[:behovs - len(blandade)])
        varningar.append(
            f"Kunde bara fylla {len(valda) + len(blandade)} av {ANTAL_FRAGOR} frågor")

    for p in blandade:
        anvanda.add(p["id"])
    valda.extend(blandade)

    rnd.shuffle(valda)
    return valda, varningar


@bp.route("/kompass")
def start():
    from app import TAX
    domaner = tillgangliga_domaner(TAX)
    valbara = sum(1 for d in domaner if d["valbar"])
    return render_template(
        "kompass_start.html", domaner=domaner, valbara=valbara,
        max_valda=MAX_VALDA, antal_fragor=ANTAL_FRAGOR,
        pastaenden_totalt=len(las_pastaenden()),
    )


@bp.route("/kompass/fragor")
def fragor():
    valda = [d for d in request.args.getlist("doman") if d][:MAX_VALDA]
    if not valda:
        return redirect(url_for("kompass.start"))

    fragor_, varningar = valj_fragor(valda)
    if not fragor_:
        return render_template("kompass_tom.html", varningar=varningar)

    session["kompass_valda"] = valda
    session["kompass_fragor"] = [f["id"] for f in fragor_]

    return render_template(
        "kompass_fragor.html", fragor=fragor_, valda=valda,
        skala=SKALA, varningar=varningar,
    )


@bp.route("/kompass/svar", methods=["POST"])
def svar():
    """Tar emot svaren och lamnar over till CR-004:s resultatvy."""
    data = request.get_json(silent=True) or {}
    session["kompass_svar"] = data.get("svar", [])
    session["kompass_valda"] = data.get("valda_domaner", [])
    return jsonify({"ok": True, "next": url_for("kompass.resultat")})


@bp.route("/kompass/resultat")
def resultat():
    """Implementeras i CR-004. Placeholder tills dess."""
    return redirect(url_for("kompass.start"))
