# Valmanifest 2026 - domänanalys

**Version 0.1.0**

Insamling, strukturering och visualisering av samtliga åtta riksdagspartiers
valmanifest inför riksdagsvalet 13 september 2026.

Projektet börjar i källdata och lägger ett tolkningslager ovanpå. Lagret gör
materialet navigerbart - det drar inga slutsatser. Det är en människas jobb.

## Struktur

```
val2026/
├── manifest/          Källdokument (PDF + extraherad text) + INDEX.md
├── domains/
│   ├── taxonomi.yaml  12 domäner, 60 subdomäner, 5 konfliktaxlar
│   ├── extrahera.py   Segmentering + heuristisk taggning
│   └── forslag.jsonl  1 528 förslag, en per rad
├── app/               Flask-app
├── CHANGELOG.md
└── README.md
```

## Två lager

Analysen håller isär två saker som annars blandas ihop:

1. **Sakfrågan** - den neutrala taxonomin i `taxonomi.yaml`. Följer inget
   partis egen kapitelindelning, och är därför jämförbar mellan partier.
2. **Inramningen** - partiets egen rubrik, bevarad på varje förslag i
   fältet `partiets_egen_rubrik`.

Skillnaden mellan lagren är i sig ett analysresultat: den visar hur ett parti
väljer att presentera politik som sakligt hör hemma någon annanstans.

## Köra

```bash
pip install flask pyyaml
python3 domains/extrahera.py     # bygger om forslag.jsonl
python3 app/app.py               # http://127.0.0.1:5001
```

## Vyer

| Vy | Fråga den besvarar |
|---|---|
| `/` | Vilka domäner täcker partierna - och var är de tysta? |
| `/doman/<id>` | Vad säger partierna faktiskt inom ett sakområde? |
| `/axlar` | Vilka mönster skär tvärs över domängränserna? |
| `/inramning` | Hur ramar partiet in sin egen politik? |
| `/om` | Metod, felkällor och förbehåll |

## Så läser du täckningsmatrisen

Kulören visar vilken domän raden gäller. Mättnaden visar hur stor andel av
partiets eget manifest som ligger där - andel används i stället för antal
eftersom manifesten är olika långa. Streckad ruta betyder tystnad: inget
förslag alls i domänen.

Andelen mäter hur mycket **text** partiet ägnar frågan. Det är inte samma sak
som hur viktig den är för dem.

## Viktigt om tillförlitligheten

Taggningen är **maskinell och oreviderad**. Den bygger på
nyckelordsmatchning, inte på läsning, och har systematiska svagheter:

- 40% av raderna har bara en nyckelordsträff.
- Ord som förekommer hos både för- och motståndare kan ge fel domän.
- Konfliktaxlarna kräver entydiga fraser för att skilja ståndpunkt från
  omnämnande. Därför blir träffarna få, och axlarna redovisas som
  belägglistor snarare än positionsskalor.

Siffrorna duger för att hitta mönster och tystnader. De duger inte som
belägg för vad ett parti tycker - kontrollera alltid mot källtexten i
`manifest/`.

Ett konkret exempel på varför: i en tidig version matchade nyckelordet `isk`
(investeringssparkonto) som delsträng i *svensk*, *fisket* och *människors*,
vilket färgade en hel rad i matrisen. Felet upptäcktes för att någon
ifrågasatte varför raden såg likadan ut för alla partier. Se CHANGELOG.

## Källor

Samtliga dokument hämtade 2026-09-13 från respektive partis officiella
webbplats. Fullständiga URL:er och SHA256-checksummor i `manifest/INDEX.md`.
