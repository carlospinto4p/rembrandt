"""CRUD operations for concepts and topics."""

import asyncio
from rembrandt import Concept, Database, Topic


async def main():
    db = await Database.connect(":memory:")

    # --- Concepts ---
    c1 = await db.add_concept(
        "What is ML?",
        "A subset of AI that learns from data",
        tags=["data-science"],
    )
    print(f"Added concept #{c1.id}: {c1.front}")

    concepts = await db.add_concepts(
        [
            Concept(
                front="What is SQL?",
                back="Structured Query Language",
                tags=["databases"],
            ),
            Concept(
                front="What is REST?",
                back="Representational State Transfer",
                tags=["web"],
            ),
        ]
    )
    print(f"Bulk added {len(concepts)} concepts")

    all_concepts = await db.get_concepts()
    print(f"Total: {len(all_concepts)}")

    tagged = await db.get_concepts(
        tag="data-science",
    )
    print(f"Data-science tagged: {len(tagged)}")

    c1_updated = c1.model_copy(
        update={"back": "AI that learns from data"},
    )
    await db.update_concept(c1_updated)
    print(f"Updated concept #{c1.id}")

    # --- Topics ---
    topic = await db.add_topic(
        Topic(
            title="CS Fundamentals",
            tags=["cs"],
            concept_count=len(concepts),
            concept_ids=[c.id for c in concepts],
        )
    )
    print(f"Added topic #{topic.id}: {topic.title}")

    topics = await db.get_topics()
    print(f"Total topics: {len(topics)}")
    print(f"  '{topics[0].title}' has {len(topics[0].concept_ids)} concepts")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
