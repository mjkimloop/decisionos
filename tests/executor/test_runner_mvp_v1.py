from apps.executor.runner import ExecutorRunner, PluginRegistry
from apps.executor.plugins import register_python_func, python_call
import pytest

def test_executor_ok():
    reg = PluginRegistry()
    reg.register("python.call", python_call)

    def add(a,b,x=0): return a+b+x
    register_python_func("add", add)

    runner = ExecutorRunner(reg)
    res = runner.execute({"action":"python.call","fn":"add","args":[1,2],"kwargs":{"x":3}})
    assert res.ok and res.output == 6 and res.reason == "exec.ok"

def test_executor_missing_handler():
    reg = PluginRegistry()
    runner = ExecutorRunner(reg)
    res = runner.execute({"action":"unknown"})
    assert not res.ok and res.reason == "exec.error"
