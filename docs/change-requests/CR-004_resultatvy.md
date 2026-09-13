# CR-004: Resultatvy - matchning med spårbarhet till källförslagen

| Field | Value |
|-------|-------|
| **CR Number** | CR-004 |
| **Date** | 2026-09-13 |
| **Author** | Claude Code |
| **Status** | Proposed |
| **Priority** | Medium |
| **Complexity** | Medium |
| **Estimated Scope** | app, ny vy |
| **Related CRs** | CR-001, CR-002, CR-003 |
| **Depends On** | CR-003 (behöver matchningsresultat att visa) |
| **Breaking Changes** | No |

---

## Executive Summary

Resultatvyn ska svara på två frågor i den ordningen: *vilka källor ligger
närmast mina svar*, och *vilka konkreta förslag är det som ligger bakom den
siffran*.

Den andra frågan är den som gör verktyget annorlunda än en vanlig valkompass.
Där andra verktyg stannar vid en procentsats leder det här tillbaka till de
faktiska textstyckena i källdokumenten.

**Current Problems:**
1. En matchningsprocent utan underlag är ett påstående användaren måste ta på
   tro.
2. Befintliga verktyg visar resultat men inte vad resultatet bygger på, vilket
   gör dem omöjliga att ifrågasätta.

---

## Problem Analysis

### Vad brainstormen efterfrågade

Formuleringen ur transkriptet, om vad resultatet ska visa:

> "man får som en stapel [...] till exempel ekonomi och välfärd, [källa X]
> 56 förslag. Alltså så, så man får liksom det, där ser man liksom det du har
> klickat in. Då får du många förslag som har lagts fram för det du vill."

Och om varför:

> "Istället för att bara få de svar där som du inte måste gå och läsa igenom
> för mycket, utan du får snaps om du behöver."

Alltså: översikt först, detaljer på begäran. Inte en vägg av text, men
detaljerna ska finnas ett klick bort.

Notera också preciseringen i transkriptet om vad matchningen betyder:

> "inte vilket som stämmer överens, vilket parti vill lika mycket som du"

Det är en skillnad värd att respektera i ordvalen: verktyget visar
**överensstämmelse mellan dina svar och vad källorna föreslår**, inte en
rekommendation.

---

## Proposed Solution

### Vylayout, tre nivåer

```
Nivå 1   Rangordnade staplar per källa
         + täckningssiffra (obligatorisk)
              ↓ klick
Nivå 2   Nedbrytning per domän för vald källa
              ↓ klick
Nivå 3   De faktiska förslagen med källhänvisning
```

### Nivå 1: Översikt

En stapel per källa, rangordnade. Varje rad visar:

| Element | Exempel | Motiv |
|---------|---------|-------|
| Källa | Källa B | |
| Matchning | 72% | Från CR-003 |
| Täckning | belägg för 31 av 50 | **Obligatorisk**, se CR-003 |
| Stapel | ▓▓▓▓▓▓▓░░░ | Visuell jämförelse |

Källor under täckningströskeln visas gråmarkerade med varning, inte dolda.
Att dölja dem vore att fatta ett beslut åt användaren.

**Obligatorisk textrad ovanför resultatet:**

> Procenten visar hur väl dina svar stämmer med de förslag som går att belägga
> i respektive dokument. Den bygger på maskinellt extraherad text där 40 % av
> underlaget vilar på en enda nyckelordsträff. Den är en ingång till
> materialet, inte ett omdöme.

### Nivå 2: Nedbrytning per domän

För vald källa: hur fördelar sig överensstämmelsen över domänerna?

De domäner användaren valde som sina tre viktigaste markeras tydligt, eftersom
det troligen är dem de bryr sig om.

Här visas också **oenigheten** — påståenden där användaren och källan drar åt
olika håll. Ett verktyg som bara visar överensstämmelse är en
bekräftelsemaskin.

