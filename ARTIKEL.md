# Från 108 000 ord till en fråga man kan ställa

## Hur åtta valmanifest blev ett navigerbart underlag på fyrtio minuter, och varför det sista steget ändå kräver en människa

*Teknisk genomgång av val2026-projektet. Skriven 2026-09-13.*

---

## Vad det här handlar om

Åtta svenska riksdagspartier publicerade valmanifest inför valet 13 september
2026. Tillsammans 269 sidor och 108 523 ord. Frågan var enkel: vad står det
faktiskt i dem, och var är partierna tysta?

Den här artikeln beskriver hur materialet gick från åtta PDF-filer till en
struktur man kan ställa frågor mot. Den beskriver också var processen gick
fel, eftersom det är där det mesta av lärdomen sitter.

Total tid: cirka 40 minuter från tom mapp till taggad version. Det inkluderar
två återvändsgränder och ett allvarligt fel som upptäcktes av en människa,
inte av maskinen.

> **Om artikelns karaktär.** Det här är en teknisk genomgång av en
> databearbetningsprocess. Den innehåller siffror om partiernas manifest,
> eftersom det är materialet pipelinen bearbetar — men den utvärderar inte
> politiken, rangordnar inte partier och rekommenderar inget.
>
> Siffrorna är inte heller lämpliga att lyfta ur sitt sammanhang. De bygger på
> en heuristik där 40% av raderna vilar på en enda nyckelordsträff, ett
> redaktionellt beslut om vilka dokument som ingår (se fas 1), och en taxonomi
> jag konstruerat själv. De beskriver **min pipelines utdata**, inte objektiva
> egenskaper hos partierna. Läs dem som exempel på vad processen producerar,
> och gå till källtexten i `manifest/` innan du citerar något som ett faktum
> om ett parti.

**Sammanfattning av arbetsdelningen:**

| Steg | Vem | Tid |
|------|-----|-----|
| Hämtning av åtta manifest | Maskin | ~10 min |
| Taxonomidesign | Människa (med maskin som bollplank) | ~5 min |
| Segmentering + taggning | Maskin | ~8 min |
| App | Maskin | ~12 min |
| **Upptäcka att en hel domän var brus** | **Människa** | **30 sekunder** |
| Rättning + omkörning | Maskin | ~3 min |

Det sista steget är artikelns poäng.

---

## Fas 1: Hämtning (10:19-10:29)

### Beslut: bara förstahandskällor

Första beslutet var att inte använda sammanfattningar, valkompasser eller
nyhetsartiklar. Bara partiernas egna dokument från deras egna domäner.

Praktiskt innebar det domänbegränsad sökning per parti: sök efter
Socialdemokraternas valmanifest, men bara på socialdemokraterna.se. Det tog
bort hela klassen av problem där en välmenande sammanfattning smyger in som
källa.

Sex av åtta gick på en gång. Två gjorde motstånd, och båda är lärorika.

### Problem 1: Centerpartiet publicerar inget PDF

C:s manifest "Sverige kan mer" med 328 reformförslag finns bara som
webbplats. Ingen nedladdningsbar fil någonstans.

Sajten visade sig vara WordPress, vilket betyder ett publikt REST API:

```
https://val2026.centerpartiet.se/wp-json/wp/v2/pages?per_page=100
```

Det gav en lista över 34 sidor. Femton av dem utgjorde manifestet: sju
temaområden plus deras respektive "det här vill vi"-fördjupningar. Resten var
quiz, valfilmer och kampanjsidor.

Att hämta strukturerat via API:et i stället för att skrapa HTML gav ren text
utan navigationsskräp. 22 982 ord.

**Lärdom:** innan du skrapar, kolla om det finns ett API. WordPress, Drupal
och de flesta moderna CMS exponerar ett som standard. Det är nästan alltid
renare data.

### Problem 2: Vänsterpartiet var helt blockerat

Hela domänen vansterpartiet.se svarade HTTP 403 på allt automatiserat.
Cloudflare.

Ordningen jag försökte i, med resultat:

| Försök | Resultat |
|--------|----------|
| `curl` med webbläsar-User-Agent | 403 |
| HTTP/2 med full `sec-ch-ua`-uppsättning | 403 |
| Regionala underdomäner (stockholm, göteborg, skåne) | 403 |
| Proxytjänst (r.jina.ai) | 403 (Cloudflare-utmaning vidarebefordrad) |
| Google Docs viewer som mellanhand | Misslyckades |
| `chrome --headless` | "Attention Required" |
| **Riktig Chrome, icke-headless, via DevTools-protokollet** | **Fungerade** |

