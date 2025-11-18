from scripts.ci.github_checks import build_payload


def test_build_payload_maps_conclusion():
    payload = build_payload(
        name="Release Gate",
        sha="abc123",
        conclusion="success",
        summary="ok",
        title="Gate",
        text="details",
        details_url="https://example.com/run",
    )
    assert payload["name"] == "Release Gate"
    assert payload["head_sha"] == "abc123"
    assert payload["conclusion"] == "success"
    assert payload["output"]["title"] == "Gate"
    assert payload["details_url"] == "https://example.com/run"
