"""Tests for emulator management (unit tests with mocked subprocess)."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from phone_farm.emulator import Emulator


@pytest.mark.asyncio
async def test_create_avd_runs_avdmanager() -> None:
    emu = Emulator(slot=0, api_level=34, ram_mb=1536, device_profile="pixel_6")
    with patch("phone_farm.emulator.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "", "")
        await emu.create_avd()
        args = mock_run.call_args[0][0]
        assert "avdmanager" in args[0]
        assert "phone-farm-slot-0" in args


@pytest.mark.asyncio
async def test_start_headless_passes_no_window_flag() -> None:
    emu = Emulator(slot=0, api_level=34, ram_mb=1536, device_profile="pixel_6")
    with patch("phone_farm.emulator.start_emulator_process", new_callable=AsyncMock) as mock_start:
        mock_start.return_value = MagicMock()
        await emu.start(headless=True)
        args = mock_start.call_args[0][0]
        assert "-no-window" in args


@pytest.mark.asyncio
async def test_stop_kills_process() -> None:
    emu = Emulator(slot=0, api_level=34, ram_mb=1536, device_profile="pixel_6")
    mock_proc = MagicMock()
    mock_proc.terminate = MagicMock()
    mock_proc.wait = AsyncMock()
    emu._process = mock_proc
    await emu.stop()
    mock_proc.terminate.assert_called_once()


def test_avd_name_uses_slot() -> None:
    emu = Emulator(slot=3, api_level=34, ram_mb=1536, device_profile="pixel_6")
    assert emu.avd_name == "phone-farm-slot-3"


def test_adb_serial_uses_port_offset() -> None:
    emu = Emulator(slot=2, api_level=34, ram_mb=1536, device_profile="pixel_6")
    # Emulator ports: 5554, 5556, 5558, ...
    assert emu.adb_serial == "emulator-5558"
