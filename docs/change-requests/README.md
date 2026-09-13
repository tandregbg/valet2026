# Change Requests

Index över ändringsförslag för val2026-projektet.

Next available CR number: **CR-005**

---

## Aktiva

| CR | Titel | Status | Prioritet | Beror på |
|----|-------|--------|-----------|----------|
| [CR-001](CR-001_valkompass_domanval_och_fragemotor.md) | Valkompass - domänval och frågemotor | Proposed | High | CR-002 |
| [CR-002](CR-002_pastaendebank.md) | Påståendebank - från taggade förslag till graderbara påståenden | **Draft** | High | - |
| [CR-003](CR-003_matchningsalgoritm.md) | Matchningsalgoritm | **Draft** | Medium | CR-002 |
| [CR-004](CR-004_resultatvy.md) | Resultatvy - matchning med spårbarhet | Proposed | Medium | CR-003 |

---

## Beroendekedja

```
CR-002 (påståendebank)          <- kritisk väg, Draft
   │
   ├──> CR-001 (frågemotor)
   │
   └──> CR-003 (matchning)      <- Draft
              │
              └──> CR-004 (resultatvy)
```

**CR-002 är den kritiska vägen.** Ingenting annat kan implementeras
meningsfullt innan påståendebanken finns, och den innehåller projektets
svåraste öppna problem: hur man skriver om partiskt formulerade textstycken
till neutrala påståenden utan att införa systematisk snedvridning.

CR-002 och CR-003 ligger som **Draft** med öppna frågor som måste besvaras
innan de kan promotas till Proposed. Det är avsiktligt — att skriva dem som
färdiga specar hade dolt att de viktigaste besluten inte är fattade.

---

## Ursprung

Konceptet kommer från en brainstorm 2026-09-13 11:13 (Livia, Tomas), inspelad
och transkriberad. Beslut som togs där och som ligger fast i CR-001:

- Max tre domäner väljs som "mina viktigaste frågor"
- Femgradig skala (1-5), inte fyrgradig — mittenläget behövs
- 50 frågor totalt, 10 per vald domän + resten blandade
- Resultat som staplar, med de faktiska förslagen ett klick bort

Transkriptet noterade också en tidsram ("en vecka, kanske rent av flera
dagar"). Den bedömningen gjordes innan CR-002:s omfattning var känd — cirka
fem timmars redaktionellt granskningsarbete plus implementation. Värt att
ompröva innan arbetet startar.

---

## Statuslivscykel

```
Draft -> Proposed -> Planned -> Implemented -> Archived
```

| Status | Betydelse |
|--------|-----------|
| **Draft** | Idé fångad, viktiga beslut kvarstår |
| **Proposed** | Genomarbetad, redo att implementera |
| **Planned** | Godkänd, inplanerad |
| **Implemented** | Levererad |
| **Archived** | Död, återtagen eller uppgången i annan CR |
