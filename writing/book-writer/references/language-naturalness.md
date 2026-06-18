# Language naturalness — writing in a real language, not in AI-default

## Why this discipline exists

AI-generated text in any language has a tendency toward what could be called **the smoothed average of the corpus.** Every word is grammatically correct. Every sentence parses. The text is publishable in the loose sense — it can be read without errors. But a reader who is a native speaker of the target language, especially a literary reader, often feels something off without being able to name it. The text reads as *translated* even when it was generated directly, because AI models implicitly translate from a kind of language-neutral abstraction into surface tokens, smoothing over the specific rhythms, idioms, and structural preferences that distinguish one written language from another.

This problem affects all languages. It affects fiction and non-fiction, journalism and academic prose, technical documentation and poetry. It is the most universal AI-failure mode because it operates below the level of content. A book can have the right ideas, the right structure, the right voice on conceptual level, and still feel wrong because the sentences themselves are AI-default rather than language-native.

The discipline against this is not stylistic perfectionism. It is the disciplined refusal to let AI-default syntax stand when language-native syntax exists.

## The general principle

When AI generates a sentence, it typically chooses among several plausible structures and selects the one that is most frequent in its training corpus across all languages. This frequency-weighted selection produces sentences that are correct in target language but structured according to a cross-linguistic average. The average tends to favour:

- **Longer hypotactic sentences** (multiple subordinate clauses) over coordinated short sentences, because hypotactic sentences are more frequent in training material from formal registers
- **Nominalised constructions** (the signing of the treaty) over verbal constructions (when the treaty was signed), because nominalisations are common in academic and bureaucratic writing
- **Passive voice** in non-fiction, because much published prose uses it
- **Standard subject-verb-object order** even where target language allows freer ordering for emphasis
- **Generic transitional phrases** (it should be noted, it is important to remember) that exist in many languages and read as institutional everywhere
- **The formal register choice** when several registers are valid

Each of these choices is locally defensible. Each is also the choice that signals AI rather than human writer. A real writer in any language has specific rhythmic preferences, idiom-clusters they reach for, register choices they make consistently, syntactic structures they favour and others they avoid. The AI-default smooths all those preferences into the median of all writers.

The discipline is therefore: **identify what the AI-default would produce, then deliberately choose a structure more characteristic of a real writer in this specific language for this specific persona.**

## What this requires of the persona

A writer-persona is not just a name and a biography. It is a **specific relationship to the target language**. The persona has read certain authors deeply and not others. The persona has personal habits — sentence length they favour, words they overuse, structures they avoid. The persona writes in the language of their education and milieu, with the specific markers of that milieu.

For language-naturalness to work, the persona must be specified at this level. Not just "Daan Verstegen, Dutch journalist-historian" but "Daan reads Mak and de Jong but not Boterman; he prefers short main clauses with one subordinate clause attached; he uses *immers* and *toch* sparingly but consistently; he avoids genitive nominalisations; he writes Dutch the way a Utrecht-educated 62-year-old with a Berlin career would write."

This level of detail is in addition to the writing-craft persona. It can be added to the persona document or kept separately. For multi-language work it must be specified per language.

---

## Dutch — common AI-defaults and how to avoid them

Dutch is particularly vulnerable to AI-default failures because much published Dutch text is translated from English, and AI models trained on this data acquire patterns that read as translation rather than as original Dutch.

### Pattern 1 — Long English-syntactic sentences

**AI-default (translated-feeling):**
*Hij wist dat hij als parlementaire katholiek met sociaalliberale neigingen voor de generaals een geschikte zondebok zou zijn voor de capitulatie die zij niet zelf wilden tekenen.*

**Dutch-native:**
*Hij wist het wel: voor de generaals was hij precies de juiste zondebok. Een parlementaire katholiek met sociaalliberale neigingen, die de schande van de capitulatie kon dragen die zij zelf niet wilden tekenen.*

The Dutch version breaks the sentence in two and uses the colon-and-restart structure that Dutch journalism favours. The single-sentence version reads as direct translation of an English original.

### Pattern 2 — *Het X was...* constructions

**AI-default:** *Het verschil was geen toeval.*

**Dutch-native:** *Dat was geen toeval.* or *Toeval was het niet.*

