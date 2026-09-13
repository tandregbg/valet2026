# CR-001: Valkompass - domänval och frågemotor

| Field | Value |
|-------|-------|
| **CR Number** | CR-001 |
| **Date** | 2026-09-13 |
| **Author** | Claude Code |
| **Status** | Proposed |
| **Priority** | High |
| **Complexity** | Medium |
| **Estimated Scope** | app, domains, ny datamodell för svar |
| **Related CRs** | CR-002 (påståendebank), CR-003 (matchning), CR-004 (resultatvy) |
| **Depends On** | CR-002 (påståendebanken måste finnas innan motorn kan servera frågor) |
| **Breaking Changes** | No |

---

## Executive Summary

Täckningsmatrisen visar hur materialet fördelar sig, men besvarar inte
frågan en användare faktiskt har: *vad tycker jag, och vilka förslag ligger
nära det?* Den här CR:en bygger flödet som tar användaren från domänval till
besvarade frågor.

Konceptet kommer från en brainstorm 2026-09-13 (Livia, Tomas). Kärnidén: låt
användaren välja **max tre domäner** som sina viktigaste frågor, servera sedan
50 påståenden att gradera, viktade mot de valda domänerna.

**Current Problems:**
1. Materialet är strukturerat men bara navigerbart uppifrån och ner. Det finns
   ingen väg in för någon som vet vad de tycker men inte vad som står i
   dokumenten.
2. Befintliga valkompasser använder fyrgradig skala utan mittenläge, vilket
   tvingar fram en ståndpunkt även när användaren är neutral.

---

## Problem Analysis

### Nuläge

Appen har fyra vyer som alla utgår från materialet: täckningsmatris,
domändjupdykning, konfliktaxlar, inramning. Alla kräver att användaren redan
vet vad de letar efter.

De 1 528 taggade förslagen är en tillgång som inte används för det mest
uppenbara ändamålet: att låta någon jämföra sina egna åsikter mot vad som
faktiskt står i dokumenten.

### Observation från brainstormen

Om skalan i befintliga verktyg (fyra smileys, mycket dåligt till mycket bra):

> "det finns ju ingen i mitten [...] Man kan ju tycka att ett förslag är ändå
> bara okej, det är inte dåligt. Det blir inte bra, men man tycker ändå att
> det hade funkat."

Det är ett konkret designfel att åtgärda, inte en smaksak. En jämn skala utan
mittpunkt tvingar fram falsk polarisering i datan.

### Avgränsning mot befintliga verktyg

Skillnaden mot etablerade valkompasser är att svaren här matchas mot
**faktiska textstycken ur källdokumenten**, inte mot partiernas svar på en
enkät. Det gör resultatet spårbart: varje matchning kan pekas tillbaka till
ett stycke i ett manifest.

Det är också den svåraste delen, och den ligger i CR-002 och CR-003.

---

## Proposed Solution

### Flöde

```
1. Domänval        Välj max 3 av 12 domäner
       ↓
2. Frågesekvens    50 påståenden, gradera 1-5
       ↓
3. Resultat        Matchning + spårning till källförslag (CR-004)
```

### Steg 1: Domänval

De 12 domänerna från `taxonomi.yaml` presenteras som valbara kort. Användaren
väljer **upp till tre**.

Beslut från brainstormen: max tre, inte fritt antal.

> "Nej, tre. Tre stycken? Max tre. Det här är mina tre viktiga frågor inför
> valet."

Tre är också vad som får plats i en fördelning på 30 frågor utan att varje
domän blir för tunn (10 frågor per domän).

**Designval:** användaren ska kunna välja *färre* än tre. Väljer man en enda
domän blir fördelningen 10 riktade + 40 blandade. Det är ett giltigt val som
inte ska blockeras.

### Steg 2: Frågefördelning

| Typ | Antal | Urval |
|-----|------:|-------|
| Riktade | 10 per vald domän (max 30) | Påståenden från de valda domänerna |
| Blandade | 50 minus riktade | Fördelade över resterande domäner |
| **Totalt** | **50** | |

Med tre valda domäner: 30 riktade + 20 blandade.
Med en vald domän: 10 riktade + 40 blandade.

De blandade frågorna finns för att resultatet inte ska bli självuppfyllande.
Väljer man bara klimat och bara får klimatfrågor blir matchningen cirkulär.

### Steg 3: Graderingsskala

Fem steg, 1 till 5:

| Värde | Betydelse |
|-------|-----------|
| 1 | Tar helt avstånd |
| 2 | Tveksam |
| 3 | Neutral / kan fungera |
| 4 | Positiv |
| 5 | Instämmer helt |

