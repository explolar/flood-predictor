"""Tests for UI component modules."""

import pytest


class TestConstants:
    def test_crop_prices_not_empty(self):
        from ui_components.constants import CROP_PRICES
        assert len(CROP_PRICES) > 0
        for crop, price in CROP_PRICES.items():
            assert isinstance(crop, str)
            assert isinstance(price, (int, float))
            assert price > 0


class TestLegends:
    def test_mca_legend_returns_html(self):
        from ui_components.legends import get_mca_legend
        html = get_mca_legend("test_map")
        assert isinstance(html, str)
        assert "test_map" in html or len(html) > 50

    def test_sar_legend_returns_html(self):
        from ui_components.legends import get_sar_legend
        html = get_sar_legend("test_map")
        assert isinstance(html, str)
        assert len(html) > 50


class TestReports:
    def test_generate_report_returns_string(self):
        from ui_components.reports import generate_report
        report = generate_report(
            [84.9, 25.5, 85.3, 25.8],
            {"lulc": 40, "slope": 30, "rain": 30},
            {"pre_start": "2024-05-01", "pre_end": "2024-05-30",
             "f_start": "2024-08-01", "f_end": "2024-08-30",
             "threshold": 3.0, "polarization": "VH", "speckle": True},
            {"area_ha": 1500, "pop_exposed": "25,000"}
        )
        assert isinstance(report, str)
        assert len(report) > 100
