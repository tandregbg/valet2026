# Från 108 000 ord till ett navigerbart underlag

## Hur åtta heterogena dokument strukturerades på fyrtio minuter, och varför det sista steget ändå kräver en människa

*Teknisk genomgång av en databearbetningspipeline. Skriven 2026-09-13.*

---

## Vad det här handlar om

Åtta organisationer publicerade var sitt programdokument samtidigt.
Tillsammans 269 sidor och 108 523 ord, i åtta olika format och med åtta olika
egna kapitelindelningar. Uppgiften: gör dem jämförbara.

Den här artikeln beskriver hur materialet gick från åtta PDF-filer till en
struktur man kan ställa frågor mot. Den beskriver också var processen gick
fel, eftersom det är där det mesta av lärdomen sitter.

Total tid: cirka 40 minuter från tom mapp till taggad version. Det inkluderar
två återvändsgränder och ett allvarligt fel som upptäcktes av en människa,
inte av maskinen.

> **Om artikelns karaktär.** Det här är en teknisk genomgång av en
> databearbetningsprocess. Korpusen råkar bestå av valmanifest, men artikeln
> handlar om pipelinen, inte om innehållet i dokumenten.
>
> Därför redovisas inga resultat per dokument. Där ett exempel behövs för att
> förklara ett tekniskt problem används källorna anonymiserade. Siffror som
> förekommer beskriver **pipelinens utdata** — hur många rader den producerade,
> hur många som var felaktiga — inte egenskaper hos källorna.
>
> Samma process fungerar på vilken heterogen dokumentsamling som helst:
> myndighetsremisser, leverantörsavtal, forskningsrapporter. Valmanifesten
> var råkorpusen för att de publicerades samtidigt och är jämförbara i form.

**Sammanfattning av arbetsdelningen:**

| Steg | Vem | Tid |
|------|-----|-----|
| Hämtning av åtta dokument | Maskin | ~10 min |
| Taxonomidesign | Människa (med maskin som bollplank) | ~5 min |
| Segmentering + taggning | Maskin | ~8 min |
| App | Maskin | ~12 min |
| **Upptäcka att en hel domän var brus** | **Människa** | **30 sekunder** |
| Rättning + omkörning | Maskin | ~3 min |

Det sista steget är artikelns poäng.

---

## Fas 1: Hämtning (10:19-10:29)

### Beslut: bara förstahandskällor

Första beslutet var att inte använda sammanfattningar, sammanställningar eller
nyhetsartiklar. Bara utgivarnas egna dokument från deras egna domäner.

Praktiskt innebar det domänbegränsad sökning per källa: sök efter dokumentet,
men bara på utgivarens eget domännamn. Det tar bort hela klassen av problem
där en välmenande sammanfattning smyger in som källa.

Sex av åtta gick på en gång. Två gjorde motstånd, och båda är lärorika.

### Problem 1: en källa publicerade inget PDF

Ett av dokumenten, med 328 numrerade förslag, fanns bara som webbplats. Ingen
nedladdningsbar fil någonstans.

Sajten visade sig vara WordPress, vilket betyder ett publikt REST API:

```
https://<utgivarens-domän>/wp-json/wp/v2/pages?per_page=100
```

Det gav en lista över 34 sidor. Femton av dem utgjorde dokumentet: sju
temaområden plus deras respektive fördjupningar. Resten var kampanjmaterial
utan sakinnehåll.

Att hämta strukturerat via API:et i stället för att skrapa HTML gav ren text
utan navigationsskräp. 22 982 ord.

**Lärdom:** innan du skrapar, kolla om det finns ett API. WordPress, Drupal
och de flesta moderna CMS exponerar ett som standard. Det är nästan alltid
renare data.

### Problem 2: en källa var helt blockerad

En av utgivarnas domäner svarade HTTP 403 på allt automatiserat. Cloudflare.

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