### Nivå 3: Källförslagen

De faktiska textstyckena, med:

- Originaltext (inte den omskrivna påståendeversionen)
- Källhänvisning: dokument och sida
- Vilket påstående det kopplades till
- Användarens eget svar på det påståendet

Om påståendet skrevs om från originalet (CR-002) visas båda versionerna. Den
som vill kontrollera att omskrivningen var rimlig ska kunna göra det.

### Vad vyn inte ska göra

Explicit uteslutet:

- Ingen rekommendation, ingen "ditt parti"-formulering
- Ingen delningsknapp med förifyllt resultat (se CR-001 öppen fråga)
- Ingen sammanfattning i fritext av vad resultatet "betyder"

Det sista är viktigast. En genererad text som tolkar resultatet åt användaren
lägger ett tolkningslager ovanpå ett redan osäkert underlag.

---

## Implementation Plan

### Phase 1: Nivå 1

1. Route `/kompass/resultat`
2. Beräkna via CR-003, rendera rangordnade staplar
3. Täckningssiffra och förbehållstext
4. Gråmarkering under tröskel

### Phase 2: Nivå 2

1. Route `/kompass/resultat/<kalla>`
2. Domännedbrytning, valda domäner markerade
3. Separat sektion för oenighet

### Phase 3: Nivå 3

1. Utfällbara förslag under varje domän
2. Original + omskrivning + källhänvisning
3. Länk vidare till befintlig `/doman/<id>`-vy

---

## Files to Modify/Create

| File | Action | Changes |
|------|--------|---------|
| `app/app.py` | Modify | Routes `/kompass/resultat`, `/kompass/resultat/<kalla>` |
| `app/templates/kompass_resultat.html` | **CREATE** | Nivå 1 och 2 |
| `app/static/stil.css` | Modify | Staplar, nedbrytning, utfällning |

---

## Testing Plan

### Test Case 1: Täckningssiffran syns alltid

- Generera resultat
- Verifiera: varje källa visar både procent och antal belägg
- Verifiera: ingen vy visar procent isolerat

### Test Case 2: Låg täckning gråmarkeras

- Konstruera svar där en källa får belägg för 6 av 50
- Verifiera: gråmarkerad med varning, fortfarande synlig

### Test Case 3: Oenighet visas

- Svara emot en källas tydliga linje
- Verifiera: oenighetssektionen listar de påståendena

### Test Case 4: Spårbarhet hela vägen

- Klicka från stapel till domän till förslag
- Verifiera: originaltext och sidhänvisning finns
- Verifiera: omskriven version visas bredvid originalet

### Test Case 5: Förbehållstexten går inte att missa

- Ladda resultatvyn
- Verifiera: förbehållet syns utan att skrolla, på både desktop och mobil

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Procenten uppfattas som exakt trots förbehåll | **High** | **High** | Täckning alltid bredvid procenten; förbehåll ovanför resultatet, inte under |
| Resultatet delas som skärmdump utan kontext | High | Medium | Förbehållstexten placerad så att den kommer med i en normal skärmdump |
| Användaren stannar på nivå 1 och missar underlaget | Medium | Medium | Nivå 2 nås med ett klick; antal förslag visas redan på nivå 1 |
| Oenighetssektionen upplevs som negativ | Low | Low | Neutral rubrik ("Där ni skiljer er åt"), inte värderande |

---

## Rollback

1. Ta bort resultatroutes från `app/app.py`
2. Radera `kompass_resultat.html`
3. Återställ `stil.css`

---

## Open Questions

- Ska resultatet kunna exporteras som PDF? Sannolikt nej i v1 — det skapar ett
  dokument som lever vidare utan förbehållen.
- Ska användaren kunna ändra enskilda svar från resultatvyn och se hur
  matchningen förändras? Pedagogiskt bra, men riskerar att inbjuda till att
  justera svaren tills önskat resultat uppnås.
