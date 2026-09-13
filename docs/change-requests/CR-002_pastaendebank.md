# CR-002: Påståendebank - från taggade förslag till graderbara påståenden

| Field | Value |
|-------|-------|
| **CR Number** | CR-002 |
| **Date** | 2026-09-13 |
| **Author** | Claude Code |
| **Status** | Proposed |
| **Priority** | High |
| **Complexity** | Medium-High |
| **Estimated Scope** | domains, ny datafil, redaktionell process |
| **Related CRs** | CR-001 (frågemotor konsumerar banken), CR-003 (matchning) |
| **Depends On** | None |

---

## Executive Summary

En valkompass behöver **påståenden att gradera**, inte textstycken ur ett
dokument. De 1 528 extraherade förslagen kan inte användas som frågor rakt av:
de är olika långa, skrivna i partiets egen röst, och många innehåller
formuleringar som avslöjar avsändaren.

Den här CR:en definierar hur påståendebanken byggs. Den innehåller
valkompasskonceptets svåraste problem: hur partiskt formulerade textstycken
blir neutrala påståenden utan att införa systematisk snedvridning.

**Current Problems:**
1. Förslagen är formulerade av avsändaren och bär deras röst. Ett påstående
   som lyder "Vi vill kraftigt öka antalet läkare" avslöjar både ståndpunkt
   och sannolikt avsändare.
2. Längden varierar från en mening till ett helt stycke. Obrukbart som
   enhetliga frågor.
3. Många förslag är inte graderbara påståenden alls, utan principer eller
   kritik mot motståndare.

---

## Problem Analysis

### Varför förslagen inte kan användas direkt

Ett representativt exempel ur materialet (förkortat):

> "Öka antal läkare i primärvården. Bara en tredjedel av befolkningen uppger
> idag att de har en fast läkarkontakt på sin vårdcentral, trots all den
> forskning som visar att kontinuitet i vården leder till lägre dödlighet..."

Problemen: 71 ord, innehåller både förslag och motivering, och är skrivet i
partiets argumenterande röst.

Som graderbart påstående behöver det bli ungefär:

> "Antalet läkare i primärvården bör öka."

Det är en **redaktionell omskrivning**, inte en teknisk transformation. Och
det är precis där risken sitter.

### Riskerna med omskrivning

| Risk | Beskrivning |
|------|-------------|
| Ordval styr svar | "Kraftigt öka" mot "öka" ger olika svarsfördelning på samma sakfråga |
| Asymmetrisk formulering | Om ett partis förslag skrivs positivt och ett annats defensivt snedvrids matchningen |
| Bortfall av förbehåll | Många förslag har villkor ("i takt med att ekonomin tillåter") som försvinner |
| Falsk enkelhet | Komplexa förslag komprimeras till något som låter självklart att hålla med om |

Det här är samma klass av problem som `isk`-buggen i extraktionen, fast
värre: där producerade felet synligt brus, här producerar det **osynlig
snedvridning**. Ett dåligt formulerat påstående ser ut precis som ett bra.

### Varför det inte kan automatiseras helt

En språkmodell kan omformulera 1 528 stycken till påståenden på några minuter.
Den kan inte avgöra om resultatet är neutralt, för neutralitet är en egenskap
hos *relationen mellan* påståenden, inte hos ett enskilt påstående.

Det kräver att någon läser dem sida vid sida.

---

## Proposed Solution

### Tvåstegsprocess med mänsklig grind

```
Steg 1 (maskin)     Kandidatgenerering
                    1 528 förslag -> filtrera -> ~300 kandidater
                           ↓
Steg 2 (människa)   Redaktionell granskning
                    ~300 kandidater -> godkänn/skriv om -> ~150 påståenden
                           ↓
                    pastaenden.jsonl
```

### Steg 1: Kandidatgenerering (maskinellt)

Filtrera bort det som inte kan bli påståenden:

| Filter | Motiv |
|--------|-------|
| `typ` inte i (`reform`, `mal`) | Principer och kritik är inte graderbara som sakförslag |
| Längd > 60 ord | För långa att komprimera utan tolkning |
| Dubbletter över källor | Samma sakfråga från flera avsändare slås ihop |

**Uppmätt utfall: 305 kandidater.** Fördelning per domän varierar från 6
(bostad) till ~80 (klimat).

### Beslutat: traffsakerhet=1 släpps in

Det strama filtret (`traffsakerhet > 1`) gav bara 141 kandidater och lämnade
**8 av 12 domäner under CR-001:s minimum på 10**. Med det underlaget hade två
tredjedelar av domänvalen varit omöjliga att välja.

Beslut 2026-09-13: tillåt `traffsakerhet = 1` och `typ = mal`. Det ger 305
kandidater och 10 av 12 domäner över minimum.

**Priset, explicit:** kandidatunderlaget innehåller nu de rader som vilar på en
enda nyckelordsträff — exakt den kategori där `isk`-buggen dolde sig. Det
hanteras genom:

