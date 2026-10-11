import numpy as np
import pytest

from app.ai.preprocessing import preprocessing_pipeline
from app.schemas.document import PreprocessingMode


@pytest.fixture
def color_image():
    return np.full((12, 16, 3), (20, 80, 160), dtype=np.uint8)


def test_preprocessing_mode_contract_values():
    assert {mode.value for mode in PreprocessingMode} == {
        "balanced", "high-contrast", "grayscale", "none"
    }


def test_balanced_preserves_legacy_input_mode_dispatch(color_image, monkeypatch):
    expected = color_image.copy()
    calls = []

    def screen(image):
        calls.append("screen")
        return expected

    monkeypatch.setattr(preprocessing_pipeline, "run_screen_preprocessing", screen)
    result = preprocessing_pipeline.run_preprocessing_pipeline(
        color_image, input_mode="digital", preprocessing_mode="balanced"
    )

    assert calls == ["screen"]
    assert result is expected


def test_high_contrast_uses_scanned_paper_pipeline(color_image, monkeypatch):
    expected = color_image.copy()
    calls = []

    def scanned(image, config):
        calls.append((image, config))
        return expected

    monkeypatch.setattr(preprocessing_pipeline, "run_scanned_preprocessing", scanned)
    result = preprocessing_pipeline.run_preprocessing_pipeline(
        color_image, {"test": True}, input_mode="screen",
        preprocessing_mode="high-contrast"
    )

    assert len(calls) == 1
    assert calls[0][0] is color_image
    assert calls[0][1] == {"test": True}
    assert result is expected


def test_grayscale_converts_to_three_channel_grayscale(color_image):
    result = preprocessing_pipeline.run_preprocessing_pipeline(
        color_image, preprocessing_mode="grayscale"
    )

    assert result.shape == color_image.shape
    assert np.array_equal(result[:, :, 0], result[:, :, 1])
    assert np.array_equal(result[:, :, 1], result[:, :, 2])


def test_none_skips_preprocessing_and_returns_independent_image(color_image, monkeypatch):
    def unexpected(*_args, **_kwargs):
        raise AssertionError("No-preprocessing mode must not invoke a filter")

    monkeypatch.setattr(preprocessing_pipeline, "run_screen_preprocessing", unexpected)
    monkeypatch.setattr(preprocessing_pipeline, "run_scanned_preprocessing", unexpected)
    result = preprocessing_pipeline.run_preprocessing_pipeline(
        color_image, input_mode="scanned_paper", preprocessing_mode="none"
    )

    assert np.array_equal(result, color_image)
    assert result is not color_image


def test_unknown_preprocessing_mode_is_rejected(color_image):
    with pytest.raises(ValueError, match="Unsupported preprocessing_mode"):
        preprocessing_pipeline.run_preprocessing_pipeline(
            color_image, preprocessing_mode="silent-noop"
        )


def test_omitted_mode_keeps_legacy_scanned_paper_behavior(color_image, monkeypatch):
    expected = color_image.copy()
    calls = []

    def scanned(image, config):
        calls.append(image)
        return expected

    monkeypatch.setattr(preprocessing_pipeline, "run_scanned_preprocessing", scanned)
    result = preprocessing_pipeline.run_preprocessing_pipeline(
        color_image, input_mode="scanned_paper"
    )

    assert calls == [color_image]
    assert result is expected