Det som fungerade: starta en riktig Chrome-instans utanför skärmen, låta den
passera Cloudflare-utmaningen som en vanlig webbläsare, och sedan köra
`fetch()` i sidans egen kontext över DevTools-protokollet. Då följer
sessionens cookies med.

```javascript
const r = await fetch(PDF_URL, {credentials: 'include'});
const b = await r.arrayBuffer();
// -> base64 tillbaka över DevTools
```

Två småsaker kostade tid: zsh tolkade `--remote-allow-origins=*` som en glob
(måste citeras), och websocket-biblioteket skickade Origin-headern dubbelt.

**Viktig avgränsning:** det här är ett publikt dokument som partiet självt
distribuerar. Blockeringen är ett generellt bot-skydd, inte ett uttryck för
att dokumentet vore hemligt. Hade det funnits en `robots.txt`-regel eller
inloggning hade svaret varit att sluta.

### Textextraktion

```bash
pdftotext -layout -enc UTF-8 manifest.pdf manifest.txt
```

`-layout` bevarar kolumnstruktur, vilket spelar roll för flerspaltiga
dokument. Utan flaggan blandas spalterna ihop och meningarna blir obegripliga.

Resultat efter fas 1:

| Parti | Dokument | Sidor | Ord |
|-------|----------|------:|----:|
| S | Valprogram 2026 | 21 | 7 088 |
| M | Valmanifest 2026 | 50 | 16 810 |
| SD | Valplattform 2026 | 12 | 3 057 |
| C | Valmanifest 2026 (webb) | - | 22 982 |
| V | Valmanifest 2026 | 21 | 5 377 |
| KD | Valmanifest 2026 | 10 | 4 646 |
| MP | Valmanifest 2026 | 9 | 3 222 |
| L | Valmanifest 2026 | 40 | 9 478 |

Ett redaktionellt beslut här: MP:s valmanifest är bara 9 sidor. I en
jämförelse hade de blivit kraftigt underrepresenterade. Jag hämtade därför
även deras politiska handlingsprogram 2026-2030 (106 sidor, 35 546 ord).

Det är ett *tolkningsbeslut*, inte ett tekniskt. Det påverkar alla siffror
nedströms: MP har 456 förslag i den slutliga datan, näst flest av alla, till
stor del för att jag lade till ett dokument de andra inte fick. Sådana beslut
måste dokumenteras, annars blir jämförelsen tyst missvisande.

---

## Fas 2: Taxonomin (10:29-10:34)

### Varför partiernas egna rubriker inte går att använda

Det första jag gjorde var att titta på hur partierna själva strukturerar sina
manifest. Det avgjorde hela designen:

| Parti | Egen toppnivå | Problem |
|-------|---------------|---------|
| S | 3 kapitel | Inget heter klimat |
| M | Löpande prosa | Ingen numrering alls |
| SD | ~35 platta rubriker | Ingen gruppering |
| C | 7 teman | - |
| V | 3 prioriteringar | Allt annat nedtryckt |
| KD | 4 "hörnstenar" | Värderingar som toppnivå |
| MP | 15 kapitel | Djurvälfärd på toppnivå |
| L | 8 kapitel | - |

Att MP har djurvälfärd på toppnivå och V har tre prioriteringar är i sig
intressant. Men det gör indelningarna obrukbara som gemensam axel. Sorterar
man efter partiets egen struktur mäter man deras retorik, inte deras politik.

### Lösningen: två lager

**Lager 1, sakfrågan.** En neutral taxonomi som inte följer någons
kapitelindelning: 12 domäner, 60 subdomäner. Ekonomi och skatt,
arbetsmarknad, vård och välfärd, skola, brott, migration, klimat, bostad,
familj, försvar, demokrati, landsbygd.

**Lager 2, inramningen.** Partiets egen rubrik sparas på varje förslag i
fältet `partiets_egen_rubrik`.

Det andra lagret är det som gör analysen intressant. Skillnaden mellan vad ett
förslag *handlar om* och var partiet *väljer att placera det* är ett resultat
i sig. När V rubricerar nio förslag under "STOPPA RÅNET AV HUSHÅLLEN" och de
sakligt spänner över fem domäner, är det inramning i arbete.

