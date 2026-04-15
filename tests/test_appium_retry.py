# tests/test_appium_retry.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from phone_farm.appium_server import AppiumServer, create_driver_with_retry


@pytest.fixture
def appium():
    return AppiumServer(slot=0, base_port=4723)


@pytest.mark.asyncio
async def test_health_check_retries_on_failure(appium):
    """Health check retries when /status raises then succeeds."""
    responses = [Exception("Connection refused"), MagicMock(status=200)]
    call_count = 0

    async def mock_get(url, **kwargs):
        nonlocal call_count
        resp = responses[min(call_count, 1)]
        call_count += 1
        if isinstance(resp, Exception):
            raise resp
        return resp

    with patch("phone_farm.appium_server._http_get", side_effect=mock_get):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await appium._health_check()
    assert result is True
    assert call_count == 2


@pytest.mark.asyncio
async def test_health_check_fails_after_max_retries(appium):
    """Health check returns False after all retries fail."""
    async def always_fail(url, **kwargs):
        raise Exception("Connection refused")

    with patch("phone_farm.appium_server._http_get", side_effect=always_fail):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await appium._health_check()
    assert result is False


@pytest.mark.asyncio
async def test_webdriver_retry_on_connection_refused():
    """WebDriver creation retries on connection refused and succeeds."""
    fail_then_succeed = [Exception("Connection refused"), MagicMock()]
    call_count = 0

    def mock_remote(*args, **kwargs):
        nonlocal call_count
        result = fail_then_succeed[min(call_count, 1)]
        call_count += 1
        if isinstance(result, Exception):
            raise result
        return result

    with patch("phone_farm.appium_server.webdriver.Remote", side_effect=mock_remote):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            driver = await create_driver_with_retry("http://localhost:4723")
    assert driver is not None
    assert call_count == 2
