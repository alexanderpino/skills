#!/usr/bin/env python3
"""Is there enough information to refine this item? Stdlib only, no network.

  python intake.py assess --text ticket.txt [--kind feature|bug|spike|enabling|auto] [--lang <code>|auto]
  python intake.py assess --bundle bundle.json --write     # fills story.intake + questions

The script finds LEXICAL SIGNALS, not meaning. It can tell that the words
"expected" and "actual" occur; it cannot tell whether what follows them is
usable. Every dimension it marks present comes with the snippet it matched, so
the reader (human or agent) confirms or overrides. validate.py then holds the
bundle to whatever was recorded: a dimension marked present must quote the
source text, a dimension marked missing must have a blocking question, and a
bundle whose verdict is not "sufficient" may not contain subtasks.

Three verdicts:
  sufficient    every required dimension present or explicitly assumed -> refine
  scoutable     required dimensions missing, but there is at least one code anchor
                and a reachable repo -> run Phase 2 only, to sharpen the questions,
                then stop and ask
  insufficient  nothing to scan for and nothing to decompose -> ask first
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _yaml import get, load_config  # noqa: E402

DEFAULT_REQUIRED = {
    "feature": ["actor", "outcome", "trigger"],
    "bug": ["repro", "expected", "actual", "environment"],
    # A research item has no actor and no outcome yet - that is the point of it. What
    # it must have is a question narrow enough to answer, a decision waiting on the
    # answer, and a price we are willing to pay for it.
    "spike": ["question", "decision", "timebox"],
    # An enabler - upgrade, platform, tooling, infrastructure - has no customer-facing
    # outcome either, and "as a developer I want" is the fudge that hides it. What it
    # must name is the work it unlocks and what it costs to keep not doing it
    # [P: SAFe enablers; Reinertsen, cost of delay]. Without the first it is
    # gold-plating; without the second it loses every prioritisation it enters.
    "enabling": ["unlocks", "cost_of_delay"],
}
DEFAULT_RECOMMENDED = {
    "feature": ["success_signal", "scope"],
    "bug": ["impact"],
    "spike": ["answer_shape"],
    "enabling": ["success_signal", "scope"],
}

# Each dimension: list of regexes. Case-insensitive. English and Dutch side by side,
# because a Dutch ticket must not sail through on the absence of English keywords.
SIGNALS = {
    "actor": [
        r"\bas an? \w+", r"\bals (een )?\w+ wil\b", r"\b(user|users|customer|customers|admin|"
        r"operator|developer|maintainer|implementer|implementor|reviewer|contributor|engineer|"
        r"finance|support|tenant|merchant|partner|agent)s?\b",
        r"\b(gebruiker|klant|beheerder|medewerker|partner|afdeling)s?\b", r"\bfor (the )?\w+ team\b",
    ],
    "outcome": [
        r"\bso that\b", r"\bso (a|an|the|we|they|you|i|nobody|no one)\b", r"\bzodat\b",
        r"\b(i|we|they) (want|need|don'?t want|should be able)\b",
        r"\b(wil|willen|moet|moeten|kan|kunnen)\b", r"\bshould (not )?\b", r"\bable to\b",
        r"\bno longer\b", r"\bniet meer\b", r"\binstead of\b", r"\bin plaats van\b",
    ],
    "trigger": [
        r"\bwhen(ever)?\b", r"\bwanneer\b", r"\bzodra\b", r"\bon (checkout|login|submit|save|"
        r"upload|export|import|payment|signup|sign-up|startup|load)\b", r"\bbij (het )?\w+en\b",
        r"\bafter\b", r"\bna(dat)? \w+", r"\bat (checkout|login|runtime|startup)\b",
        r"\bduring\b", r"\btijdens\b", r"\bevery (day|night|hour|week|month)\b",
        r"\b(dagelijks|wekelijks|maandelijks|elke)\b",
    ],
    "success_signal": [
        r"\b\d+(\.\d+)?\s?(%|ms|s|sec|seconds|minutes|min|hours|per (day|week|month))\b",
        r"\b(binnen|onder|maximaal|max\.?)\s+\d+\s?(ms|seconden|sec|minuut|minuten|uur|dagen)\b",
        r"\b\d+\s?(seconden|minuut|minuten|uur|dagen)\b", r"\bper (dag|week|maand)\b",
        r"\bp9[059]\b", r"\b(metric|metrics|measure|measured|kpi|alert|alerting)\b",
        r"\b(gemeten|meetbaar|kpi)\b", r"\bzero\b", r"\bnul\b", r"\bno more (manual|refunds|errors)\b",
        r"\bgeen (handmatige|fouten)\b", r"\bso we (can|know)\b", r"\bzodat we\b",
    ],
    "scope": [
        r"\bout of scope\b", r"\bbuiten scope\b", r"\bnot (in|part of) (this|scope)\b",
        r"\bexcluding\b", r"\bexcept\b", r"\bbehalve\b", r"\balleen\b", r"\bonly\b",
        r"\blater\b", r"\bfollow-?up\b", r"\bniet (in|voor) deze\b",
    ],
    "repro": [
        r"(^|\n)\s*\d+[.)]\s+\S", r"\bsteps? to reproduce\b", r"\breproduc\w+\b",
        r"\bstappen\b", r"\breproduceer\w*\b", r"\bhow to trigger\b", r"\bto reproduce\b",
    ],
    "expected": [r"\bexpected\b", r"\bexpect\b", r"\bverwacht\w*\b", r"\bshould (have|be|return|show)\b",
                 r"\bzou (moeten|verwachten)\b", r"\bhoort\b"],
    "actual": [r"\bactual(ly)?\b", r"\bwerkelijk\b", r"\bdaadwerkelijk\b", r"\bin plaats (daarvan|van)\b",
               r"\binstead\b", r"\bbut (it|we|the)\b", r"\bmaar (het|we|de)\b", r"\breturns?\s+(a\s+)?[45]\d\d\b",
               r"\b(crash|crashes|hangs|fails|failing|error|exception|stack ?trace)\b",
               r"\b(crasht|faalt|fout|foutmelding|storing|werkt niet|kapot)\b"],
    "environment": [r"\b(prod|production|staging|acceptance|acc|test|dev|local)\b(?! (user|team))",
                    r"\bv\d+(\.\d+)+\b", r"\bversion\b", r"\bversie\b", r"\b(chrome|firefox|safari|edge|ios|android|windows|macos|linux)\b",
                    r"\b(omgeving|productie|acceptatie)\b", r"\bbuild \d+\b", r"\brelease \d", r"\bcommit\b"],
    "impact": [r"\b\d+\s?%\b", r"\b(all|every|some|most|\d+) (users|customers|orders|requests|tenants)\b",
               r"\b(alle|sommige|\d+) (gebruikers|klanten|orders)\b", r"\b(always|sometimes|intermittent|"
               r"occasionally|since)\b", r"\b(altijd|soms|sinds|af en toe)\b", r"\bper (day|week|dag|week)\b",
               r"\b(blocking|blocker|urgent|sev\d|p[0-3])\b", r"\b(blokkerend|urgent|spoed)\b"],
    # Research dimensions. "Investigate X" is a topic, not a question - these look for
    # something that can come back answered.
    "question": [r"\?", r"\b(whether|which of|how many|how long|can we|is it (feasible|possible))\b",
                 r"\b(of we|welke van|hoeveel|hoe lang|kunnen we|is het (haalbaar|mogelijk))\b",
                 r"\bfind out (if|whether|which|how)\b", r"\buitzoeken (of|welke|hoe)\b"],
    "decision": [r"\b(decide|decision|choose|choice|pick|before we (can )?(build|commit|start))\b",
                 r"\b(beslis\w*|besluit|keuze|kiezen|voordat we)\b", r"\bdepends on the (answer|outcome)\b",
                 r"\b(option|alternative)s?\b", r"\b(optie|alternatief|alternatieven)\b"],
    "timebox": [r"\btimebox\w*\b", r"\b\d+(\.\d+)?\s?(day|days|hour|hours|dag|dagen|uur)\b",
                r"\bno (more|longer) than\b", r"\bniet (meer|langer) dan\b", r"\bmax(imum|imaal)?\b",
                r"\bhalf a day\b", r"\bhalve dag\b"],
    # Enabler dimensions. "unlocks" wants a named consumer of this work; "cost_of_delay"
    # wants the thing that breaks, slows or stays risky while it is not done.
    "unlocks": [r"\b(unlocks?|unblocks?|enables?|prerequisite for|needed (for|by|before)|"
                r"so that we can|before we can|makes? \w+ possible)\b",
                r"\b(ontgrendelt|maakt \w+ mogelijk|nodig (voor|om)|voorwaarde voor|"
                r"zodat we|voordat we)\b", r"\b[A-Z][A-Z0-9]{1,9}-\d+\b"],
    "cost_of_delay": [r"\b(end.of.life|eol|deprecat\w+|unsupported|no longer (supported|maintained)|"
                      r"security (patch|fix|advisory)|cve-\d+|blocks?|blocked|slows?|"
                      r"every (sprint|week|release)|each time|manual(ly)?|toil|"
                      r"if we (don'?t|do not)|until we|otherwise)\b",
                      r"\b(niet meer ondersteund|verouderd|blokkeert|vertraagt|handmatig|"
                      r"elke (sprint|week|release)|als we (dit )?niet|zolang we|anders)\b"],
    "answer_shape": [r"\b(spike|proof of concept|poc|prototype|benchmark|measurement|comparison)\b",
                     r"\b(prototype|meting|vergelijking|onderzoeksnotitie)\b",
                     r"\b(adr|design note|write-?up|recommendation|advies|notitie)\b",
                     r"\bwe will know\b", r"\bwe weten dan\b"],
}

# Things that give Phase 2 something to search for.
ANCHOR_PATTERNS = [
    (r"\b[A-Z][a-z]+(?:[A-Z][a-z0-9]+)+\b", "CamelCase symbol"),
    (r"\b[a-z]+_[a-z0-9_]+\b", "snake_case symbol"),
    (r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/[\w/{}.-]+", "endpoint"),
    (r"(?<![\w:])/[\w.-]+(?:/[\w.-]+)+", "path"),
    (r"`([^`]{2,80})`", "code span"),
    (r"\b[45]\d\d\b", "http status"),
    (r"\b[A-Z]{2,}-\d+\b", "ticket key"),
    (r"\b\w+\.(py|ts|tsx|js|go|rs|java|kt|cs|sql|yaml|yml|json|proto)\b", "filename"),
    (r"\"([^\"]{4,80})\"", "quoted string"),
    (r"\b[A-Z][A-Z0-9_]{3,}\b", "constant / error code"),
]

# Title-case words that are grammar, not domain: skip as anchors.
COMMON_TITLE_WORDS = {"only", "please", "also", "then", "when", "expected", "actual", "steps",
                      "after", "before", "this", "that", "there", "these", "those", "with",
                      "from", "into", "alleen", "wanneer", "verwacht", "stappen", "daarna"}

# A mechanism named with no outcome is a solution smuggled into the ask.
MECHANISM_WORDS = [r"\b(redis|kafka|rabbitmq|cache|caching|index|indexes|cron|queue|webhook|"
                   r"microservice|refactor|rewrite|migrate to|upgrade to|switch to|replace \w+ with|"
                   r"use \w+ instead|elasticsearch|graphql|grpc)\b"]

BUG_WORDS = [r"\b(bug|defect|broken|crash\w*|error|exception|500|fails?|failing|regression|"
             r"incorrect|wrong|doesn'?t work|does not work|not working|fix|fixed|hotfix)\b",
             r"\b(fout|foutmelding|storing|kapot|werkt niet|crasht|faalt|regressie|onjuist|"
             r"verkeerd|fixen|gaat mis|mislukt)\b"]

# Deliberately narrow. These name the *act* of finding out; a ticket that merely
# mentions a risk or an option is not research. One hit is enough because none of
# these words appears in a story that already knows what it is building.
RESEARCH_WORDS = [r"\b(spike|proof of concept|feasibility|investigate|investigation|"
                  r"research|explore|exploration|prototype|evaluate options|"
                  r"compare (the )?options|find out (if|whether|which|how)|"
                  r"we don'?t know (yet|if|whether|which))\b",
                  r"\b(onderzoek|onderzoeken|uitzoeken|uitzoekwerk|haalbaarheid|"
                  r"haalbaarheidsonderzoek|verkennen|verkenning|vooronderzoek|"
                  r"opties vergelijken|we weten (nog )?niet)\b"]

# Work whose customer is the team. Narrow on purpose: "platform" and "pipeline" are
# domain nouns in half the businesses this will meet, so they are not here alone.
ENABLER_WORDS = [r"\b(as an? (developer|engineer|team|ops|sre|devops)\b|upgrade|bump|"
                 r"set ?up|introduce (a|the|an)|ci/cd|ci pipeline|build pipeline|"
                 r"infrastructure|tooling|dev(eloper)? experience|dependency (update|upgrade)|"
                 r"end.of.life|eol|deprecat\w+|enabler|tech(nical)? enabler|scaffold\w*)\b",
                 r"\b(als (een )?(developer|ontwikkelaar|engineer|team)\b|upgraden|opzetten|"
                 r"inrichten|infrastructuur|tooling|afhankelijkheid (bijwerken|upgraden)|"
                 r"verouderd|niet meer ondersteund|enabler)\b"]

# A project that does not exist yet. Only the act of starting one counts - "new
# feature" and "new endpoint" are ordinary stories inside something that exists.
GREENFIELD_WORDS = [r"\b(greenfield|from scratch|new (project|service|repo|repository|skill|"
                    r"application|app|package|library|module)\b|brand.new|does not exist yet|"
                    r"set up a new|bootstrap(ping)? a)\b",
                    r"\b(nieuw (project|systeem|repo|skill|pakket|onderdeel)|vanaf nul|"
                    r"bestaat nog niet|opzetten van een nieuw)\b"]

DUTCH_STOPWORDS = (r"\b(de|het|een|en|niet|wordt|worden|moet|moeten|zodat|wanneer|gebruiker|"
                   r"gebruikers|klant|klanten|als|maar|voor|bij|op|je|dat|ook|naar|zijn|sinds|"
                   r"altijd|alle|graag|krijg|krijgt|geeft|stappen|verwacht|werkelijk)\b")

QUESTIONS = {
    "en": {
        "actor": "Who is this for? (best guess: {guess})",
        "outcome": "What is different for them afterwards - what can they do or see that they cannot today? (best guess: {guess})",
        "trigger": "What triggers it - which action, event or schedule? (best guess: {guess})",
        "success_signal": "How will we know it worked - a number, a metric, an absence of something? (best guess: {guess})",
        "scope": "What is explicitly not part of this? (best guess: {guess})",
        "repro": "Exact steps to reproduce, from a clean state?",
        "expected": "What should have happened?",
        "actual": "What happened instead - error text, screenshot, response?",
        "environment": "Which environment, version or build, and which client?",
        "impact": "How many users or orders, how often, since when?",
        "question": "What exactly do we not know - phrased so it can come back answered, not as a topic?",
        "decision": "Which decision is waiting on the answer, and who makes it? (If none, this is reading, not a ticket.)",
        "timebox": "How long are we willing to spend before we decide with what we have?",
        "answer_shape": "What does the answer look like when it arrives - a number, a working prototype, a recommendation?",
        "unlocks": "Which story, team or capability is waiting on this? Name it. (If nothing is, this is gold-plating.)",
        "cost_of_delay": "What breaks, slows down or stays risky for every sprint this is not done?",
    },
    "nl": {
        "actor": "Voor wie is dit? (vermoeden: {guess})",
        "outcome": "Wat is er daarna anders voor hen - wat kunnen ze doen of zien dat nu niet kan? (vermoeden: {guess})",
        "trigger": "Wat zet het in gang - welke actie, gebeurtenis of schema? (vermoeden: {guess})",
        "success_signal": "Hoe weten we dat het werkt - een getal, een metriek, het uitblijven van iets? (vermoeden: {guess})",
        "scope": "Wat hoort er uitdrukkelijk niet bij? (vermoeden: {guess})",
        "repro": "Exacte stappen om te reproduceren, vanaf een schone staat?",
        "expected": "Wat had er moeten gebeuren?",
        "actual": "Wat gebeurde er in plaats daarvan - fouttekst, screenshot, response?",
        "environment": "Welke omgeving, versie of build, en welke client?",
        "impact": "Hoeveel gebruikers of orders, hoe vaak, sinds wanneer?",
        "question": "Wat weten we precies niet - geformuleerd zodat het beantwoord terug kan komen, niet als onderwerp?",
        "decision": "Welk besluit wacht op het antwoord, en wie neemt het? (Is er geen, dan is dit lezen en geen ticket.)",
        "timebox": "Hoeveel tijd willen we eraan besteden voordat we beslissen met wat we hebben?",
        "answer_shape": "Hoe ziet het antwoord eruit als het er is - een getal, een werkend prototype, een advies?",
        "unlocks": "Welke story, welk team of welke capability wacht hierop? Noem het. (Wacht er niets, dan is dit vergulden.)",
        "cost_of_delay": "Wat breekt, vertraagt of blijft risicovol voor elke sprint dat dit niet gedaan is?",
    },
}


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def detect_kind(text):
    """Research first: a research item often talks about a bug or a feature, because
    that is what it is research *about*. Assessing it as one asks for an actor and a
    repro that will never exist, and 'insufficient' then looks like a bad ticket
    rather than the wrong questionnaire. Bug before enabler, because "upgrade the
    library to stop the crash" is a bug with a proposed fix, not an enabler."""
    if sum(len(re.findall(p, text, re.I)) for p in RESEARCH_WORDS) >= 1:
        return "spike"
    if sum(len(re.findall(p, text, re.I)) for p in BUG_WORDS) >= 2:
        return "bug"
    if sum(len(re.findall(p, text, re.I)) for p in ENABLER_WORDS) >= 1:
        return "enabling"
    return "feature"