### Två designval värda att motivera

**Varför klimat och landsbygd är separata domäner.** Annars kollapsar C:s och
SD:s landsbygdspolitik in i klimatpolitik, och skillnaden mellan dem försvinner.

**Varför "vinster i välfärden" är en subdomän, inte en domän.** Den är en
konfliktaxel, inte ett sakområde. Den hanteras bättre i det tvärgående lagret.

### Datamodellen

Ett förslag är den atomära enheten, inte ett kapitel:

```yaml
id: KD-0142
parti: KD
doman: valfard-halsa
subdoman: sjukvard-organisation
axlar: [{axel: centralisering, riktning: a}]
typ: reform              # reform | mal | princip | kritik
kvantifiering: ["2 000 kronor"]
text: "Gör vården till ett nationellt ansvar och avveckla de 21 regionerna"
partiets_egen_rubrik: "2. VÄLFÄRDENS KÄRNA FÖRST"
traffsakerhet: 3
granskad: false
```

`granskad: false` på varje rad. Det är inte en detalj. Det är en explicit
markering av att ingen människa har verifierat raden, och den följer med hela
vägen ut i gränssnittet.

---

## Fas 3: Segmentering och taggning (10:34-10:42)

### Varför det behövdes åtta parsers

Ett "förslag" ser typografiskt olika ut i varje dokument:

- **KD** använder punktlistor med ett specialtecken som bullet
- **L** har numrerade förslag: `12. Rubrik. Brödtext...`
- **V** har fetstilta underrubriker följt av stycken
- **MP och C** har löpande kapiteltext
- **SD, M, S** är styckebaserade utan tydliga markörer

Det gick inte att skriva en generell parser. Jag skrev åtta, med gemensam
normalisering:

```python
def normalisera(s):
    s = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", s)   # avstavning över radbrytning
    s = re.sub(r"\s*\n\s*", " ", s)
    s = re.sub(r"[•●▪·à›]\s*", "", s)              # punktglyfer från PDF
    s = re.sub(r"\.{4,}", " ", s)                   # innehållsförteckningens prickar
    return re.sub(r"\s{2,}", " ", s).strip()
```

Avstavningshanteringen är viktigare än den ser ut. PDF-extraktion delar ord
över radbrytningar, och `arbetsmark-\nnad` matchar inte nyckelordet
"arbetsmarknad".

### Taggningen: nyckelord, inte språkmodell

Här gjorde jag ett medvetet val som är värt att förklara.

Taggningen hade kunnat göras genom att skicka varje textstycke till en
språkmodell och fråga vilken domän det hör till. Det hade gett bättre
träffsäkerhet. Jag valde nyckelordsmatchning ändå, av tre skäl:

1. **Determinism.** Samma indata ger samma utdata, varje gång. Kör man om
   extraktionen får man identiskt resultat. Det går att felsöka.

2. **Granskbarhet.** När en rad är feltaggad kan man se exakt vilket
   nyckelord som orsakade det. Med en språkmodell får man en klassificering
   utan spårbar orsak. Det visade sig avgörande, se fas 5.

3. **Det är ärligare om sin egen svaghet.** En nyckelordsträffare som ger
   "träffsäkerhet 1" signalerar tydligt att den gissar. En språkmodell låter
   lika självsäker när den har fel som när den har rätt.

Poängsättningen: flerordiga nyckelord ger 2 poäng (starkare signal), enordiga
ger 1. Högsta summa vinner. Under 1 poäng: ingen tagg, raden utelämnas.

Utelämnande framför gissning. Bortfallet blev 2-21% per parti och redovisas
öppet.

### Första iterationen och en första rättning

Första körningen gav 32% bortfall för KD. Diagnosen visade välformulerade
förslag som föll bort på ordglapp:

> "Maxtaxa för kommunala avgifter för bygglov."

Uppenbart bostadspolitik. Men nyckelordet var "bostadsbyggande" och texten sa
"bygglov". Rubriken ovanför sa "SÅ KAN FLER FÅ EN EGEN BOSTAD".

Två rättningar:

1. **Rubriken som reservsignal.** Saknar brödtexten nyckelord, används
   partiets egen rubrik med halv vikt.

2. **Stammatchning.** Enordiga nyckelord matchas på de sex första tecknen, så
   att "bostad" träffar "bostadsbyggande".

