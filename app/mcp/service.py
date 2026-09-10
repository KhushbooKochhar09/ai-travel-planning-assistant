import asyncio
import sys

from fastmcp import Client


SERVER_CONFIG = {
    "mcpServers": {
        "singapore": {
            "command": sys.executable,
            "args": ["-m", "app.mcp.weather_server"],
        }
    }
}


async def call_mcp_tools(
    tools: list[str],
    latitude: float = 1.3521,
    longitude: float = 103.8198,
    amount: float | None = None,
    from_currency: str = "INR",
    to_currency: str = "SGD",
) -> dict:
    """Call the MCP tools selected by the intent router."""

    results = {}

    try:
        async with Client(SERVER_CONFIG) as client:

            if "weather" in tools:
                try:
                    weather = await client.call_tool(
                        "get_weather",
                        {
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                    )

                    results["weather"] = weather.data

                except Exception as error:
                    results["weather"] = {
                        "error": (
                            "Weather MCP tool is currently unavailable."
                        ),
                        "details": str(error),
                    }

            if "currency" in tools:
                if amount is None:
                    results["currency"] = {
                        "error": (
                            "Currency conversion requires an amount."
                        )
                    }
                else:
                    try:
                        currency = await client.call_tool(
                            "convert_currency",
                            {
                                "amount": amount,
                                "from_currency": from_currency,
                                "to_currency": to_currency,
                            },
                        )

                        results["currency"] = currency.data

                    except Exception as error:
                        results["currency"] = {
                            "error": (
                                "Currency MCP tool is currently unavailable."
                            ),
                            "details": str(error),
                        }

    except Exception as error:
        for tool in tools:
            if tool == "weather":
                results["weather"] = {
                    "error": (
                        "Weather MCP service is currently unavailable."
                    ),
                    "details": str(error),
                }

            elif tool == "currency":
                results["currency"] = {
                    "error": (
                        "Currency MCP service is currently unavailable."
                    ),
                    "details": str(error),
                }

    return results


def get_mcp_data(
    tools: list[str],
    latitude: float = 1.3521,
    longitude: float = 103.8198,
    amount: float | None = None,
    from_currency: str = "INR",
    to_currency: str = "SGD",
) -> dict:
    """Synchronous wrapper for the MCP service."""

    return asyncio.run(
        call_mcp_tools(
            tools=tools,
            latitude=latitude,
            longitude=longitude,
            amount=amount,
            from_currency=from_currency,
            to_currency=to_currency,
        )
    )