from fastapi.concurrency import run_in_threadpool
from app.ai.pipeline.pipeline_controller import PipelineController
import base64
import uuid
import os

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class AIService:
    def __init__(self):
        # We can pass an empty or default config for now, 
        # or load from settings if needed.
        self.controller = PipelineController(config={})

    async def process(self, input_type: str, file=None, strokes=None, base64_image=None):
        """
        Main entry point for AI analysis.
        """
        if input_type == "image":
            if not file:
                raise ValueError("File is required for image input type")
            image_path = self._save_image(file)

        elif input_type == "canvas":
            if not base64_image:
                raise ValueError("Base64 snapshot is required for canvas input type")
            image_path = self._save_canvas_snapshot(base64_image)
        else:
            raise ValueError("Invalid input type")

        # Run heavy AI pipeline safely on a background thread
        result = await run_in_threadpool(self.controller.process_image, image_path)

        if result is None:
            raise ValueError("AI Pipeline failed to process image.")

        # Enrich with stroke data if available (canvas mode)
        if strokes:
            result = self._augment_with_strokes(result, strokes)

        return result

    def _save_image(self, file):
        filename = f"{uuid.uuid4()}.jpg"
        path = os.path.join(UPLOAD_DIR, filename)

        with open(path, "wb") as f:
            f.write(file.file.read())

        # Reset file cursor for future use if needed
        file.file.seek(0)
        return path

    def _save_canvas_snapshot(self, base64_image: str):
        filename = f"{uuid.uuid4()}.png"
        path = os.path.join(UPLOAD_DIR, filename)

        # Handle data URI scheme if present (e.g. data:image/png;base64,...)
        if "," in base64_image:
            base64_image = base64_image.split(",")[1]

        image_bytes = base64.b64decode(base64_image)

        with open(path, "wb") as f:
            f.write(image_bytes)

        return path

    def _augment_with_strokes(self, result, strokes):
        # Future enhancement: process actual stroke speeds, smoothness, etc.
        result["stroke_analysis"] = {
            "stroke_count": len(strokes),
            "status": "Canvas enrichment applied"
        }
        return result
