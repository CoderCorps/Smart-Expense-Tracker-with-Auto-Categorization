from pydantic import BaseModel


class CategoryOut(BaseModel):
    id: int
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class TrainingResult(BaseModel):
    """
    Returned by POST /categorization/train and GET /training-status.

    The same shape serves both so the frontend can render one progress
    card whether or not a model exists yet.
    """

    message: str
    training_examples: int
    categories_covered: int
    is_trained: bool = True
    minimum_examples: int | None = None