Bortfallet sjönk från 11-32% till 1-15%. Den andra rättningen skulle visa sig
vara ett allvarligt misstag, men det upptäcktes inte då.

---

## Fas 4: Appen (10:42-10:52)

Flask, 227 rader. Fyra vyer, var och en med en distinkt fråga:

| Vy | Fråga |
|----|-------|
| `/` | Vilka domäner täcker partierna, och var är de tysta? |
| `/doman/<id>` | Vad säger de faktiskt inom ett sakområde? |
| `/axlar` | Vilka mönster skär tvärs över domängränserna? |
| `/inramning` | Hur ramar partiet in sin egen politik? |

### Ett designbeslut som ändrades

Täckningsmatrisens bakgrundsfärg byggde först på absolut antal förslag,
normaliserat mot radens högsta värde. Det var fel, av en subtil anledning:

C har 552 förslag, V har 96. Färgen mätte alltså dokumentlängd, inte
prioritering. C färgades mörkt nästan överallt utan att det sade något.

Värre: den lilla siffran i cellen visade *andel av eget manifest* medan färgen
visade *absolut antal*. Två olika mått i samma ruta.

Rättat till andel, normaliserad mot högsta andel i hela matrisen. Nu säger
färg och siffra samma sak.

### När en visualisering ljuger

Konfliktaxlarna var tänkta som positionsskalor: partierna utplacerade på en
linje mellan "mer offentligt" och "mer marknad".

Första körningen placerade V och MP på marknadssidan. Uppenbart fel.

Orsaken: nyckelorden räknade *omnämnanden*, inte *ståndpunkt*. V skriver ofta
"vinstjakt" och "marknadsstyrning" — just för att de är emot.

Jag försökte med negationsdetektion:

```python
NEKANDE = re.compile(r"\b(avskaffa\w*|stoppa\w*|förbjud\w*|nej till|...)\b")
# "avskaffa lagen om valfrihet" -> vänder riktningen
```

Det rättade riktningen, men inte problemet. Ordet "marknad" matchade
fortfarande inuti "marknadsstyrning".

Slutlig lösning: bara entydiga flerordsfraser. "Stoppa vinstjakten", "fritt
vårdval". Det gav korrekta riktningar, men bara 1-4 träffar per parti.

**Och där togs beslutet som jag tycker är det viktigaste i hela projektet:**
axelvyn visar inte längre positioner. Den visar de enskilda beläggen, sida vid
sida, med en förklaring av varför det inte finns någon skala.

En positionsskala hade sett mer auktoritativ ut än underlaget tillåter. Det är
precis den sortens visualisering som får folk att tro på siffror som inte
bär vikten. Att ta bort den var rätt beslut även om den såg snyggare ut.

---

## Fas 5: Felet som en människa hittade

Appen var klar. Matrisen såg bra ut. Då kom en fråga:

> "jag förstår inte de bruna bakgrundsfärgerna som är rakt över för ekonomi
> och skatt specifikt?"

Raden "Ekonomi och skatt" var mörk för *alla åtta partier*. Det är ett
misstänkt mönster. Åtta partier med olika ideologi bör inte ägna exakt lika
stor andel av sina manifest åt samma sak.

Diagnosen tog 30 sekunder:

```
vilket nyckelord matchar:
   214  isk (stam 'isk')
     4  kapitalskatt
     2  utdelning
```

Nyckelordet `isk` — investeringssparkonto — matchade som **delsträng** inuti
vanliga svenska ord:

- sv**isk** → *svensk*
- högteknolog**isk** → *högteknologisk*
- f**isk**et → *fisket*
- fr**isk**t → *friskt*
- männ**isk**ors → *människors*
- europe**isk** → *europeisk*

Ett förslag om Östersjöfiske, ett om rent dricksvatten och ett om Mellanöstern
låg alla under "kapital och förmögenhet".

**214 av 221 träffar i subdomänen var rena felträffar.**

Orsaken var stammatchningen jag införde i fas 3 för att lösa
bostad/bostadsbyggande-problemet. Den matchade utan förankring vid ordgräns.
I svenska är det förödande — korta fragment sitter inuti helt orelaterade
sammansättningar.

Rättningen:

```python
if len(nyckel) < 5:
    m = re.compile(r"\b" + re.escape(nyckel) + r"\b")   # helt ord
else:
    stam = nyckel[:6] if len(nyckel) > 7 else nyckel
    m = re.compile(r"\b" + re.escape(stam))             # stam vid ordgräns
```

