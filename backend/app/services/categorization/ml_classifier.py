"""
ML-based transaction categorization: TF-IDF + logistic regression.

THE IDEA
Every time a user corrects a wrong auto-category (PUT /transactions/{id}),
that correction is saved as CategorySource.MANUAL_CORRECTION — a labeled
training example, for free, with zero extra data collection. Once there
are enough of them, train a small text classifier on them and use it in
preference to the keyword rules in rule_based.py.

Deep learning is the wrong tool at this data size. TF-IDF over word and
bigram features, fed to logistic regression, trains in milliseconds on a
few hundred rows and can be explained in an interview.

ONE MODEL PER USER
Models are keyed by user id and live in a directory outside the package
(see settings.ML_MODEL_DIR). Two reasons:

  * Correctness. "AMZN MKTP" means Shopping to one user and Groceries to
    another. A single shared model trained on whoever happened to click
    first gives everyone else that person's answers.
  * Privacy. Descriptions are the training data, and they're some of the
    most sensitive text in the app. They shouldn't cross accounts.

A model is only consulted for the user it was trained for, and only when
it's confident enough to beat the rules — see MIN_CHANCE_MULTIPLE below.
Otherwise predict() returns None and the caller falls back to keywords.
"""

from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from backend.app.core.config import settings

# When to trust the model over the keyword rules.
#
# A fixed probability threshold doesn't work here, because what counts as
# confident depends on how many categories the model knows. With four
# categories a coin-flip is 0.25, and a correct, well-separated prediction
# lands around 0.36-0.42 — so a flat 0.5 bar rejects every good answer and
# the model never fires. With nine categories chance is 0.11 and the same
# bar is even further out of reach.
#
# So the test is relative to chance, plus a margin over the runner-up.
# Measured on a 12-example model: correct predictions clear both easily,
# while an unrecognisable description sits exactly at chance with a ratio
# of 1.0 and is correctly refused.
MIN_CHANCE_MULTIPLE = 1.3
MIN_MARGIN_RATIO = 1.25

# A model trained on a handful of corrections is worse than the keyword
# rules, and worse in a way that's hard to notice: it's confidently wrong
# on everything it hasn't seen. Refuse to train until there's enough to
# learn from.
MIN_TRAINING_EXAMPLES = 10
MIN_TRAINING_CATEGORIES = 2


class NotEnoughTrainingData(Exception):
    """Raised when the corrections on file can't support a useful model."""


@dataclass
class Prediction:
    category_name: str
    confidence: float


def _model_path(user_id: int) -> Path:
    directory = Path(settings.ML_MODEL_DIR)
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"user_{user_id}.joblib"


class MLCategorizer:
    """
    The categorizer for one user's transactions.

    Construct it per request. Loading is a single joblib read of a model
    measured in kilobytes, and holding one in a module global is how a
    freshly trained model ends up ignored until the server restarts.
    """

    def __init__(self, user_id: int):
        self.user_id = user_id
        self.model: LogisticRegression | None = None
        self.vectorizer: TfidfVectorizer | None = None

        self._load()

    # -----------------------------------------------------
    # Training
    # -----------------------------------------------------

    def train(self, descriptions: list[str], category_names: list[str]) -> int:
        """
        Fit and persist a model from this user's manual corrections.

        Returns the number of examples trained on.

        Raises:
            NotEnoughTrainingData: too few examples, or too few distinct
                categories for a classifier to be meaningful.
        """

        if len(descriptions) != len(category_names):
            raise ValueError("descriptions and category_names must be the same length")

        if len(descriptions) < MIN_TRAINING_EXAMPLES:
            raise NotEnoughTrainingData(
                f"Need at least {MIN_TRAINING_EXAMPLES} corrected transactions "
                f"to train, but only {len(descriptions)} are available. Correct "
                f"a few more categories and try again."
            )

        if len(set(category_names)) < MIN_TRAINING_CATEGORIES:
            raise NotEnoughTrainingData(
                "Corrections must span at least "
                f"{MIN_TRAINING_CATEGORIES} different categories to train."
            )

        vectorizer = TfidfVectorizer(
            lowercase=True,
            # Bigrams catch merchant names that only mean something as a
            # pair, like "prime video" or "salary credit".
            ngram_range=(1, 2),
            min_df=1,
        )

        features = vectorizer.fit_transform(descriptions)

        model = LogisticRegression(max_iter=1000)
        model.fit(features, category_names)

        joblib.dump(
            {"model": model, "vectorizer": vectorizer},
            _model_path(self.user_id),
        )

        self.model = model
        self.vectorizer = vectorizer

        return len(descriptions)

    # -----------------------------------------------------
    # Prediction
    # -----------------------------------------------------

    def predict(self, description: str) -> Prediction | None:
        """
        Predict a category for a description.

        Returns None when this user has no trained model, or when the
        model isn't confident enough to beat the keyword rules — see
        MIN_CHANCE_MULTIPLE for what "confident enough" means and why it
        isn't a fixed number.
        """

        if not description or not description.strip():
            return None

        if self.model is None or self.vectorizer is None:
            return None

        probabilities = self.model.predict_proba(
            self.vectorizer.transform([description])
        )[0]

        if len(probabilities) < 2:
            return None

        ranked = sorted(probabilities, reverse=True)
        best, runner_up = float(ranked[0]), float(ranked[1])

        chance = 1.0 / len(probabilities)

        if best < chance * MIN_CHANCE_MULTIPLE:
            return None

        # A clear winner, not a near-tie between two plausible categories.
        if runner_up > 0 and best / runner_up < MIN_MARGIN_RATIO:
            return None

        best_index = int(probabilities.argmax())
        confidence = best

        return Prediction(
            # classes_ holds numpy strings; str() keeps what leaves this
            # module comparable to the category names in the database.
            category_name=str(self.model.classes_[best_index]),
            confidence=confidence,
        )

    @property
    def is_trained(self) -> bool:
        return self.model is not None and self.vectorizer is not None

    # -----------------------------------------------------
    # Persistence
    # -----------------------------------------------------

    def _load(self) -> None:
        path = _model_path(self.user_id)

        if not path.exists():
            return

        try:
            payload = joblib.load(path)
            self.model = payload["model"]
            self.vectorizer = payload["vectorizer"]
        except Exception:
            # A model written by an older version, or a half-written file.
            # Falling back to the keyword rules is always safe, so treat
            # an unreadable model as no model.
            self.model = None
            self.vectorizer = None
