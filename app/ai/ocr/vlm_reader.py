"""
Local vision-language model reader for handwritten lines both OCR engines struggle with.

The model sees the line image itself (not just OCR text), so it can resolve what a text-only corrector cannot.
It runs locally (default Qwen/Qwen3-VL-2B-Instruct, Apache-2.0) and only on lines the ensemble flags as
uncertain; its reading is accepted only through the anchored selection rule in htr_ensemble / ocr_engine
(it must stay close to what the ink supports). No patient data leaves the machine.

Environment:
  HTR_VLM          1 enables the VLM stage (default 0: opt-in, it needs ~4.5 GB of GPU memory)
  HTR_VLM_MODEL    model id or local path (default Qwen/Qwen3-VL-2B-Instruct)
"""
import os
from typing import List, Optional, Sequence, Tuple

import numpy as np

DEFAULT_MODEL = "Qwen/Qwen3-VL-2B-Instruct"

PLAIN_PROMPT = ("Transcribe the handwritten text in this image exactly as written. Keep the original spelling, "
                "numbers, punctuation, units and medical abbreviations. Output only the transcription.")
HINT_PROMPT = ("Transcribe the handwritten text in this image exactly as written. Two OCR engines read it as:\n"
               "1) {a}\n2) {b}\nThey may both be wrong. Trust the image. Output only the correct transcription.")


class VLMLineReader:
    def __init__(self, model: Optional[str] = None, device: Optional[str] = None, max_new_tokens: int = 64):
        import torch
        from transformers import AutoModelForImageTextToText, AutoProcessor

        self.model_id = model or os.getenv("HTR_VLM_MODEL", DEFAULT_MODEL)
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        dtype = torch.bfloat16 if self.device == "cuda" else torch.float32
        self.processor = AutoProcessor.from_pretrained(self.model_id)
        self.processor.tokenizer.padding_side = "left"
        self.model = AutoModelForImageTextToText.from_pretrained(self.model_id, dtype=dtype).to(self.device).eval()
        self.max_new_tokens = max_new_tokens

    def read(self, crops: Sequence[np.ndarray], hints: Optional[Sequence[Tuple[str, str]]] = None,
             batch_size: int = 8) -> List[Tuple[str, float]]:
        """Returns (text, mean token probability) per BGR crop."""
        import cv2
        import torch
        from PIL import Image

        results: List[Tuple[str, float]] = []
        for start in range(0, len(crops), batch_size):
            chunk = crops[start: start + batch_size]
            convs = []
            for k, crop in enumerate(chunk):
                pil = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                if pil.height < 32:
                    pil = pil.resize((max(32, int(pil.width * 32 / pil.height)), 32))
                prompt = PLAIN_PROMPT
                if hints is not None:
                    a, b = hints[start + k]
                    prompt = HINT_PROMPT.format(a=a or "(empty)", b=b or "(empty)")
                convs.append([{"role": "user", "content": [{"type": "image", "image": pil}, {"type": "text", "text": prompt}]}])
            inputs = self.processor.apply_chat_template(
                convs, tokenize=True, add_generation_prompt=True, return_dict=True, return_tensors="pt", padding=True
            ).to(self.device)
            with torch.inference_mode():
                out = self.model.generate(**inputs, max_new_tokens=self.max_new_tokens, do_sample=False,
                                          return_dict_in_generate=True, output_scores=True)
            new_tokens = out.sequences[:, inputs["input_ids"].shape[1]:]
            texts = self.processor.batch_decode(new_tokens, skip_special_tokens=True)
            probs = torch.stack([torch.softmax(s.float(), dim=-1).max(dim=-1).values for s in out.scores], dim=1)
            pad = self.processor.tokenizer.pad_token_id
            for row, text in enumerate(texts):
                valid = new_tokens[row] != pad
                p = probs[row][valid[: probs.shape[1]]]
                conf = float(torch.exp(torch.log(p.clamp_min(1e-6)).mean())) if p.numel() else 0.0
                results.append((text.strip().strip('"').strip(), round(conf, 4)))
            if self.device == "cuda":
                torch.cuda.empty_cache()
        return results
