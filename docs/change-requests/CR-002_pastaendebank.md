# CR-002: Påståendebank - från taggade förslag till graderbara påståenden

| Field | Value |
|-------|-------|
| **CR Number** | CR-002 |
| **Date** | 2026-09-13 |
| **Author** | Claude Code |
| **Status** | Draft |
| **Priority** | High |
| **Estimated Scope** | domains, ny datafil, redaktionell process |
| **Related CRs** | CR-001 (frågemotor konsumerar banken), CR-003 (matchning) |
| **Depends On** | None |

---

## Executive Summary

En valkompass behöver **påståenden att gradera**, inte textstycken ur ett
dokument. De 1 528 extraherade förslagen kan inte användas som frågor rakt av:
de är olika långa, skrivna i partiets egen röst, och många innehåller
formuleringar som avslöjar avsändaren.

Den här CR:en definierar hur påståendebanken byggs — och den är avsiktligt
**Draft**, för den innehåller det svåraste öppna problemet i hela
valkompasskonceptet.

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
| `typ != "reform"` | Principer och kritik är inte graderbara som sakförslag |
| `traffsakerhet <= 1` | 40% av materialet, för osäkert taggat |
| Längd > 60 ord | För långa att komprimera utan tolkning |
| Dubbletter över källor | Samma sakfråga från flera avsändare slås ihop |

Kvar: uppskattningsvis 250-350 kandidater. Behöver mätas.

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

## Open Questions

Det här är skälet till att CR:en är Draft.

**1. Vem granskar?**
150 påståenden à ~2 minuter är ungefär 5 timmars redaktionellt arbete. Det är
inte en eftermiddag. Ska det göras av en person, eller behövs två oberoende
för att fånga systematisk snedvridning?

**2. Hur hanteras påståenden som bara en källa driver?**
Ett påstående som bara förekommer i ett dokument ger automatiskt hög matchning
med den avsändaren om användaren instämmer. Det kan vara korrekt — eller ge
oproportionerligt utslag. Behövs viktning?

**3. Ska påståenden som ingen driver finnas med?**
För att mäta avstånd behövs kanske påståenden som *alla* källor avvisar. De
finns inte i materialet, eftersom materialet bara innehåller vad avsändarna
själva föreslår. Ska sådana konstrueras, och i så fall av vem?

**4. Hur hanteras motstridiga förslag inom samma sakfråga?**
Två källor kan vilja motsatta saker i samma fråga. Blir det ett påstående där
den ena är "för" och den andra "emot", eller två separata påståenden?
Det första är renare men kräver att man tolkar in motstånd som inte står
skrivet.

**5. Krävs extern granskning innan publicering?**
Om verktyget publiceras bör någon utan koppling till projektet granska
påståendebanken för snedvridning. Vem, och enligt vilka kriterier?

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
