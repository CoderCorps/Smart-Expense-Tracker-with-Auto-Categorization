"""
PERSON B OWNS THIS FILE. This is the "wow" feature — genuinely optional for
a working demo (rule_based.py alone is enough to ship), but this is the
single most portfolio-worthy piece of the whole project if you get to it.
See the workflow doc for suggested timing (Week 3-4, after core CRUD works).

THE IDEA:
Every time a user corrects a wrong auto-category (PUT /transactions/{id}),
we save that as CategorySource.MANUAL_CORRECTION in the database — that's
a labeled training example, for free, with zero extra data collection work.
Once there are enough of them (a few hundred, realistically), train a small
text classifier on them and use it instead of the keyword rules.

SUGGESTED APPROACH (simple, appropriate for this project's size):
  1. Pull all transactions where category_source == MANUAL_CORRECTION
  2. Vectorize the `description` text with TF-IDF (sklearn's TfidfVectorizer)
  3. Train a Multinomial Naive Bayes or Logistic Regression classifier on
     (vectorized description -> category_id). Both are fast to train, work
     well on small text datasets, and are easy to explain in an interview —
     don't reach for a deep learning model here, it's the wrong tool for
     this amount of data.
  4. Save the trained model + vectorizer to disk with joblib so you don't
     retrain on every API call
  5. In predict(), if the model's confidence for its top prediction is
     below some threshold (e.g. 0.5), return None so the caller falls back
     to rule_based.categorize() instead of guessing badly

This file currently has the class shape stubbed out. Nothing here runs yet —
that's the task.
"""

"""
PERSON B OWNS THIS FILE.

ML-based transaction categorization using TF-IDF + Logistic Regression.

Training data comes from transactions that users manually corrected.
The trained model and vectorizer are persisted with joblib.
"""

from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "ml_model.joblib"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.joblib"

CONFIDENCE_THRESHOLD = 0.5


@dataclass
class Prediction:
    category_name: str
    confidence: float


class MLCategorizer:
    def __init__(self):
        self.model = None
        self.vectorizer = None

        self._load_model()

    def train(
        self,
        descriptions: list[str],
        category_names: list[str],
    ) -> None:
        """
        Train the classifier using transaction descriptions and
        their manually corrected category names.
        """

        if not descriptions or not category_names:
            raise ValueError("Training data cannot be empty.")

        if len(descriptions) != len(category_names):
            raise ValueError(
                "Descriptions and category_names must have the same length."
            )

        if len(set(category_names)) < 2:
            raise ValueError(
                "At least two different categories are required for training."
            )

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
        )

        X = self.vectorizer.fit_transform(descriptions)

        self.model = LogisticRegression(
            max_iter=1000,
        )

        self.model.fit(X, category_names)

        joblib.dump(self.model, MODEL_PATH)
        joblib.dump(self.vectorizer, VECTORIZER_PATH)

    def predict(self, description: str) -> Prediction | None:
        """
        Predict a category for a transaction description.

        Returns None when the model is not trained or when its
        confidence is below the configured threshold.
        """

        if not description or not description.strip():
            return None

        if self.model is None or self.vectorizer is None:
            self._load_model()

        if self.model is None or self.vectorizer is None:
            return None

        X = self.vectorizer.transform([description])

        probabilities = self.model.predict_proba(X)[0]

        best_index = probabilities.argmax()
        confidence = float(probabilities[best_index])

        if confidence < CONFIDENCE_THRESHOLD:
            return None

        category_name = self.model.classes_[best_index]

        return Prediction(
            category_name=category_name,
            confidence=confidence,
        )

    def _load_model(self) -> None:
        """Load the persisted model and vectorizer if they exist."""

        if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
            self.model = joblib.load(MODEL_PATH)
            self.vectorizer = joblib.load(VECTORIZER_PATH)