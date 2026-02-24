"""Monolingual Spanish vocabulary quiz.

Learn Spanish words through their Spanish definitions (no
translations). Uses `quick_session()` with an inline word list.
Handles all three definition-mode exercise types: multiple choice,
reverse flashcard, and self-graded.

Usage::

    uv run python examples/07_spanish_vocabulary.py
"""

from pathlib import Path

from rembrandt import quick_session
from rembrandt.models import ExerciseType

_DB_PATH = (
    Path(__file__).resolve().parent.parent
    / "data"
    / "spanish_definitions.db"
)

_WORDS = [
    {"word": "gato", "definition": "Animal doméstico felino"},
    {"word": "perro",
     "definition": "Animal doméstico que ladra"},
    {"word": "casa",
     "definition": "Edificio para habitar"},
    {"word": "libro",
     "definition": "Conjunto de hojas impresas y encuadernadas"},
    {"word": "agua",
     "definition": "Líquido transparente e inodoro"},
    {"word": "sol",
     "definition": "Estrella que ilumina la Tierra"},
    {"word": "luna",
     "definition": "Satélite natural de la Tierra"},
    {"word": "árbol",
     "definition": "Planta de tronco leñoso y elevado"},
    {"word": "mesa",
     "definition": "Mueble con superficie plana y patas"},
    {"word": "silla",
     "definition": "Asiento con respaldo para una persona"},
    {"word": "pan",
     "definition": "Alimento hecho con harina y agua cocidos"},
    {"word": "fuego",
     "definition": "Calor y luz producidos por combustión"},
    {"word": "río",
     "definition": "Corriente de agua continua que desemboca"},
    {"word": "nube",
     "definition": "Masa de vapor de agua en la atmósfera"},
    {"word": "piedra",
     "definition": "Sustancia mineral dura y compacta"},
    {"word": "camino",
     "definition": "Vía para transitar de un lugar a otro"},
    {"word": "ventana",
     "definition": "Abertura en una pared para luz y aire"},
    {"word": "puerta",
     "definition": "Abertura para entrar y salir de un lugar"},
    {"word": "mano",
     "definition": "Parte del cuerpo al final del brazo"},
    {"word": "ojo",
     "definition": "Órgano de la vista"},
]


def main() -> None:
    session = quick_session(
        _WORDS,
        db_path=_DB_PATH,
        language_from="es",
        language_to="es",
        user_id="demo",
    )

    print("=== Vocabulario en Español ===")
    print(
        "Aprende palabras a través de sus definiciones."
    )
    print("Escribe tu respuesta (o 'q' para salir).\n")

    correct = 0
    total = 0

    while True:
        exercise = session.next_exercise()
        if exercise is None:
            break

        total += 1
        etype = exercise.exercise_type
        print(f"--- Pregunta {total} ---")

        if etype == ExerciseType.MULTIPLE_CHOICE:
            print(
                "¿Qué significa "
                f"'{exercise.word.word_from}'?"
            )
            for idx, opt in enumerate(exercise.options, 1):
                print(f"  {idx}. {opt}")
            answer = input("> ").strip()
            if answer.lower() == "q":
                total -= 1
                break
            result = session.answer(answer)

        elif etype == ExerciseType.REVERSE_FLASHCARD:
            print(
                "Definición: "
                f"{exercise.word.word_to}"
            )
            print("¿Cuál es la palabra?")
            answer = input("> ").strip()
            if answer.lower() == "q":
                total -= 1
                break
            result = session.answer(answer)

        else:  # SELF_GRADED
            print(
                f"Palabra: {exercise.word.word_from}"
            )
            print("(Piensa en la definición...)")
            input("Pulsa Enter para ver la respuesta.")
            print(
                f"  → {exercise.word.word_to}"
            )
            print("Puntúa tu respuesta (0-5):")
            answer = input("> ").strip()
            if answer.lower() == "q":
                total -= 1
                break
            quality = int(answer)
            result = session.answer(quality=quality)

        if result.correct:
            correct += 1
            print("¡Correcto!\n")
        else:
            expected = result.expected
            print(f"Incorrecto — respuesta: {expected}\n")

    if total > 0:
        pct = correct / total * 100
        print(f"Puntuación: {correct}/{total} ({pct:.0f}%)")

    session.db.close()


if __name__ == "__main__":
    main()
