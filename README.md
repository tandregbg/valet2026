# Valmanifest 2026 — strukturerad datamängd och analysverktyg

[![Tester](https://img.shields.io/badge/tester-34%20gr%C3%B6na-brightgreen)]()
[![Version](https://img.shields.io/badge/version-0.6.1-blue)]()

Åtta svenska valmanifest (108 206 ord) omvandlade till en strukturerad,
granskningsbar datamängd — med en webbapp för att utforska den och en
valkompass byggd på granskade påståenden.

**Projektet är ett metodexempel:** hur en stor textmassa kan bli ett underlag
som människor kan fatta beslut på, utan att överlåta tolkningen till en
språkmodell.

📄 **Utförlig genomgång av processen:** [`ARTIKEL.md`](ARTIKEL.md) — sex faser,
vad som gick fel, och var gränsen går mellan vad maskinen klarar och vad den
inte gör.

---

## Poängen: flödet är omvänt

Det vanliga sättet är att klistra in texten i en chatt och be om en analys.
108 206 ord får plats i ett modernt kontextfönster, så det *går*.

Problemet är inte kapaciteten — det är att modellen då fattar hundratals små
tolkningsbeslut som ingen ser: vad som räknas som ett förslag, vilken kategori
det hör till, vad som är jämförbart med vad. Besluten är inte nedskrivna, går
inte att granska, och kan ändras mellan två körningar.

Här görs det tvärtom:

```
1. Läs in källdata          ->  verifierad, med checksummor
2. Läs och förstå strukturen ->  MÄNNISKA
3. Konstruera en taxonomi    ->  MÄNNISKA, i en fil man kan invända mot
4. Segmentera och tagga      ->  KOD, deterministiskt
5. Granska och skriv om      ->  MÄNNISKA, varje rad
6. Visualisera strukturen    ->  KOD
```

Analysen görs **på strukturen**, inte på texten. Kategorierna är definierade
innan analysen börjar, i en fil som går att läsa, versionshantera och
argumentera emot.

---

## Vad som är vad

| Lager | Innehåll |
|---|---|
| **Rent innehåll** | Utgivarnas egen text, ordagrant. Inget genererat. |
| **AI-assisterad kod** | Verktyget. Skrivet med AI-assistans, deterministiskt när det körs. |
| **Språkmodell** | Utvecklingsassistent och utkastgenerator. **Ingen roll i databearbetningen.** |
| **Mänskligt omdöme** | Taxonomin, granskningen, och besluten om vad som inte ska redovisas. |

Taggningen av 1 528 textstycken görs med nyckelordsmatchning, inte med en
språkmodell. Sämre träffsäkerhet — men determinism, granskbarhet och ärlighet
om osäkerhet väger tyngre. Se `ARTIKEL.md` för varför det visade sig avgörande.

---

## Struktur

```
val2026/
├── manifest/          Källdokument (PDF + text) + INDEX.md med checksummor
├── domains/
│   ├── taxonomi.yaml      12 domäner, 60 subdomäner, 5 konfliktaxlar
│   ├── kallor.yaml        Källförteckning med URL och SHA256
│   ├── extrahera.py       Segmentering + taggning
│   ├── forslag.jsonl      1 528 taggade textstycken
│   ├── kandidater.py      Kandidatgenerering till valkompassen
│   ├── kandidater.jsonl   291 kandidater
│   └── pastaenden.jsonl   122 granskade påståenden
├── app/               Flask-app
├── docs/change-requests/  CR-001..005
├── tests/             30 tester
├── ARTIKEL.md         Teknisk genomgång av processen
└── CHANGELOG.md
```

## Köra

```bash
python3 -m venv .venv && .venv/bin/pip install flask pyyaml pytest
.venv/bin/python domains/extrahera.py     # bygg om forslag.jsonl
.venv/bin/python -m pytest tests/ -q      # 34 tester
.venv/bin/python app/app.py               # startar servern
```

Appen binder till `0.0.0.0` och skriver ut både den lokala adressen och
nätverksadressen vid start, så den går att testa från telefon eller annan
dator på samma nät.

| Miljövariabel | Default | Effekt |
|---|---|---|
| `VAL2026_HOST` | `0.0.0.0` | Sätt till `127.0.0.1` för att bara lyssna lokalt |
| `VAL2026_PORT` | `5001` | Port |
| `VAL2026_SECRET` | slumpas | Sessionsnyckel; sätt för att behålla sessioner över omstart |

**Appen har ingen inloggning.** Alla på nätverket kan nå den, inklusive
`/granskning` som skriver till datafilerna. Kör bara på nät du litar på, och
använd en riktig WSGI-server om den någonsin ska exponeras bredare.

## Vyer

| Vy | Fråga |
|---|---|
| `/` | Hur fördelar sig varje källas innehåll över domänerna? |
| `/doman/<id>` | Vad står det faktiskt inom ett sakområde? |
| `/axlar` | Vilka mönster skär tvärs över domängränserna? |
| `/inramning` | Hur förhåller sig källans egen rubrik till sakfrågan? |
| `/kompass` | Valkompass: gradera 50 påståenden, se överensstämmelse |
| `/granskning` | Redaktionell granskning av kandidater |
| `/om` | Källor, process, arbetsdelning och brister |

---

## Spårbarhet

Varje påstående i valkompassen går att följa tillbaka till en namngiven fil
med checksumma. Kedjan är verifierad — noll brutna länkar.

```
Påstående → källhänvisning → originaltext → taggat stycke
          → utgivarens egen rubrik → källdokument (SHA256)
```

---

## Brister — läs dessa

- **40 % av de taggade textstyckena** vilar på en enda nyckelordsträff.
- **Fyra av tolv domäner** har för få granskade påståenden och är inte
  valbara i valkompassen. Kandidatunderlaget är uttömt — det är en verklig
  gräns i materialet.
- **En källa fick bidra med ett extra dokument** (Miljöpartiets
  handlingsprogram), vilket påverkar alla jämförelser den ingår i. Beslutet
  redovisas öppet i `domains/kallor.yaml`.
- **Antal enheter speglar dokumentets längd** och parserns granularitet minst
  lika mycket som utgivarens prioriteringar.
- **Matchningen mäter överensstämmelse där det finns belägg, aldrig avstånd.**
  Att ett förslag saknas betyder inte motstånd.

Ett konkret exempel på varför granskning behövs: nyckelordet `isk`
(investeringssparkonto) matchade som delsträng i *svensk*, *fisket* och
*människors*. 214 av 221 träffar i en subdomän var brus. Maskinen upptäckte
det inte — pipelinen körde grönt. En människa som tyckte att en färg såg
konstig ut gjorde det.

## Vad projektet inte gör

Verktyget utvärderar ingen politik, rangordnar inte partier och rekommenderar
inget. Det gör åtta dokument läsbara sida vid sida enligt en struktur som är
öppen att granska. Läsningen, och besluten, är läsarens.

---

## Källor

Samtliga dokument hämtade 2026-09-13 från respektive utgivares officiella
webbplats. Fullständiga URL:er och SHA256 i `domains/kallor.yaml` och
`manifest/INDEX.md`.

## Licens

Koden är fri att använda. **Källdokumenten tillhör respektive utgivare** och
ingår här som citat för analysändamål.
