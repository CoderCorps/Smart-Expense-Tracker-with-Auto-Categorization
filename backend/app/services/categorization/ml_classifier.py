from dataclasses import dataclass
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression


MODEL_DIR = Path(__file__).resolve().parent
MODEL_PATH = MODEL_DIR / "ml_model.joblib"
VECTORIZER_PATH = MODEL_DIR / "tfidf_vectorizer.joblib"

CONFIDENCE_THRESHOLD = 0.50


@dataclass
class Prediction:
    category_name: str
    confidence: float


class MLCategorizer:

    def __init__(self):
        self.model = None
        self.vectorizer = None

        if MODEL_PATH.exists() and VECTORIZER_PATH.exists():
            self.model = joblib.load(MODEL_PATH)
            self.vectorizer = joblib.load(VECTORIZER_PATH)

    def train(
        self,
        descriptions: list[str],
        category_names: list[str],
    ) -> None:

        if len(descriptions) < 2:
            raise ValueError("At least 2 training examples are required.")

        if len(set(category_names)) < 2:
            raise ValueError(
                "Training requires at least 2 different categories."
            )

        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
            sublinear_tf=True,
        )

        X = self.vectorizer.fit_transform(descriptions)

        self.model = LogisticRegression(
            max_iter=1000,
            solver="lbfgs"
        )

        self.model.fit(X, category_names)

        joblib.dump(self.model, MODEL_PATH)
        joblib.dump(self.vectorizer, VECTORIZER_PATH)

    def predict(self, description: str) -> Prediction | None:

        if self.model is None or self.vectorizer is None:
            return None

        if not description or not description.strip():
            return None

        X = self.vectorizer.transform([description])

        probabilities = self.model.predict_proba(X)[0]

        best_index = probabilities.argmax()

        category_name = self.model.classes_[best_index]
        confidence = float(probabilities[best_index])

        if confidence < CONFIDENCE_THRESHOLD:
            return None

        return Prediction(
            category_name=category_name,
            confidence=confidence,
        )