# apps/common/pydantic_compat.py
"""
Pydantic v1/v2 compatibility layer (v0.5.11u-15a).

Provides unified API for gradual migration:
- TypeAdapter wrapper (replaces parse_obj_as)
- BaseSettings with v2 ConfigDict
- model_dump/json aliases
- Common type serializers (Decimal, DateTime)
"""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any, Type, TypeVar

try:
    import pydantic as p
    _V2 = hasattr(p, "field_validator")
except Exception:
    _V2 = False

T = TypeVar('T')

# ===== Version detection =====
PYDANTIC_V2 = _V2


# ===== Type Adapter (v2) / parse_obj_as (v1) =====
if _V2:
    from pydantic import TypeAdapter as _TypeAdapter

    def parse_obj_as(t: Type[T], data: Any) -> T:
        """v1-compatible wrapper for TypeAdapter.validate_python()."""
        return _TypeAdapter(t).validate_python(data)

    def parse_obj_as_json(t: Type[T], data: str | bytes) -> T:
        """v1-compatible wrapper for TypeAdapter.validate_json()."""
        return _TypeAdapter(t).validate_json(data)

else:
    from pydantic import parse_obj_as as _parse_obj_as
    from pydantic.tools import parse_raw_as

    def parse_obj_as(t: Type[T], data: Any) -> T:
        """v1 parse_obj_as passthrough."""
        return _parse_obj_as(t, data)

    def parse_obj_as_json(t: Type[T], data: str | bytes) -> T:
        """v1 parse_raw_as passthrough."""
        return parse_raw_as(t, data)


# ===== BaseModel dump methods =====
if _V2:
    from pydantic import BaseModel

    def model_to_dict(
        m: BaseModel,
        by_alias: bool = True,
        exclude_none: bool = True,
        **kwargs
    ) -> dict:
        """v2 model_dump with v1-compatible defaults."""
        return m.model_dump(by_alias=by_alias, exclude_none=exclude_none, **kwargs)

    def model_to_json(
        m: BaseModel,
        by_alias: bool = True,
        exclude_none: bool = True,
        **kwargs
    ) -> str:
        """v2 model_dump_json with v1-compatible defaults."""
        return m.model_dump_json(by_alias=by_alias, exclude_none=exclude_none, **kwargs)

else:
    from pydantic import BaseModel

    def model_to_dict(
        m: BaseModel,
        by_alias: bool = True,
        exclude_none: bool = True,
        **kwargs
    ) -> dict:
        """v1 dict() passthrough."""
        return m.dict(by_alias=by_alias, exclude_none=exclude_none, **kwargs)

    def model_to_json(
        m: BaseModel,
        by_alias: bool = True,
        exclude_none: bool = True,
        **kwargs
    ) -> str:
        """v1 json() passthrough."""
        return m.json(by_alias=by_alias, exclude_none=exclude_none, **kwargs)


# ===== BaseSettings (v2: pydantic-settings) =====
if _V2:
    try:
        from pydantic_settings import BaseSettings as _BaseSettings, SettingsConfigDict

        class BaseSettings(_BaseSettings):
            """v2 BaseSettings with default config."""
            model_config = SettingsConfigDict(
                env_prefix='DECISIONOS_',
                env_file='.env',
                env_file_encoding='utf-8',
                extra='ignore',
                case_sensitive=False,
            )

    except ImportError:
        # pydantic-settings not installed, fallback to stub
        from pydantic import BaseModel as _BaseModel

        class BaseSettings(_BaseModel):
            """Stub BaseSettings when pydantic-settings unavailable."""
            pass

else:
    from pydantic import BaseSettings as _BaseSettings

    class BaseSettings(_BaseSettings):
        """v1 BaseSettings with default config."""
        class Config:
            env_prefix = 'DECISIONOS_'
            env_file = '.env'
            env_file_encoding = 'utf-8'
            extra = 'ignore'
            case_sensitive = False


# ===== Validators =====
if _V2:
    from pydantic import field_validator, model_validator

    # v1 compatibility: validator → field_validator
    def validator(*fields, pre: bool = False, always: bool = False, **kw):
        """v1-style validator mapped to v2 field_validator."""
        mode = 'before' if pre else 'after'
        return field_validator(*fields, mode=mode, **kw)

else:
    from pydantic import validator, root_validator

    # v2 compatibility stubs
    def field_validator(*fields, mode: str = 'after', **kw):
        """v2-style field_validator mapped to v1 validator."""
        pre = (mode == 'before')
        return validator(*fields, pre=pre, **kw)

    def model_validator(mode: str = 'after', **kw):
        """v2-style model_validator mapped to v1 root_validator."""
        pre = (mode == 'before')
        return root_validator(pre=pre, **kw)


# ===== ConfigDict (v2) / Config (v1) =====
if _V2:
    from pydantic import ConfigDict

    def make_config(
        from_attributes: bool = False,
        populate_by_name: bool = False,
        str_strip_whitespace: bool = False,
        **kwargs
    ) -> ConfigDict:
        """Create v2 ConfigDict."""
        return ConfigDict(
            from_attributes=from_attributes,
            populate_by_name=populate_by_name,
            str_strip_whitespace=str_strip_whitespace,
            **kwargs
        )

else:
    def make_config(
        from_attributes: bool = False,
        populate_by_name: bool = False,
        str_strip_whitespace: bool = False,
        **kwargs
    ):
        """Create v1 Config class."""
        class Config:
            orm_mode = from_attributes
            allow_population_by_field_name = populate_by_name
            anystr_strip_whitespace = str_strip_whitespace
            for k, v in kwargs.items():
                setattr(Config, k, v)
        return Config


# ===== Common type serializers =====
if _V2:
    from typing import Annotated
    from pydantic import PlainSerializer

    # Decimal → string (避免精度丢失)
    DecimalStr = Annotated[
        Decimal,
        PlainSerializer(lambda d: format(d, 'f'), return_type=str, when_used='json')
    ]

else:
    # v1: use json_encoders in Config
    DecimalStr = Decimal


__all__ = [
    'PYDANTIC_V2',
    'parse_obj_as',
    'parse_obj_as_json',
    'model_to_dict',
    'model_to_json',
    'BaseSettings',
    'validator',
    'field_validator',
    'model_validator',
    'make_config',
    'DecimalStr',
]
