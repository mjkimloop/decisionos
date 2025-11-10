from datetime import timedelta, timezone, datetime
import pytest
from apps.common.timeutil import within_clock_skew

pytestmark = [pytest.mark.gate_aj]


def test_clock_skew_ok():
    now = datetime.now(timezone.utc)
    ts = now - timedelta(seconds=45)
    assert within_clock_skew(now, ts, 90)


def test_clock_skew_reject():
    now = datetime.now(timezone.utc)
    ts = now - timedelta(seconds=200)
    assert not within_clock_skew(now, ts, 90)