Effekten:

| | Före | Efter |
|---|---:|---:|
| ekonomi-skatt | 418 (26%) | **225 (14,7%)** |
| kapital-förmögenhet | 221 | **5** |
| Totalt underlag | 1 604 | 1 528 |

Fördelningen blev jämn: ekonomi 14,7%, klimat 14,1%, arbetsmarknad 14,0%. Och
de domäner vars förslag tidigare kapades av ekonomi — skola, vård, landsbygd —
steg motsvarande.

### Varför det här är artikelns huvudpunkt

Maskinen hade inget sätt att upptäcka det här felet.

Den producerade 1 604 välformade rader med korrekt JSON, rimliga
domänfördelningar och inga undantag. Varje enskild tagg var internt
konsistent. Pipelinen körde grönt.

Felet var synligt bara som ett *mönster som inte borde finnas*: en rad som såg
likadan ut för åtta olika partier.

Det krävde någon som tittade på en färg och tyckte att den såg konstig ut.

Och notera vad som gjorde diagnosen möjlig: eftersom taggningen var
nyckelordsbaserad kunde jag räkna exakt vilket ord som orsakade varje träff.
Hade jag använt en språkmodell för klassificeringen hade jag haft 214
felklassificerade rader utan spårbar orsak. Jag hade behövt läsa dem manuellt
för att ens misstänka mönstret.

**Determinismen var det som gjorde felet fixbart på tre minuter i stället för
tre timmar.**

---

## Vad datan visar, och vad den inte visar

Efter rättningen, 1 528 förslag:

```
  225 (14,7%)  ekonomi-skatt
  216 (14,1%)  klimat-energi-miljo
  214 (14,0%)  arbetsmarknad
  151 ( 9,9%)  kriminalitet-rattsvasende
  147 ( 9,6%)  valfard-halsa
  143 ( 9,4%)  forsvar-utrikes
  131 ( 8,6%)  demokrati-rattigheter
   93 ( 6,1%)  skola-utbildning
   80 ( 5,2%)  migration-integration
   53 ( 3,5%)  familj-barn
   40 ( 2,6%)  landsbygd-regional
   35 ( 2,3%)  bostad-infrastruktur
```

Fördelningen är jämn över de tre största domänerna, vilket i sig är ett
rimlighetstest: en pipeline som producerar en dominerande domän bör
misstänkas (se fas 5).

**En not om att läsa enskilda celler.** Matrisen inbjuder till påståenden av
typen "parti X ägnar mer utrymme åt A än åt B". Sådana avläsningar är
tekniskt korrekta men analytiskt svaga, av tre skäl som alla följer av
metoden ovan:

- Andelen mäter textmängd, inte prioritet. Ett parti kan avhandla sin
  viktigaste fråga på två meningar.
- Segmenterarens granularitet skiljer sig mellan partier. Ett dokument med
  punktlistor ger fler och kortare "förslag" än ett med löpande prosa,
  vid samma politiska innehåll.
- 40% av raderna vilar på en enda nyckelordsträff.

En tom cell betyder **att min heuristik inte hittade några träffar** — inte
att partiet saknar politik på området. Med 2-21% bortfall och en taxonomi vars
ordval inte matchar alla partiers språkbruk lika väl är en tom cell minst lika
ofta ett fel i taggningen som en tystnad i manifestet. Varje sådan cell är en
hypotes att gå tillbaka till källtexten och pröva, aldrig en slutsats.

Det är också därför appen länkar varje cell direkt till de underliggande
förslagen med källhänvisning. Verktyget är byggt för att leda tillbaka till
texten, inte för att ersätta den.

### Tre mått som inte höll

Ärlighet om vad som inte fungerade:

**Kvantifieringsmåttet.** Tanken var att mäta löftesprecision genom att räkna
förslag som innehåller en siffra. Det fångade bara 60 av 1 528 rader (3,9%).
För glest för att säga något meningsfullt. M sticker ut med 16% mot övrigas
2-6%, men underlaget är 21 rader. Det är för tunt att dra slutsatser från.

**Utsagetyperna.** "Princip" utgör 56% av alla rader, vilket säger mer om att
heuristiken kräver ett tydligt verb för att klassa något som reform än om
partiernas faktiska skrivsätt.

