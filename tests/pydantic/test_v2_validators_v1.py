# tests/pydantic/test_v2_validators_v1.py
"""Test Pydantic v2 validators compatibility (v0.5.11u-15a)."""
from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from apps.common.pydantic_compat import field_validator, model_validator, PYDANTIC_V2


class ValidatedModel(BaseModel):
    """Test model with validators."""
    value: int
    name: str

    @field_validator('value')
    @classmethod
    def value_positive(cls, v):
        """Ensure value is positive."""
        if v <= 0:
            raise ValueError('value must be positive')
        return v

    @field_validator('name')
    @classmethod
    def name_not_empty(cls, v):
        """Ensure name is not empty."""
        if not v or not v.strip():
            raise ValueError('name cannot be empty')
        return v.strip()


class CoherentModel(BaseModel):
    """Test model with model validator."""
    min_val: int
    max_val: int

    @model_validator(mode='after')
    def check_min_max(self):
        """Ensure min <= max."""
        if self.min_val > self.max_val:
            raise ValueError('min_val must be <= max_val')
        return self


def test_field_validator_positive():
    """Test field_validator rejects negative values."""
    with pytest.raises(ValidationError) as exc_info:
        ValidatedModel(value=-1, name="test")

    assert "value must be positive" in str(exc_info.value)


def test_field_validator_accepts_valid():
    """Test field_validator accepts valid values."""
    model = ValidatedModel(value=42, name="test")
    assert model.value == 42
    assert model.name == "test"


def test_field_validator_strips_whitespace():
    """Test field_validator strips name whitespace."""
    model = ValidatedModel(value=10, name="  spaced  ")
    assert model.name == "spaced"


def test_field_validator_rejects_empty_name():
    """Test field_validator rejects empty name."""
    with pytest.raises(ValidationError) as exc_info:
        ValidatedModel(value=10, name="   ")

    assert "name cannot be empty" in str(exc_info.value)


def test_model_validator_coherence():
    """Test model_validator enforces min/max coherence."""
    with pytest.raises(ValidationError) as exc_info:
        CoherentModel(min_val=10, max_val=5)

    assert "min_val must be <= max_val" in str(exc_info.value)


def test_model_validator_accepts_valid():
    """Test model_validator accepts valid min/max."""
    model = CoherentModel(min_val=5, max_val=10)
    assert model.min_val == 5
    assert model.max_val == 10


def test_model_validator_equal_values():
    """Test model_validator accepts equal min/max."""
    model = CoherentModel(min_val=7, max_val=7)
    assert model.min_val == 7
    assert model.max_val == 7


def test_validators_work_together():
    """Test field and model validators work together."""
    # Both validators pass
    model1 = ValidatedModel(value=100, name="valid")
    assert model1.value == 100

    # Field validator fails
    with pytest.raises(ValidationError):
        ValidatedModel(value=-1, name="negative")

    # Model validator coherence
    model2 = CoherentModel(min_val=1, max_val=100)
    assert model2.max_val == 100
