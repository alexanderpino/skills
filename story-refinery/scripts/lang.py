#!/usr/bin/env python3
"""Language: detect it, adopt it, render in it. Stdlib only.

Tickets arrive in any language, and a refined story goes back in the language it
came in - a Dutch description with English headings reads as a translation error.
So: `detect()` says which language a text is in (or that it cannot tell), the
bundle records it in story.language, every human-facing field is written in it,
and emit.py / summary.py take their headings from HEADINGS / LABELS for that code,
falling back to English with a finding (LANG003) rather than silently.

Detection is stopword-based and counts *distinct* function words, so one
sentence in the wrong language cannot flip a ticket. It knows the languages below;
anything else comes back as None and is recorded as "unknown" - the model then
names it by reading, and the gates that cannot check that language say so.
"""

import re

STOPWORDS = {
    "en": "the and that with for from when should would this there which have has are was were "
          "will not but they their user users be to of in on it is as by an at or if",
    "nl": "de het een en niet wordt worden moet moeten zodat wanneer gebruiker gebruikers klant "
          "klanten als maar voor bij op je dat ook naar zijn sinds altijd alle graag krijgt geeft "
          "verwacht van is er om met dan nog wel",
    "de": "der die das und nicht wird werden muss müssen damit wenn benutzer kunde als aber für "
          "bei auf dass auch nach sind seit immer alle ein eine ist von zu mit dem den im",
    "fr": "le la les et pas est sont doit doivent pour que qui avec dans sur une un des du au "
          "aux ne quand utilisateur client mais aussi depuis toujours tous cette ce",
    "es": "el la los las y no es son debe deben para que con en una un del al por cuando "
          "usuario cliente pero también desde siempre todos esta este se lo",
    "it": "il la le gli e non è sono deve devono per che con una un del al da quando utente "
          "cliente ma anche sempre tutti questa questo si lo di",
    "pt": "o a os as e não é são deve devem para que com em uma um do da ao quando usuário "
          "cliente mas também desde sempre todos esta este se lo de",
}
_RX = {code: re.compile(r"\b(%s)\b" % "|".join(map(re.escape, words.split())), re.I)
       for code, words in STOPWORDS.items()}
MIN_DISTINCT = 4

# Languages the intake's lexical signal patterns cover. Others are detected and
# recorded, but the intake dimensions must be assessed by reading.
PATTERN_LANGUAGES = ("en", "nl")

# The connector AC008 counts alternatives on, per language.
CONNECTOR = {"en": r"\bor\b", "nl": r"\bof\b", "de": r"\boder\b", "fr": r"\bou\b",
             "es": r"\bo\b", "it": r"\bo\b", "pt": r"\bou\b"}


def score(text):
    return {code: len({m.group(0).lower() for m in rx.finditer(text or "")})
            for code, rx in _RX.items()}


def detect(text):
    """(code, distinct stopwords) for the best language, or (None, best) below the floor."""
    s = score(text)
    code = max(s, key=s.get) if s else None
    best = s.get(code, 0) if code else 0
    if best < MIN_DISTINCT:
        return None, best
    # A near tie between two languages is not a detection.
    second = sorted(s.values())[-2] if len(s) > 1 else 0
    if second and best - second < 2 and len((text or "").split()) < 40:
        return None, best
    return code, best


def code_of(bundle):
    """story.language.code, falling back to intake.lang, then 'en'."""
    story = bundle.get("story") or {}
    lang = story.get("language") or {}
    return (lang.get("code") if isinstance(lang, dict) else lang) \
        or (story.get("intake") or {}).get("lang") or "en"


# ------------------------------------------------------------------- rendering