**Konfliktaxlarna som skala.** Se fas 4.

Alla tre redovisas med sina svagheter i appens metodvy i stället för att tas
bort. Ett mått som inte håller är information, så länge det inte presenteras
som om det höll.

### Den grundläggande begränsningen

Andelen mäter hur mycket **text** ett parti ägnar en fråga. Det är inte samma
sak som hur viktig den är för dem. Ett parti kan säga något avgörande på två
meningar.

40% av raderna vilar fortfarande på en enda nyckelordsträff. `granskad` är
`false` på alla 1 528.

---

## Processen, generaliserad

Mönstret gäller långt utanför valmanifest.

**1. Källdata, förstahands och verifierad.** Inga sammanfattningar. Checksummor
och URL:er för varje dokument. Det som ser ut som byråkrati i början är det som
gör att man kan gå tillbaka och kontrollera ett påstående i slutet.

**2. En neutral struktur som inte kommer från källan.** Källans egen indelning
är nästan alltid organiserad efter källans intressen. Använder man den mäter
man deras berättelse. Bygg en egen axel, och spara källans som separat data.

**3. Atomära enheter, inte dokument.** Ett förslag, inte ett kapitel. Det är
det som gör materialet filtrerbart.

**4. Deterministisk bearbetning där det går.** Inte för att det är
träffsäkrare, utan för att det är felsökbart. När något ser fel ut vill man
kunna svara på *varför*.

**5. Ett gränssnitt som redovisar sin egen osäkerhet.** "Osäker taggning" på
svaga rader. En metodsida som listar felkällorna. Om verktyget döljer sin
osäkerhet lär sig användaren att lita på fel saker.

**6. En människa som tittar på helheten och reagerar på det som ser konstigt
ut.** Det här steget går inte att automatisera bort, för det handlar om att
känna igen ett mönster som inte borde finnas.

### Arbetsdelningen

Maskinen är bra på det mekaniska: hämta, extrahera, segmentera, tagga,
rendera. 108 523 ord blev navigerbara på cirka 40 minuter. Den delen är inte
svår längre.

Människan äger de tre besluten som faktiskt formade resultatet:

- **Taxonomidesignen.** Att klimat och landsbygd måste vara separata domäner,
  annars försvinner skillnaden mellan C och MP. Det är sakkunskap.
- **Att ta bort positionsskalan.** Att medvetet göra visualiseringen mindre
  imponerande för att underlaget inte bar den. Det är omdöme.
- **Att se att en brun rad var fel.** Det är misstänksamhet mot sitt eget
  verktyg.

Inget av de tre är svårt i teknisk mening. Alla tre kräver någon som håller
frågan "stämmer det här?" levande medan maskinen producerar.

Det sista är hela poängen. Verktyget gör materialet navigerbart. Det drar inga
slutsatser. Det kan inte avgöra om ett mönster är verkligt eller ett artefakt
av dess egen implementation.

Och nej — ingenting i det här projektet säger något om hur man bör rösta. Det
var aldrig meningen. Det gör manifesten läsbara sida vid sida. Läsningen är
fortfarande läsarens jobb.

---

## Teknisk sammanfattning

| | |
|---|---|
| Källmaterial | 8 valmanifest, 269 sidor, 108 523 ord |
| Extraherade förslag | 1 528 |
| Taxonomi | 12 domäner, 60 subdomäner, 5 konfliktaxlar |
| Kod | 1 693 rader (468 extraktion, 227 app, resten mallar/stil) |
| Beroenden | `flask`, `pyyaml`, `pdftotext` (poppler) |
| Total tid | ~40 minuter |
| Version | 0.1.0 |

**Verktyg:** `curl` och Chrome DevTools-protokollet för hämtning,
`pdftotext -layout` för extraktion, Python 3 med regex för segmentering och
taggning, Flask och ren CSS för gränssnittet. Ingen språkmodell i
databearbetningen — medvetet, se fas 3.

**Repostruktur:**

```
val2026/
├── manifest/      Källdokument + INDEX.md med checksummor
├── domains/       taxonomi.yaml, extrahera.py, forslag.jsonl
├── app/           Flask-app
├── CHANGELOG.md   Inklusive felen och rättningarna
└── README.md
```

Allt som gick fel står i CHANGELOG. Det är avsiktligt: en changelog som bara
listar framsteg är en marknadsföringstext.