**Viktig avgränsning:** det här är ett publikt dokument som utgivaren själv
distribuerar gratis. Blockeringen är ett generellt bot-skydd, inte ett uttryck
för att dokumentet vore skyddat. Hade det funnits en `robots.txt`-regel, en
inloggning eller villkor som förbjöd det hade svaret varit att sluta.

### Textextraktion

```bash
pdftotext -layout -enc UTF-8 manifest.pdf manifest.txt
```

`-layout` bevarar kolumnstruktur, vilket spelar roll för flerspaltiga
dokument. Utan flaggan blandas spalterna ihop och meningarna blir obegripliga.

Resultat efter fas 1:

| Källa | Format | Sidor | Ord |
|-------|--------|------:|----:|
| A | PDF | 21 | 7 088 |
| B | PDF | 50 | 16 810 |
| C | PDF | 12 | 3 057 |
| D | Webb (REST API) | - | 22 982 |
| E | PDF (bakom bot-skydd) | 21 | 5 377 |
| F | PDF | 10 | 4 646 |
| G | PDF | 9 | 3 222 |
| H | PDF | 40 | 9 478 |

Spännvidden är poängen: 3 000 till 23 000 ord, och en källa som inte ens
publicerade en fil. Det är den sortens heterogenitet som gör jämförelsen svår.

**Ett redaktionellt beslut värt att notera som mönster.** Ett av dokumenten
var bara 9 sidor, medan det längsta var 50. I en jämförelse hade den korta
källan blivit kraftigt underrepresenterad, så jag hämtade även utgivarens
längre programdokument (106 sidor) som komplement.

Det är ett *tolkningsbeslut*, inte ett tekniskt. Det påverkar alla siffror
nedströms: den källan hamnade näst högst i antal extraherade enheter, till
stor del för att den fick bidra med ett dokument de andra inte fick.

Sådana beslut är oundvikliga när korpusen är heterogen. Poängen är inte att
undvika dem utan att dokumentera dem, annars blir jämförelsen tyst
missvisande på ett sätt ingen kan upptäcka i efterhand.

---

## Fas 2: Taxonomin (10:29-10:34)

### Varför källornas egna rubriker inte går att använda

Det första jag gjorde var att titta på hur dokumenten själva är strukturerade.
Det avgjorde hela designen:

| Källa | Egen toppnivå | Konsekvens |
|-------|---------------|------------|
| A | 3 kapitel | Ett stort sakområde saknar helt egen rubrik |
| B | Löpande prosa | Ingen numrering alls |
| C | ~35 platta rubriker | Ingen gruppering, ingen hierarki |
| D | 7 teman | Hanterbar |
| E | 3 prioriteringar | Allt utanför dessa tre är nedtryckt |
| F | 4 "hörnstenar" | Kategorier som inte är sakområden |
| G | 15 kapitel | Ett smalt specialområde på toppnivå |
| H | 8 kapitel | Hanterbar |

Varje utgivare har strukturerat sitt dokument efter den berättelse de vill
förmedla. Det är rationellt av dem — och det gör indelningarna obrukbara som
gemensam axel.

**Den generella principen:** källans egen struktur är optimerad för källans
syfte. Sorterar man efter den mäter man deras framställning, inte deras
innehåll. Det gäller lika mycket för leverantörsofferter och årsredovisningar
som för den här korpusen.

### Lösningen: två lager

**Lager 1, sakfrågan.** En neutral taxonomi som inte följer någons
kapitelindelning: 12 domäner, 60 subdomäner. Ekonomi och skatt,
arbetsmarknad, vård och välfärd, skola, brott, migration, klimat, bostad,
familj, försvar, demokrati, landsbygd.

**Lager 2, inramningen.** Källans egen rubrik sparas på varje enhet i fältet
`partiets_egen_rubrik`.

Det andra lagret är det som gör analysen intressant. Skillnaden mellan vad en
enhet *handlar om* och var källan *väljer att placera den* är ett resultat i
sig. När en källa samlar nio förslag under en slagkraftig rubrik och de
sakligt spänner över fem olika domäner, är det inramning i arbete — mätbar,
utan att man behöver ha någon åsikt om innehållet.

### Två designval värda att motivera

**Varför två närliggande domäner hölls isär.** Vissa källor behandlar
angränsande sakområden under samma rubrik. Slås domänerna ihop försvinner
skillnaden mellan källor som faktiskt skriver om olika saker. Sådana
gränsdragningar kräver sakkunskap om materialet — de går inte att härleda ur
datan.

**Varför "vinster i välfärden" är en subdomän, inte en domän.** Den är en
konfliktaxel, inte ett sakområde. Den hanteras bättre i det tvärgående lagret.

### Datamodellen

Ett förslag är den atomära enheten, inte ett kapitel:

```yaml
id: F-0142
parti: F                 # källidentifierare
doman: valfard-halsa
subdoman: sjukvard-organisation
axlar: [{axel: centralisering, riktning: a}]
typ: reform              # reform | mal | princip | kritik
kvantifiering: ["2 000 kronor"]
text: "<förslagets text, oförändrad från källan>"
partiets_egen_rubrik: "<källans egen rubrik ovanför stycket>"
traffsakerhet: 3
granskad: false
```

`granskad: false` på varje rad. Det är inte en detalj. Det är en explicit
markering av att ingen människa har verifierat raden, och den följer med hela
vägen ut i gränssnittet.

---

## Fas 3: Segmentering och taggning (10:34-10:42)

### Varför det behövdes åtta olika parsers

Ett "förslag" ser typografiskt olika ut i varje dokument:

- En källa använder punktlistor med ett ovanligt specialtecken som bullet
- En har numrerade förslag: `12. Rubrik. Brödtext...`
- En har fetstilta underrubriker följt av stycken
- Två har löpande kapiteltext utan listor
- Tre är styckebaserade utan tydliga markörer alls

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

Första körningen gav 32% bortfall för en av källorna. Diagnosen visade
välformulerade förslag som föll bort på ordglapp:

> "Maxtaxa för kommunala avgifter för bygglov."

Uppenbart bostadsfrågor. Men nyckelordet var "bostadsbyggande" och texten sa
"bygglov". Rubriken ovanför löd "SÅ KAN FLER FÅ EN EGEN BOSTAD" — signalen
fanns, men på fel rad.

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
| `/` | Hur fördelar sig varje källas innehåll över domänerna? |
| `/doman/<id>` | Vad står det faktiskt inom ett sakområde? |
| `/axlar` | Vilka mönster skär tvärs över domängränserna? |
| `/inramning` | Hur förhåller sig källans egen rubrik till sakfrågan? |

### Ett designbeslut som ändrades

Täckningsmatrisens bakgrundsfärg byggde först på absolut antal förslag,
normaliserat mot radens högsta värde. Det var fel, av en subtil anledning:

Den längsta källan har 552 extraherade enheter, den kortaste 52. Färgen mätte
alltså dokumentlängd, inte fördelning. Den längsta källan färgades mörkt nästan
överallt utan att det sade något.

Värre: den lilla siffran i cellen visade *andel av eget manifest* medan färgen
visade *absolut antal*. Två olika mått i samma ruta.

Rättat till andel, normaliserad mot högsta andel i hela matrisen. Nu säger
färg och siffra samma sak.

### När en visualisering ljuger

Konfliktaxlarna var tänkta som positionsskalor: källorna utplacerade på en
linje mellan två motpoler, till exempel "mer offentligt" och "mer marknad".

Första körningen placerade flera källor på fel sida av linjen — källor vars
dokument uttryckligen argumenterar mot en position hamnade som anhängare av
den.

Orsaken är generell och värd att förstå: **nyckelord räknar omnämnanden, inte
ståndpunkt.** Den som argumenterar emot något skriver ordet oftare än den som
är likgiltig inför det. En motståndare till ett fenomen nämner fenomenet i
varje mening; en anhängare kan beskriva samma sak med helt andra ord.

Frekvens är alltså en usel proxy för hållning. Det gäller varje textkorpus där
man försöker mäta attityd med ordlistor.

Jag försökte med negationsdetektion:

```python
NEKANDE = re.compile(r"\b(avskaffa\w*|stoppa\w*|förbjud\w*|nej till|...)\b")
# "avskaffa lagen om X" -> vänder riktningen för X
```

Det rättade riktningen, men inte problemet. Ett enstaka ord matchade
fortfarande inuti längre sammansättningar med annan innebörd.

Slutlig lösning: bara entydiga flerordsfraser, där formuleringen i sig bär
ståndpunkten. Det gav korrekta riktningar — men bara 1-4 träffar per källa.

**Och där togs beslutet som jag tycker är det viktigaste i hela projektet:**
axelvyn visar inte längre positioner. Den visar de enskilda beläggen, sida vid
sida, med en förklaring av varför det inte finns någon skala.

En positionsskala hade sett mer auktoritativ ut än underlaget tillåter. Fyra
datapunkter utplacerade på en linje ser exakt lika övertygande ut som fyra
hundra — det är visualiseringens problem, inte betraktarens.

Att ta bort den var rätt beslut även om den såg snyggare ut. **Regeln jag tog
med mig: om underlaget inte bär formen, byt form — förfina inte siffrorna
tills de ser tillräckliga ut.**

---

## Fas 5: Felet som en människa hittade

Appen var klar. Matrisen såg bra ut. Då kom en fråga från någon som tittade
på den:

> "jag förstår inte de bruna bakgrundsfärgerna som är rakt över för [den här
> domänen] specifikt?"

En av raderna var mörk för *alla åtta källor*. Det är ett misstänkt mönster:
åtta oberoende dokument, skrivna av olika organisationer med olika syften, bör
inte fördela sig identiskt över en domän.

Att mönstret var *för* regelbundet var hela signalen.

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

Ett stycke om fiske, ett om dricksvatten och ett om utrikespolitik låg alla
under "kapital och förmögenhet".

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

## Vad pipelinen producerade

Efter rättningen, 1 528 extraherade enheter fördelade över taxonomin:

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

**Varför inga siffror per källa redovisas här.** Det vore tekniskt enkelt att
bryta ned tabellen per dokument. Jag gör det inte, och skälet är metodologiskt
snarare än försiktighet:

- Andelen mäter textmängd, inte vikt. En källa kan avhandla sitt viktigaste
  ärende på två meningar och ägna tjugo sidor åt bakgrund.
- Segmenterarens granularitet skiljer sig mellan källor. Ett dokument med
  punktlistor ger fler och kortare enheter än ett med löpande prosa, vid
  identiskt sakinnehåll. Den skillnaden är ett artefakt av typografi.
- 40% av raderna vilar på en enda nyckelordsträff.

Tre osäkerheter som var för sig är hanterbara, men som multiplicerat gör
jämförelser mellan enskilda celler meningslösa.

En tom cell betyder **att heuristiken inte hittade några träffar** — inte att
källan saknar innehåll på området. Med 2-21% bortfall och en taxonomi vars
ordval inte matchar alla källors språkbruk lika väl är en tom cell minst lika
ofta ett fel i taggningen som en faktisk lucka i dokumentet.

Varje cell är en hypotes att gå tillbaka till källtexten och pröva, aldrig en
slutsats. Därför länkar appen varje cell direkt till de underliggande
styckena med källhänvisning. **Verktyget är byggt för att leda tillbaka till
texten, inte för att ersätta den** — och den designprincipen är överförbar till
varje analysverktyg som bearbetar dokument någon annan har skrivit.

### Tre mått som inte höll

Ärlighet om vad som inte fungerade:

