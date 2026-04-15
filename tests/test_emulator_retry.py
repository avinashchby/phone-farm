# tests/test_emulator_retry.py
import pytest
from unittest.mock import AsyncMock, patch

from phone_farm.emulator import Emulator, EmulatorError


@pytest.fixture
def emu():
    return Emulator(slot=0, api_level=34, ram_mb=2048, device_profile="pixel_6")


@pytest.mark.asyncio
async def test_create_avd_retries_on_failure(emu):
    """create_avd() retries once on failure and succeeds on second attempt."""
    call_count = 0

    async def mock_run_cmd(args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("AVD creation failed")
        return (0, "success", "")

    with patch("phone_farm.emulator.run_cmd", side_effect=mock_run_cmd):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await emu.create_avd()
    assert call_count == 2


@pytest.mark.asyncio
async def test_create_avd_raises_after_max_retries(emu):
    """create_avd() raises EmulatorError after 2 failed attempts."""
    async def always_fail(args, **kwargs):
        raise Exception("AVD creation failed")

    with patch("phone_farm.emulator.run_cmd", side_effect=always_fail):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(EmulatorError, match="AVD creation failed"):
                await emu.create_avd()


@pytest.mark.asyncio
async def test_boot_with_retry_succeeds_on_third_attempt(emu):
    """_boot_with_retry() retries up to 3 times."""
    call_count = 0

    async def fail_twice(self_inner=None):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("boot failed")

    with patch.object(emu, "_start_once", side_effect=fail_twice):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            await emu._boot_with_retry()
    assert call_count == 3


@pytest.mark.asyncio
async def test_boot_with_retry_raises_after_3_failures(emu):
    """_boot_with_retry() raises EmulatorError after 3 failures."""
    async def always_fail(self_inner=None):
        raise Exception("boot failed")

    with patch.object(emu, "_start_once", side_effect=always_fail):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(EmulatorError):
                await emu._boot_with_retry()
