"""
Pydantic serialization utilities for ORM objects.

Provides helper functions to serialize SQLAlchemy ORM objects through
Pydantic schemas, reducing boilerplate in route handlers.
"""

from typing import TypeVar, List, Type
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def serialize_orm(model_class: Type[BaseModel], orm_obj) -> dict:
    """
    Serialize a single ORM object to dict via Pydantic schema.

    Args:
        model_class: Pydantic model class to use for validation
        orm_obj: SQLAlchemy ORM object to serialize

    Returns:
        Dictionary representation of the object

    Example:
        >>> process_data = serialize_orm(ProcessResponse, process)
    """
    return model_class.model_validate(orm_obj).model_dump()


def serialize_orm_list(model_class: Type[BaseModel], orm_objs: List) -> List[dict]:
    """
    Serialize a list of ORM objects to list of dicts via Pydantic schema.

    Args:
        model_class: Pydantic model class to use for validation
        orm_objs: List of SQLAlchemy ORM objects to serialize

    Returns:
        List of dictionary representations

    Example:
        >>> process_list = serialize_orm_list(ProcessResponse, processes)
        >>> activities_data = serialize_orm_list(ActivityLogResponse, activities)
    """
    return [model_class.model_validate(obj).model_dump() for obj in orm_objs]
