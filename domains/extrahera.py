#!/usr/bin/env python3
"""
Segmenterar valmanifesten till atomara forslag och forsta-taggar dem
mot domains/taxonomi.yaml.

Varje parti har sin egen typografiska konvention i PDF:en, darfor finns
en parti-specifik segmenterare per parti. Gemensamt for alla: resultatet
ar en rad per forslag i forslag.jsonl, med partiets EGEN rubrik bevarad
sa att bada lagren (sakfraga + inramning) kan jamforas.

VIKTIGT: taggningen ar heuristisk och ska granskas manuellt. Falt
'granskad' ar false tills en manniska bekraftat raden. Se CHANGELOG.
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "manifest"
DOMAINS = ROOT / "domains"

PARTIER = {
    "S":  {"namn": "Socialdemokraterna", "fil": "S-valprogram-2026.txt",
           "dok": "Valprogram 2026", "farg": "#e8112d"},
    "M":  {"namn": "Moderaterna", "fil": "M-valmanifest-2026.txt",
           "dok": "Valmanifest 2026", "farg": "#52bdec"},
    "SD": {"namn": "Sverigedemokraterna", "fil": "SD-valplattform-2026.txt",
           "dok": "Valplattform 2026", "farg": "#ddaa00"},
    "C":  {"namn": "Centerpartiet", "fil": "C-valmanifest-2026.md",
           "dok": "Valmanifest 2026", "farg": "#009933"},
    "V":  {"namn": "Vänsterpartiet", "fil": "V-valmanifest-2026.txt",
           "dok": "Valmanifest 2026", "farg": "#af0000"},
    "KD": {"namn": "Kristdemokraterna", "fil": "KD-valmanifest-2026.txt",
           "dok": "Valmanifest 2026", "farg": "#000077"},
    "MP": {"namn": "Miljöpartiet", "fil": "MP-handlingsprogram-2026-2030.txt",
           "dok": "Politiskt handlingsprogram 2026-2030", "farg": "#83cf39"},
    "L":  {"namn": "Liberalerna", "fil": "L-valmanifest-2026.txt",
           "dok": "Valmanifest 2026", "farg": "#006ab3"},
}


def normalisera(s: str) -> str:
    """Slar ihop avstavningar och whitespace fran PDF-extraktionen."""
    s = s.replace("­", "")
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)   # avstavning over radbrytning
    s = re.sub(r"\s*\n\s*", " ", s)
    s = re.sub(r"[•●▪·à›]\s*", "", s)        # kvarvarande punktglyfer fran PDF
    s = re.sub(r"\.{4,}", " ", s)             # innehallsforteckningens punktrader
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def ar_innehallsforteckning(p: str) -> bool:
    """Filtrerar bort TOC-fragment: hog andel sidnummer, fa hela meningar."""
    if "INNEHÅLL" in p.upper()[:40]:
        return True
    tal = len(re.findall(r"\b\d{1,3}\b", p))
    ord_antal = len(p.split())
    return ord_antal > 0 and tal / ord_antal > 0.18 and tal >= 5


def ar_sidnummer(rad: str) -> bool:
    return bool(re.fullmatch(r"\s*\d{1,3}\s*", rad))


# ---------------------------------------------------------------- segmentering

def seg_bullets(text, bullet_re, rubrik_re):
    """Generisk: punktlistor under versalrubriker (KD, delvis andra)."""
    ut = []
    rubrik = None
    buf = []

    def spola():
        if buf:
            p = normalisera(" ".join(buf))
            if len(p.split()) >= 4:
                ut.append((rubrik, p))
        buf.clear()

    for rad in text.split("\n"):
        if ar_sidnummer(rad):
            continue
        if rubrik_re.match(rad.strip()) and len(rad.strip()) > 6:
            spola()
            rubrik = rad.strip()
            continue
        m = bullet_re.match(rad)
        if m:
            spola()
            buf.append(m.group(1))
        elif buf and rad.strip():
            buf.append(rad.strip())
        elif not rad.strip():
            spola()
    spola()
    return ut


def seg_kd(text):
    return seg_bullets(
        text,
        bullet_re=re.compile(r"^\s*[àÃà>•\-•]\s+(.*)"),
        rubrik_re=re.compile(r"^[A-ZÅÄÖ][A-ZÅÄÖ0-9 ,\.\-–:]{6,70}$"),
    )


def seg_l(text):
    """L: numrerade forslag '12. Rubrik. Brodtext...'"""
    ut = []
    kapitel = None
    kap_re = re.compile(r"^\s*(\d{1,2})\.\s+([A-ZÅÄÖ][^\n]{3,60})\.\s*$")
    forslag_re = re.compile(r"^\s*(\d{1,3})\.\s+(.+)")
    buf, aktiv = [], None

    def spola():
        nonlocal aktiv
        if aktiv and buf:
            p = normalisera(" ".join(buf))
            if len(p.split()) >= 5:
                ut.append((kapitel, p))
        buf.clear()
        aktiv = None

    for rad in text.split("\n"):
        if ar_sidnummer(rad):
            continue
        mk = kap_re.match(rad)
        if mk:
            spola()
            kapitel = f"{mk.group(1)}. {mk.group(2)}"
            continue
        mf = forslag_re.match(rad)
        if mf and len(mf.group(2).split()) > 3:
            spola()
            aktiv = mf.group(1)
            buf.append(mf.group(2))
        elif aktiv and rad.strip():
            buf.append(rad.strip())
        elif not rad.strip():
            spola()
    spola()
    return ut


def seg_underrubrik(text, rubrik_re, underrubrik_re):
    """V, SD, M, S: brodtextstycken under (under)rubriker."""
    ut = []
    rubrik = None
    buf = []

    def spola():
        if buf:
            p = normalisera(" ".join(buf))
            if len(p.split()) >= 12:
                ut.append((rubrik, p))
        buf.clear()

    for rad in text.split("\n"):
        r = rad.strip()
        if ar_sidnummer(rad):
            continue
        if rubrik_re.match(r) and len(r) > 6:
            spola()
            rubrik = r
            continue
        if underrubrik_re and underrubrik_re.match(r) and len(r) > 6:
            spola()
            buf.append(r)
            continue
        if r:
            buf.append(r)
        else:
            spola()
    spola()
    return ut


def seg_v(text):
    return seg_underrubrik(
        text,
        rubrik_re=re.compile(r"^[A-ZÅÄÖ][A-ZÅÄÖ0-9 ,\.\-–:]{8,70}$"),
        underrubrik_re=re.compile(r"^[A-ZÅÄÖ][a-zåäöA-ZÅÄÖ ,\-]{6,60}$"),
    )


def seg_sd(text):
    return seg_underrubrik(
        text,
        rubrik_re=re.compile(r"^[A-ZÅÄÖ][a-zåäöA-ZÅÄÖ ,\-]{6,55}$"),
        underrubrik_re=None,
    )


def seg_stycken(text, rubrik_re):
    """M och S: langre brodtext, styckebaserad."""
    return seg_underrubrik(text, rubrik_re=rubrik_re, underrubrik_re=None)


def seg_m(text):
    return seg_stycken(text, re.compile(r"^[A-ZÅÄÖ][A-ZÅÄÖ0-9 ,\.\-–:]{8,70}$"))


def seg_s(text):
    return seg_stycken(text, re.compile(r"^(Vi ska |[A-ZÅÄÖ][A-ZÅÄÖ ,\-]{8,60}$)"))


def seg_mp(text):
    """MP handlingsprogram: numrerade kapitel, brodtext i stycken."""
    ut = []
    kapitel = None
    kap_re = re.compile(r"^\s*(\d{1,2})\.\s+([A-ZÅÄÖ][^\n\.]{4,70})\s*$")
    buf = []

    def spola():
        if buf:
            p = normalisera(" ".join(buf))
            if len(p.split()) >= 10:
                ut.append((kapitel, p))
        buf.clear()

    for rad in text.split("\n"):
        r = rad.strip()
        if ar_sidnummer(rad) or "......" in r:
            continue
        mk = kap_re.match(r)
        if mk:
            spola()
            kapitel = f"{mk.group(1)}. {mk.group(2)}"
            continue
        if r:
            buf.append(r)
        else:
            spola()
    spola()
    return ut


def seg_c(text):
    """C: markdown fran WP-API. '## rubrik' + punktlistor/stycken."""
    ut = []
    rubrik = None
    buf = []

    def spola():
        if buf:
            p = normalisera(" ".join(buf))
            if len(p.split()) >= 5:
                ut.append((rubrik, p))
        buf.clear()

    for rad in text.split("\n"):
        r = rad.strip()
        if r.startswith("## "):
            spola()
            rubrik = r[3:].strip()
            continue
        if r.startswith("#") or r.startswith("http"):
            continue
        if r.startswith("- "):
            spola()
            buf.append(r[2:].strip())
        elif r:
            buf.append(r)
        else:
            spola()
    spola()
    return ut


SEGMENTERARE = {
    "KD": seg_kd, "L": seg_l, "V": seg_v, "SD": seg_sd,
    "M": seg_m, "S": seg_s, "MP": seg_mp, "C": seg_c,
}


# -------------------------------------------------------------------- taggning

class Taggare:
    def __init__(self, tax):
        self.tax = tax
        self.sub = []          # (domain_id, sub_id, [nyckelord])
        for d in tax["domaner"]:
            for s in d["subdomaner"]:
                self.sub.append((d["id"], s["id"], [k.lower() for k in s["nyckelord"]]))
        self.axlar = tax["axlar"]

    def domain(self, txt, rubrik=None):
        """Taggar mot texten. Om texten ar otydlig anvands partiets egen
        rubrik som fallback - den barb ofta domanen aven nar brodtexten
        saknar nyckelord ('SA KAN FLER FA EN EGEN BOSTAD')."""
        dom, sub, poang = self._matcha(txt)
        if poang >= 1:
            return dom, sub, poang
        if rubrik:
            dom, sub, poang = self._matcha(rubrik)
            if poang >= 1:
                return dom, sub, poang * 0.5   # halv vikt: svagare signal
        return None, None, 0

    def _matcha(self, txt):
        """Flerordiga nyckelord kraver exakt traff (starkare signal).
        Enordiga matchas pa stam MEN forankrat vid ordgrans, annars blir
        korta nycklar katastrofalt breda: 'isk' (investeringssparkonto)
        matchade tidigare som delstrang i svensk, fisket, friskt,
        manniskors och europeisk - 214 av 221 traffar var brus.

        Ordgrans framfor stammen tillater fortfarande sammansattningar
        och boljningar framat ('bostad' -> 'bostadsbyggande'), men inte
        traffar mitt inne i ett annat ord."""
        t = txt.lower()
        bast, poang = None, 0
        for dom, sub, nycklar in self.sub:
            p = 0
            for k in nycklar:
                if " " in k:
                    if k in t:
                        p += 2
                elif self._ordtraff(t, k):
                    p += 1
            if p > poang:
                bast, poang = (dom, sub), p
        if not bast:
            return None, None, 0
        return bast[0], bast[1], poang

    _ordcache: dict = {}

    @classmethod
    def _ordtraff(cls, txt_low, nyckel):
        """Stammatchning forankrad vid ordborjan. Nycklar kortare an 5
        tecken kraver helt ord - de ar for korta for att stamma sakert."""
        m = cls._ordcache.get(nyckel)
        if m is None:
            if len(nyckel) < 5:
                m = re.compile(r"\b" + re.escape(nyckel) + r"\b")
            else:
                stam = nyckel[:6] if len(nyckel) > 7 else nyckel
                m = re.compile(r"\b" + re.escape(stam))
            cls._ordcache[nyckel] = m
        return bool(m.search(txt_low))

    # Verb som vander innebörden av ett nyckelord. "Avskaffa lagen om
    # valfrihet" ar motsatsen till "valfrihet" - utan detta raknas V som
    # marknadsvanligt bara for att de skriver om marknaden.
    NEKANDE = re.compile(
        r"\b(avskaffa\w*|avveckla\w*|stoppa\w*|stopp för|förbjud\w*|riv upp|"
        r"ta bort|slopa\w*|motverka\w*|begränsa\w*|nej till|emot|mot\b|"
        r"avprivatiser\w*|återta\w*|förstatliga\w*|inte ska|varken)\b")

    def _riktad_traff(self, txt_low, nyckelord):
        """Raknar traffar, men vander den om ett nekande verb star nara.
        Returnerar (traffar_for, traffar_emot)."""
        fore, emot = 0, 0
        for k in nyckelord:
            kl = k.lower()
            start = 0
            while True:
                i = txt_low.find(kl, start)
                if i < 0:
                    break
                start = i + len(kl)
                # Fonster fore nyckelordet: nekande verb styr oftast framat
                fonster = txt_low[max(0, i - 60):i]
                if self.NEKANDE.search(fonster):
                    emot += 1
                else:
                    fore += 1
        return fore, emot

    def axel(self, txt):
        t = txt.lower()
        ut = []
        for a in self.axlar:
            a_for, a_emot = self._riktad_traff(t, a["nyckelord_a"])
            b_for, b_emot = self._riktad_traff(t, a["nyckelord_b"])
            # Ett nekat A-ord ar ett svagt stod for B, och tvartom
            pa = a_for + b_emot
            pb = b_for + a_emot
            if pa or pb:
                ut.append({
                    "axel": a["id"],
                    "riktning": "a" if pa > pb else ("b" if pb > pa else "oklar"),
                    "styrka": abs(pa - pb),
                })
        return ut

    @staticmethod
    def typ(txt):
        t = txt.lower()
        if re.search(r"\b(vi vill|vi föreslår|inför|höj|sänk|avskaffa|bygg|satsa|"
                     r"stoppa|skärp|utöka|garantera|ta bort|genomför)\b", t):
            return "reform"
        if re.search(r"\b(målet är|ska vara|vi ska nå|senast \d{4}|år \d{4})\b", t):
            return "mal"
        if re.search(r"\b(regeringen har|tidöregeringen|misslyckats|"
                     r"under socialdemokraterna|har lett till)\b", t):
            return "kritik"
        return "princip"

    @staticmethod
    def kvantifiering(txt):
        """Plockar ut siffersatta loften - matt pa konkretionsgrad."""
        tal = re.findall(
            r"\b\d[\d\s ]{0,12}(?:,\d+)?\s*"
            r"(?:kronor|kr|miljarder|miljoner|procent|%|år|månader|timmar|elever|platser)\b",
            txt, re.I)
        return [re.sub(r"\s+", " ", x).strip() for x in tal][:5]


def main():
    tax = yaml.safe_load((DOMAINS / "taxonomi.yaml").read_text(encoding="utf-8"))
    taggare = Taggare(tax)
    rader = []
    stat = {}

    for kod, meta in PARTIER.items():
        fil = MANIFEST / meta["fil"]
        if not fil.exists():
            print(f"  SAKNAS: {fil}", file=sys.stderr)
            continue
        text = fil.read_text(encoding="utf-8", errors="replace")
        bitar = SEGMENTERARE[kod](text)

        n = 0
        for rubrik, payload in bitar:
            if ar_innehallsforteckning(payload):
                continue
            dom, sub, poang = taggare.domain(payload, rubrik)
            if not dom or poang < 1:
                continue          # otaggbart -> utelamnas, raknas som bortfall
            n += 1
            rader.append({
                "id": f"{kod}-{n:04d}",
                "parti": kod,
                "parti_namn": meta["namn"],
                "dokument": meta["dok"],
                "doman": dom,
                "subdoman": sub,
                "traffsakerhet": poang,
                "axlar": taggare.axel(payload),
                "typ": taggare.typ(payload),
                "kvantifiering": taggare.kvantifiering(payload),
                "text": payload[:600],
                "partiets_egen_rubrik": rubrik,
                "granskad": False,
            })
        stat[kod] = {"segment": len(bitar), "taggade": n}

    ut = DOMAINS / "forslag.jsonl"
    with ut.open("w", encoding="utf-8") as f:
        for r in rader:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"Skrev {len(rader)} förslag till {ut.relative_to(ROOT)}\n")
    print(f"{'Parti':<5} {'Segment':>8} {'Taggade':>8} {'Bortfall':>9}")
    for kod, s in stat.items():
        bortfall = s["segment"] - s["taggade"]
        pct = (bortfall / s["segment"] * 100) if s["segment"] else 0
        print(f"{kod:<5} {s['segment']:>8} {s['taggade']:>8} {bortfall:>6} ({pct:.0f}%)")


if __name__ == "__main__":
    main()
