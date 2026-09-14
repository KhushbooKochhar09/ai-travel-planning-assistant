from app.assistant import parse_currency_request
from app.mcp.router import select_tools
from app.mcp.service import get_mcp_data


def test_router_and_mcp_service():
    query = "I have ₹60,000, plan my Singapore trip based on weather"

    tools = select_tools(query)

    assert "weather" in tools
    assert "currency" in tools
    assert "rag" in tools

    data = get_mcp_data(tools, amount=60000)

    assert "weather" in data
    assert "currency" in data
    assert "error" not in data["weather"]
    assert "error" not in data["currency"]


def test_parse_currency_request_keeps_expected_directions():
    assert parse_currency_request("convert 60,000 INR to SGD") == (60000.0, "INR", "SGD")
    assert parse_currency_request("what is 100 USD in SGD") == (100.0, "USD", "SGD")
    assert parse_currency_request("convert SGD to INR 2500") == (2500.0, "SGD", "INR")
