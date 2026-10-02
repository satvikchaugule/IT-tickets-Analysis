import os
import sys
import json
import pytest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from genai_analyzer import GenAIAnalyzer
from prompts import build_ticket_analysis_prompt


def _row():
    return pd.Series({
        "Ticket ID": 1001,
        "Ticket Type": "Technical issue",
        "Ticket Subject": "VPN connection failure",
        "Ticket Description": (
            "Every time I try to connect to the office VPN I get an authentication error. "
            "My network is working fine. Password works on the portal but not in the client."
        ),
        "Ticket Priority": "High",
        "Ticket Channel": "Chat",
        "Product Purchased": "Corporate VPN Client",
    })


def test_mock_mode_enabled_without_key():
    g = GenAIAnalyzer(api_key="", model="gpt-test")
    assert g.use_mock is True


def test_mock_analyze_ticket_structure():
    g = GenAIAnalyzer(api_key="")
    out = g.analyze_ticket(_row())
    for k in ["summary", "category", "suggested_priority", "possible_cause", "suggested_resolution"]:
        assert k in out
        assert isinstance(out[k], str)
        assert len(out[k].strip()) > 0
    assert out["category"] == "Technical issue"
    assert out["suggested_priority"] == "High"
    assert "1." in out["suggested_resolution"]
    assert "vpn" in out["possible_cause"].lower() or "VPN" in out["possible_cause"]


def test_validate_output_enforces_known_priority():
    g = GenAIAnalyzer(api_key="")
    bad = {
        "summary": "s",
        "category": "Technical issue",
        "suggested_priority": "UNKNOWN",
        "possible_cause": "c",
        "suggested_resolution": "steps",
    }
    fixed = g._validate_genai_output(bad)
    assert fixed["suggested_priority"] == "Medium"
    bad2 = dict(bad)
    bad2["category"] = "Something weird"
    fixed2 = g._validate_genai_output(bad2)
    assert fixed2["category"] == "Other"


def test_parse_json_safe_strips_fences():
    g = GenAIAnalyzer(api_key="")
    text = "```json\n{\"summary\": \"hi\", \"category\": \"Other\", \"suggested_priority\": \"Low\", \"possible_cause\": \"x\", \"suggested_resolution\": \"y\"}\n```"
    parsed = g._parse_json_safe(text)
    assert parsed.get("summary") == "hi"


def test_parse_json_safe_bad_text():
    g = GenAIAnalyzer(api_key="")
    assert g._parse_json_safe("not json at all") == {}


def test_prompt_building_contains_ticket_data():
    sys_p, user_p = build_ticket_analysis_prompt(
        ticket_id=1, ticket_type="Billing inquiry", ticket_subject="Wrong invoice",
        ticket_description="Charged twice", ticket_priority="Medium",
        ticket_channel="Email", product_purchased="Service X"
    )
    assert "Billing inquiry" in user_p
    assert "Wrong invoice" in user_p
    assert "Charged twice" in user_p
    assert "Service X" in user_p
    assert "JSON" in sys_p


def test_analyze_dataframe_creates_output_file(tmp_path):
    g = GenAIAnalyzer(api_key="")
    df = pd.DataFrame([dict(_row()) for _ in range(3)])
    out_df = g.analyze_dataframe(df, max_tickets=2)
    assert len(out_df) == 2
    assert "ticket_id" in out_df.columns
    assert (out_df["ticket_id"] == 1001).all()
