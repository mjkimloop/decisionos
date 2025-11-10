from apps.policy.parser import parse_policy


def test_parse_policy_with_metadata():
    text = """
    permit(read, subject, resource) meta {
        id: "allow-view"
        priority: 7
        purpose: "review"
    }
    when { subject.get("role") == "reviewer" }
    """

    policy = parse_policy(text)

    assert policy.effect == "allow"
    assert policy.priority == 7
    assert policy.policy_id == "allow-view"
    assert policy.purpose == "review"
    assert policy.metadata["id"] == "allow-view"
    assert policy.metadata["priority"] == 7
