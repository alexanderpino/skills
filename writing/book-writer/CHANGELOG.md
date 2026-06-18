# Skill book-writer — Changelog

## v18 (huidige versie)

Eén nieuwe reference plus aanpassing van de Phase 4 per-chapter loop. De aanpassing dient een specifiek doel: maken dat de skill bruikbaar is voor agents met kleinere context-budgetten.

### Nieuwe reference

**`chapter-mini-outline.md`** — Verplichte sectie-level decompositie van elk hoofdstuk voordat het wordt geschreven. Per hoofdstuk een `chapters/NN-slug.outline.md` met per-sectie purpose, opening anchor, beats (verb-driven, niet thematisch), bronnen, throughline-touch, handoff naar volgende sectie, en eventuele speciale technieken. Meeste hoofdstukken hebben 4-8 secties van 800-1500 woorden.

Anti-AI-tells specifiek voor mini-outlines:
1. Sections-as-paragraphs (over-decompositie naar 500-woord stukjes)
2. Purposes that are synonyms (fake-decompositie)
3. Beats that are themes (atmosfeer in plaats van events)
4. Missing handoffs (lijstvorm in plaats van narratief)
5. Decorative throughline-touch (elke sectie pretendeert het te dienen)
6. Word budgets that don't sum (~10% tolerantie tegenover chapter target)
7. Sources evenly spread (echte hoofdstukken gebruiken sommige bronnen zwaar, andere licht)

Aanleiding: gebruiker's observatie dat de skill geen mini-outline per hoofdstuk maakt, en dat agents met kleinere budgetten ook goede boeken moeten kunnen schrijven — wat momenteel niet werkbaar is omdat een heel hoofdstuk genereren in één call onhaalbaar is voor zulke agents.

### Waarom dit belangrijk is voor agent-budgets

De mini-outline lost vier specifieke problemen op voor agents met beperkte context:

1. **Sectie-at-a-time writing** — agent schrijft één sectie per call (~1000 woorden) in plaats van een heel hoofdstuk (~8000 woorden). Elke call laadt alleen: persona, throughline-contribution, mini-outline, bronnen voor déze sectie, vorige sectie voor tonale continuïteit.

2. **Resumable across sessions** — als de agent of mens halverwege moet pauzeren, is hervatten triviaal: "ik was bij sectie 4 van 7, hier is de mini-outline, hier is sectie 3 voor continuïteit, schrijf sectie 4."

3. **Pre-flight detection van structurele problemen** — een verkeerd-gestructureerd hoofdstuk wordt zichtbaar in de mini-outline (5 minuten kosten) in plaats van pas na 8000 woorden generen (uren kosten).

4. **Standardised section interface** — elke sectie heeft een gedefinieerde input (vorige sectie's einde) en output (handoff naar volgende). Dezelfde engineering-principe als modulair software-ontwerp.

### Uitbreidingen aan SKILL.md

- **Phase 4 per-chapter loop**: nieuwe stap 3 "Produce mini-outline" toegevoegd tussen "Plan visuals" en "Draft". Verplicht voor elk hoofdstuk. Mini-outline wordt getoond aan gebruiker zonder approval gate — visibility-zonder-gate-patroon zodat werk kan doorlopen terwijl de gebruiker geïnformeerd blijft.
- **Phase 4 draft step**: aangepast om expliciet section-by-section te werken volgens de mini-outline. Elke sectie laadt alleen z'n directe context.
- **Always-available references**: chapter-mini-outline.md geïntegreerd met substantiële beschrijving van wanneer en hoe toe te passen, met expliciete vermelding van de context-budget-rationale.

### Skill statistieken

- 33 references (van 32 in v17)
- 10.255 woorden in SKILL.md (van 9.982 in v17)
- ~87.000 woorden totaal in references

## Versie geschiedenis

- **v11**: 23 references, basis-skill
- **v12**: + library-systeem, + language-naturalness
- **v13**: + reading-level, + extreme-constraint
- **v14**: + technical-documentation
- **v15**: + slice-methodology, + claim-verification, persona-modaliteiten
- **v16**: + productive-puzzlement
- **v17**: + throughline-discipline (met Phase 3/4/5 integraties)
- **v18** (huidig): + chapter-mini-outline (met Phase 4 loop-restructure voor agent-budget-awareness)

## Patroon dat zich blijft herhalen

Wederom een gebruikersinitiatief, geen interne skill-reflectie. Maar deze versie is interessant op een nieuwe manier: het is de eerste versie die expliciet **agents met andere capability-profielen** in overweging neemt. Tot v17 was de impliciete aanname dat een claude-instantie met ruime context het werk doet. v18 dwingt de skill om decomposabel te zijn — dezelfde boek-output moet ook produceerbaar zijn met kleinere per-call budgets.

Dat opent een groter design-vraag voor toekomstige versies: **wat moet de skill nog meer aanpassen om voor agents met andere capability-profielen te werken?** Denk aan:

- Progressive context loading (niet alle references tegelijk inladen, maar per fase / per taak)
- Budget-aware scope hints bij intake
- Standardised resume-protocols voor cross-session werk
- Sectie-niveau revision (in plaats van hoofdstuk-niveau)

Dit is mogelijk de richting van een toekomstige `agent-budget-awareness.md` reference. Voor nu is v18 een eerste stap in die richting.
