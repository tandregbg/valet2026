# CR-003: Matchningsalgoritm

| Field | Value |
|-------|-------|
| **CR Number** | CR-003 |
| **Date** | 2026-09-13 |
| **Author** | Claude Code |
| **Status** | Draft |
| **Priority** | Medium |
| **Estimated Scope** | app, beräkningslogik |
| **Related CRs** | CR-001 (levererar svaren), CR-002 (levererar påståendena), CR-004 (visar resultatet) |
| **Depends On** | CR-002 (matchning kräver källkopplade påståenden) |

---

## Executive Summary

Givet användarens 50 graderade svar: hur beräknas vilka källor som ligger
närmast? Den här CR:en definierar algoritmen och, viktigare, vad den
**inte** kan säga.

**Current Problems:**
1. Källorna har inte svarat på några frågor — de har publicerat dokument.
   Deras "ståndpunkt" per påstående måste härledas, och saknas oftast.
2. Frånvaro av ett förslag i ett dokument betyder inte motstånd. Det kan lika
   gärna betyda att frågan inte var prioriterad, eller att extraktionen
   missade den.

---

## Problem Analysis

### Den grundläggande asymmetrin

En traditionell valkompass frågar partierna direkt: de får samma påståenden
och svarar på samma skala. Matchningen blir en jämförelse mellan två
likadana vektorer.

Här finns ingen sådan symmetri. Vi har:

- Användarens svar: 50 värden på skala 1-5
- Källornas "svar": härledda ur vad de råkar ha skrivit

Det är inte samma sorts data, och algoritmen får inte låtsas att det är det.

### Vad frånvaro betyder

Om ett dokument inte innehåller något om ett påstående finns tre möjliga
förklaringar:

1. Avsändaren är emot förslaget
2. Avsändaren prioriterar inte frågan
3. Extraktionen missade det (2-21% bortfall, 40% svaga träffar)

Algoritmen kan inte skilja dem åt. **Därför får frånvaro aldrig tolkas som
motstånd.** Det är det enskilt viktigaste designbeslutet i den här CR:en.

Konsekvensen: matchningen kan bara mäta **överensstämmelse där det finns
belägg**, aldrig avstånd baserat på tystnad.

---

## Proposed Solution

### Trestegsberäkning

**Steg 1: Hållning per påstående och källa**

Ur `pastaenden.jsonl` (CR-002) finns för varje påstående en lista över källor
som driver det. Hållningen kodas:

| Kod | Betydelse | Numeriskt |
|-----|-----------|-----------|
| `for` | Källan föreslår detta | +1 |
| `emot` | Källan avvisar detta explicit | -1 |
| `saknas` | Inget belägg | ingen data (ej 0) |

Skillnaden mellan `saknas` och 0 är hela poängen. Ett `saknas` utesluts ur
beräkningen för den källan, det drar inte ned matchningen.

**Steg 2: Poäng per påstående**

Användarens svar normaliseras från 1-5 till -1..+1:

```
anvandarvarde = (svar - 3) / 2     # 1 -> -1,0 | 3 -> 0,0 | 5 -> +1,0
```

För varje påstående där källan har belägg:

```
poang = anvandarvarde * kallans_hallning
```

Ett påstående användaren gav 5 och källan driver: `+1.0 * +1 = +1.0`.
Ett påstående användaren gav 1 och källan driver: `-1.0 * +1 = -1.0`.
En trea ger 0 oavsett — neutralt svar påverkar inte matchningen.

**Steg 3: Normalisering**

```
matchning = summa(poang) / antal_belagg_for_kallan
```

Divisionen med antal belägg är kritisk. En källa med långt dokument har fler
belägg och skulle annars få högre absolut poäng bara på volym — samma fel som
färgsättningen i täckningsmatrisen hade.

### Redovisning av täckning

Varje matchningsresultat måste åtföljas av hur många av de 50 påståendena
källan faktiskt hade belägg för:

> Källa B: 72% överensstämmelse (belägg för 31 av 50 påståenden)

En källa med 90% på 8 belägg är inte en bättre matchning än 72% på 31. Utan
täckningssiffran är procenten vilseledande.

### Viktning mot valda domäner

Öppen fråga. Två alternativ:

**A. Ingen viktning.** Alla 50 påståenden väger lika. De valda domänerna får
redan genomslag genom att de utgör 30 av 50 frågor.

**B. Explicit viktning.** Påståenden i valda domäner väger dubbelt.

Alternativ A är förmodligen rätt: viktningen finns redan inbyggd i
frågefördelningen, och dubbel viktning riskerar att göra resultatet nästan
helt bestämt av domänvalet. Behöver testas mot riktiga svar.

---

## Open Questions

**1. Hur kodas `emot`?**
CR-002 noterar att motstånd sällan står explicit i dokumenten. Om `emot` i
praktiken aldrig förekommer blir algoritmen enbart en mätning av positiv
överensstämmelse. Det är hanterbart, men måste då sägas rakt ut i
resultatvyn.

**2. Minsta täckning för att visa en matchning?**
Om en källa bara har belägg för 5 av 50 påståenden — ska den visas alls?
Förslag: visa, men gråmarkerad med tydlig varning under en tröskel
(exempelvis 15 belägg).

**3. Ska överhoppade frågor påverka?**
Nej enligt CR-001. Men de minskar underlaget, vilket bör synas i
täckningssiffran.

**4. Hanterar algoritmen att samma sakfråga kan förekomma i flera påståenden?**
Om påståendebanken innehåller två närliggande formuleringar av samma sak får
den frågan dubbel vikt av misstag. CR-002 ska fånga dubbletter, men
algoritmen bör tåla att den inte gör det perfekt.

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Frånvaro tolkas som motstånd i någon kodväg | Medium | **High** | `saknas` som explicit tredje tillstånd, aldrig 0; enhetstest som verifierar |
| Procent utan täckning uppfattas som exakt | **High** | High | Täckningssiffra obligatorisk i all visning (CR-004) |
| Volymbias från olika dokumentlängd | Medium | High | Normalisering mot antal belägg, inte summa |
| Domänviktning gör resultatet cirkulärt | Medium | Medium | Börja utan viktning, mät mot testsvar |

---

## Testing Plan

### Test Case 1: Frånvaro drar inte ned

- Konstruera källa med belägg för 10 av 50 påståenden, alla instämmande
- Verifiera: hög matchningsprocent, låg täckning
- Verifiera: de 40 utan belägg påverkar inte procenten

### Test Case 2: Volymneutralitet

- Två källor med identisk hållning, en med dubbelt så många belägg
- Verifiera: samma matchningsprocent

### Test Case 3: Neutrala svar

- Besvara alla 50 med 3
- Verifiera: alla källor får 0% (varken för eller emot), inte 50%

### Test Case 4: Överhoppade

- Hoppa över 10 frågor
- Verifiera: täckningssiffran sjunker, procenten beräknas på resterande 40

---

## Nästa steg innan Proposed

1. CR-002 måste först visa om `emot` är kodbart i praktiken (öppen fråga 1).
2. Testa viktning A mot B på 5-10 riktiga svarsomgångar.
3. Fastställ tröskel för minsta täckning.
