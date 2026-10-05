"""Base model for all SQLAlchemy models with typed constructor."""
from app.extensions import db


class BaseModel(db.Model):
    """Abstract base model with keyword arguments constructor for static analyzers."""
    __abstract__ = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