1. Varje kandidat med `traffsakerhet = 1` **måste** granskas manuellt innan
   den kan bli påstående. Ingen automatisk godkännning.
2. Fältet `svag_traff: true` följer med till `pastaenden.jsonl` och vidare till
   resultatvyn.
3. Bostad (6) och landsbygd (9) når fortfarande inte 10 och markeras som
   otillgängliga för domänval (CR-001 Phase 1).

Varje kandidat får ett förslag till omskrivning genererat maskinellt, som
**utgångspunkt för granskningen** — inte som färdigt påstående.

### Steg 2: Redaktionell granskning (mänsklig)

Ett granskningsgränssnitt som visar, sida vid sida:

- Originaltexten
- Källhänvisning (dokument, sida)
- Föreslagen omskrivning
- Fält för egen formulering
- Godkänn / förkasta

**Granskningskriterier** som ska stå i gränssnittet, inte i ett dokument
någon glömt:

1. Går påståendet att både hålla med om och ta avstånd från?
2. Är det fritt från värdeladdade ord ("rättvis", "ansvarsfull", "kraftfull")?
3. Skulle någon kunna gissa avsändaren från formuleringen?
4. Innehåller det exakt en sakfråga, inte två hopslagna?
5. Överlever förbehållen i originalet, eller ändrar komprimeringen innebörden?

### Datamodell

```json
{
  "id": "P-0042",
  "text": "Antalet läkare i primärvården bör öka.",
  "doman": "valfard-halsa",
  "subdoman": "primarvard",
  "kallor": [
    {"parti": "E", "forslag_id": "V-0071", "hallning": "for"},
    {"parti": "A", "forslag_id": "S-0012", "hallning": "for"}
  ],
  "granskad_av": "TA",
  "granskad_datum": "2026-09-14",
  "originaltext": "Öka antal läkare i primärvården. Bara en tredjedel...",
  "anmarkning": "Ursprungligt förslag innehöll även finansiering, utelämnat"
}
```

`originaltext` och `anmarkning` sparas alltid. Om någon ifrågasätter ett
påstående ska man kunna visa exakt vad det kommer från och vad som ströks.

### Miniminivå per domän

Frågemotorn (CR-001) behöver minst 10 påståenden per domän. Med 12 domäner är
absolut minimum 120 godkända påståenden, med marginal ~150.

Domäner som inte når 10 måste antingen:
- kompletteras med fler kandidater från svagare taggade förslag, eller
- markeras som otillgängliga för domänval

Det andra alternativet är ärligare än att fylla ut med dåliga påståenden.

---

## Beslutade frågor (2026-09-13)

**1. Vem granskar?**
En person i v1. Granskningsgränssnittet byggs så att dubbelgranskning kan
läggas till senare (fältet `granskad_av` är en lista, inte en sträng).
Deploy-målet är lokalt, vilket sänker risken av en enskild granskares bias.

**2. Påståenden som bara en källa driver?**
Behålls utan viktning. Täckningssiffran i CR-004 gör det synligt när en
matchning bygger på få belägg, vilket är en ärligare lösning än dold viktning.

**3. Påståenden som ingen driver?**
Nej. Materialet innehåller bara vad källorna själva föreslår, och att
konstruera motförslag vore att lägga in egna formuleringar i en bank som ska
vara spårbar till källtext.

**4. Motstridiga förslag inom samma sakfråga?**
Ett påstående per sakfråga, med `hallning: for|emot` per källa. `emot` sätts
**endast** när dokumentet explicit avvisar — aldrig genom tolkning av tystnad.
Se CR-003.

**5. Extern granskning?**
Krävs inte för lokalt bruk. Blir ett krav om verktyget publiceras publikt;
noteras i README som en förutsättning för publicering.

---

## Open Questions

Inga blockerande. Kvarstående att mäta under implementation:

- Faktisk granskningstakt (uppskattat ~2 min/påstående, verifieras efter 20).

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Systematisk snedvridning i formuleringar | **High** | **High** | Granskningskriterier i gränssnittet, dubbelgranskning, extern kontroll före publicering |
| För få kandidater i vissa domäner | High | Medium | Mät tidigt; markera domäner som otillgängliga hellre än att fylla ut med dåliga påståenden |
| Redaktionellt arbete underskattas, blir aldrig klart | Medium | High | Tidsuppskatta efter 20 granskade; ompröva omfattning om takten inte håller |
| Omskrivning ändrar innebörd utan att någon märker | Medium | High | `originaltext` alltid sparad och visad i resultatvyn |

---

## Nästa steg innan Proposed

1. Kör filtret, mät faktiskt antal kandidater per domän.
2. Granska 20 kandidater manuellt, tidsuppskatta resten.
3. Besvara öppen fråga 1 och 4 — de avgör om omfattningen är realistisk.
4. Först därefter: promota till Proposed med bemannad plan.
