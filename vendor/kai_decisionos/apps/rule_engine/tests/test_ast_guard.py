import pytest
from apps.rule_engine.parser import parse_expression


def test_disallow_function_call():
    with pytest.raises(ValueError):
        parse_expression("__import__('os')")


def test_disallow_attribute_chain():
    with pytest.raises(ValueError):
        parse_expression("payload.values")


def test_allow_arithmetic_compare():
    parse_expression('payload.get("a",0) + 2 > 3')

