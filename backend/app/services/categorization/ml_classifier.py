"""
PERSON B OWNS THIS FILE.

ML-based transaction categorization using character-level TF-IDF
+ Logistic Regression.

Training data comes from built-in examples and user corrections.
The trained model and vectorizer are persisted with joblib.
"""

from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from .training_data import TRAINING_DATA


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

    def train_from_training_data(self) -> None:
        descriptions = []
        category_names = []

        for category, examples in TRAINING_DATA.items():
            for description in examples:
                descriptions.append(description)
                category_names.append(category)

        self.train(descriptions, category_names)

    def train(
        self,
        descriptions: list[str],
        category_names: list[str],
    ) -> None:
        """
        Train the classifier using transaction descriptions
        and their category names.
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

        # Character-level TF-IDF works better with short,
        # messy merchant descriptions.
        self.vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(2, 5),
            min_df=1,
            lowercase=True,
            sublinear_tf=True,
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

        Returns None when the model is not trained or when
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