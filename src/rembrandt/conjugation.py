"""Rule-based Spanish verb conjugation engine.

Supports regular -ar, -er, -ir verbs and common irregular verbs
across six tenses: presente, pretérito, imperfecto, futuro,
condicional, and subjuntivo presente.
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
    "futuro",
    "condicional",
    "subjuntivo_presente",
]

# Tenses where the stem is the full infinitive
# (rather than infinitive minus the last 2 chars).
_FULL_STEM_TENSES = {"futuro", "condicional"}

_REGULAR: dict[str, dict[str, list[str]]] = {
    "ar": {
        "presente": [
            "o", "as", "a", "amos", "áis", "an",
        ],
        "pretérito": [
            "é", "aste", "ó", "amos", "asteis", "aron",
        ],
        "imperfecto": [
            "aba", "abas", "aba",
            "ábamos", "abais", "aban",
        ],
        "futuro": [
            "é", "ás", "á", "emos", "éis", "án",
        ],
        "condicional": [
            "ía", "ías", "ía",
            "íamos", "íais", "ían",
        ],
        "subjuntivo_presente": [
            "e", "es", "e", "emos", "éis", "en",
        ],
    },
    "er": {
        "presente": [
            "o", "es", "e", "emos", "éis", "en",
        ],
        "pretérito": [
            "í", "iste", "ió", "imos", "isteis",
            "ieron",
        ],
        "imperfecto": [
            "ía", "ías", "ía",
            "íamos", "íais", "ían",
        ],
        "futuro": [
            "é", "ás", "á", "emos", "éis", "án",
        ],
        "condicional": [
            "ía", "ías", "ía",
            "íamos", "íais", "ían",
        ],
        "subjuntivo_presente": [
            "a", "as", "a", "amos", "áis", "an",
        ],
    },
    "ir": {
        "presente": [
            "o", "es", "e", "imos", "ís", "en",
        ],
        "pretérito": [
            "í", "iste", "ió", "imos", "isteis",
            "ieron",
        ],
        "imperfecto": [
            "ía", "ías", "ía",
            "íamos", "íais", "ían",
        ],
        "futuro": [
            "é", "ás", "á", "emos", "éis", "án",
        ],
        "condicional": [
            "ía", "ías", "ía",
            "íamos", "íais", "ían",
        ],
        "subjuntivo_presente": [
            "a", "as", "a", "amos", "áis", "an",
        ],
    },
}

# Irregular verbs only need entries for tenses where they
# differ from regular conjugation.  Tenses not listed here
# fall through to the regular engine.
_IRREGULAR: dict[str, dict[str, list[str]]] = {
    "ser": {
        "presente": [
            "soy", "eres", "es",
            "somos", "sois", "son",
        ],
        "pretérito": [
            "fui", "fuiste", "fue",
            "fuimos", "fuisteis", "fueron",
        ],
        "imperfecto": [
            "era", "eras", "era",
            "éramos", "erais", "eran",
        ],
        "subjuntivo_presente": [
            "sea", "seas", "sea",
            "seamos", "seáis", "sean",
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
        "subjuntivo_presente": [
            "esté", "estés", "esté",
            "estemos", "estéis", "estén",
        ],
    },
    "haber": {
        "presente": [
            "he", "has", "ha",
            "hemos", "habéis", "han",
        ],
        "pretérito": [
            "hube", "hubiste", "hubo",
            "hubimos", "hubisteis", "hubieron",
        ],
        "imperfecto": [
            "había", "habías", "había",
            "habíamos", "habíais", "habían",
        ],
        "futuro": [
            "habré", "habrás", "habrá",
            "habremos", "habréis", "habrán",
        ],
        "condicional": [
            "habría", "habrías", "habría",
            "habríamos", "habríais", "habrían",
        ],
        "subjuntivo_presente": [
            "haya", "hayas", "haya",
            "hayamos", "hayáis", "hayan",
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
        "futuro": [
            "tendré", "tendrás", "tendrá",
            "tendremos", "tendréis", "tendrán",
        ],
        "condicional": [
            "tendría", "tendrías", "tendría",
            "tendríamos", "tendríais", "tendrían",
        ],
        "subjuntivo_presente": [
            "tenga", "tengas", "tenga",
            "tengamos", "tengáis", "tengan",
        ],
    },
    "ir": {
        "presente": [
            "voy", "vas", "va",
            "vamos", "vais", "van",
        ],
        "pretérito": [
            "fui", "fuiste", "fue",
            "fuimos", "fuisteis", "fueron",
        ],
        "imperfecto": [
            "iba", "ibas", "iba",
            "íbamos", "ibais", "iban",
        ],
        "subjuntivo_presente": [
            "vaya", "vayas", "vaya",
            "vayamos", "vayáis", "vayan",
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
        "futuro": [
            "haré", "harás", "hará",
            "haremos", "haréis", "harán",
        ],
        "condicional": [
            "haría", "harías", "haría",
            "haríamos", "haríais", "harían",
        ],
        "subjuntivo_presente": [
            "haga", "hagas", "haga",
            "hagamos", "hagáis", "hagan",
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
        "futuro": [
            "podré", "podrás", "podrá",
            "podremos", "podréis", "podrán",
        ],
        "condicional": [
            "podría", "podrías", "podría",
            "podríamos", "podríais", "podrían",
        ],
        "subjuntivo_presente": [
            "pueda", "puedas", "pueda",
            "podamos", "podáis", "puedan",
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
        "futuro": [
            "diré", "dirás", "dirá",
            "diremos", "diréis", "dirán",
        ],
        "condicional": [
            "diría", "dirías", "diría",
            "diríamos", "diríais", "dirían",
        ],
        "subjuntivo_presente": [
            "diga", "digas", "diga",
            "digamos", "digáis", "digan",
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
        "futuro": [
            "querré", "querrás", "querrá",
            "querremos", "querréis", "querrán",
        ],
        "condicional": [
            "querría", "querrías", "querría",
            "querríamos", "querríais", "querrían",
        ],
        "subjuntivo_presente": [
            "quiera", "quieras", "quiera",
            "queramos", "queráis", "quieran",
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
        "futuro": [
            "sabré", "sabrás", "sabrá",
            "sabremos", "sabréis", "sabrán",
        ],
        "condicional": [
            "sabría", "sabrías", "sabría",
            "sabríamos", "sabríais", "sabrían",
        ],
        "subjuntivo_presente": [
            "sepa", "sepas", "sepa",
            "sepamos", "sepáis", "sepan",
        ],
    },
    "dar": {
        "presente": [
            "doy", "das", "da",
            "damos", "dais", "dan",
        ],
        "pretérito": [
            "di", "diste", "dio",
            "dimos", "disteis", "dieron",
        ],
        "imperfecto": [
            "daba", "dabas", "daba",
            "dábamos", "dabais", "daban",
        ],
        "subjuntivo_presente": [
            "dé", "des", "dé",
            "demos", "deis", "den",
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
        "futuro": [
            "vendré", "vendrás", "vendrá",
            "vendremos", "vendréis", "vendrán",
        ],
        "condicional": [
            "vendría", "vendrías", "vendría",
            "vendríamos", "vendríais", "vendrían",
        ],
        "subjuntivo_presente": [
            "venga", "vengas", "venga",
            "vengamos", "vengáis", "vengan",
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
        "futuro": [
            "pondré", "pondrás", "pondrá",
            "pondremos", "pondréis", "pondrán",
        ],
        "condicional": [
            "pondría", "pondrías", "pondría",
            "pondríamos", "pondríais", "pondrían",
        ],
        "subjuntivo_presente": [
            "ponga", "pongas", "ponga",
            "pongamos", "pongáis", "pongan",
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
        "futuro": [
            "saldré", "saldrás", "saldrá",
            "saldremos", "saldréis", "saldrán",
        ],
        "condicional": [
            "saldría", "saldrías", "saldría",
            "saldríamos", "saldríais", "saldrían",
        ],
        "subjuntivo_presente": [
            "salga", "salgas", "salga",
            "salgamos", "salgáis", "salgan",
        ],
    },
    "ver": {
        "presente": [
            "veo", "ves", "ve",
            "vemos", "veis", "ven",
        ],
        "pretérito": [
            "vi", "viste", "vio",
            "vimos", "visteis", "vieron",
        ],
        "imperfecto": [
            "veía", "veías", "veía",
            "veíamos", "veíais", "veían",
        ],
        "subjuntivo_presente": [
            "vea", "veas", "vea",
            "veamos", "veáis", "vean",
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
        `"imperfecto"`, `"futuro"`, `"condicional"`,
        `"subjuntivo_presente"`.
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

    # Check irregular table first (only for tenses where
    # the verb is actually irregular; missing tenses fall
    # through to regular conjugation).
    if infinitive in _IRREGULAR:
        forms = _IRREGULAR[infinitive].get(tense)
        if forms is not None:
            return forms[person]

    # Regular conjugation
    if conjugation_group not in _REGULAR:
        return None

    if tense in _FULL_STEM_TENSES:
        stem = infinitive
    else:
        stem = infinitive[:-2]
    ending = _REGULAR[conjugation_group][tense][person]
    return stem + ending
