"""Tests for the QA runner module."""

from phone_farm.web.qa_runner import _extract_clickables, _simple_screen_sig


def test_extract_clickables_from_xml():
    """Extract clickable elements with bounds."""
    xml = (
        '<node clickable="true" bounds="[100,200][300,400]" />'
        '<node clickable="false" bounds="[0,0][100,100]" />'
        '<node clickable="true" bounds="[500,600][700,800]" />'
    )
    result = _extract_clickables(xml)
    assert len(result) == 2
    assert result[0]["center"] == (200, 300)
    assert result[1]["center"] == (600, 700)


def test_extract_clickables_reverse_attr_order():
    """Handle bounds before clickable attribute."""
    xml = '<node bounds="[10,20][30,40]" clickable="true" />'
    result = _extract_clickables(xml)
    assert len(result) == 1
    assert result[0]["center"] == (20, 30)


def test_extract_clickables_empty_xml():
    """Return empty list for XML with no clickables."""
    result = _extract_clickables('<hierarchy />')
    assert result == []


def test_simple_screen_sig_deterministic():
    """Same XML produces same signature."""
    xml = '<node text="Hello" />'
    sig1 = _simple_screen_sig(xml)
    sig2 = _simple_screen_sig(xml)
    assert sig1 == sig2
    assert len(sig1) == 16


def test_simple_screen_sig_differs():
    """Different XML produces different signature."""
    sig1 = _simple_screen_sig('<node text="Hello" />')
    sig2 = _simple_screen_sig('<node text="World" />')
    assert sig1 != sig2
