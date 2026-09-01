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

from dataclasses import dataclass


@dataclass
class Prediction:
    category_name: str
    confidence: float


class MLCategorizer:
    def __init__(self):
        self.model = None
        self.vectorizer = None

    def train(self, descriptions: list[str], category_names: list[str]) -> None:
        """
        TODO: fit a TfidfVectorizer on `descriptions`, fit a classifier on
        the vectors against `category_names`, store both on self, and
        persist them to disk (joblib.dump) so predict() can load them
        without retraining every time the server restarts.
        """
        raise NotImplementedError

    def predict(self, description: str) -> Prediction | None:
        """
        TODO: vectorize `description` with the trained vectorizer, get the
        model's predicted category and confidence score, and return None
        if confidence is below your chosen threshold (so the caller falls
        back to rule-based categorization instead of trusting a bad guess).
        """
        raise NotImplementedError
