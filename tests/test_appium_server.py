"""Tests for Appium server management."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from phone_farm.appium_server import AppiumServer


def test_port_calculated_from_base_and_slot() -> None:
    server = AppiumServer(slot=0, base_port=4723)
    assert server.port == 4723
    server2 = AppiumServer(slot=3, base_port=4723)
    assert server2.port == 4726


@pytest.mark.asyncio
async def test_start_launches_appium_process() -> None:
    server = AppiumServer(slot=0, base_port=4723)
    with patch("phone_farm.appium_server.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_proc = MagicMock()
        mock_proc.stdout = MagicMock()
        mock_exec.return_value = mock_proc
        with patch("phone_farm.appium_server.asyncio.sleep", new_callable=AsyncMock):
            await server.start()
        args = mock_exec.call_args[0]
        assert "appium" in args[0]
        assert "--port" in args
        assert "4723" in args


@pytest.mark.asyncio
async def test_stop_terminates_process() -> None:
    server = AppiumServer(slot=0, base_port=4723)
    mock_proc = MagicMock()
    mock_proc.terminate = MagicMock()
    mock_proc.wait = AsyncMock()
    server._process = mock_proc
    await server.stop()
    mock_proc.terminate.assert_called_once()
