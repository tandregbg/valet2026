#!/usr/bin/env python3
"""
CR-002 steg 2: redaktionell granskning.

Blueprint som monteras i app.py. Visar en kandidat i taget med originaltext
bredvid utkastet, granskningskriterierna synliga i gransssnittet (inte i ett
dokument nagon glomt), och skriver godkanda pastaenden till pastaenden.jsonl.
"""
import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from flask import Blueprint, jsonify, redirect, render_template, request, url_for

ROOT = Path(__file__).resolve().parent.parent
DOMAINS = ROOT / "domains"

bp = Blueprint("granskning", __name__)

KRITERIER = [
    "Går påståendet att både hålla med om och ta avstånd från?",
    "Är det fritt från värdeladdade ord (rättvis, ansvarsfull, kraftfull)?",
    "Skulle någon kunna gissa avsändaren från formuleringen?",
    "Innehåller det exakt en sakfråga, inte två hopslagna?",
    "Överlever förbehållen i originalet komprimeringen?",
]


def las_kandidater():
    f = DOMAINS / "kandidater.jsonl"
    if not f.exists():
        return []
    return [json.loads(l) for l in f.read_text(encoding="utf-8").splitlines() if l.strip()]


def spara_kandidater(rader):
    (DOMAINS / "kandidater.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rader) + "\n",
        encoding="utf-8")


def bygg_pastaenden():
    """Skriver om pastaenden.jsonl fran godkanda kandidater. Kors efter
    varje godkannande sa att banken alltid speglar granskningslaget."""
    godkanda = [r for r in las_kandidater() if r["status"] == "godkand"]
    ut = []
    for i, k in enumerate(godkanda, start=1):
        ut.append({
            "id": f"P-{i:04d}",
            "text": k.get("slutlig_text") or k["utkast"],
            "doman": k["doman"],
            "subdoman": k["subdoman"],
            "kallor": k["kallor"],
            "svag_traff": k["svag_traff"],
            "granskad_av": k["granskad_av"],
            "granskad_datum": k["granskad_datum"],
            "originaltext": k["originaltext"],
            "anmarkning": k.get("anmarkning"),
        })
    (DOMAINS / "pastaenden.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in ut) + "\n" if ut else "",
        encoding="utf-8")
    return ut


@bp.route("/granskning")
def index():
    rader = las_kandidater()
    kvar = [r for r in rader if r["status"] == "kandidat"]
    godkanda = [r for r in rader if r["status"] == "godkand"]
    forkastade = [r for r in rader if r["status"] == "forkastad"]

    # Per domän: hur långt är vi mot CR-001:s minimum på 10?
    from collections import Counter
    per_doman = Counter(r["doman"] for r in godkanda)
    domaner = sorted({r["doman"] for r in rader})
    status_doman = [
        {"doman": d, "godkanda": per_doman.get(d, 0), "klar": per_doman.get(d, 0) >= 10}
        for d in domaner
    ]

    return render_template(
        "granskning_index.html",
        kvar=len(kvar), godkanda=len(godkanda), forkastade=len(forkastade),
        totalt=len(rader), status_doman=status_doman,
    )


@bp.route("/granskning/nasta")
def nasta():
    doman = request.args.get("doman")
    rader = las_kandidater()
    kvar = [r for r in rader if r["status"] == "kandidat"]
    if doman:
        kvar = [r for r in kvar if r["doman"] == doman]
    if not kvar:
        return redirect(url_for("granskning.index"))
    # Svaga träffar först - de kräver mest uppmärksamhet och bör inte
    # hamna sist när granskaren är trött
    kvar.sort(key=lambda r: (not r["svag_traff"], r["id"]))
    return redirect(url_for("granskning.visa", kandidat_id=kvar[0]["id"], doman=doman))


@bp.route("/granskning/<kandidat_id>")
def visa(kandidat_id):
    rader = las_kandidater()
    k = next((r for r in rader if r["id"] == kandidat_id), None)
    if not k:
        return redirect(url_for("granskning.index"))
    kvar = sum(1 for r in rader if r["status"] == "kandidat")
    return render_template(
        "granskning_kandidat.html",
        k=k, kriterier=KRITERIER, kvar=kvar, totalt=len(rader),
        doman=request.args.get("doman"),
    )


@bp.route("/granskning/<kandidat_id>/beslut", methods=["POST"])
def beslut(kandidat_id):
    rader = las_kandidater()
    k = next((r for r in rader if r["id"] == kandidat_id), None)
    if not k:
        return redirect(url_for("granskning.index"))

    handling = request.form.get("handling")
    granskare = (request.form.get("granskare") or "TA").strip()[:10]

    if handling == "godkann":
        text = (request.form.get("slutlig_text") or "").strip()
        if not text:
            return redirect(url_for("granskning.visa", kandidat_id=kandidat_id))
        k["slutlig_text"] = text
        k["status"] = "godkand"
        if granskare not in k["granskad_av"]:
            k["granskad_av"].append(granskare)
        k["granskad_datum"] = date.today().isoformat()
        k["anmarkning"] = (request.form.get("anmarkning") or "").strip() or None
    elif handling == "forkasta":
        k["status"] = "forkastad"
        if granskare not in k["granskad_av"]:
            k["granskad_av"].append(granskare)
        k["granskad_datum"] = date.today().isoformat()
        k["anmarkning"] = (request.form.get("anmarkning") or "").strip() or None

    spara_kandidater(rader)
    bygg_pastaenden()
    return redirect(url_for("granskning.nasta", doman=request.args.get("doman")))
