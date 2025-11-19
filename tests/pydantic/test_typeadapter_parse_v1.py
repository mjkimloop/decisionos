# tests/pydantic/test_typeadapter_parse_v1.py
"""Test Pydantic v1/v2 TypeAdapter compatibility (v0.5.11u-15a)."""
from __future__ import annotations

from typing import List

import pytest
from pydantic import BaseModel

from apps.common.pydantic_compat import parse_obj_as, parse_obj_as_json, PYDANTIC_V2


class SampleModel(BaseModel):
    """Test model."""
    name: str
    count: int


def test_parse_obj_as_dict():
    """Test parse_obj_as with dict input."""
    data = {"name": "test", "count": 42}
    result = parse_obj_as(SampleModel, data)

    assert isinstance(result, SampleModel)
    assert result.name == "test"
    assert result.count == 42


def test_parse_obj_as_list():
    """Test parse_obj_as with list of models."""
    data = [
        {"name": "a", "count": 1},
        {"name": "b", "count": 2},
    ]
    result = parse_obj_as(List[SampleModel], data)

    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0].name == "a"
    assert result[1].count == 2


def test_parse_obj_as_json_string():
    """Test parse_obj_as_json with JSON string."""
    json_data = '{"name": "json-test", "count": 99}'
    result = parse_obj_as_json(SampleModel, json_data)

    assert isinstance(result, SampleModel)
    assert result.name == "json-test"
    assert result.count == 99


def test_parse_obj_as_json_bytes():
    """Test parse_obj_as_json with JSON bytes."""
    json_data = b'{"name": "bytes-test", "count": 77}'
    result = parse_obj_as_json(SampleModel, json_data)

    assert isinstance(result, SampleModel)
    assert result.name == "bytes-test"
    assert result.count == 77


def test_parse_obj_as_validation_error():
    """Test parse_obj_as raises validation error on invalid data."""
    from pydantic import ValidationError

    data = {"name": "test", "count": "invalid"}  # count should be int

    with pytest.raises(ValidationError) as exc_info:
        parse_obj_as(SampleModel, data)

    # Both v1 and v2 should raise ValidationError
    assert "count" in str(exc_info.value)


def test_pydantic_version_detection():
    """Test PYDANTIC_V2 flag is correctly set."""
    # Just verify it's a boolean
    assert isinstance(PYDANTIC_V2, bool)

    # If v2 is available, TypeAdapter should exist
    if PYDANTIC_V2:
        import pydantic
        assert hasattr(pydantic, "TypeAdapter")
        assert hasattr(pydantic, "field_validator")
