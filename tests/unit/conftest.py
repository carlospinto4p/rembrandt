"""Shared fixtures for unit tests."""

import pytest
import pytest_asyncio

from rembrandt.db import Database
from rembrandt.models import Concept


@pytest_asyncio.fixture
async def db(tmp_path):
    """Empty database for tests."""
    database = await Database.connect(tmp_path / "test.db")
    yield database
    await database.close()


@pytest.fixture
def sample_concepts():
    """Data-science concept pairs for exercise tests."""
    return [
        Concept(
            id=i,
            front=c[0],
            back=c[1],
        )
        for i, c in enumerate(
            [
                (
                    "What is a p-value?",
                    "Probability of observing data at least"
                    " as extreme as the sample,"
                    " given H0 is true",
                ),
                (
                    "What is overfitting?",
                    "Model learns noise in training data,"
                    " performs poorly on unseen data",
                ),
                (
                    "What is gradient descent?",
                    "Optimization algorithm that iteratively"
                    " adjusts parameters to minimize"
                    " a loss function",
                ),
                (
                    "What is cross-validation?",
                    "Technique to evaluate model performance"
                    " by partitioning data into train"
                    " and test sets",
                ),
                (
                    "What is regularization?",
                    "Adding a penalty term to the loss"
                    " function to prevent overfitting",
                ),
            ],
            start=1,
        )
    ]


@pytest.fixture
def short_concepts():
    """Short front/back pairs for fuzzy matching tests."""
    return [
        Concept(
            id=i,
            front=c[0],
            back=c[1],
        )
        for i, c in enumerate(
            [
                ("cat", "gato"),
                ("dog", "perro"),
                ("house", "casa"),
                ("book", "libro"),
                ("water", "agua"),
            ],
            start=1,
        )
    ]


@pytest_asyncio.fixture
async def db_with_concepts(tmp_path):
    """Database pre-loaded with concepts and users."""
    database = await Database.connect(
        tmp_path / "test.db",
    )
    await database.register_user("u1", "pass")
    await database.register_user("u2", "pass")
    await database.add_concepts(
        [
            Concept(
                front="What is a p-value?",
                back=(
                    "Probability of observing data"
                    " as extreme as sample given H0"
                ),
            ),
            Concept(
                front="What is overfitting?",
                back=("Model learns noise, poor generalization"),
            ),
            Concept(
                front="What is gradient descent?",
                back=("Iterative optimization to minimize loss"),
            ),
            Concept(
                front="What is cross-validation?",
                back=("Evaluate model by partitioning data"),
            ),
            Concept(
                front="What is regularization?",
                back=("Penalty term to prevent overfitting"),
            ),
        ]
    )
    yield database
    await database.close()