# Enough English function words that a ticket in a third language cannot pass as one.
ENGLISH_STOPWORDS = r"\b(the|and|that|with|for|from|when|should|would|this|there|which|"\
                    r"have|has|are|was|were|will|not|but|they|their|user|users)\b"


def _stopword_score(text, pattern):
    """Distinct stopwords, not occurrences. Counting occurrences means four 'de's in a
    French sentence score as Dutch, after which the whole assessment runs in the wrong
    language and every check quietly passes."""
    return len({m.lower() for m in re.findall(pattern, text, re.I)})


def detect_lang(text):
    """The language of the item, or 'unknown'. Detection lives in lang.py so emit.py
    and summary.py render in the same language the intake recorded."""
    import lang as L
    code, _ = L.detect(text)
    return code or "unknown"


def language_is_supported(text, lang):
    """The dimension patterns and the vagueness lexicon cover the languages in
    lang.PATTERN_LANGUAGES. Any other language is detected and recorded, but its
    dimensions must be assessed by reading - the patterns would find nothing and the
    item would pass every check without anyone having looked."""
    import lang as L
    if len(text.split()) < 12:
        return True                      # too short to judge; 'very short' already flags it
    return lang in L.PATTERN_LANGUAGES


def find_signal(text, dimension):
    for pattern in SIGNALS.get(dimension, []):
        m = re.search(pattern, text, re.I | re.M)
        if m:
            start = max(0, m.start() - 30)
            end = min(len(text), m.end() + 50)
            return text[start:end].replace("\n", " ").strip()
    return None


