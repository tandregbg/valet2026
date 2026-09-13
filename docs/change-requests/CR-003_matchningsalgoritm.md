# CR-003: Matchningsalgoritm

| Field | Value |
|-------|-------|
| **CR Number** | CR-003 |
| **Date** | 2026-09-13 |
| **Implementation Date** | 2026-09-13 |
| **Author** | Claude Code |
| **Status** | Implemented |
| **Priority** | Medium |
| **Complexity** | Medium |
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

**Beslutat: alternativ A, ingen extra viktning.** Alla 50 påståenden väger
lika. De valda domänerna får redan genomslag genom att de utgör 30 av 50
frågor.

---

## Beslutade frågor (2026-09-13)

**1. Hur kodas `emot`?**
`emot` sätts endast vid explicit avvisande i källtexten (CR-002 beslut 4).
I praktiken blir det sällsynt. Algoritmen mäter därför i huvudsak positiv
överensstämmelse, och resultatvyn måste säga det rakt ut:

> Matchningen mäter var dina svar sammanfaller med förslag källan faktiskt
> driver. Den mäter inte avstånd — att ett förslag saknas i ett dokument
> betyder inte att avsändaren är emot det.

**2. Minsta täckning?**
Tröskel: **15 belägg av 50**. Under den visas källan gråmarkerad med varning,
aldrig dold.

**3. Överhoppade frågor?**
Påverkar inte procenten, men sänker täckningssiffran.

**4. Dubbletter?**
Algoritmen deduplicerar på `subdoman` + normaliserad text före beräkning, som
skyddsnät om CR-002:s dubblettfilter missar något.

**5. Domänviktning?**
Alternativ A: ingen extra viktning. De valda domänerna får redan genomslag
genom att utgöra 30 av 50 frågor. Dubbel viktning skulle göra resultatet
nästan helt bestämt av domänvalet.

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

## Open Questions

Inga blockerande.