The *Het + abstract noun + was* construction is grammatically correct but reads as translated from *The difference was no coincidence*. Dutch writers tend toward *dat*, *daar*, or fronted alternatives.

### Pattern 3 — Locative-existential constructions

**AI-default:** *Op de debet-zijde stond ook iets minder zichtbaars.*

**Dutch-native:** *Er was ook iets minder zichtbaars aan de debetzijde.* or *Aan die debetzijde stond ook iets dat minder zichtbaar was.*

The *Op X stond Y* construction is direct translation of *On X stood Y*. Dutch prefers existential *er* or rephrasing.

### Pattern 4 — Genitive nominalisations

**AI-default:** *De ondertekening van het verdrag vond plaats op 28 juni.*

**Dutch-native:** *Op 28 juni werd het verdrag ondertekend.* or *Het verdrag werd op 28 juni getekend.*

Dutch favours verbal constructions over nominalisations more strongly than English. *De ondertekening van X*, *het besluit tot Y*, *de bekendmaking van Z* all read as bureaucratic-translated unless the noun phrase is doing specific work.

### Pattern 5 — *Wie X wilde, moest Y* constructions

**AI-default:** *Wie de revolutie wilde begrijpen, moest verder terugkijken.*

**Dutch-native:** *Om de revolutie te begrijpen moest je verder terugkijken.* or *De revolutie begin je niet in 1918 te begrijpen.* or *Om die revolutie te kunnen plaatsen moeten we verder terug.*

The *Wie X wilde Y, moest Z* construction is grammatically Dutch but stylistically formal-translated. Native Dutch journalism uses *om-te-infinitief* or fronted infinitive constructions more.

### Pattern 6 — Relative clause overuse with *die*

**AI-default:** *Een man die in een huis woonde dat aan een straat lag die door een buurt liep die rustig was.*

**Dutch-native:** *Een man in een huis aan een straat in een rustige buurt.* or breaks into multiple sentences.

Each *die*-clause adds a layer that English handles fine but Dutch readers experience as stacked. Dutch prefers prepositional reduction or sentence-breaking.

### Pattern 7 — Missing tussenwerpingen

Native Dutch prose uses small inserted words that signal speaker stance: *natuurlijk*, *toch*, *immers*, *weliswaar*, *overigens*, *eigenlijk*, *trouwens*, *dat moet erbij gezegd*, *het is veelzeggend dat*. These don't translate to English directly, so they are absent from translated-feeling Dutch. Their absence makes prose flat.

**AI-default:** *Het cijfer was niet zo onverteerbaar als het in de propaganda werd voorgesteld.*

**Dutch-native:** *Het cijfer was, dat moet erbij gezegd, niet zo onverteerbaar als het in de propaganda werd voorgesteld.*

The *dat moet erbij gezegd* signals the journalist-historian's stance and adds a small pause. Without such markers Dutch journalism feels institutional.

### Pattern 8 — *Die* versus *wat*

**AI-default (over-uses *die*):** *Iets dat hij niet kon vergeten.*

**Dutch-native:** *Iets wat hij niet kon vergeten.*

For neuter antecedents and indefinite pronouns (*iets*, *niets*, *alles*, *dat*), modern Dutch uses *wat*, not *dat*. Older formal Dutch and AI-output use *dat* — which sounds 19th-century or translated.

### Pattern 9 — Word order in subordinate clauses

Dutch has strict V-final order in subordinate clauses (*omdat hij ziek was*, not *omdat hij was ziek*). AI generally gets this right. The trickier case is multi-verb constructions:

**AI-default:** *...dat hij niet kon hebben geweten.*
**Dutch-native:** *...dat hij niet had kunnen weten.* or *...dat hij niet kon weten.*

The word order of multi-auxiliary constructions has specific Dutch patterns that don't always match English progressive-perfect equivalents.

### Pattern 10 — Anglicisms in vocabulary

Less syntactic, more lexical. Words that exist in Dutch but read as translations:
- *adresseren* (in the sense of "deal with") — Dutch *aanpakken*, *behandelen*
- *implementeren* — often *uitvoeren* or *invoeren*
- *prioriteren* — often *voorrang geven*, *prioriteit geven aan*
- *focus op* — often *aandacht voor*, *gericht op*
- *een issue* — often *een probleem*, *een kwestie*

