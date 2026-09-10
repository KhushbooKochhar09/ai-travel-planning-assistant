import asyncio
import sys

from fastmcp import Client


async def get_mcp_data():
    """Call Weather and Currency MCP tools."""

    server_config = {
        "mcpServers": {
            "weather": {
                "command": sys.executable,
                "args": ["-m", "app.mcp.weather_server"],
            }
        }
    }

    async with Client(server_config) as client:
        tools = await client.list_tools()

        print("Available MCP tools:")
        for tool in tools:
            print(f"- {tool.name}")

        weather = await client.call_tool(
            "get_weather",
            {
                "latitude": 1.3521,
                "longitude": 103.8198,
            },
        )

        currency = await client.call_tool(
            "convert_currency",
            {
                "amount": 60000,
                "from_currency": "INR",
                "to_currency": "SGD",
            },
        )

        print("\nWeather result:")
        if weather.data and "error" in weather.data:
            print(f"Weather unavailable: {weather.data['error']}")
        else:
            print(weather.data)

        print("\nCurrency result:")
        if currency.data and "error" in currency.data:
            print(f"Currency unavailable: {currency.data['error']}")
        else:
            print(currency.data)


if __name__ == "__main__":
    asyncio.run(get_mcp_data())
