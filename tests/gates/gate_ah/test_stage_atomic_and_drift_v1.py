import os, threading, time, sys
import pytest
from apps.experiment.stage_file import write_stage_atomic, read_stage_with_hash, guard_and_repair

pytestmark = [pytest.mark.gate_ah]
WIN = sys.platform.startswith("win")

def test_atomic_write_and_read(tmp_path):
    path = tmp_path / "desired_stage.txt"
    s = write_stage_atomic("canary", str(path))
    assert s.stage == "canary"
    # no trailing newline
    with open(path, "rb") as f:
        assert not f.read().endswith(b"\n")

@pytest.mark.skipif(WIN, reason="requires POSIX rename semantics")
def test_concurrent_writers_no_corruption(tmp_path):
    path = tmp_path / "desired_stage.txt"
    stages = ["stable","canary","promote","abort"]
    def writer(i):
        for _ in range(50):
            write_stage_atomic(stages[i%4], str(path))
    threads = [threading.Thread(target=writer, args=(i,)) for i in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    st = read_stage_with_hash(str(path))
    assert st.stage in stages

def test_guard_and_repair_on_corruption(tmp_path):
    path = tmp_path / "desired_stage.txt"
    write_stage_atomic("canary", str(path))
    # corrupt
    with open(path, "wb") as f:
        f.write(b"cana")  # partial
    repaired = guard_and_repair(str(path))
    assert repaired.stage == "stable"