Plus ett separat **"hoppa över"** som inte är samma sak som 3. En överhoppad
fråga ska inte räknas in i matchningen alls, medan en trea är ett aktivt
neutralt svar.

Varför 5 och inte 10:

> "1-10 kommer vara för långt, så då kommer vi för mycket att läsa in."

### Datamodell

Svar lagras klientside (localStorage) under pågående session. Ingen
serverlagring i denna CR — det kräver en integritetsdiskussion som inte är
förd.

```json
{
  "valda_domaner": ["klimat-energi-miljo", "skola-utbildning", "valfard-halsa"],
  "svar": [
    {"pastaende_id": "P-0142", "varde": 4},
    {"pastaende_id": "P-0087", "varde": null, "hoppad": true}
  ],
  "startad": "2026-09-13T11:13:00Z",
  "taxonomi_version": "0.1.0"
}
```

`taxonomi_version` sparas så att ett resultat kan ogiltigförklaras om
taxonomin ändras under pågående session.

---

## Implementation Plan

### Phase 1: Domänval

1. Ny route `/kompass` med domänvalsvy.
2. Kortlayout för de 12 domänerna, återanvänd färgerna från `taxonomi.yaml`.
3. Klientlogik: max 3 val, fortsätt-knapp aktiveras vid minst 1.
4. Spara val i localStorage.

### Phase 2: Frågemotor

1. Urvalsalgoritm: dra 10 per vald domän + fyll ut till 50 från övriga.
2. Deterministiskt urval med seed, så att samma val ger samma frågor
   (viktigt för att kunna felsöka och för att två personer ska kunna
   jämföra).
3. Route `/kompass/fragor` med en fråga i taget, progressindikator.
4. Navigering framåt/bakåt, svar sparas löpande.

### Phase 3: Skala och interaktion

1. Femgradig skala med tydliga etiketter, inte bara siffror.
2. Separat "hoppa över"-knapp.
3. Tangentbordsstöd (1-5 + piltangenter) — 50 frågor är många att klicka.

---

## Files to Modify/Create

| File | Action | Changes |
|------|--------|---------|
| `app/app.py` | Modify | Routes `/kompass`, `/kompass/fragor` |
| `app/kompass.py` | **CREATE** | Urvalsalgoritm, fördelningslogik |
| `app/templates/kompass_start.html` | **CREATE** | Domänval |
| `app/templates/kompass_fragor.html` | **CREATE** | Frågesekvens |
| `app/static/kompass.js` | **CREATE** | Klientlogik, localStorage, tangentbord |
| `app/static/stil.css` | Modify | Stilar för kort, skala, progress |

---

## Testing Plan

### Test Case 1: Fördelning vid tre valda domäner

- Välj tre domäner, starta frågesekvens
- Verifiera: exakt 50 frågor, varav 30 från valda domäner (10 per domän)
- Verifiera: 20 blandade från övriga nio domäner

### Test Case 2: Fördelning vid en vald domän

- Välj en domän
- Verifiera: 10 riktade + 40 blandade, totalt 50

### Test Case 3: Domän med för få påståenden

- Simulera domän med färre än 10 tillgängliga påståenden
- Verifiera: fyller ut från närliggande domän, loggar varning, kraschar inte

### Test Case 4: Hoppa över

- Hoppa över 5 frågor
- Verifiera: de räknas inte som neutrala i underlaget
- Verifiera: resultatvyn redovisar antalet överhoppade

### Test Case 5: Avbrott och återupptagande

- Svara på 20 frågor, ladda om sidan
- Verifiera: sessionen återupptas på fråga 21 med svaren kvar

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| För få kvalitetssäkrade påståenden i vissa domäner | High | High | CR-002 sätter miniminivå per domän; motorn fyller ut och varnar |
| 50 frågor är för många, användare hoppar av | Medium | Medium | Progressindikator, tangentbord, möjlighet att få preliminärt resultat efter 25 |
| Deterministiskt urval gör verktyget förutsägbart/gamebart | Low | Low | Acceptabelt; spårbarheten väger tyngre |
| localStorage otillgängligt (privat läge) | Medium | Low | Fallback till sessionsminne, varna att omladdning nollställer |

---

## Rollback

1. Ta bort routes `/kompass*` från `app/app.py`.
2. Radera `app/kompass.py`, kompass-mallarna och `kompass.js`.
3. Återställ `stil.css` till föregående commit.

Ingen befintlig funktionalitet berörs — CR:en är additiv.

---

## Open Questions

- Ska resultatet gå att dela via länk? Det kräver att svaren kodas i URL eller
  lagras serverside, vilket öppnar en integritetsfråga som inte är diskuterad.
- Ska man kunna ändra domänval mitt i sekvensen, eller kräver det omstart?