HEADINGS = {
    "en": {"why": "Why / What", "goal": "Goal", "complexity": "Complexity",
           "prerequisites": "Prerequisites", "acceptance_criteria": "Acceptance criteria",
           "decision_table": "Decision table", "non_goals": "Non-goals",
           "technical_notes": "Technical notes", "decisions": "Decisions", "risks": "Risks",
           "open_questions": "Open questions", "subtasks": "Subtasks",
           "non_functional": "Non-functional", "ruled_out": "Already ruled out",
           "contracts": "Contracts that cross a boundary", "done_when": "Done when",
           "waves": "Execution waves", "for_developer": "For the developer",
           "freshness": "Freshness", "glossary": "Glossary", "links": "Links to create",
           "not_there_yet": "Not there yet", "re_refinement": "Re-refinement",
           "review": "Review", "triage": "Triage", "outcome": "The outcome this serves"},
    "nl": {"why": "Waarom / Wat", "goal": "Doel", "complexity": "Complexiteit",
           "prerequisites": "Randvoorwaarden", "acceptance_criteria": "Acceptatiecriteria",
           "decision_table": "Beslistabel", "non_goals": "Buiten scope",
           "technical_notes": "Technische notities", "decisions": "Besluiten", "risks": "Risico's",
           "open_questions": "Open vragen", "subtasks": "Subtaken",
           "non_functional": "Niet-functioneel", "ruled_out": "Al uitgesloten",
           "contracts": "Contracten over een grens", "done_when": "Klaar wanneer",
           "waves": "Uitvoeringsgolven", "for_developer": "Voor de ontwikkelaar",
           "freshness": "Actualiteit", "glossary": "Begrippen", "links": "Aan te maken links",
           "not_there_yet": "Bestaat nog niet", "re_refinement": "Her-refinement",
           "review": "Review", "triage": "Triage", "outcome": "Het doel dat dit dient"},
    "de": {"why": "Warum / Was", "goal": "Ziel", "complexity": "Komplexität",
           "prerequisites": "Voraussetzungen", "acceptance_criteria": "Akzeptanzkriterien",
           "decision_table": "Entscheidungstabelle", "non_goals": "Nicht-Ziele",
           "technical_notes": "Technische Hinweise", "decisions": "Entscheidungen", "risks": "Risiken",
           "open_questions": "Offene Fragen", "subtasks": "Teilaufgaben",
           "non_functional": "Nicht-funktional", "ruled_out": "Bereits ausgeschlossen",
           "contracts": "Verträge über eine Grenze", "done_when": "Fertig wenn",
           "waves": "Ausführungswellen", "for_developer": "Für den Entwickler",
           "freshness": "Aktualität", "glossary": "Glossar", "links": "Anzulegende Verknüpfungen",
           "not_there_yet": "Noch nicht vorhanden", "re_refinement": "Erneutes Refinement",
           "review": "Review", "triage": "Triage", "outcome": "Das Ziel dahinter"},
    "fr": {"why": "Pourquoi / Quoi", "goal": "Objectif", "complexity": "Complexité",
           "prerequisites": "Prérequis", "acceptance_criteria": "Critères d'acceptation",
           "decision_table": "Table de décision", "non_goals": "Hors périmètre",
           "technical_notes": "Notes techniques", "decisions": "Décisions", "risks": "Risques",
           "open_questions": "Questions ouvertes", "subtasks": "Sous-tâches",
           "non_functional": "Non fonctionnel", "ruled_out": "Déjà exclu",
           "contracts": "Contrats traversant une frontière", "done_when": "Terminé quand",
           "waves": "Vagues d'exécution", "for_developer": "Pour le développeur",
           "freshness": "Fraîcheur", "glossary": "Glossaire", "links": "Liens à créer",
           "not_there_yet": "Pas encore là", "re_refinement": "Re-raffinement",
           "review": "Revue", "triage": "Triage", "outcome": "L'objectif servi"},
    "es": {"why": "Por qué / Qué", "goal": "Objetivo", "complexity": "Complejidad",
           "prerequisites": "Requisitos previos", "acceptance_criteria": "Criterios de aceptación",
           "decision_table": "Tabla de decisión", "non_goals": "Fuera de alcance",
           "technical_notes": "Notas técnicas", "decisions": "Decisiones", "risks": "Riesgos",
           "open_questions": "Preguntas abiertas", "subtasks": "Subtareas",
           "non_functional": "No funcional", "ruled_out": "Ya descartado",
           "contracts": "Contratos que cruzan un límite", "done_when": "Hecho cuando",
           "waves": "Oleadas de ejecución", "for_developer": "Para el desarrollador",
           "freshness": "Vigencia", "glossary": "Glosario", "links": "Enlaces a crear",
           "not_there_yet": "Aún no existe", "re_refinement": "Re-refinamiento",
           "review": "Revisión", "triage": "Triaje", "outcome": "El objetivo que sirve"},
    "it": {"why": "Perché / Cosa", "goal": "Obiettivo", "complexity": "Complessità",
           "prerequisites": "Prerequisiti", "acceptance_criteria": "Criteri di accettazione",
           "decision_table": "Tabella decisionale", "non_goals": "Fuori ambito",
           "technical_notes": "Note tecniche", "decisions": "Decisioni", "risks": "Rischi",
           "open_questions": "Domande aperte", "subtasks": "Sottoattività",
           "non_functional": "Non funzionale", "ruled_out": "Già escluso",
           "contracts": "Contratti che attraversano un confine", "done_when": "Fatto quando",
           "waves": "Ondate di esecuzione", "for_developer": "Per lo sviluppatore",
           "freshness": "Attualità", "glossary": "Glossario", "links": "Collegamenti da creare",
           "not_there_yet": "Non ancora presente", "re_refinement": "Ri-raffinamento",
           "review": "Revisione", "triage": "Triage", "outcome": "L'obiettivo servito"},
    "pt": {"why": "Porquê / O quê", "goal": "Objetivo", "complexity": "Complexidade",
           "prerequisites": "Pré-requisitos", "acceptance_criteria": "Critérios de aceitação",
           "decision_table": "Tabela de decisão", "non_goals": "Fora do escopo",
           "technical_notes": "Notas técnicas", "decisions": "Decisões", "risks": "Riscos",
           "open_questions": "Questões em aberto", "subtasks": "Subtarefas",
           "non_functional": "Não funcional", "ruled_out": "Já descartado",
           "contracts": "Contratos que cruzam uma fronteira", "done_when": "Concluído quando",
           "waves": "Ondas de execução", "for_developer": "Para o desenvolvedor",
           "freshness": "Atualidade", "glossary": "Glossário", "links": "Ligações a criar",
           "not_there_yet": "Ainda não existe", "re_refinement": "Re-refinamento",
           "review": "Revisão", "triage": "Triagem", "outcome": "O objetivo servido"},
}