These anglicisms are increasingly accepted in Dutch but signal a specific register (corporate, technical) that doesn't fit literary or journalistic prose written by an older persona.

### Pattern 11 — Sentence rhythm — Mak's example

A characteristic Mak rhythm: *"Het was iets bijzonders, die ochtend."* Or: *"Hij keek nog één keer om, maar het was te laat."*

The structure is **main statement + comma + qualifier-phrase**. Native Dutch journalism uses this; AI-Dutch tends to integrate the qualifier as a subordinate clause or relative clause, losing the rhythm.

### Quick check questions during writing

Before accepting a paragraph as written, ask:
1. Is any sentence longer than 30 words? Can it be broken?
2. Are there *Het X was...* constructions? Could they become *Dat was...*?
3. Are there genitive nominalisations? Could they become verbal?
4. Have I used *die* where modern Dutch wants *wat*?
5. Are there small Dutch insertion words (*toch*, *immers*, *natuurlijk*, *overigens*) — at least one or two per paragraph?
6. Could any *Op X stond Y* become *Er was Y op X*?
7. Are subordinate clauses verb-final correctly?
8. Are there anglicisms that betray a register the persona wouldn't use?

---

## English — common AI-defaults and how to avoid them

English prose by AI has different default-failures than Dutch, because the training corpus is much larger and includes many native English writers. The failures are subtler and more about smoothness-toward-median than translation-feel.

### Pattern 1 — Generic openings

**AI-default:** *In the world of politics, leaders often face difficult choices.*

**Real writer:** *Politics rewards the leader who can lie convincingly to themselves first.* (specific claim, specific perspective)

AI tends to open paragraphs with grand-but-empty statements that establish topic without taking position. Real writers commit to a position in the opening sentence.

### Pattern 2 — Hedge accumulation

**AI-default:** *It might perhaps be argued that, in some sense, this could potentially be seen as a kind of failure.*

**Real writer:** *This was a failure.* or *Whether to call this a failure depends on what we mean by success.*

AI hedges to remain inoffensive. Real writers choose: assert clearly, or specify what's contested, but rarely pile up modal qualifiers.

### Pattern 3 — Three-part list structures

**AI-default:** *He was tired, hungry, and afraid.* / *The decision was important, complex, and far-reaching.*

**Real writer:** Either two-part (more specific) or four-part (more rhythmic) or a single specific adjective. AI's preference for three-part lists is so pronounced that any AI-detection tool flags it.

### Pattern 4 — Em-dash overuse

AI-output tends toward em-dashes for parenthetical insertion at high frequency. Native English writers use them too — but more sparingly, and varying with commas, parentheses, semicolons. A paragraph with three em-dashes signals AI; one em-dash is fine.

### Pattern 5 — Vague abstractions where specifics are available

**AI-default:** *Many factors contributed to the situation.*

**Real writer:** *Three factors mattered most: the railroad strike, the August harvest failure, and the death of Stresemann.*

AI generalises when specifics are available. Real writers specify because their persona has read enough to know which specifics matter.

### Pattern 6 — Smooth transitions between contradictory ideas

**AI-default:** *The economy was strong. However, unemployment was rising.*

**Real writer:** *The economy was strong. Unemployment was rising too. The two were related and the relation was the story.* (signals the writer has a specific take)

AI's "however" / "nevertheless" / "yet" transitions present contradictions as cleanly resolved by the conjunction. Real writers often leave contradictions unresolved as a thinking move.

### Pattern 7 — Missing voice

The hardest one to articulate. AI-English often has all the right words and no detectable speaker. Real writers leave traces: characteristic word choices, slight rhythmic preferences, recurring metaphor families, particular ways of starting sentences. AI-English is voice-flat.

The cure is the persona: a writer with specific reading history, specific habits, specific irritations. When the writer has personality, the prose has voice. When the persona is generic, the prose is generic.

### Quick check questions during writing

1. Does any sentence open with *It is...* or *There are...* in a context where a stronger subject would work?
2. Have I used three-part list structures more than once per page?
3. Are there em-dashes within em-dashes, or three em-dashes in one paragraph?
4. Have I generalised where I could have specified?
5. Is there a paragraph with no detectable voice — could anyone have written it?
6. Have I used institutional transitions (however, nevertheless, furthermore, moreover) where stronger logic-markers would do?

