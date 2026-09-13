# CR-006: Navigering till alla vyer

| Field | Value |
|-------|-------|
| **CR Number** | CR-006 |
| **Date** | 2026-09-13 |
| **Implementation Date** | 2026-09-13 |
| **Author** | Claude Code |
| **Status** | Implemented |
| **Priority** | High |
| **Complexity** | Low |
| **Estimated Scope** | app/templates, app/static |
| **Related CRs** | CR-001 (valkompass), CR-002 (granskning), CR-005 (om-sida) |
| **Depends On** | None |
| **Breaking Changes** | No |

---

## Executive Summary

Menyn i `base.html` var oförändrad sedan v0.1.0 och listade bara de fyra
ursprungliga vyerna. Valkompassen (CR-001), granskningsgränssnittet (CR-002)
och den omarbetade om-sidan (CR-005) gick bara att nå genom att skriva in
URL:en manuellt.

**Current Problems:**
1. Tre av sex vyer saknades helt i navigeringen.
2. "Metod" pekade på om-sidan men beskrev inte längre vad den innehåller.
3. Ingen markering av vilken vy man befinner sig i.
4. Sidfoten påstod att taggningen var "oreviderad", vilket inte längre
   stämmer för valkompassens påståenden.

---

## Problem Analysis

Ett förbiseende vid leverans av CR-001, CR-002 och CR-005: varje CR byggde
sin vy och registrerade sin route, men ingen uppdaterade den delade
navigeringen. Varje CR var komplett i sig — bristen uppstod i mellanrummet.

**Lärdom:** när flera CR:er lägger till vyer i samma app bör den delade
navigeringen vara en uttrycklig punkt i respektive CR:s Files to Modify,
eller hanteras av en separat CR som här.

---

## Proposed Solution

Sex länkar i två grupper med visuell avdelare:

| Grupp | Länkar | Syfte |
|-------|--------|-------|
| Utforska | Täckning, Konfliktaxlar, Inramning | Materialet uppifrån och ner |
| Använd och förstå | Valkompass, Granskning, Om & källor | Verktyg och metod |

- Valkompass markeras som primär (accentfärg) — det är den vy en besökare
  troligen vill åt.
- Aktiv vy markeras via `request.endpoint` / `request.blueprint`.
- "Metod" byter namn till "Om & källor" eftersom sidan nu innehåller
  källförteckning, processbeskrivning och arbetsdelning.
- Under 620px tas avdelaren bort och gapet minskas.

Sidfoten rättas: taggningen av textstyckena är maskinell, men valkompassens
påståenden är redaktionellt granskade. Att påstå motsatsen underskattar
underlaget.

---

## Files to Modify/Create

| File | Action | Changes |
|------|--------|---------|
| `app/templates/base.html` | Modify | Sex länkar, grupper, aktiv-markering, rättad sidfot |
| `app/static/stil.css` | Modify | `.navgrupp`, `.aktiv`, `.navprimar` |
| `tests/test_navigering.py` | **CREATE** | 4 tester |

---

## Testing Plan

### Test Case 1: Alla vyer i menyn
- Verifiera: sex länktexter renderas

### Test Case 2: Alla menylänkar svarar
- Verifiera: samtliga sex routes ger 200

### Test Case 3: Aktiv markering
- Verifiera: varje vy markerar sig själv som aktiv

### Test Case 4: Sidfoten beskriver läget korrekt
- Verifiera: "oreviderad" förekommer inte, "redaktionellt granskade" gör det

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Menyn blir för bred på mobil | Medium | Low | Avdelare tas bort under 620px, verifierat vid 560px |
| Framtida vyer glöms igen | Medium | Medium | Test som kräver att varje meny-route svarar |

---

## Rollback

1. Återställ `base.html` och `stil.css` till föregående commit
2. Radera `tests/test_navigering.py`
