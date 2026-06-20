from app.services import rationale_service as rat


def _payloads():
    return [{
        "id": "team-1", "name": "Team 01",
        "members": [
            {"role": "technical", "experience": "advanced", "tech_stack": [], "interests": []},
            {"role": "design", "experience": "beginner", "tech_stack": [], "interests": []},
        ],
    }]


class _Event:
    title = "Hack Night"
    description = "Build something"


def test_build_request_is_cacheable_and_pii_free():
    req = rat._build_request(_Event(), _payloads())
    # static instructions in a cacheable system block
    assert req["system"][0]["cache_control"]["type"] == "ephemeral"
    assert req["max_tokens"] >= 2048
    # the team id reaches the model; the tool returns the structured shape
    blob = req["system"][0]["text"] + req["messages"][0]["content"]
    assert "team-1" in blob
    props = req["tools"][0]["input_schema"]["properties"]["rationales"]["items"]["properties"]
    assert set(props) >= {"team_id", "title", "summary", "strengths", "gaps"}


def test_build_request_contains_no_pii():
    payloads = _payloads()
    # composition only — names/emails never appear in the payload
    req = rat._build_request(_Event(), payloads)
    serialized = str(req)
    for leaked in ("@", "Alice", "Bob"):
        assert leaked not in serialized


def test_parse_rationales_keeps_valid_drops_malformed():
    class Block:
        type = "tool_use"
        input = {"rationales": [
            {"team_id": "a", "title": "T", "summary": "S", "strengths": ["x"], "gaps": []},
            {"team_id": "b", "title": "only-title"},  # missing required keys -> dropped
        ]}
    out = rat._parse_rationales([Block()])
    assert out["a"]["summary"] == "S"
    assert "b" not in out


def test_parse_rationales_tolerates_omitted_team():
    class Block:
        type = "tool_use"
        input = {"rationales": []}
    assert rat._parse_rationales([Block()]) == {}
