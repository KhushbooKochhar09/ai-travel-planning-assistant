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
