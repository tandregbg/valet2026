#!/usr/bin/env python3
"""
Flask-app som visualiserar domanstrukturen i valmanifesten 2026.

Fyra vyer, var och en svarar pa en distinkt fraga:
  /            Matris: vilka domaner tacker partierna, och hur mycket?
  /doman/<id>  Djupdykning: vad sager partierna faktiskt inom en doman?
  /axlar       Konfliktaxlar: monster som skar tvars over domaner
  /inramning   Partiets egen rubrik vs sakfraga - retorik vs innehall

Data laddas en gang vid start fran domains/forslag.jsonl.
"""
from collections import Counter, defaultdict
from pathlib import Path
import json

import yaml
from flask import Flask, abort, render_template, request

ROOT = Path(__file__).resolve().parent.parent
app = Flask(__name__)

PARTIORDNING = ["V", "S", "MP", "C", "L", "KD", "M", "SD"]   # vanster -> hoger
PARTIFARGER = {
    "V": "#af0000", "S": "#e8112d", "MP": "#83cf39", "C": "#009933",
    "L": "#006ab3", "KD": "#000077", "M": "#52bdec", "SD": "#ddaa00",
}


def ladda():
    tax = yaml.safe_load((ROOT / "domains" / "taxonomi.yaml").read_text(encoding="utf-8"))
    rader = [json.loads(l) for l in
             (ROOT / "domains" / "forslag.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return tax, rader


TAX, RADER = ladda()
DOMAN_NAMN = {d["id"]: d["namn"] for d in TAX["domaner"]}
DOMAN_FARG = {d["id"]: d["farg"] for d in TAX["domaner"]}
SUB_NAMN = {s["id"]: s["namn"] for d in TAX["domaner"] for s in d["subdomaner"]}
SUB_TILL_DOM = {s["id"]: d["id"] for d in TAX["domaner"] for s in d["subdomaner"]}
AXEL_NAMN = {a["id"]: a for a in TAX["axlar"]}
PARTI_NAMN = {r["parti"]: r["parti_namn"] for r in RADER}


def partier():
    return [p for p in PARTIORDNING if p in PARTI_NAMN]


@app.route("/")
def index():
    """Tackningsmatris. Cellvarde = antal forslag. Tomma celler ar poangen:
    de visar var ett parti ar tyst."""
    matris = defaultdict(lambda: defaultdict(int))
    for r in RADER:
        matris[r["doman"]][r["parti"]] += 1

    ps = partier()
    totalt_parti = {p: sum(1 for r in RADER if r["parti"] == p) for p in ps}

    # Farglaggningen bygger pa ANDEL av partiets eget manifest, inte pa
    # antal. Annars matter fargen bara dokumentlangd: C har 592 forslag
    # och V 100, sa C hade blivit mork nastan overallt utan att det sager
    # nagot om prioritering. Skalan normaliseras mot hogsta andel i hela
    # matrisen sa att celler ar jamforbara aven mellan rader.
    alla_andelar = [
        matris[d["id"]][p] / totalt_parti[p] * 100
        for d in TAX["domaner"] for p in ps if totalt_parti[p]
    ]
    andel_max = max(alla_andelar) if alla_andelar else 1

    rader_ut = []
    for d in TAX["domaner"]:
        did = d["id"]
        celler = []
        for p in ps:
            n = matris[did][p]
            andel = (n / totalt_parti[p] * 100) if totalt_parti[p] else 0
            celler.append({
                "parti": p, "antal": n, "andel": round(andel, 1),
                "intensitet": round(andel / andel_max, 3) if andel_max else 0,
                "tyst": n == 0,
            })
        rader_ut.append({
            "id": did, "namn": d["namn"], "farg": d["farg"],
            "celler": celler, "totalt": sum(matris[did][p] for p in ps),
        })

    return render_template(
        "index.html", rader=rader_ut, partier=ps, partifarger=PARTIFARGER,
        parti_namn=PARTI_NAMN, totalt_parti=totalt_parti, totalt=len(RADER),
    )


@app.route("/doman/<doman_id>")
def doman(doman_id):
    if doman_id not in DOMAN_NAMN:
        abort(404)
    valt_parti = request.args.get("parti")
    valt_sub = request.args.get("sub")

    i_doman = [r for r in RADER if r["doman"] == doman_id]
    subs = Counter(r["subdoman"] for r in i_doman)

    urval = i_doman
    if valt_parti:
        urval = [r for r in urval if r["parti"] == valt_parti]
    if valt_sub:
        urval = [r for r in urval if r["subdoman"] == valt_sub]
    # Mest tillforlitliga forst, och kvantifierade loften fore vaga
    urval = sorted(urval, key=lambda r: (-r["traffsakerhet"], -len(r["kvantifiering"])))

    per_parti = Counter(r["parti"] for r in i_doman)
    return render_template(
        "doman.html",
        doman_id=doman_id, doman_namn=DOMAN_NAMN[doman_id], farg=DOMAN_FARG[doman_id],
        subs=[(s, SUB_NAMN.get(s, s), n) for s, n in subs.most_common()],
        forslag=urval[:150], antal_totalt=len(urval),
        per_parti=[(p, per_parti.get(p, 0)) for p in partier()],
        partifarger=PARTIFARGER, parti_namn=PARTI_NAMN,
        valt_parti=valt_parti, valt_sub=valt_sub,
        domaner=[(d["id"], d["namn"]) for d in TAX["domaner"]],
    )


@app.route("/axlar")
def axlar():
    """Konfliktaxlar - det tvargaende lagret. Visas som BELAGGLISTA,
    inte som positionsskala.

    Skalet: axlarna kraver entydiga fraser for att inte forvaxla omnamnande
    med standpunkt ('avskaffa lagen om valfrihet' ar inte marknadsvanligt).
    Med sa snava fraser blir traffarna fa - for fa for att en position ska
    vara meningsfull. Darfor redovisas de enskilda beläggen i stallet, sa
    att lasaren kan bedoma dem sjalv. Se /om."""
    ut = []
    for a in TAX["axlar"]:
        sidor = {"a": [], "b": []}
        for r in RADER:
            for ax in r["axlar"]:
                if ax["axel"] != a["id"] or ax["riktning"] == "oklar":
                    continue
                sidor[ax["riktning"]].append(r)

        for s in sidor.values():
            s.sort(key=lambda r: PARTIORDNING.index(r["parti"])
                   if r["parti"] in PARTIORDNING else 99)

        ut.append({
            "id": a["id"], "namn": a["namn"],
            "pol_a": a["pol_a"], "pol_b": a["pol_b"],
            "sida_a": sidor["a"][:14], "sida_b": sidor["b"][:14],
            "n_a": len(sidor["a"]), "n_b": len(sidor["b"]),
            "partier_a": sorted({r["parti"] for r in sidor["a"]},
                                key=lambda p: PARTIORDNING.index(p)),
            "partier_b": sorted({r["parti"] for r in sidor["b"]},
                                key=lambda p: PARTIORDNING.index(p)),
        })

    return render_template("axlar.html", axlar=ut, partifarger=PARTIFARGER,
                           parti_namn=PARTI_NAMN, doman_namn=DOMAN_NAMN)


@app.route("/inramning")
def inramning():
    """Tva lager sida vid sida: hur partiet SJALVT rubricerar ett forslag,
    mot vilken sakfraga det faktiskt ror. Skillnaden ar inramningen."""
    valt = request.args.get("parti") or partier()[0]
    egna = defaultdict(lambda: defaultdict(int))
    for r in RADER:
        if r["parti"] != valt:
            continue
        rub = r["partiets_egen_rubrik"] or "(utan rubrik)"
        egna[rub][r["doman"]] += 1

    ut = []
    for rub, domar in egna.items():
        tot = sum(domar.values())
        if tot < 2:
            continue
        ut.append({
            "rubrik": rub, "totalt": tot,
            "domaner": sorted(
                [{"id": d, "namn": DOMAN_NAMN[d], "farg": DOMAN_FARG[d],
                  "n": n, "andel": round(n / tot * 100)}
                 for d, n in domar.items()],
                key=lambda x: -x["n"]),
            "spridning": len(domar),
        })
    ut.sort(key=lambda x: (-x["spridning"], -x["totalt"]))

    # Konkretionsgrad: andel forslag med minst en siffra.
    # Mater loftesprecision, inte asikt - darfor jamforbart mellan partier.
    konkretion = []
    for p in partier():
        rs = [r for r in RADER if r["parti"] == p]
        if not rs:
            continue
        kvant = sum(1 for r in rs if r["kvantifiering"])
        reform = sum(1 for r in rs if r["typ"] == "reform")
        konkretion.append({
            "parti": p, "totalt": len(rs),
            "kvant": kvant, "kvant_pct": round(kvant / len(rs) * 100),
            "reform_pct": round(reform / len(rs) * 100),
        })

    return render_template("inramning.html", rubriker=ut[:40], valt=valt,
                           partier=partier(), partifarger=PARTIFARGER,
                           parti_namn=PARTI_NAMN, konkretion=konkretion)


@app.route("/om")
def om():
    brist = []
    for p in partier():
        rs = [r for r in RADER if r["parti"] == p]
        svaga = sum(1 for r in rs if r["traffsakerhet"] <= 1)
        brist.append({"parti": p, "totalt": len(rs), "svaga": svaga,
                      "pct": round(svaga / len(rs) * 100) if rs else 0})
    typer = Counter(r["typ"] for r in RADER)
    return render_template("om.html", brist=brist, typer=typer.most_common(),
                           totalt=len(RADER), partifarger=PARTIFARGER,
                           parti_namn=PARTI_NAMN, version=TAX["version"])


if __name__ == "__main__":
    app.run(debug=True, port=5001)