def _domain_nouns(text):
    """Title-case words that are not sentence-initial: 'Invoices', 'Exact', 'OrderDetail'.
    Product and screen names are what a scan hypothesis is made of."""
    out = []
    for m in re.finditer(r"\b[A-Z][a-z]{3,}\b", text):
        before = text[:m.start()].rstrip()
        if not before or before[-1] in ".!?:\n" or before.endswith(("- ", "* ")):
            continue
        out.append(m.group(0))
    return out


def find_anchors(text):
    seen, out = set(), []
    for value in _domain_nouns(text):
        if value.lower() not in seen and value.lower() not in COMMON_TITLE_WORDS:
            seen.add(value.lower())
            out.append({"value": value, "kind": "domain noun"})
    for pattern, label in ANCHOR_PATTERNS:
        for m in re.finditer(pattern, text):
            value = (m.group(1) if m.groups() else m.group(0)).strip()
            if len(value) < 3 or value.lower() in seen:
                continue
            # CamelCase false positives: sentence-initial words like "Finance"
            if label == "CamelCase symbol" and not re.search(r"[a-z][A-Z]", value):
                continue
            seen.add(value.lower())
            out.append({"value": value, "kind": label})
    return out[:25]


def repos_reachable(cfg):
    repos = get(cfg, "evidence.repos", []) or []
    return [r["name"] for r in repos if isinstance(r, dict)
            and r.get("path") and os.path.isdir(os.path.abspath(r["path"]))]


