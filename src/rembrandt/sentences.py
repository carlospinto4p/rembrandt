"""Template-based sentence generation for cloze exercises.

Provides fill-in-the-blank sentences for Spanish vocabulary
practice, with template banks for verbs, masculine nouns,
feminine nouns, and adjectives.
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