LABELS = {
    "en": {"why": "Why.", "size": "Size.", "complexity": "Complexity.", "in_order": "In order.",
           "hinges": "It hinges on.", "ask_round": "Ask this round.",
           "waits_earlier": "Waits on an earlier answer.", "all_answered": "Every question is answered.",
           "worth_saying": "Worth saying out loud.", "waits_missing": "Waits on work that does not exist yet.",
           "leaves_behind": "Leaves behind.", "ready": "Ready.", "not_ready": "Not ready"},
    "nl": {"why": "Waarom.", "size": "Omvang.", "complexity": "Complexiteit.", "in_order": "Op volgorde.",
           "hinges": "Het hangt af van.", "ask_round": "Deze ronde vragen.",
           "waits_earlier": "Wacht op een eerder antwoord.", "all_answered": "Elke vraag is beantwoord.",
           "worth_saying": "Hardop zeggen.", "waits_missing": "Wacht op werk dat nog niet bestaat.",
           "leaves_behind": "Laat achter.", "ready": "Klaar.", "not_ready": "Niet klaar"},
    "de": {"why": "Warum.", "size": "Umfang.", "complexity": "Komplexität.", "in_order": "Der Reihe nach.",
           "hinges": "Hängt ab von.", "ask_round": "In dieser Runde fragen.",
           "waits_earlier": "Wartet auf eine frühere Antwort.", "all_answered": "Jede Frage ist beantwortet.",
           "worth_saying": "Laut sagen.", "waits_missing": "Wartet auf Arbeit, die es noch nicht gibt.",
           "leaves_behind": "Hinterlässt.", "ready": "Bereit.", "not_ready": "Nicht bereit"},
    "fr": {"why": "Pourquoi.", "size": "Taille.", "complexity": "Complexité.", "in_order": "Dans l'ordre.",
           "hinges": "Cela dépend de.", "ask_round": "À demander ce tour-ci.",
           "waits_earlier": "Attend une réponse antérieure.", "all_answered": "Chaque question a sa réponse.",
           "worth_saying": "À dire à voix haute.", "waits_missing": "Attend un travail qui n'existe pas encore.",
           "leaves_behind": "Laisse derrière.", "ready": "Prêt.", "not_ready": "Pas prêt"},
    "es": {"why": "Por qué.", "size": "Tamaño.", "complexity": "Complejidad.", "in_order": "En orden.",
           "hinges": "Depende de.", "ask_round": "Preguntar en esta ronda.",
           "waits_earlier": "Espera una respuesta anterior.", "all_answered": "Todas las preguntas respondidas.",
           "worth_saying": "Decirlo en voz alta.", "waits_missing": "Espera trabajo que aún no existe.",
           "leaves_behind": "Deja pendiente.", "ready": "Listo.", "not_ready": "No listo"},
    "it": {"why": "Perché.", "size": "Dimensione.", "complexity": "Complessità.", "in_order": "In ordine.",
           "hinges": "Dipende da.", "ask_round": "Da chiedere in questo giro.",
           "waits_earlier": "Attende una risposta precedente.", "all_answered": "Ogni domanda ha risposta.",
           "worth_saying": "Da dire ad alta voce.", "waits_missing": "Attende lavoro che non esiste ancora.",
           "leaves_behind": "Lascia dietro.", "ready": "Pronto.", "not_ready": "Non pronto"},
    "pt": {"why": "Porquê.", "size": "Tamanho.", "complexity": "Complexidade.", "in_order": "Por ordem.",
           "hinges": "Depende de.", "ask_round": "Perguntar nesta ronda.",
           "waits_earlier": "Aguarda uma resposta anterior.", "all_answered": "Todas as perguntas respondidas.",
           "worth_saying": "Dizer em voz alta.", "waits_missing": "Aguarda trabalho que ainda não existe.",
           "leaves_behind": "Deixa para trás.", "ready": "Pronto.", "not_ready": "Não pronto"},
}


