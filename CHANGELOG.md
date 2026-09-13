# CHANGELOG

Alla ändringar i detta projekt dokumenteras här.
Format enligt [Keep a Changelog](https://keepachangelog.com/sv/1.1.0/),
versionshantering enligt [SemVer](https://semver.org/lang/sv/).

## [0.1.0] - 2026-09-13

Första sammanhållna versionen. Insamling av samtliga riksdagspartiers
valmanifest, strukturering mot en neutral sakpolitisk taxonomi, och en
Flask-app för att utforska materialet.

Noll-major är medvetet: taxonomin är inte stabiliserad och taggningen är
oreviderad. Tolkningslagret förutsätter en människa.

### Tillagt

**Källdata** (`manifest/`)

Samtliga åtta riksdagspartiers valmanifest, hämtade från respektive partis
officiella webbplats. Inga tredjepartssammanfattningar.

| Parti | Dokument | Sidor | Ord |
|-------|----------|------:|----:|
| S  | Valprogram 2026 - "Dags att ta Sverige på allvar" | 21 | 7 088 |
| M  | Valmanifest 2026 - "Ansträngning ska löna sig. Brott ska straffa sig." | 50 | 16 810 |
| SD | Valplattform 2026 - "Hemma i Sverige" | 12 | 3 057 |
| C  | Valmanifest 2026 - "Sverige kan mer" | webb | 22 982 |
| V  | Valmanifest 2026 | 21 | 5 377 |
| KD | Valmanifest 2026 - "Tro på Sverige" | 10 | 4 646 |
| MP | Valmanifest 2026 - "Sverige vinner på grön politik" | 9 | 3 222 |
| L  | Valmanifest 2026 - "För din frihet" | 40 | 9 478 |

Komplement: MP:s politiska handlingsprogram 2026-2030 (106 sidor,
35 546 ord), eftersom deras valmanifest på 9 sidor annars ger en kraftigt
underrepresenterad bild i jämförelser.

Text extraherad med `pdftotext -layout -enc UTF-8`. Checksummor i
`manifest/INDEX.md`.

**Domänmodell** (`domains/`)

- `taxonomi.yaml` (v0.1.0) - 12 domäner, 60 subdomäner, 5 konfliktaxlar,
  4 utsagetyper.
- `extrahera.py` - segmentering och heuristisk taggning, med en
  partispecifik parser per dokument.
- `forslag.jsonl` - 1 528 förslag, ett per rad.

**Applikation** (`app/`)

Flask-app med fem vyer: täckningsmatris, domändjupdykning, konfliktaxlar,
inramning och metodsida. Ljust tema genomgående.

### Extraktionsutfall

| Parti | Segment | Taggade | Bortfall |
|-------|--------:|--------:|---------:|
| S     |  53 |  52 |  1 (2%)  |
| M     | 156 | 131 | 25 (16%) |
| SD    |  62 |  56 |  6 (10%) |
| C     | 681 | 552 | 129 (19%) |
| V     | 102 |  96 |  6 (6%)  |
| KD    | 111 |  88 | 23 (21%) |
| MP    | 474 | 456 | 18 (4%)  |
| L     |  99 |  97 |  2 (2%)  |

Bortfall = segment som inte kunde domäntaggas med rimlig säkerhet. De
utelämnas hellre än gissas.

### Metodbeslut

**Tvålagersmodellen.** Partiernas egna kapitelindelningar kan inte användas
som gemensam hierarki - S har tre kapitel utan klimatrubrik, MP har djur på
toppnivå, SD har 35 platta rubriker utan gruppering. Att sortera efter
partiets egen struktur mäter retorik, inte politik. Därför en neutral
taxonomi för jämförelse, med partiets egen rubrik bevarad i fältet
`partiets_egen_rubrik`. Skillnaden mellan lagren är i sig ett resultat.

**Konfliktaxlarna redovisas som belägg, inte som position.** Första
versionen placerade V och MP på marknadssidan av axeln stat-marknad -
uppenbart fel. Orsaken: nyckelorden räknade omnämnanden, inte ståndpunkt.
V skriver ofta "vinstjakt" och "marknadsstyrning" just för att de är emot.
Negationsdetektion ("avskaffa lagen om valfrihet") rättade riktningen men
räckte inte - ordet "marknad" matchade fortfarande "marknadsstyrning".
Axlarna snävades till entydiga flerordsfraser, vilket gav korrekta
riktningar men bara 1-4 träffar per parti. Det är för tunt för en
positionsskala, och axelvyn redovisar därför de enskilda beläggen i
stället. Medveten avgränsning: en skala hade sett mer auktoritativ ut än
underlaget tillåter.

**Färgläggning på andel, inte antal.** Mättnaden i täckningsmatrisen byggde
först på absolut antal normaliserat per rad. Det gjorde färgen till ett mått
på dokumentlängd - C har 552 förslag och V 96, så C färgades mörkt nästan
överallt utan att det sade något om prioritering. Värre: färgen och siffran
under den sade olika saker i samma ruta. Mättnaden bygger nu på andel av
partiets eget manifest, normaliserad mot högsta andel i hela matrisen.

**Ordgränsförankrad stammatchning.** Enordiga nyckelord matchas på stam för
att fånga svenska sammansättningar ("bostad" träffar "bostadsbyggande"),
men förankrat vid ordgräns. Nycklar kortare än fem tecken kräver helt ord.

### Rättat under utvecklingen

**Felträff som färgade en hel rad.** Nyckelordet `isk`
(investeringssparkonto) matchade som delsträng inne i vanliga svenska ord:
*svensk*, *högteknologisk*, *fisket*, *friskt*, *människors*, *europeisk*.
214 av 221 förslag i subdomänen kapital-förmögenhet var rena felträffar,
vilket svällde domänen ekonomi-skatt till 26% av underlaget och färgade
hela raden brun i matrisen. Upptäckt genom att en läsare ifrågasatte varför
raden såg likadan ut för alla partier.

Effekt av rättningen: ekonomi-skatt 418 → 225 förslag (26% → 14,7%),
kapital-förmögenhet 221 → 5. De domäner vars förslag tidigare kapades av
ekonomi (skola, vård, landsbygd) steg motsvarande.

Lärdom: stamavkortning utan ordgräns är farlig i svenska, där korta
fragment förekommer inuti helt orelaterade sammansättningar.

**Innehållsförteckningar** läckte in som förslag (hög andel sidnummer, få
hela meningar) och filtreras nu bort, liksom kvarvarande punktglyfer från
PDF-extraktionen.

### Hämtningsanmärkningar

**Centerpartiet** publicerar inget PDF-manifest. "Sverige kan mer"
(328 reformförslag) finns enbart som webbplats. Innehållet hämtades
strukturerat via sajtens publika WordPress REST API för de 15 sidor som
tillsammans utgör manifestet.

**Vänsterpartiet** har hela domänen bakom en Cloudflare-regel som avvisar
automatiserade klienter med HTTP 403. Dokumentet hämtades via en riktig
webbläsarsession styrd över DevTools-protokollet, efter att
Cloudflare-utmaningen passerats. Verifierat som äkta PDF.

### Kända begränsningar

- Taggningen är maskinell och oreviderad. `granskad` är `false` på samtliga
  1 528 rader.
- 40% av raderna har bara en nyckelordsträff och bör granskas manuellt.
  Enstaka felträffar kvarstår - "utdelning" matchar både aktieutdelning och
  utdelning av datorer.
- Utsagetypen "princip" är överrepresenterad eftersom heuristiken kräver ett
  tydligt verb för att klassa något som konkret reform.
- Antal förslag speglar manifestets längd och segmenterarens granularitet
  minst lika mycket som partiets prioriteringar.
- Vad "ett förslag" motsvarar varierar mellan partier, eftersom dokumenten
  har olika typografisk struktur.

### Nästa steg

- Manuell granskning av rader med `traffsakerhet <= 1`.
- Dubbeltaggning av ett parti som stickprov på systematisk bias.
- Sidhänvisning per förslag för full spårbarhet till källan.
- Komplettera med riksdagens voteringsdata - vad partierna gjort, inte lovat.

[0.1.0]: https://github.com/tomasandre/val2026/releases/tag/v0.1.0
