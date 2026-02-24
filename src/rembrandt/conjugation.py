"""Rule-based Spanish verb conjugation engine.

Supports regular -ar, -er, -ir verbs and common irregular verbs
across three tenses: presente, pretérito, and imperfecto.
"""

PERSONS: list[str] = [
    "yo",
    "tú",
    "él/ella",
    "nosotros",
    "vosotros",
    "ellos/ellas",
]

TENSES: list[str] = [
    "presente",
    "pretérito",
    "imperfecto",
]

_REGULAR: dict[str, dict[str, list[str]]] = {
    "ar": {
        "presente": ["o", "as", "a", "amos", "áis", "an"],
        "pretérito": [
            "é", "aste", "ó", "amos", "asteis", "aron",
        ],
        "imperfecto": [
            "aba", "abas", "aba",
            "ábamos", "abais", "aban",
        ],
    },
    "er": {
        "presente": ["o", "es", "e", "emos", "éis", "en"],
        "pretérito": [
            "í", "iste", "ió", "imos", "isteis", "ieron",
        ],
        "imperfecto": [
            "ía", "ías", "ía",
            "íamos", "íais", "ían",
        ],
    },
    "ir": {
        "presente": ["o", "es", "e", "imos", "ís", "en"],
        "pretérito": [
            "í", "iste", "ió", "imos", "isteis", "ieron",
        ],
        "imperfecto": [
            "ía", "ías", "ía",
            "íamos", "íais", "ían",
        ],
    },
}

_IRREGULAR: dict[str, dict[str, list[str]]] = {
    "ser": {
        "presente": [
            "soy", "eres", "es", "somos", "sois", "son",
        ],
        "pretérito": [
            "fui", "fuiste", "fue",
            "fuimos", "fuisteis", "fueron",
        ],
        "imperfecto": [
            "era", "eras", "era",
            "éramos", "erais", "eran",
        ],
    },
    "estar": {
        "presente": [
            "estoy", "estás", "está",
            "estamos", "estáis", "están",
        ],
        "pretérito": [
            "estuve", "estuviste", "estuvo",
            "estuvimos", "estuvisteis", "estuvieron",
        ],
        "imperfecto": [
            "estaba", "estabas", "estaba",
            "estábamos", "estabais", "estaban",
        ],
    },
    "haber": {
        "presente": [
            "he", "has", "ha", "hemos", "habéis", "han",
        ],
        "pretérito": [
            "hube", "hubiste", "hubo",
            "hubimos", "hubisteis", "hubieron",
        ],
        "imperfecto": [
            "había", "habías", "había",
            "habíamos", "habíais", "habían",
        ],
    },
    "tener": {
        "presente": [
            "tengo", "tienes", "tiene",
            "tenemos", "tenéis", "tienen",
        ],
        "pretérito": [
            "tuve", "tuviste", "tuvo",
            "tuvimos", "tuvisteis", "tuvieron",
        ],
        "imperfecto": [
            "tenía", "tenías", "tenía",
            "teníamos", "teníais", "tenían",
        ],
    },
    "ir": {
        "presente": [
            "voy", "vas", "va", "vamos", "vais", "van",
        ],
        "pretérito": [
            "fui", "fuiste", "fue",
            "fuimos", "fuisteis", "fueron",
        ],
        "imperfecto": [
            "iba", "ibas", "iba",
            "íbamos", "ibais", "iban",
        ],
    },
    "hacer": {
        "presente": [
            "hago", "haces", "hace",
            "hacemos", "hacéis", "hacen",
        ],
        "pretérito": [
            "hice", "hiciste", "hizo",
            "hicimos", "hicisteis", "hicieron",
        ],
        "imperfecto": [
            "hacía", "hacías", "hacía",
            "hacíamos", "hacíais", "hacían",
        ],
    },
    "poder": {
        "presente": [
            "puedo", "puedes", "puede",
            "podemos", "podéis", "pueden",
        ],
        "pretérito": [
            "pude", "pudiste", "pudo",
            "pudimos", "pudisteis", "pudieron",
        ],
        "imperfecto": [
            "podía", "podías", "podía",
            "podíamos", "podíais", "podían",
        ],
    },
    "decir": {
        "presente": [
            "digo", "dices", "dice",
            "decimos", "decís", "dicen",
        ],
        "pretérito": [
            "dije", "dijiste", "dijo",
            "dijimos", "dijisteis", "dijeron",
        ],
        "imperfecto": [
            "decía", "decías", "decía",
            "decíamos", "decíais", "decían",
        ],
    },
    "querer": {
        "presente": [
            "quiero", "quieres", "quiere",
            "queremos", "queréis", "quieren",
        ],
        "pretérito": [
            "quise", "quisiste", "quiso",
            "quisimos", "quisisteis", "quisieron",
        ],
        "imperfecto": [
            "quería", "querías", "quería",
            "queríamos", "queríais", "querían",
        ],
    },
    "saber": {
        "presente": [
            "sé", "sabes", "sabe",
            "sabemos", "sabéis", "saben",
        ],
        "pretérito": [
            "supe", "supiste", "supo",
            "supimos", "supisteis", "supieron",
        ],
        "imperfecto": [
            "sabía", "sabías", "sabía",
            "sabíamos", "sabíais", "sabían",
        ],
    },
    "dar": {
        "presente": [
            "doy", "das", "da", "damos", "dais", "dan",
        ],
        "pretérito": [
            "di", "diste", "dio",
            "dimos", "disteis", "dieron",
        ],
        "imperfecto": [
            "daba", "dabas", "daba",
            "dábamos", "dabais", "daban",
        ],
    },
    "venir": {
        "presente": [
            "vengo", "vienes", "viene",
            "venimos", "venís", "vienen",
        ],
        "pretérito": [
            "vine", "viniste", "vino",
            "vinimos", "vinisteis", "vinieron",
        ],
        "imperfecto": [
            "venía", "venías", "venía",
            "veníamos", "veníais", "venían",
        ],
    },
    "poner": {
        "presente": [
            "pongo", "pones", "pone",
            "ponemos", "ponéis", "ponen",
        ],
        "pretérito": [
            "puse", "pusiste", "puso",
            "pusimos", "pusisteis", "pusieron",
        ],
        "imperfecto": [
            "ponía", "ponías", "ponía",
            "poníamos", "poníais", "ponían",
        ],
    },
    "salir": {
        "presente": [
            "salgo", "sales", "sale",
            "salimos", "salís", "salen",
        ],
        "pretérito": [
            "salí", "saliste", "salió",
            "salimos", "salisteis", "salieron",
        ],
        "imperfecto": [
            "salía", "salías", "salía",
            "salíamos", "salíais", "salían",
        ],
    },
    "ver": {
        "presente": [
            "veo", "ves", "ve", "vemos", "veis", "ven",
        ],
        "pretérito": [
            "vi", "viste", "vio",
            "vimos", "visteis", "vieron",
        ],
        "imperfecto": [
            "veía", "veías", "veía",
            "veíamos", "veíais", "veían",
        ],
    },
}