# Names of the complexity metrics, so the card's one-line form reads in the story's
# language too. Keys match complexity.NAMES.
METRIC_NAMES = {
    "nl": {"repos": "projecten geraakt", "code_paths": "codepaden gewijzigd",
           "files_written": "bestanden geschreven", "read_set": "bestanden in context",
           "contracts": "contracten gekruist", "breaking_contracts": "brekende contractwijzigingen",
           "owner_teams": "eigenaar-teams", "rule_space": "beslistabel-combinaties",
           "forks": "ontwerpkeuzes", "deferred": "uitgestelde besluiten",
           "unknowns": "blokkerende onbekenden", "irreversible": "onomkeerbare stappen",
           "critical_path": "kritiek pad (subtaken diep)", "domain": "Cynefin-domein",
           "greenfield": "greenfield"},
    "de": {"repos": "betroffene Projekte", "code_paths": "geänderte Codepfade",
           "files_written": "geschriebene Dateien", "read_set": "Dateien im Kontext",
           "contracts": "überschrittene Verträge", "breaking_contracts": "brechende Vertragsänderungen",
           "owner_teams": "besitzende Teams", "rule_space": "Entscheidungstabellen-Kombinationen",
           "forks": "Entwurfsentscheidungen", "deferred": "vertagte Entscheidungen",
           "unknowns": "blockierende Unbekannte", "irreversible": "unumkehrbare Schritte",
           "critical_path": "kritischer Pfad (Teilaufgaben tief)", "domain": "Cynefin-Domäne",
           "greenfield": "Greenfield"},
    "fr": {"repos": "projets touchés", "code_paths": "chemins de code modifiés",
           "files_written": "fichiers écrits", "read_set": "fichiers en contexte",
           "contracts": "contrats traversés", "breaking_contracts": "changements de contrat cassants",
           "owner_teams": "équipes propriétaires", "rule_space": "combinaisons de la table de décision",
           "forks": "choix de conception", "deferred": "décisions différées",
           "unknowns": "inconnues bloquantes", "irreversible": "étapes irréversibles",
           "critical_path": "chemin critique (profondeur)", "domain": "domaine Cynefin",
           "greenfield": "greenfield"},
    "es": {"repos": "proyectos afectados", "code_paths": "rutas de código cambiadas",
           "files_written": "archivos escritos", "read_set": "archivos en contexto",
           "contracts": "contratos cruzados", "breaking_contracts": "cambios de contrato rompedores",
           "owner_teams": "equipos propietarios", "rule_space": "combinaciones de la tabla de decisión",
           "forks": "decisiones de diseño", "deferred": "decisiones diferidas",
           "unknowns": "incógnitas bloqueantes", "irreversible": "pasos irreversibles",
           "critical_path": "ruta crítica (profundidad)", "domain": "dominio Cynefin",
           "greenfield": "greenfield"},
    "it": {"repos": "progetti toccati", "code_paths": "percorsi di codice modificati",
           "files_written": "file scritti", "read_set": "file nel contesto",
           "contracts": "contratti attraversati", "breaking_contracts": "modifiche di contratto rompenti",
           "owner_teams": "team proprietari", "rule_space": "combinazioni della tabella decisionale",
           "forks": "scelte di progettazione", "deferred": "decisioni rinviate",
           "unknowns": "incognite bloccanti", "irreversible": "passi irreversibili",
           "critical_path": "percorso critico (profondità)", "domain": "dominio Cynefin",
           "greenfield": "greenfield"},
    "pt": {"repos": "projetos afetados", "code_paths": "caminhos de código alterados",
           "files_written": "ficheiros escritos", "read_set": "ficheiros em contexto",
           "contracts": "contratos cruzados", "breaking_contracts": "alterações de contrato disruptivas",
           "owner_teams": "equipas proprietárias", "rule_space": "combinações da tabela de decisão",
           "forks": "decisões de design", "deferred": "decisões adiadas",
           "unknowns": "incógnitas bloqueantes", "irreversible": "passos irreversíveis",
           "critical_path": "caminho crítico (profundidade)", "domain": "domínio Cynefin",
           "greenfield": "greenfield"},
}


def metric_name(key, code, english):
    """The metric's name in `code`, or the English name complexity.py already has."""
    return METRIC_NAMES.get(code, {}).get(key, english.get(key, key))


def heading(key, code, override=None):
    """The heading for `key` in language `code`; a config override wins; English is the
    fallback when the language has no table - and `has_headings` says whether it did."""
    if override and key in override:
        return override[key]
    return HEADINGS.get(code, HEADINGS["en"]).get(key, HEADINGS["en"][key])


def label(key, code, override=None):
    if override and key in override:
        return override[key]
    return LABELS.get(code, LABELS["en"]).get(key, LABELS["en"][key])


def has_headings(code, override=None):
    return code in HEADINGS or bool(override and set(override) >= set(HEADINGS["en"]))
