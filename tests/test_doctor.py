"""Tests for doctor/prerequisite checker."""

import pytest
from unittest.mock import AsyncMock, patch

from phone_farm.doctor import Doctor, CheckResult


def test_check_result_dataclass() -> None:
    r = CheckResult(name="java", ok=True, message="Java 17 found")
    assert r.ok is True


@pytest.mark.asyncio
async def test_check_java_passes_when_found() -> None:
    doc = Doctor()
    with patch("phone_farm.doctor.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, 'openjdk version "17.0.10"', "")
        result = await doc.check_java()
    assert result.ok is True


@pytest.mark.asyncio
async def test_check_java_fails_when_missing() -> None:
    doc = Doctor()
    with patch("phone_farm.doctor.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.side_effect = FileNotFoundError
        result = await doc.check_java()
    assert result.ok is False


@pytest.mark.asyncio
async def test_check_node_passes_when_found() -> None:
    doc = Doctor()
    with patch("phone_farm.doctor.run_cmd", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = (0, "v20.11.0", "")
        result = await doc.check_node()
    assert result.ok is True


@pytest.mark.asyncio
async def test_check_all_returns_list_of_results() -> None:
    doc = Doctor()
    with patch.object(doc, "check_java", new_callable=AsyncMock) as mj, \
         patch.object(doc, "check_node", new_callable=AsyncMock) as mn, \
         patch.object(doc, "check_adb", new_callable=AsyncMock) as ma, \
         patch.object(doc, "check_appium", new_callable=AsyncMock) as map_, \
         patch.object(doc, "check_disk_space", new_callable=AsyncMock) as md:
        mj.return_value = CheckResult("java", True, "ok")
        mn.return_value = CheckResult("node", True, "ok")
        ma.return_value = CheckResult("adb", True, "ok")
        map_.return_value = CheckResult("appium", True, "ok")
        md.return_value = CheckResult("disk", True, "ok")
        results = await doc.check_all()
    assert len(results) == 5
    assert all(r.ok for r in results)