def assess(text, cfg, kind="auto", lang="auto"):
    kind = detect_kind(text) if kind == "auto" else kind
    lang = detect_lang(text) if lang == "auto" else lang
    fallback = DEFAULT_REQUIRED.get(kind) or DEFAULT_REQUIRED["feature"]
    required = get(cfg, "intake.%s_required" % kind, fallback) or fallback
    recommended = get(cfg, "intake.%s_recommended" % kind,
                      DEFAULT_RECOMMENDED.get(kind, [])) or DEFAULT_RECOMMENDED.get(kind, [])
    min_anchors = get(cfg, "intake.min_anchors", 1)

    dims = []
    for dim in list(required) + list(recommended):
        snippet = find_signal(text, dim)
        dims.append({
            "id": dim,
            "required": dim in required,
            "status": "present" if snippet else "missing",
            "evidence": snippet or "",
            "heuristic": True,
        })
    anchors = find_anchors(text)
    reachable = repos_reachable(cfg)
    mechanism = any(re.search(p, text, re.I) for p in MECHANISM_WORDS)
    outcome_present = any(d["id"] == "outcome" and d["status"] == "present" for d in dims)

    missing_required = [d["id"] for d in dims if d["required"] and d["status"] == "missing"]
    mechanism_only = mechanism and not outcome_present
    # A story for a project that does not exist yet has nothing to scan. That is not
    # a missing anchor, it is a different Phase 2: reuse is what gets ruled out, and the
    # first subtask is a walking skeleton. Flag it so the reader confirms it in
    # evidence.greenfield rather than the gates demanding citations into thin air.
    greenfield = any(re.search(p, text, re.I) for p in GREENFIELD_WORDS)
    if not missing_required:
        verdict = "sufficient"
    elif mechanism_only:
        # A named solution with no stated purpose is not scoutable: scanning for how to
        # build it answers the wrong question. Ask what it is for first.
        verdict = "insufficient"
    elif len(anchors) >= min_anchors and reachable:
        verdict = "scoutable"
    else:
        verdict = "insufficient"

    flags = []
    if not language_is_supported(text, lang):
        flags.append("language %r: the dimension patterns and the vagueness lexicon cover %s "
                     "only, so this assessment looked at almost nothing - assess every "
                     "dimension by reading, set heuristic: false, and write the refinement in "
                     "the item's own language (story.language). Add a vagueness_lexicon for "
                     "it in refinery.yaml, or that check stays decorative"
                     % (lang, "/".join(__import__("lang").PATTERN_LANGUAGES)))
    if mechanism_only:
        flags.append("mechanism-only: a solution is named but no outcome - ask what it is for "
                     "before scanning for how to build it")
    if greenfield:
        flags.append("greenfield-candidate: the text describes a project that does not exist "
                     "yet. If so, set evidence.greenfield (target, reason), rule out reuse "
                     "instead of scanning, and plan a walking skeleton first - see "
                     "references/evidence.md")
    if len(text.split()) < 12:
        flags.append("very short: %d words" % len(text.split()))
    if not reachable and (get(cfg, "evidence.repos") or []):
        flags.append("no configured repo is reachable on disk - Phase 2 cannot run")
    if not (get(cfg, "evidence.repos") or []):
        flags.append("no repos configured - run evidence.py init first")

    questions = []
    for d in dims:
        if d["status"] == "missing":
            guess = "?"  # the assistant replaces this with its actual best guess
            questions.append({
                "dimension": d["id"],
                "blocking": d["required"],
                # Question templates ship in en and nl; any other language gets the
                # English template and the flag already says to put it in the item's
                # language when it is asked.
                "text": QUESTIONS.get(lang, QUESTIONS["en"])[d["id"]].format(guess=guess),
            })

    return {
        "assessed_at": now_iso(),
        "kind": kind,
        "lang": lang,
        "verdict": verdict,
        "verdict_basis": "lexical signals only - confirm every dimension against the source text",
        "word_count": len(text.split()),
        "dimensions": dims,
        "anchors": anchors,
        "repos_reachable": reachable,
        "flags": flags,
        "questions": questions,
    }


