import httpx
from fastmcp import FastMCP

mcp = FastMCP("Singapore Weather")


@mcp.tool
def get_weather(latitude: float, longitude: float) -> dict:
    """Get the current weather and 7-day forecast for a location."""

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&current=temperature_2m,precipitation,weather_code"
        "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max"
        "&forecast_days=7"
        "&timezone=auto"
    )

    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    except httpx.HTTPError as error:
        return {
            "error": "Weather service is currently unavailable.",
            "details": str(error),
        }


@mcp.tool
def convert_currency(
    amount: float,
    from_currency: str,
    to_currency: str,
) -> dict:
    """Get the current exchange rate and convert an amount."""

    url = (
        "https://api.frankfurter.dev/v1/latest"
        f"?amount={amount}"
        f"&from={from_currency.upper()}"
        f"&to={to_currency.upper()}"
    )

    try:
        response = httpx.get(url, timeout=10)
        response.raise_for_status()
        return response.json()

    except httpx.HTTPError as error:
        return {
            "error": "Currency service is currently unavailable.",
            "details": str(error),
        }
