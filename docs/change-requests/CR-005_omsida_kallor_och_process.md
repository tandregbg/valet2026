# CR-005: Om-sida med källreferenser och processbeskrivning

| Field | Value |
|-------|-------|
| **CR Number** | CR-005 |
| **Date** | 2026-09-13 |
| **Implementation Date** | 2026-09-13 |
| **Author** | Claude Code |
| **Status** | Implemented |
| **Priority** | High |
| **Complexity** | Medium |
| **Estimated Scope** | app, domains, README |
| **Related CRs** | CR-001..004 |
| **Depends On** | None |
| **Breaking Changes** | No |

---

## Executive Summary

Projektet ska publiceras på GitHub. Då behöver källorna vara refererade på ett
sätt som går att granska, och processen beskriven så att metoden är
återanvändbar — inklusive varför man inte bara kan lägga materialet i en chatt
och be om en analys.

**Current Problems:**
1. Källförteckningen fanns bara i `manifest/INDEX.md`, inte i gränssnittet.
2. Metodsidan beskrev felkällor men inte processen eller arbetsdelningen.
3. Ingenting förklarade vad som är genererat och vad som är källtext.

---

## Proposed Solution

Ny om-sida i sex sektioner:

1. **Källor** — tabell med utgivare, dokument, sidor, ord, länk till både
   dokument och landningssida, samt SHA256. Hämtningsanmärkningar utfällbara.
2. **Processen** — åtta steg, vart och ett märkt Kod eller Människa.
3. **Varför inte bara en chatt** — sex parvisa jämförelser.
4. **Människa, LLM och kod** — fyra lager separerade.
5. **Datamängden** — filerna, med antal rader, plus spårbarhetskedjan.
6. **Brister** — felkällor, isk-buggen som fallstudie, och avgränsning.

Källförteckningen flyttas till `domains/kallor.yaml` (maskinläsbar) så att
sidan kan generera tabellen ur data i stället för hårdkodad markup.

**Alla siffror härleds vid rendering.** Ändras datamängden följer sidan med.

---

## Files to Modify/Create

| File | Action | Changes |
|------|--------|---------|
| `domains/kallor.yaml` | **CREATE** | Strukturerad källförteckning |
| `app/app.py` | Modify | `/om` byggs om, data härleds |
| `app/templates/om.html` | Modify | Sex sektioner |
| `app/static/stil.css` | Modify | Stilar för flöde, jämförelse, lager |
| `README.md` | Modify | Anpassad för publicering |
| `tests/test_omsida.py` | **CREATE** | 5 tester |

---

## Testing Plan

### Test Case 1: Alla sektioner finns
- Verifiera: sex ankare renderas

### Test Case 2: Varje källa har länk och checksumma
- Loopa `kallor.yaml`, verifiera att utgivare, URL och SHA256 finns i HTML

### Test Case 3: Siffror härleds ur data
- Räkna rader i `pastaenden.jsonl`, verifiera att samma tal står på sidan

### Test Case 4: Arbetsdelningen skiljer fyra lager
- Verifiera: alla fyra rubriker renderas

### Test Case 5: isk-felet dokumenteras
- Verifiera: exemplet finns kvar med sina siffror

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Sidan blir inaktuell när data ändras | Medium | High | Alla siffror härleds vid rendering; test verifierar |
| Källförteckningen dubbellagras | Medium | Low | `kallor.yaml` är källan; INDEX.md behålls som läsbar kopia |
| Processbeskrivningen läses som marknadsföring | Low | Medium | Brister-sektionen ligger på samma sida, inte undangömd |

---

## Rollback

1. Återställ `app/templates/om.html` och `/om`-routen
2. Radera `domains/kallor.yaml` och `tests/test_omsida.py`