def print_report(rep):
    print("kind=%s lang=%s words=%d  ->  %s" % (rep["kind"], rep["lang"], rep["word_count"],
                                                rep["verdict"].upper()))
    print("(%s)" % rep["verdict_basis"])
    for d in rep["dimensions"]:
        tag = "REQ" if d["required"] else "rec"
        mark = "present" if d["status"] == "present" else "MISSING"
        print("  %-3s %-15s %-8s %s" % (tag, d["id"], mark, ("- " + d["evidence"][:70]) if d["evidence"] else ""))
    if rep["anchors"]:
        print("  anchors (%d): %s" % (len(rep["anchors"]),
                                      ", ".join(a["value"] for a in rep["anchors"][:8])))
    else:
        print("  anchors: none - nothing to scan for")
    print("  repos reachable: %s" % (", ".join(rep["repos_reachable"]) or "none"))
    for f in rep["flags"]:
        print("  ! %s" % f)
    if rep["questions"]:
        print("\nAsk before continuing (replace every '?' guess with your own):")
        for q in rep["questions"]:
            print("  [%s] %s" % ("blocking" if q["blocking"] else "non-blocking", q["text"]))
    if rep["verdict"] == "scoutable":
        print("\nScoutable: run Phase 2 to sharpen the questions above, then stop and ask. "
              "Do not decompose.")
    elif rep["verdict"] == "insufficient":
        # Say which of the three reasons it is; "nothing to scan for" when the real
        # cause is an unreachable repo sends the reader to fix the wrong thing.
        if any(f.startswith("mechanism-only") for f in rep["flags"]):
            why = "a mechanism is named with no outcome - ask what it is for before scanning"
        elif not rep["anchors"]:
            why = "there is nothing to scan for"
        elif not rep["repos_reachable"]:
            why = "there are anchors but no configured repo is reachable, so Phase 2 cannot run"
        else:
            why = "required dimensions are missing"
        print("\nInsufficient: ask first - %s." % why)