def can_conjugate(
    infinitive: str,
    conjugation_group: str,
) -> bool:
    """Check if a verb can be conjugated by this engine.

    :param infinitive: The verb infinitive (e.g. `"hablar"`).
    :param conjugation_group: Verb group (`"ar"`, `"er"`,
        or `"ir"`).
    :return: ``True`` if the verb is irregular and known, or
        is a regular verb with a valid group.
    """
    if infinitive in _IRREGULAR:
        return True
    return conjugation_group in _REGULAR


def conjugate(
    infinitive: str,
    conjugation_group: str,
    tense: str,
    person: int,
) -> str | None:
    """Conjugate a Spanish verb.

    :param infinitive: The verb infinitive (e.g. `"hablar"`).
    :param conjugation_group: Verb group (`"ar"`, `"er"`,
        or `"ir"`).
    :param tense: One of `"presente"`, `"pretérito"`,
        `"imperfecto"`.
    :param person: Person index 0-5 (yo=0 through
        ellos/ellas=5).
    :return: The conjugated form, or `None` if the verb
        cannot be conjugated.
    :raises ValueError: If `tense` is not recognised or
        `person` is out of range.
    """
    if tense not in TENSES:
        raise ValueError(
            f"Unknown tense: {tense!r}. "
            f"Expected one of {TENSES}"
        )
    if not 0 <= person <= 5:
        raise ValueError(
            f"person must be 0-5, got {person}"
        )

    # Check irregular table first
    if infinitive in _IRREGULAR:
        return _IRREGULAR[infinitive][tense][person]

    # Regular conjugation
    if conjugation_group not in _REGULAR:
        return None

    stem = infinitive[:-2]
    ending = _REGULAR[conjugation_group][tense][person]
    return stem + ending
