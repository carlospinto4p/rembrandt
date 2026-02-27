"""Template-based sentence generation for cloze exercises.

Provides fill-in-the-blank sentences for Spanish vocabulary
practice, with template banks for verbs, masculine nouns,
feminine nouns, and adjectives.  Also provides English
templates for translation cloze (EN->ES) exercises.

Templates can be extended at runtime via
`load_cloze_templates()`, which reads a JSON file and
appends its entries to the built-in banks.
"""

import json
import random
from pathlib import Path

_VERB_TEMPLATES: list[str] = [
    "Quiero {word} contigo",
    "Voy a {word} mañana",
    "Necesito {word} más",
    "Me gusta {word}",
    "Puedo {word} bien",
    "Prefiero {word} aquí",
    "Debo {word} ahora",
    "Espero {word} pronto",
    "Intento {word} cada día",
    "Acabo de {word}",
    "No puedo {word} ahora",
    "Siempre quiero {word}",
    "Hay que {word} más",
    "Es difícil {word}",
    "Me encanta {word}",
]

_NOUN_M_TEMPLATES: list[str] = [
    "El {word} es muy importante",
    "Necesito el {word}",
    "El {word} está en la mesa",
    "¿Dónde está el {word}?",
    "Me gusta el {word}",
    "Un {word} grande",
    "El {word} es bonito",
    "Quiero un {word} nuevo",
    "Tengo el {word} aquí",
    "Este {word} es mío",
    "No encuentro el {word}",
    "El {word} cuesta mucho",
    "Compré un {word} ayer",
    "El {word} es pequeño",
    "Dame el {word}",
]

_NOUN_F_TEMPLATES: list[str] = [
    "La {word} es muy importante",
    "Necesito la {word}",
    "La {word} está en la mesa",
    "¿Dónde está la {word}?",
    "Me gusta la {word}",
    "Una {word} grande",
    "La {word} es bonita",
    "Quiero una {word} nueva",
    "Tengo la {word} aquí",
    "Esta {word} es mía",
    "No encuentro la {word}",
    "La {word} cuesta mucho",
    "Compré una {word} ayer",
    "La {word} es pequeña",
    "Dame la {word}",
]

_ADJECTIVE_TEMPLATES: list[str] = [
    "Es muy {word}",
    "No es tan {word}",
    "Parece {word}",
    "Está bastante {word}",
    "Se siente {word}",
    "Es demasiado {word}",
    "Es poco {word}",
    "Qué {word} es",
    "Es realmente {word}",
    "No parece {word}",
    "Siempre es {word}",
    "Nunca es {word}",
    "Todo parece {word}",
    "Se ve muy {word}",
    "Es increíblemente {word}",
]


def _select_template(
    *,
    verb: list[str],
    noun_m: list[str],
    noun_f: list[str],
    adjective: list[str],
    gender: str | None,
    conjugation_group: str | None,
) -> str:
    """Pick a template based on POS heuristic.

    :param verb: Verb template bank.
    :param noun_m: Masculine noun template bank.
    :param noun_f: Feminine noun template bank.
    :param adjective: Adjective template bank.
    :param gender: Noun gender, or `None`.
    :param conjugation_group: Verb group, or `None`.
    :return: A randomly chosen template string.
    """
    if conjugation_group is not None:
        templates = verb
    elif gender == "m":
        templates = noun_m
    elif gender == "f":
        templates = noun_f
    elif gender is not None:
        templates = noun_m
    else:
        templates = adjective
    return random.choice(templates)


def generate_cloze(
    word: str,
    *,
    gender: str | None = None,
    conjugation_group: str | None = None,
) -> tuple[str, str]:
    """Generate a cloze sentence with a blank for `word`.

    Picks a template bank based on POS heuristic:
    `conjugation_group` set -> verb, `gender` set -> noun
    (m/f), else -> adjective.

    :param word: The Spanish word to blank out.
    :param gender: Noun gender (`"m"` or `"f"`), or `None`.
    :param conjugation_group: Verb group (`"ar"`, `"er"`,
        `"ir"`), or `None`.
    :return: A tuple of `(sentence_with_blank, answer)` where
        the blank is `"___"`.
    """
    template = _select_template(
        verb=_VERB_TEMPLATES,
        noun_m=_NOUN_M_TEMPLATES,
        noun_f=_NOUN_F_TEMPLATES,
        adjective=_ADJECTIVE_TEMPLATES,
        gender=gender,
        conjugation_group=conjugation_group,
    )
    sentence = template.replace("{word}", "___")
    return sentence, word


# --- English templates for translation cloze exercises ---

_EN_VERB_TEMPLATES: list[str] = [
    "I want to {word} tomorrow",
    "I need to {word} more",
    "I like to {word}",
    "I can {word} well",
    "I prefer to {word} here",
    "I must {word} now",
    "I hope to {word} soon",
    "I try to {word} every day",
    "I just finished {word}ing",
    "I am going to {word}",
    "I cannot {word} right now",
    "I always want to {word}",
    "It is hard to {word}",
    "I love to {word}",
    "We should {word} together",
]

_EN_NOUN_TEMPLATES: list[str] = [
    "The {word} is very important",
    "I need the {word}",
    "The {word} is on the table",
    "Where is the {word}?",
    "I like the {word}",
    "A big {word}",
    "The {word} is nice",
    "I want a new {word}",
    "I have the {word} here",
    "This {word} is mine",
    "I cannot find the {word}",
    "The {word} costs a lot",
    "I bought a {word} yesterday",
    "The {word} is small",
    "Give me the {word}",
]

_EN_ADJECTIVE_TEMPLATES: list[str] = [
    "It is very {word}",
    "It is not that {word}",
    "It seems {word}",
    "It is quite {word}",
    "It feels {word}",
    "It is too {word}",
    "It is hardly {word}",
    "How {word} it is",
    "It is really {word}",
    "It does not seem {word}",
    "It is always {word}",
    "It is never {word}",
    "Everything seems {word}",
    "It looks very {word}",
    "It is incredibly {word}",
]

# Map JSON keys to their corresponding template lists.
_TEMPLATE_KEYS: dict[str, list[str]] = {
    "verb": _VERB_TEMPLATES,
    "noun_m": _NOUN_M_TEMPLATES,
    "noun_f": _NOUN_F_TEMPLATES,
    "adjective": _ADJECTIVE_TEMPLATES,
    "en_verb": _EN_VERB_TEMPLATES,
    "en_noun": _EN_NOUN_TEMPLATES,
    "en_adjective": _EN_ADJECTIVE_TEMPLATES,
}


def extend_cloze_templates(
    data: dict[str, list[str]],
) -> int:
    """Extend built-in cloze template banks from a dict.

    :param data: Mapping of template-bank keys to lists of
        template strings.  Valid keys: `"verb"`, `"noun_m"`,
        `"noun_f"`, `"adjective"`, `"en_verb"`, `"en_noun"`,
        `"en_adjective"`.
    :return: Total number of templates added.
    :raises ValueError: If a key is unrecognised or a
        template does not contain `{word}`.
    """
    count = 0
    for key, templates in data.items():
        if key not in _TEMPLATE_KEYS:
            raise ValueError(
                f"Unknown template key: {key!r}. "
                f"Expected one of {list(_TEMPLATE_KEYS)}"
            )
        for t in templates:
            if "{word}" not in t:
                raise ValueError(
                    f"Template missing {{word}} "
                    f"placeholder: {t!r}"
                )
            _TEMPLATE_KEYS[key].append(t)
            count += 1
    return count


def load_cloze_templates(path: str | Path) -> int:
    """Load cloze templates from a JSON file.

    The JSON file should contain an object with optional keys:
    `"verb"`, `"noun_m"`, `"noun_f"`, `"adjective"`,
    `"en_verb"`, `"en_noun"`, `"en_adjective"`.  Each key
    maps to a list of template strings containing `{word}`.

    Templates are appended to the built-in banks, so they
    extend (not replace) the defaults.

    :param path: Path to the JSON file.
    :return: Total number of templates added.
    :raises FileNotFoundError: If the file does not exist.
    :raises ValueError: If a key is unrecognised or a
        template does not contain `{word}`.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return extend_cloze_templates(data)


def generate_translation_cloze_sentence(
    word: str,
    *,
    gender: str | None = None,
    conjugation_group: str | None = None,
) -> tuple[str, str]:
    """Generate an English cloze sentence for translation cloze.

    Picks a template bank based on POS heuristic:
    `conjugation_group` set -> verb, `gender` set -> noun,
    else -> adjective.

    :param word: The English word to blank out.
    :param gender: Noun gender (`"m"` or `"f"`), or `None`.
    :param conjugation_group: Verb group (`"ar"`, `"er"`,
        `"ir"`), or `None`.
    :return: A tuple of `(sentence_with_blank, hint)` where
        the blank is `"___"` and hint is the English word.
    """
    template = _select_template(
        verb=_EN_VERB_TEMPLATES,
        noun_m=_EN_NOUN_TEMPLATES,
        noun_f=_EN_NOUN_TEMPLATES,
        adjective=_EN_ADJECTIVE_TEMPLATES,
        gender=gender,
        conjugation_group=conjugation_group,
    )
    sentence = template.replace("{word}", "___")
    return sentence, word
