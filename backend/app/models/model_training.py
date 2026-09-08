from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.database import Base


class ModelTrainingState(Base):
    __tablename__ = "model_training_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)

    trained_correction_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )