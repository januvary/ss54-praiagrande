"""
Protocol Counter Model
Thread-safe protocol number generation using database-level locking.
"""

from sqlalchemy import Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from datetime import datetime
from app.database import Base


class ProtocolCounter(Base):
    """
    Counter for generating unique protocol numbers.
    Uses row-level locking to prevent race conditions.
    """

    __tablename__ = "protocol_counters"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_sequence: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    def __repr__(self):
        return f"<ProtocolCounter {self.year}: {self.last_sequence}>"
