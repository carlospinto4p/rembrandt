"""Template-based sentence generation for cloze exercises.

Provides fill-in-the-blank sentences for Spanish vocabulary
practice, with template banks for verbs, masculine nouns,
feminine nouns, and adjectives.  Also provides English
templates for production (EN->ES) exercises.
"""

import random

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
]


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
    if conjugation_group is not None:
        templates = _VERB_TEMPLATES
    elif gender == "m":
        templates = _NOUN_M_TEMPLATES
    elif gender == "f":
        templates = _NOUN_F_TEMPLATES
    else:
        templates = _ADJECTIVE_TEMPLATES

    template = random.choice(templates)
    sentence = template.replace("{word}", "___")
    return sentence, word


# --- English templates for production exercises ---

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
]


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
    if conjugation_group is not None:
        templates = _EN_VERB_TEMPLATES
    elif gender is not None:
        templates = _EN_NOUN_TEMPLATES
    else:
        templates = _EN_ADJECTIVE_TEMPLATES

    template = random.choice(templates)
    sentence = template.replace("{word}", "___")
    return sentence, word