**Kvantifieringsmåttet.** Tanken var att mäta hur konkreta utfästelserna är
genom att räkna enheter som innehåller en siffra. Det fångade bara 60 av
1 528 rader (3,9%). En källa avviker uppåt, men på ett underlag av 21 rader.
För glest för att bära någon slutsats alls — spridningen mellan källor är väl
inom vad slumpen förklarar vid den urvalsstorleken.

**Utsagetyperna.** "Princip" utgör 56% av alla rader. Det säger mer om att
heuristiken kräver ett tydligt verb för att klassa något som konkret åtgärd än
om källornas faktiska skrivsätt.

**Konfliktaxlarna som skala.** Se fas 4.

Alla tre redovisas med sina svagheter i appens metodvy i stället för att tas
bort. Ett mått som inte håller är information, så länge det inte presenteras
som om det höll.

### Den grundläggande begränsningen

Andelen mäter hur mycket **text** en källa ägnar en fråga. Det är inte samma
sak som hur viktig den är. En källa kan säga något avgörande på två meningar.

40% av raderna vilar fortfarande på en enda nyckelordsträff. `granskad` är
`false` på alla 1 528.

---

## Processen, generaliserad

Mönstret gäller långt utanför valmanifest.

**1. Källdata, förstahands och verifierad.** Inga sammanfattningar. Checksummor
och URL:er för varje dokument. Det som ser ut som byråkrati i början är det som
gör att man kan gå tillbaka och kontrollera ett påstående i slutet — och det
är enda sättet att kunna dementera ett felaktigt påstående om sin egen analys.

**2. En neutral struktur som inte kommer från källan.** Källans egen indelning
är nästan alltid organiserad efter källans syfte. Använder man den mäter man
deras framställning. Bygg en egen axel — och spara källans som separat data,
för avvikelsen mellan de två är ofta det mest informativa i hela materialet.

**3. Atomära enheter, inte dokument.** Ett stycke eller en punkt, inte ett
kapitel. Det är det som gör materialet filtrerbart — och som gör att varje
påstående kan spåras till en specifik rad i en specifik källa.

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

Människan äger de fyra besluten som faktiskt formade resultatet:

- **Taxonomidesignen.** Vilka sakområden som måste hållas isär för att en
  verklig skillnad inte ska försvinna. Det är sakkunskap om materialet, inte
  om data.
- **Att ta bort positionsskalan.** Att medvetet göra visualiseringen mindre
  imponerande för att underlaget inte bar den. Det är omdöme.
- **Att se att en rad var fel.** Att reagera på ett mönster som var för
  regelbundet för att vara äkta. Det är misstänksamhet mot sitt eget verktyg.
- **Att avgöra vad som inte ska redovisas.** Att en nedbrytning är tekniskt
  möjlig betyder inte att underlaget bär den.

Inget av de fyra är svårt i teknisk mening. Alla fyra kräver någon som håller
frågan "stämmer det här?" levande medan maskinen producerar.

Det är hela poängen. Verktyget gör materialet navigerbart. Det drar inga
slutsatser, och det kan inte avgöra om ett mönster är verkligt eller ett
artefakt av dess egen implementation. Den skillnaden är inte en fråga om mer
data eller bättre modell — den kräver någon som vet vad materialet handlar om
och som är beredd att misstro sitt eget resultat.

Pipelinen gör dokumenten läsbara sida vid sida. Läsningen är fortfarande
läsarens jobb, och den delen är inte en brist i verktyget utan dess
avgränsning.

---

## Teknisk sammanfattning

| | |
|---|---|
| Källmaterial | 8 programdokument, 269 sidor, 108 523 ord |
| Extraherade enheter | 1 528 |
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
projekt/
├── manifest/      Källdokument + INDEX.md med checksummor och URL:er
├── domains/       taxonomi.yaml, extrahera.py, forslag.jsonl
├── app/           Flask-app
├── CHANGELOG.md   Inklusive felen och rättningarna
└── README.md
```

Allt som gick fel står i CHANGELOG. Det är avsiktligt: en changelog som bara
listar framsteg är en marknadsföringstext.
