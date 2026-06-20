"""Seed a SQLite database with Data Science concepts."""

import asyncio
from rembrandt import Concept, Database, Topic


# -- Concepts by topic -----------------------------------------------

STATISTICS = [
    Concept(
        front="What is the Central Limit Theorem?",
        back="The sampling distribution of the sample mean "
        "approaches a normal distribution as n grows, "
        "regardless of the population distribution.",
        context="Requires independent samples and n >= 30 "
        "as a common rule of thumb.",
        tags=["statistics", "probability"],
    ),
    Concept(
        front="What is a p-value?",
        back="The probability of observing a test statistic "
        "at least as extreme as the one computed, assuming "
        "the null hypothesis is true.",
        context="A small p-value (< alpha) leads to "
        "rejecting the null hypothesis.",
        tags=["statistics", "hypothesis-testing"],
    ),
    Concept(
        front="Type I error vs Type II error",
        back="Type I: rejecting H0 when it is true "
        "(false positive). Type II: failing to reject "
        "H0 when it is false (false negative).",
        tags=["statistics", "hypothesis-testing"],
    ),
    Concept(
        front="What is the difference between population and sample?",
        back="A population is the entire group of "
        "interest; a sample is a subset drawn from it "
        "for analysis.",
        tags=["statistics"],
    ),
    Concept(
        front="What is Bayes' Theorem?",
        back="P(A|B) = P(B|A) * P(A) / P(B). It updates "
        "the probability of A given new evidence B.",
        context="Foundation of Bayesian statistics and "
        "many ML classifiers (e.g. Naive Bayes).",
        tags=["statistics", "probability"],
    ),
    Concept(
        front="What is the Law of Large Numbers?",
        back="As the sample size increases, the sample "
        "mean converges to the population mean.",
        tags=["statistics", "probability"],
    ),
    Concept(
        front="What is a confidence interval?",
        back="A range of values that, with a given "
        "confidence level (e.g. 95%), is expected to "
        "contain the true population parameter.",
        tags=["statistics"],
    ),
    Concept(
        front="What is standard deviation vs variance?",
        back="Variance is the average of squared "
        "deviations from the mean. Standard deviation "
        "is the square root of variance — same unit as "
        "the data.",
        tags=["statistics"],
    ),
]

MACHINE_LEARNING = [
    Concept(
        front="What is the bias-variance tradeoff?",
        back="Bias: error from wrong assumptions "
        "(underfitting). Variance: error from sensitivity "
        "to training noise (overfitting). Reducing one "
        "typically increases the other.",
        tags=["ml", "model-evaluation"],
    ),
    Concept(
        front="What is cross-validation?",
        back="A technique that splits data into k folds, "
        "trains on k-1, validates on the remaining fold, "
        "and averages the results to estimate model "
        "performance.",
        context="k=5 or k=10 are common choices.",
        tags=["ml", "model-evaluation"],
    ),
    Concept(
        front="What is regularization?",
        back="Adding a penalty to the loss function to "
        "discourage complex models. L1 (Lasso) drives "
        "coefficients to zero; L2 (Ridge) shrinks them.",
        tags=["ml", "regression"],
    ),
    Concept(
        front="What is gradient descent?",
        back="An optimization algorithm that iteratively "
        "updates parameters in the direction of steepest "
        "decrease of the loss function.",
        context="Variants: batch, stochastic (SGD), mini-batch.",
        tags=["ml", "optimization"],
    ),
    Concept(
        front="What is a decision tree?",
        back="A model that recursively splits data on "
        "feature thresholds to minimize impurity "
        "(Gini or entropy) at each node.",
        context="Prone to overfitting; ensembles like "
        "Random Forest address this.",
        tags=["ml", "algorithms"],
    ),
    Concept(
        front="What is Random Forest?",
        back="An ensemble of decision trees trained on "
        "random subsets of data and features. Final "
        "prediction is the majority vote (classification) "
        "or average (regression).",
        tags=["ml", "algorithms"],
    ),
    Concept(
        front="What is a support vector machine (SVM)?",
        back="A classifier that finds the hyperplane "
        "maximizing the margin between classes. Uses "
        "kernel functions for non-linear boundaries.",
        tags=["ml", "algorithms"],
    ),
    Concept(
        front="Precision vs Recall",
        back="Precision = TP / (TP + FP) — of predicted "
        "positives, how many are correct. Recall = "
        "TP / (TP + FN) — of actual positives, how many "
        "were found.",
        tags=["ml", "model-evaluation"],
    ),
    Concept(
        front="What is the F1 score?",
        back="The harmonic mean of precision and recall: "
        "2 * (P * R) / (P + R). Useful when class "
        "distribution is imbalanced.",
        tags=["ml", "model-evaluation"],
    ),
    Concept(
        front="What is overfitting?",
        back="When a model learns noise in the training "
        "data and performs poorly on unseen data. Signs: "
        "high training accuracy, low test accuracy.",
        context="Remedies: more data, regularization, "
        "cross-validation, simpler models.",
        tags=["ml", "model-evaluation"],
    ),
]

