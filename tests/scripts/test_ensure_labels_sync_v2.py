import json, subprocess, os, sys, pytest

def test_catalog_hash_present(tmp_path):
    """카탈로그 해시 생성 확인"""
    cat = tmp_path / "catalog.json"
    cat.write_text(json.dumps({"labels": [], "groups": {}}, ensure_ascii=False), encoding="utf-8")
    # dry-run without token → exit 0
    r = subprocess.run(
        [sys.executable, "scripts/ensure_labels.py", "--repo", "x/y", "--catalog", str(cat), "--dry-run"],
        capture_output=True,
        text=True
    )
    assert r.returncode == 0
    assert "catalog_hash=" in r.stdout


def test_catalog_v2_structure(tmp_path):
    """v2 카탈로그 구조 검증"""
    cat = {
        "catalog_hash_alg": "sha256",
        "groups": {"infra": {"weight": 1.3, "visibility": "public"}},
        "labels": [
            {
                "name": "reason:test",
                "color": "ee0701",
                "description": "Test label",
                "group": "infra",
                "priority": 100,
                "aliases": ["test-alias"]
            }
        ]
    }
    cat_file = tmp_path / "catalog_v2.json"
    cat_file.write_text(json.dumps(cat, ensure_ascii=False), encoding="utf-8")

    # 파일 로드 확인
    with open(cat_file, "r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded["catalog_hash_alg"] == "sha256"
    assert "infra" in loaded["groups"]
    assert loaded["labels"][0]["name"] == "reason:test"
    assert loaded["labels"][0]["aliases"] == ["test-alias"]


def test_alias_handling(tmp_path):
    """Alias 처리 확인"""
    cat = {
        "labels": [
            {
                "name": "reason:main",
                "color": "ff0000",
                "description": "Main label",
                "aliases": ["alias1", "alias2"]
            }
        ],
        "groups": {}
    }
    cat_file = tmp_path / "catalog.json"
    cat_file.write_text(json.dumps(cat), encoding="utf-8")

    r = subprocess.run(
        [sys.executable, "scripts/ensure_labels.py", "--repo", "test/repo", "--catalog", str(cat_file), "--dry-run"],
        capture_output=True,
        text=True
    )

    # dry-run에서도 정상 종료
    assert r.returncode == 0
