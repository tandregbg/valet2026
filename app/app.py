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
import os
import secrets
import socket

import yaml
from flask import Flask, abort, render_template, request

ROOT = Path(__file__).resolve().parent.parent
app = Flask(__name__)
# Sessionsnyckel for kompassens mellanlagring. Lokalt bruk (deploy.target=local);
# byt till miljovariabel om appen nagonsin exponeras.
# Sessionsnyckel. Slumpas per start om VAL2026_SECRET inte satts - da
# nollstalls pagaende kompassessioner vid omstart, vilket ar ratt beteende
# for lokalt bruk. Satt variabeln for att behalla sessioner over omstart.
app.secret_key = os.environ.get("VAL2026_SECRET") or secrets.token_hex(32)

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


# CR-002: granskningsgranssnitt for pastaendebanken
from granskning import bp as granskning_bp   # noqa: E402
app.register_blueprint(granskning_bp)

# CR-001: valkompassens domanval och fragemotor
from kompass import bp as kompass_bp         # noqa: E402
app.register_blueprint(kompass_bp)


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
    """Om-sidan: kallor, process, arbetsdelning och brister.

    Alla siffror harleds ur faktisk data - inget hardkodat, sa att sidan
    inte kan bli inaktuell nar datamangden andras."""
    kallor = yaml.safe_load((ROOT / "domains" / "kallor.yaml").read_text(encoding="utf-8"))

    pastaenden = []
    pf = ROOT / "domains" / "pastaenden.jsonl"
    if pf.exists():
        pastaenden = [json.loads(l) for l in
                      pf.read_text(encoding="utf-8").splitlines() if l.strip()]
    kandidater = []
    kf = ROOT / "domains" / "kandidater.jsonl"
    if kf.exists():
        kandidater = [json.loads(l) for l in
                      kf.read_text(encoding="utf-8").splitlines() if l.strip()]

    ord_totalt = (sum(d["ord"] for d in kallor["dokument"])
                  + sum(k["ord"] for k in kallor.get("komplement", [])))
    sidor_totalt = (sum(d["sidor"] or 0 for d in kallor["dokument"])
                    + sum(k["sidor"] or 0 for k in kallor.get("komplement", [])))
    svaga = sum(1 for r in RADER if r["traffsakerhet"] <= 1)

    korpus = {
        "ord_totalt": f"{ord_totalt:,}",
        "sidor_totalt": sidor_totalt,
        "dokument": len(kallor["dokument"]) + len(kallor.get("komplement", [])),
        "forslag": len(RADER),
        "pastaenden": len(pastaenden),
        "kandidater": len(kandidater),
        "svaga_pct": round(svaga / len(RADER) * 100) if RADER else 0,
    }

    processteg = [
        {"titel": "Hämta förstahandskällor", "aktor": "Kod", "aktor_klass": "kod",
         "text": "Domänbegränsad sökning per utgivare, nedladdning, verifiering "
                 "av filtyp och checksumma. Inga sammanfattningar.",
         "utfall": f"{corpus_dok(kallor)} dokument, {sidor_totalt} sidor"},
        {"titel": "Extrahera text", "aktor": "Kod", "aktor_klass": "kod",
         "text": "pdftotext -layout bevarar kolumnstruktur. En källa publicerade "
                 "inget PDF och hämtades via sajtens REST API.",
         "utfall": f"{ord_totalt:,} ord".replace(",", " ")},
        {"titel": "Läsa igenom och förstå strukturen", "aktor": "Människa",
         "aktor_klass": "manniska",
         "text": "Varje utgivare strukturerar sitt dokument efter sin egen "
                 "berättelse. En har tre kapitel, en har trettiofem platta "
                 "rubriker. Slutsats: källornas egna indelningar går inte att "
                 "använda som gemensam axel.",
         "utfall": None},
        {"titel": "Konstruera en neutral taxonomi", "aktor": "Människa",
         "aktor_klass": "manniska",
         "text": "Tolv sakområden som inte följer någon utgivares indelning, "
                 "med subdomäner och nyckelord. Definierad i en fil som går "
                 "att läsa, invända mot och versionshantera.",
         "utfall": "12 domäner, 60 subdomäner"},
        {"titel": "Segmentera till atomära enheter", "aktor": "Kod",
         "aktor_klass": "kod",
         "text": "En parser per dokument, eftersom typografin skiljer sig. "
                 "Ett förslag är enheten, inte ett kapitel.",
         "utfall": f"{len(RADER)} textstycken"},
        {"titel": "Tagga mot taxonomin", "aktor": "Kod", "aktor_klass": "kod",
         "text": "Deterministisk nyckelordsmatchning. Ingen språkmodell — "
                 "determinism och granskbarhet väger tyngre än träffsäkerhet.",
         "utfall": f"{corpus_taggade(RADER)} taggade, resten utelämnade"},
        {"titel": "Granska och skriva om", "aktor": "Människa",
         "aktor_klass": "manniska",
         "text": "Varje kandidat läst mot originaltexten och bedömd enligt fem "
                 "kriterier. Trasig text, metatext, rubriker utan sakinnehåll "
                 "och feltaggningar förkastade. Resten omskrivna så att "
                 "avsändarens röst försvinner.",
         "utfall": f"{len(pastaenden)} godkända av {len(kandidater)} kandidater"},
        {"titel": "Visualisera", "aktor": "Kod", "aktor_klass": "kod",
         "text": "Vyer som redovisar sin egen osäkerhet: svaga träffar märks, "
                 "täckningssiffror visas alltid bredvid procent, varje cell "
                 "länkar tillbaka till källtexten.",
         "utfall": None},
    ]

    jamforelse = [
        {"chatt": "Modellen bestämmer själv vad som är ett förslag och vilken "
                  "kategori det hör till. Besluten syns inte.",
         "struktur": "Kategorierna är definierade i en fil innan analysen "
                     "börjar. Går att läsa, invända mot och ändra."},
        {"chatt": "Två körningar av samma fråga kan ge olika svar.",
         "struktur": "Samma indata ger samma utdata. Kör om och jämför."},
        {"chatt": "Ett påstående i svaret går inte att spåra till en rad i ett "
                  "dokument.",
         "struktur": "Varje enhet bär sin originaltext och sin källa. Noll "
                     "brutna länkar i kedjan."},
        {"chatt": "Modellen sammanfattar — och sammanfattningen tar bort det "
                  "man behövde se.",
         "struktur": "Ingenting komprimeras bort. Strukturen gör materialet "
                     "filtrerbart, originalet finns kvar."},
        {"chatt": "Osäkerhet syns inte. Svaret låter lika säkert oavsett.",
         "struktur": "Svaga träffar är märkta i gränssnittet. Man ser var "
                     "underlaget är tunt."},
        {"chatt": "Ett fel i tolkningen är osynligt och oåtkomligt.",
         "struktur": "Ett fel går att spåra till en regel och rättas på "
                     "minuter. Det hände — se Brister."},
    ]

    lager = [
        {"titel": "Rent innehåll", "marke": "från källorna", "klass": "innehall",
         "beskrivning": "Text som utgivarna själva skrivit och publicerat. "
                        "Ingenting av detta är genererat.",
         "punkter": [
             "Samtliga valmanifest, ordagrant",
             "Originaltexten bakom varje påstående",
             "Utgivarnas egna rubriker, bevarade per enhet",
         ]},
        {"titel": "AI-assisterad kod", "marke": "verktyget", "klass": "kod",
         "beskrivning": "Programkod skriven med AI-assistans, men "
                        "deterministisk när den körs. Ingen modell är "
                        "inblandad i bearbetningen av data.",
         "punkter": [
             "Hämtning, textextraktion och segmentering",
             "Nyckelordsmatchning mot taxonomin",
             "Matchningsalgoritm och webbgränssnitt",
             "Tester som verifierar invarianterna",
         ]},
        {"titel": "Språkmodell", "marke": "begränsad roll", "klass": "llm",
         "beskrivning": "Används som assistent i utvecklingsarbetet och för "
                        "att generera utkast — aldrig som beslutsfattare över "
                        "data.",
         "punkter": [
             "Skrev koden tillsammans med en människa",
             "Genererade förslag till omskrivningar som utgångspunkt",
             "Ingen roll i taggningen av textstyckena",
             "Ingen roll i matchningsberäkningen",
         ]},
        {"titel": "Mänskligt omdöme", "marke": "avgörande", "klass": "manniska",
         "beskrivning": "Besluten som formade resultatet. Inget av dem är "
                        "tekniskt svårt — alla kräver någon som vet vad "
                        "materialet handlar om.",
         "punkter": [
             "Taxonomins gränsdragningar",
             "Att förkasta en positionsskala underlaget inte bar",
             "Att upptäcka att en hel domän var brus",
             "Redaktionell granskning av varje påstående",
             "Att avgöra vad som inte ska redovisas",
         ]},
    ]

    datafiler = [
        {"fil": "manifest/*.pdf + .txt", "beskrivning": "Källdokument och extraherad text",
         "antal": korpus["dokument"], "enhet": "dokument"},
        {"fil": "domains/taxonomi.yaml", "beskrivning": "Domäner, subdomäner, konfliktaxlar",
         "antal": 12, "enhet": "domäner"},
        {"fil": "domains/forslag.jsonl", "beskrivning": "Taggade textstycken med källa",
         "antal": len(RADER), "enhet": "rader"},
        {"fil": "domains/kandidater.jsonl", "beskrivning": "Kandidater för granskning",
         "antal": len(kandidater), "enhet": "kandidater"},
        {"fil": "domains/pastaenden.jsonl", "beskrivning": "Granskade påståenden till valkompassen",
         "antal": len(pastaenden), "enhet": "påståenden"},
        {"fil": "domains/kallor.yaml", "beskrivning": "Källförteckning med URL och checksumma",
         "antal": korpus["dokument"], "enhet": "poster"},
    ]

    kedja = [
        {"steg": "Påstående i valkompassen", "falt": "pastaenden.jsonl → text"},
        {"steg": "Källhänvisning", "falt": "kallor[].parti + forslag_id"},
        {"steg": "Originaltext", "falt": "originaltext"},
        {"steg": "Taggat textstycke", "falt": "forslag.jsonl → id"},
        {"steg": "Utgivarens egen rubrik", "falt": "partiets_egen_rubrik"},
        {"steg": "Källdokument med checksumma", "falt": "kallor.yaml → sha256"},
    ]

    begransningar = [
        f"{korpus['svaga_pct']} % av de taggade textstyckena vilar på en enda "
        "nyckelordsträff.",
        "Antal enheter speglar dokumentets längd och parserns granularitet "
        "minst lika mycket som utgivarens prioriteringar.",
        "Fyra domäner har för få granskade påståenden och är inte valbara i "
        "valkompassen.",
        "Matchningen mäter överensstämmelse där det finns belägg, aldrig "
        "avstånd. Att ett förslag saknas betyder inte motstånd.",
        "En källa fick bidra med ett extra dokument (se Komplement), vilket "
        "påverkar alla jämförelser den ingår i.",
        "Taxonomin är konstruerad av en person och är inte stabiliserad.",
    ]

    return render_template(
        "om.html", kallor=kallor, korpus=korpus, processteg=processteg,
        jamforelse=jamforelse, lager=lager, datafiler=datafiler, kedja=kedja,
        begransningar=begransningar, version=TAX["version"],
    )


