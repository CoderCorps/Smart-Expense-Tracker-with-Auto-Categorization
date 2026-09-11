"""
Tests for the categorization layer.

Covers the keyword rules, the per-user ML classifier, and the HTTP
endpoints that expose them. The ML tests write real model files, so they
point ML_MODEL_DIR at a tmp_path rather than the app's own directory.
"""

import pytest

from backend.app.services.categorization import ml_classifier
from backend.app.services.categorization.ml_classifier import (
    MIN_TRAINING_EXAMPLES,
    MLCategorizer,
    NotEnoughTrainingData,
)
from backend.app.services.categorization.rule_based import DEFAULT_CATEGORY, categorize

# Twelve examples across four categories — above MIN_TRAINING_EXAMPLES and
# realistic enough that the classifier has something to generalize from.
TRAINING_DESCRIPTIONS = [
    "swiggy order",
    "zomato food",
    "restaurant payment",
    "uber ride",
    "ola cab",
    "irctc ticket",
    "amazon purchase",
    "flipkart order",
    "myntra shopping",
    "netflix subscription",
    "spotify premium",
    "movie ticket",
]

TRAINING_CATEGORIES = [
    "Food & Dining",
    "Food & Dining",
    "Food & Dining",
    "Travel & Transport",
    "Travel & Transport",
    "Travel & Transport",
    "Shopping",
    "Shopping",
    "Shopping",
    "Entertainment",
    "Entertainment",
    "Entertainment",
]


@pytest.fixture
def model_dir(tmp_path, monkeypatch):
    """Isolate trained models so tests never touch the real model store."""
    monkeypatch.setattr(
        ml_classifier.settings, "ML_MODEL_DIR", str(tmp_path), raising=False
    )
    return tmp_path


# =========================================================
# Keyword rules
# =========================================================

class TestRuleBased:
    @pytest.mark.parametrize(
        "description, expected",
        [
            ("SWIGGY ORDER 99213", "Food & Dining"),
            ("ZOMATO*ORDER", "Food & Dining"),
            ("UBER TRIP HELP.UBER.COM", "Travel & Transport"),
            ("AMZN Mktp IN", "Shopping"),
            ("NETFLIX SUBSCRIPTION", "Entertainment"),
            ("APOLLO PHARMACY", "Health & Fitness"),
            ("NEFT-HDFC0001-SALARY", "Salary & Income"),
            ("HOUSE RENT PAYMENT", "Rent & Housing"),
        ],
    )
    def test_recognises_real_world_descriptions(self, description, expected):
        assert categorize(description) == expected

    def test_is_case_insensitive(self):
        assert categorize("swiggy order") == categorize("SWIGGY ORDER")

    def test_unknown_description_falls_back(self):
        assert categorize("QWERTY ZXCVB 9981") == DEFAULT_CATEGORY

    @pytest.mark.parametrize("empty", ["", "   ", None])
    def test_empty_description_is_safe(self, empty):
        assert categorize(empty) == DEFAULT_CATEGORY


# =========================================================
# ML classifier
# =========================================================

