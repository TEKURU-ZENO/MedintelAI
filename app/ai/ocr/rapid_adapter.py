"""
RapidOCR engine factory for the printed-text path.

`create_rapid_ocr()` returns an object with the legacy rapidocr-onnxruntime interface the OCR engines use:
    results, elapse = engine(image, box_thresh=..., unclip_ratio=..., text_score=...)
        results: list of [box (4 x [x, y]), text, score] or None
    rec_res, elapse = engine.text_recognizer([crop, ...])
        rec_res: list of (text, score)

Presets (env RAPIDOCR_PRESET):
    legacy      rapidocr-onnxruntime 1.x package (PP-OCRv4 mobile)
    v5_mobile   rapidocr 3.x, PP-OCRv5 mobile detector + English recogniser
    v5_server   rapidocr 3.x, PP-OCRv5 server detector + recogniser (higher accuracy, slower)
    v6_small / v6_medium   rapidocr 3.x, PP-OCRv6 multilingual models
Model files are kept in app/ai/models/rapidocr (override with RAPIDOCR_MODEL_DIR) and fetched on first use.
If rapidocr 3.x or its models are unavailable the factory falls back to the legacy package.
"""
import os
import time
from pathlib import Path
from typing import Any, List, Optional, Sequence, Tuple

import numpy as np

DEFAULT_PRESET = "v6_medium"
MODEL_DIR = Path(__file__).resolve().parent.parent / "models" / "rapidocr"


def _resolve_model_dir() -> Path:
    """RAPIDOCR_MODEL_DIR, else this tree's app/ai/models/rapidocr, else a repository-level one (lets
    backend/app share the models stored under the repository's app/ai/models)."""
    env = os.getenv("RAPIDOCR_MODEL_DIR")
    if env:
        return Path(env).expanduser()
    if MODEL_DIR.is_dir():
        return MODEL_DIR
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "app" / "ai" / "models" / "rapidocr"
        if candidate.is_dir():
            return candidate
    return MODEL_DIR


def _preset_params(preset: str, threads: Optional[int]) -> dict:
    from rapidocr.utils.typings import LangRec, ModelType, OCRVersion

    table = {
        "v5_mobile": (OCRVersion.PPOCRV5, ModelType.MOBILE, ModelType.MOBILE, LangRec.EN),
        "v5_server": (OCRVersion.PPOCRV5, ModelType.SERVER, ModelType.SERVER, LangRec.CH),
        "v6_small": (OCRVersion.PPOCRV6, ModelType.SMALL, ModelType.SMALL, "en"),
        "v6_medium": (OCRVersion.PPOCRV6, ModelType.MEDIUM, ModelType.MEDIUM, "en"),
    }
    if preset not in table:
        raise ValueError(f"Unknown RAPIDOCR_PRESET '{preset}'")
    version, det_type, rec_type, rec_lang = table[preset]
    model_dir = _resolve_model_dir()
    model_dir.mkdir(parents=True, exist_ok=True)
    params = {
        "Global.log_level": "error",
        "Global.model_root_dir": str(model_dir),
        "Det.ocr_version": version, "Det.model_type": det_type,
        "Rec.ocr_version": version, "Rec.model_type": rec_type, "Rec.lang_type": rec_lang,
    }
    if version == OCRVersion.PPOCRV6:
        params["Det.lang_type"] = "en"
    if threads:
        params["EngineConfig.onnxruntime.intra_op_num_threads"] = threads
    return params


class RapidOCRAdapter:
    """Legacy-interface facade over rapidocr 3.x model sets."""

    def __init__(self, preset: str = DEFAULT_PRESET, threads: Optional[int] = None):
        from rapidocr import RapidOCR

        self.preset = preset
        self._engine = RapidOCR(params=_preset_params(preset, threads))
        # Load detector and recogniser eagerly so missing models fail here (and fall back), not mid-request
        self._engine._load_det_model()
        self._rec = self._engine._load_rec_model()

    def __call__(
        self,
        image: np.ndarray,
        box_thresh: Optional[float] = None,
        unclip_ratio: Optional[float] = None,
        text_score: Optional[float] = None,
    ) -> Tuple[Optional[List[List[Any]]], float]:
        t0 = time.time()
        out = self._engine(image, box_thresh=box_thresh, unclip_ratio=unclip_ratio, text_score=text_score)
        boxes = getattr(out, "boxes", None)
        if boxes is None or len(boxes) == 0:
            return None, time.time() - t0
        results = [
            [np.asarray(b).tolist(), str(t), float(s)]
            for b, t, s in zip(boxes, out.txts or [], out.scores or [])
        ]
        return results, time.time() - t0

    def text_recognizer(self, crops: Sequence[np.ndarray]) -> Tuple[List[Tuple[str, float]], float]:
        from rapidocr.ch_ppocr_rec.typings import TextRecInput

        t0 = time.time()
        out = self._rec(TextRecInput(img=list(crops)))
        texts = list(out.txts or [])
        scores = list(out.scores or [])
        return [(t, float(s)) for t, s in zip(texts, scores)], time.time() - t0


def create_rapid_ocr(preset: Optional[str] = None, logger=None):
    """Builds the configured printed-text OCR engine, falling back to the legacy package on any failure."""
    preset = (preset or os.getenv("RAPIDOCR_PRESET", DEFAULT_PRESET)).strip().lower()
    if preset != "legacy":
        try:
            engine = RapidOCRAdapter(preset)
            if logger:
                logger.info(f"RapidOCR {preset} model set initialized (rapidocr 3.x)")
            return engine
        except Exception as e:
            if logger:
                logger.warning(f"RapidOCR preset '{preset}' unavailable ({e}); using legacy rapidocr-onnxruntime")
    from rapidocr_onnxruntime import RapidOCR as LegacyRapidOCR
    return LegacyRapidOCR()