---

## Other languages

For languages other than Dutch and English, the principles transfer but specific patterns must be identified by writers fluent in that language. A starting checklist for any language:

- What sentence structures appear in translated texts but not in native-written texts?
- What small insertion words (modal particles, discourse markers) exist in this language and tend to be missing in AI-output?
- Where does this language place verbs differently from English/AI-default?
- What register choices does this language offer that AI tends to default into the formal register?
- What idiom-clusters do native writers use that AI-translation flattens?

Specific notes:

**German**: AI tends to over-use *jedoch* and *allerdings* where native writers vary. Subordinate-clause verb-final order is usually correct but multi-verb constructions are tricky. Modal particles (*ja*, *halt*, *eben*, *doch*, *mal*) are often absent from AI-German.

**French**: AI tends toward formal *passé simple* in literary contexts where *passé composé* would be more natural for living prose. Liaison between clauses tends to be over-explicit (*toutefois*, *cependant* repeated). The *on*-construction is often absent where French writers would use it for indefinite agency.

**Spanish**: AI-output tends toward Castilian-formal where Latin American or specific regional varieties would be more appropriate to the persona. Subjunctive use is usually correct but stiff. *Vosotros* vs *ustedes* must be persona-specified.

**Other languages**: The skill should encourage the user to identify specific patterns in their target language and to add them to this reference for future use.

---

## How this discipline integrates with the existing skill

### During Phase 0 — Persona

The persona must include language-naturalness specification. Not just *which language* but *which version of which language*. Example for Daan Verstegen:

> Daan writes Dutch in the register of a 62-year-old Utrecht-educated journalist with a Berlin career. He prefers short main clauses with one subordinate clause attached. He uses small insertion words (*toch*, *immers*, *natuurlijk*, *overigens*, *dat moet erbij gezegd*) regularly but not heavily. He avoids genitive nominalisations. He uses *wat* not *dat* for neuter antecedents. He follows Mak's rhythm of *main statement + comma + qualifier* but uses it sparingly. He does not use anglicisms — neither corporate (*adresseren*, *implementeren*) nor casual (*een issue*).

This level of specification is part of the persona, kept in `writer/persona.md` or in a separate `writer/language.md` for multi-language projects.

### During Phase 4 — Writing

Each paragraph, before being accepted as written, gets a language-naturalness pass:

1. Is any sentence translated-syntactic? (Apply the Dutch / English / target-language checks above.)
2. Is the persona's specific register present? (Insertion words, sentence rhythm, vocabulary choices.)
3. Have I used AI-default constructions where language-native alternatives exist?

This is **per-paragraph discipline**, not once-per-chapter. Like reality-grounding, it works only when applied at the unit-of-writing level.

### During Phase 5 — Manuscript finishing

A dedicated **language-naturalness revision pass**, separate from content-revision. The reviewer reads with the explicit question: *would a real writer in this language write this sentence this way?* Not *is it grammatical* but *is it natural*.

For multi-author projects or sensitive cases, a native-speaker-reader is invaluable — but the discipline-pass can be done by the AI itself when the patterns have been internalised through this reference.

### During revision-mode

If revising existing AI-generated text, the language-naturalness pass is one of the highest-value interventions. Often the content is fine but the language is flat. A focused pass that does nothing but fix the patterns above can transform a manuscript from publishable-feeling-translated to publishable-feeling-original.

---

## A note on humility

This reference is not exhaustive. It identifies patterns I've observed, with examples I can defend. But every language has more patterns than any one document can capture, and every great writer in any language uses the language in ways that resist reduction to rules.

The reference should be treated as a starting point. Specific writers, specific projects, specific contexts will require additional patterns to be identified and documented. The skill's user is encouraged to extend this reference with patterns they notice in their own work, organised by language and persona.

The deepest discipline is not following the patterns in this document. It is the habit of reading one's own AI-generated text with a native speaker's ear, asking at each sentence: *would I, or someone I admire, write this sentence in this form?* When the answer is no, the discipline is to rewrite — not because the AI version is wrong, but because the AI version is generic where the native version would be specific.