class TestMLCategorizer:
    def test_untrained_model_predicts_nothing(self, model_dir):
        """
        With no model, predict() must return None so the caller falls back
        to the keyword rules rather than getting an arbitrary answer.
        """
        assert MLCategorizer(user_id=1).predict("swiggy order") is None
        assert MLCategorizer(user_id=1).is_trained is False

    def test_train_then_predict(self, model_dir):
        categorizer = MLCategorizer(user_id=1)
        trained_on = categorizer.train(TRAINING_DESCRIPTIONS, TRAINING_CATEGORIES)

        assert trained_on == len(TRAINING_DESCRIPTIONS)

        prediction = categorizer.predict("swiggy dinner order")

        assert prediction is not None
        assert prediction.category_name == "Food & Dining"
        assert 0.0 < prediction.confidence <= 1.0

    def test_model_persists_across_instances(self, model_dir):
        MLCategorizer(user_id=1).train(TRAINING_DESCRIPTIONS, TRAINING_CATEGORIES)

        # A fresh instance, as a later request would construct.
        assert MLCategorizer(user_id=1).is_trained is True

    def test_models_do_not_leak_between_users(self, model_dir):
        """
        The bug this guards: a single shared model file meant whoever
        trained first had their categories applied to everyone else's
        transactions — and their descriptions used as the training data.
        """
        MLCategorizer(user_id=1).train(TRAINING_DESCRIPTIONS, TRAINING_CATEGORIES)

        assert MLCategorizer(user_id=2).is_trained is False
        assert MLCategorizer(user_id=2).predict("swiggy order") is None

    def test_category_name_is_a_plain_string(self, model_dir):
        """
        sklearn hands back numpy strings; they have to be plain str to
        match category names when looking up a category_id.
        """
        categorizer = MLCategorizer(user_id=1)
        categorizer.train(TRAINING_DESCRIPTIONS, TRAINING_CATEGORIES)

        prediction = categorizer.predict("amazon online purchase")

        assert type(prediction.category_name) is str

    def test_too_few_examples_refused(self, model_dir):
        with pytest.raises(NotEnoughTrainingData):
            MLCategorizer(user_id=1).train(["swiggy", "uber"], ["Food & Dining", "Travel & Transport"])

    def test_single_category_refused(self, model_dir):
        count = MIN_TRAINING_EXAMPLES + 2

        with pytest.raises(NotEnoughTrainingData):
            MLCategorizer(user_id=1).train(
                [f"swiggy order {i}" for i in range(count)],
                ["Food & Dining"] * count,
            )

    def test_mismatched_lengths_rejected(self, model_dir):
        with pytest.raises(ValueError):
            MLCategorizer(user_id=1).train(["a", "b"], ["Food & Dining"])

    def test_unreadable_model_file_degrades_to_untrained(self, model_dir):
        """A corrupt model must fall back to the rules, not raise."""
        (model_dir / "user_1.joblib").write_bytes(b"not a joblib file")

        assert MLCategorizer(user_id=1).is_trained is False

    @pytest.mark.parametrize("empty", ["", "   "])
    def test_empty_description_predicts_nothing(self, model_dir, empty):
        categorizer = MLCategorizer(user_id=1)
        categorizer.train(TRAINING_DESCRIPTIONS, TRAINING_CATEGORIES)

        assert categorizer.predict(empty) is None


# =========================================================
# HTTP layer
# =========================================================

class TestCategorizationEndpoints:
    def test_categories_include_descriptions(self, client, seed_categories):
        response = client.get("/api/v1/categorization/categories")

        assert response.status_code == 200
        body = response.json()

        assert len(body) == len(seed_categories)
        assert all("description" in category for category in body)

    def test_categories_are_sorted_by_name(self, client, seed_categories):
        names = [c["name"] for c in client.get("/api/v1/categorization/categories").json()]

        assert names == sorted(names)

    def test_training_status_reports_progress(self, client, auth_headers, model_dir):
        response = client.get("/api/v1/categorization/training-status", headers=auth_headers)

        assert response.status_code == 200
        body = response.json()

        assert body["training_examples"] == 0
        assert body["is_trained"] is False
        assert body["minimum_examples"] == MIN_TRAINING_EXAMPLES

    def test_training_without_enough_corrections_is_400(
        self, client, auth_headers, model_dir
    ):
        response = client.post("/api/v1/categorization/train", headers=auth_headers)

        assert response.status_code == 400
        assert "correct" in response.json()["detail"].lower()

    def test_training_requires_auth(self, client):
        assert client.post("/api/v1/categorization/train").status_code == 401

    def test_recategorize_rejects_another_users_transaction(
        self, client, auth_headers_user_2, test_transaction, model_dir
    ):
        response = client.post(
            f"/api/v1/categorization/recategorize/{test_transaction.id}",
            headers=auth_headers_user_2,
        )

        assert response.status_code == 404