DEEP_LEARNING = [
    Concept(
        front="What is backpropagation?",
        back="An algorithm that computes gradients of "
        "the loss w.r.t. each weight by applying the "
        "chain rule layer by layer, from output to input.",
        tags=["deep-learning"],
    ),
    Concept(
        front="What is a convolutional neural network (CNN)?",
        back="A neural network that uses convolutional "
        "layers with learnable filters to extract spatial "
        "features. Dominant in image tasks.",
        tags=["deep-learning", "architectures"],
    ),
    Concept(
        front="What is a recurrent neural network (RNN)?",
        back="A network with loops that maintain hidden "
        "state across time steps, suited for sequential "
        "data. Suffers from vanishing gradients.",
        context="LSTM and GRU are gated variants that "
        "mitigate the vanishing gradient problem.",
        tags=["deep-learning", "architectures"],
    ),
    Concept(
        front="What is the Transformer architecture?",
        back="A model based on self-attention that "
        "processes all positions in parallel (no "
        "recurrence). Foundation of BERT, GPT, etc.",
        context="Introduced in 'Attention Is All You "
        "Need' (Vaswani et al., 2017).",
        tags=["deep-learning", "architectures"],
    ),
    Concept(
        front="What is dropout?",
        back="A regularization technique that randomly "
        "sets a fraction of neuron outputs to zero during "
        "training, preventing co-adaptation.",
        tags=["deep-learning", "regularization"],
    ),
    Concept(
        front="What is batch normalization?",
        back="Normalizing layer inputs to zero mean and "
        "unit variance within each mini-batch. Speeds up "
        "training and acts as mild regularization.",
        tags=["deep-learning"],
    ),
    Concept(
        front="What is an activation function?",
        back="A non-linear function applied after a "
        "layer's linear transformation. Common choices: "
        "ReLU, sigmoid, tanh, softmax.",
        context="ReLU is the default for hidden layers; "
        "softmax is used for multi-class output.",
        tags=["deep-learning"],
    ),
]

PYTHON_AND_TOOLS = [
    Concept(
        front="What does pandas `groupby()` do?",
        back="Splits a DataFrame into groups by one or "
        "more columns, applies an aggregate function "
        "(sum, mean, count, etc.), and combines results.",
        tags=["python", "pandas"],
    ),
    Concept(
        front="What is the difference between `loc` and `iloc` in pandas?",
        back="`loc` selects by label (column/index "
        "names). `iloc` selects by integer position.",
        tags=["python", "pandas"],
    ),
    Concept(
        front="What is a NumPy array vs a Python list?",
        back="NumPy arrays are fixed-type, contiguous in "
        "memory, and support vectorized operations. "
        "Lists are heterogeneous and slower for math.",
        tags=["python", "numpy"],
    ),
    Concept(
        front="What is broadcasting in NumPy?",
        back="Automatically expanding the shape of "
        "smaller arrays to match larger ones during "
        "element-wise operations, without copying data.",
        tags=["python", "numpy"],
    ),
    Concept(
        front="What is scikit-learn's `Pipeline`?",
        back="A chain of transforms and a final "
        "estimator that bundles preprocessing and "
        "modeling into a single object, preventing "
        "data leakage in cross-validation.",
        tags=["python", "sklearn"],
    ),
    Concept(
        front="What does `train_test_split` do?",
        back="Splits arrays into random train and test "
        "subsets. Common split: 80/20 or 70/30.",
        context="Set `random_state` for reproducibility. "
        "Use `stratify` for imbalanced classes.",
        tags=["python", "sklearn"],
    ),
]

DATA_ENGINEERING = [
    Concept(
        front="What is ETL?",
        back="Extract, Transform, Load — a pipeline that "
        "extracts data from sources, transforms it "
        "(clean, enrich, aggregate), and loads it into "
        "a target system (warehouse, lake).",
        tags=["data-engineering"],
    ),
    Concept(
        front="What is a data warehouse vs a data lake?",
        back="Warehouse: structured, schema-on-write, "
        "optimized for analytics (e.g. BigQuery). "
        "Lake: raw files, schema-on-read, stores any "
        "format (e.g. S3 + Parquet).",
        tags=["data-engineering"],
    ),
    Concept(
        front="What is feature engineering?",
        back="Creating new input variables from raw data "
        "to improve model performance: encoding "
        "categoricals, scaling, interactions, "
        "aggregations, time-based features.",
        tags=["data-engineering", "ml"],
    ),
    Concept(
        front="What is data leakage?",
        back="When information from outside the training "
        "set bleeds into the model — e.g. using future "
        "data or test-set statistics during training. "
        "Leads to overoptimistic evaluation.",
        tags=["data-engineering", "ml"],
    ),
    Concept(
        front="What is normalization vs standardization?",
        back="Normalization scales features to [0, 1]. "
        "Standardization transforms to zero mean and "
        "unit variance (z-score). Standardization is "
        "preferred when features have different units.",
        tags=["data-engineering", "preprocessing"],
    ),
]


async def main() -> None:
    db = await Database.connect("data_science.db")

    # Add all concepts
    stats = await db.add_concepts(STATISTICS)
    ml = await db.add_concepts(MACHINE_LEARNING)
    dl = await db.add_concepts(DEEP_LEARNING)
    tools = await db.add_concepts(PYTHON_AND_TOOLS)
    eng = await db.add_concepts(DATA_ENGINEERING)

    # Create topics
    groups = [
        ("Statistics & Probability", ["statistics"], stats),
        ("Machine Learning", ["ml"], ml),
        ("Deep Learning", ["deep-learning"], dl),
        ("Python & Tools", ["python"], tools),
        ("Data Engineering", ["data-engineering"], eng),
    ]

    for title, tags, concepts in groups:
        topic = await db.add_topic(
            Topic(
                title=title,
                tags=tags,
                concept_count=len(concepts),
                concept_ids=[c.id for c in concepts],
            )
        )
        print(f"  {topic.title}: {len(concepts)} concepts")

    total = await db.get_concepts()
    print(f"\nTotal: {len(total)} concepts in 5 topics")
    print("Saved to data_science.db")

    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
