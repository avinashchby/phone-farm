"""Tests for emulator pool management."""

import pytest
from unittest.mock import AsyncMock

from phone_farm.pool import EmulatorPool


@pytest.mark.asyncio
async def test_pool_creates_correct_number_of_emulators() -> None:
    pool = EmulatorPool(batch_size=3, api_level=34, ram_mb=1536, device_profile="pixel_6")
    assert len(pool.emulators) == 3
    assert pool.emulators[0].slot == 0
    assert pool.emulators[2].slot == 2


@pytest.mark.asyncio
async def test_pool_start_all_boots_each_emulator() -> None:
    pool = EmulatorPool(batch_size=2, api_level=34, ram_mb=1536, device_profile="pixel_6")
    for emu in pool.emulators:
        emu.create_avd = AsyncMock()
        emu.start = AsyncMock()
        emu.wait_for_boot = AsyncMock()
    await pool.start_all(headless=True)
    for emu in pool.emulators:
        emu.create_avd.assert_called_once()
        emu.start.assert_called_once_with(headless=True)
        emu.wait_for_boot.assert_called_once()


@pytest.mark.asyncio
async def test_pool_stop_all_stops_each_emulator() -> None:
    pool = EmulatorPool(batch_size=2, api_level=34, ram_mb=1536, device_profile="pixel_6")
    for emu in pool.emulators:
        emu.stop = AsyncMock()
    await pool.stop_all()
    for emu in pool.emulators:
        emu.stop.assert_called_once()


@pytest.mark.asyncio
async def test_pool_start_all_continues_on_single_failure() -> None:
    pool = EmulatorPool(batch_size=2, api_level=34, ram_mb=1536, device_profile="pixel_6")
    pool.emulators[0].create_avd = AsyncMock(side_effect=Exception("boot fail"))
    pool.emulators[0].start = AsyncMock()
    pool.emulators[0].wait_for_boot = AsyncMock()
    pool.emulators[1].create_avd = AsyncMock()
    pool.emulators[1].start = AsyncMock()
    pool.emulators[1].wait_for_boot = AsyncMock()
    results = await pool.start_all(headless=True)
    assert results[0] is False
    assert results[1] is True
