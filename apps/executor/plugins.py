from typing import Any, Dict

# 간단한 python.call 핸들러 예시 (실전은 모듈 경로 임포트/검증 추가)
_USER_FUNCS = {}

def register_python_func(name: str, fn):
    _USER_FUNCS[name] = fn

def python_call(decision: Dict[str, Any]) -> Any:
    spec = decision
    fn_name = spec.get("fn")
    args = spec.get("args", [])
    kwargs = spec.get("kwargs", {})
    if fn_name not in _USER_FUNCS:
        raise KeyError(f"unknown fn={fn_name}")
    return _USER_FUNCS[fn_name](*args, **kwargs)

def http_call_stub(decision: Dict[str, Any]) -> Any:
    # TODO: httpx 요청/서명/재시도. MVP는 스텁
    return {"status": "stub", "decision": decision}
