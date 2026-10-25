from pathlib import Path

from app.ai.ocr.ocr_engine import MedIntelOCREngine


def test_training_output_is_default_checkpoint_location(tmp_path):
    checkpoint = tmp_path / "app" / "ai" / "models" / "trocr_medical_finetuned"
    checkpoint.mkdir(parents=True)

    assert MedIntelOCREngine._find_finetuned_model_path(tmp_path) == checkpoint.resolve()


def test_configured_checkpoint_path_takes_precedence(tmp_path):
    default = tmp_path / "app" / "ai" / "models" / "trocr_medical_finetuned"
    configured = tmp_path / "trained" / "checkpoint"
    default.mkdir(parents=True)
    configured.mkdir(parents=True)

    assert MedIntelOCREngine._find_finetuned_model_path(
        tmp_path, str(configured)
    ) == configured.resolve()


def test_legacy_backend_checkpoint_path_remains_supported(tmp_path):
    legacy = tmp_path / "backend" / "app" / "ai" / "models" / "trocr_medical_finetuned"
    legacy.mkdir(parents=True)

    assert MedIntelOCREngine._find_finetuned_model_path(tmp_path) == legacy.resolve()


def test_missing_checkpoint_does_not_claim_finetuned_model(tmp_path):
    assert MedIntelOCREngine._find_finetuned_model_path(
        tmp_path, str(tmp_path / "not-present")
    ) is None