def corpus_dok(kallor):
    return len(kallor["dokument"]) + len(kallor.get("komplement", []))


def corpus_taggade(rader):
    return len(rader)


def lokal_ip():
    """Adressen andra enheter pa natet nar appen pa. Ingen trafik skickas -
    socketen anvands bara for att fraga OS vilket interface som skulle
    anvandas mot internet."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("192.0.2.1", 1))     # TEST-NET-1, aldrig routad
        return s.getsockname()[0]
    except OSError:
        return None
    finally:
        s.close()


if __name__ == "__main__":
    # Binder till 0.0.0.0 sa att appen nas fran andra enheter pa samma nat.
    # Satt VAL2026_HOST=127.0.0.1 for att bara lyssna lokalt.
    host = os.environ.get("VAL2026_HOST", "0.0.0.0")
    port = int(os.environ.get("VAL2026_PORT", "5001"))

    print("\n  Valmanifest 2026")
    print(f"  Lokalt:    http://127.0.0.1:{port}")
    if host == "0.0.0.0":
        ip = lokal_ip()
        if ip:
            print(f"  Nätverket: http://{ip}:{port}")
        else:
            print("  Nätverket: kunde inte avgöra IP-adress")
        print("\n  Lyssnar på alla gränssnitt. Appen har ingen inloggning —")
        print("  alla på nätverket kan nå den, inklusive granskningsvyn som")
        print("  skriver till datafilerna. Kör bara på nät du litar på.")
    print()

    app.run(host=host, port=port, debug=False)
