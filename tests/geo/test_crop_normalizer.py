"""Tests for CropNormalizer — geo/crop_normalizer.py."""

import pytest

from agromind.geo.crop_normalizer import CropNormalizer


CROPS_CSV = "bolbhav-data/Agmark crops.csv"


@pytest.fixture(scope="module")
def normalizer():
    return CropNormalizer(CROPS_CSV)


class TestCropNormalizerLoad:
    def test_loads_without_error(self):
        n = CropNormalizer(CROPS_CSV)
        assert n is not None

    def test_crop_count_nonzero(self, normalizer):
        assert normalizer.total_crops > 0


class TestCropNormalizerNormalize:
    def test_exact_match(self, normalizer):
        result = normalizer.normalize("Wheat")
        assert result is not None
        assert result["crop_name"].lower() == "wheat"

    def test_case_insensitive(self, normalizer):
        result = normalizer.normalize("WHEAT")
        assert result is not None
        assert result["crop_name"].lower() == "wheat"

    def test_raw_agmark_name_resolves(self, normalizer):
        # "Wheat Atta" in CSV maps to clean name "Wheat"
        result = normalizer.normalize("Wheat Atta")
        assert result is not None
        assert result["crop_name"].lower() == "wheat"

    def test_unknown_crop_returns_none(self, normalizer):
        result = normalizer.normalize("XYZUnknownCrop999")
        assert result is None

    def test_result_has_crop_type(self, normalizer):
        result = normalizer.normalize("Wheat")
        assert result is not None
        assert "crop_type" in result

    def test_list_canonical_names(self, normalizer):
        names = normalizer.list_canonical_names()
        assert isinstance(names, list)
        assert "Wheat" in names
        assert "Maize" in names

    def test_paddy_variants_resolve_to_paddy(self, normalizer):
        for raw in ["Paddy(Dhan)(Basmati)", "Paddy(Dhan)(Common)"]:
            result = normalizer.normalize(raw)
            assert result is not None
            assert result["crop_name"].lower() == "paddy"