def write_into_bundle(path, rep):
    with open(path, "r", encoding="utf-8") as fh:
        bundle = json.load(fh)
    story = bundle.setdefault("story", {})
    existing_q = bundle.setdefault("open_questions", [])
    used = {q.get("id") for q in existing_q}
    # A re-assessment is a re-scan of the text, not a reset of the conversation. A
    # dimension somebody answered or assumed - with a name and a date on it - is newer
    # information than the text, and the question that produced it is already asked.
    # Overwriting those turned every re-refinement into a second interrogation of the
    # same people, and dropped the domain classification on the floor with them.
    previous = story.get("intake") or {}
    settled = {d.get("id"): d for d in previous.get("dimensions") or []
               if d.get("status") in ("answered", "assumed")}
    asked = {q.get("dimension") for q in existing_q if q.get("dimension")}
    dims = []
    for d in rep["dimensions"]:
        dims.append(settled.get(d["id"], d))
    n = 1
    for q in rep["questions"]:
        if q["dimension"] in settled or q["dimension"] in asked:
            continue
        while "Q%d" % n in used:
            n += 1
        qid = "Q%d" % n
        used.add(qid)
        existing_q.append({"id": qid, "text": q["text"], "owner": "",
                           "blocking": q["blocking"], "dimension": q["dimension"]})
        for d in dims:
            if d["id"] == q["dimension"]:
                d["question_id"] = qid
    rep = dict(rep, dimensions=dims)
    still_missing = [d for d in dims if d.get("required") and d.get("status") == "missing"]
    if rep["verdict"] != "sufficient" and not still_missing:
        rep["verdict"] = "sufficient"
    fresh = {k: rep[k] for k in ("assessed_at", "kind", "lang", "verdict",
                                 "dimensions", "anchors", "repos_reachable", "flags")}
    for k in ("domain", "domain_rationale"):
        if previous.get(k):
            fresh[k] = previous[k]
    story["intake"] = fresh
    # The item's language is adopted for every human-facing field; record where it
    # came from so a hand-set language (a mixed ticket, an unknown language named by
    # reading) is never overwritten by detection.
    existing = story.get("language") or {}
    if not (isinstance(existing, dict) and existing.get("source") == "given"):
        story["language"] = {"code": rep["lang"], "source": "detected" if rep["lang"] != "unknown"
                             else "undetected - name it by reading and set source: given"}
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(bundle, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    return len(rep["questions"])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("assess")
    p.add_argument("--config", default="refinery.yaml")
    p.add_argument("--text", help="file with the raw ticket text; '-' for stdin")
    p.add_argument("--bundle", help="bundle.json; reads story.source_text")
    p.add_argument("--kind", choices=["feature", "bug", "spike", "enabling", "auto"], default="auto")
    p.add_argument("--lang", default="auto", help="ISO code, or auto")
    p.add_argument("--write", action="store_true",
                   help="with --bundle: write story.intake and add questions for missing dimensions")
    p.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.text == "-":
        text = sys.stdin.read()
    elif args.text:
        with open(args.text, "r", encoding="utf-8") as fh:
            text = fh.read()
    elif args.bundle:
        with open(args.bundle, "r", encoding="utf-8") as fh:
            text = (json.load(fh).get("story") or {}).get("source_text") or ""
        if not text.strip():
            print("story.source_text is empty - record the original ask first", file=sys.stderr)
            return 2
    else:
        ap.error("give --text or --bundle")

    cfg = load_config(args.config) if os.path.exists(args.config) else {}
    rep = assess(text, cfg, args.kind, args.lang)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        print_report(rep)
    if args.write and args.bundle:
        added = write_into_bundle(args.bundle, rep)
        print("\nwrote story.intake and %d question(s) into %s" % (added, args.bundle))
    return {"sufficient": 0, "scoutable": 3, "insufficient": 4}[rep["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
