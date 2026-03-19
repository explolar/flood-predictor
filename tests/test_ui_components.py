"""Tests for UI component modules."""


class TestConstants:
    def test_crop_prices_not_empty(self):
        from ui_components.constants import CROP_PRICES

        assert len(CROP_PRICES) > 0
        for crop, price in CROP_PRICES.items():
            assert isinstance(crop, str)
            assert isinstance(price, (int, float))
            assert price >= 0
