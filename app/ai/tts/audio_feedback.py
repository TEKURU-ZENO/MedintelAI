import os
import hashlib
from typing import Dict, Any
from gtts import gTTS
from app.ai.utils.logger import get_logger

logger = get_logger(__name__)

class TTSEngine:
    def __init__(self, output_dir: str = "outputs/audio"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
    def _generate_hash(self, text: str, lang: str, slow: bool) -> str:
        key = f"{text}_{lang}_{slow}"
        return hashlib.md5(key.encode('utf-8')).hexdigest()
        
    def generate_audio(self, text: str, lang: str = 'en', slow: bool = False) -> str:
        """Generates audio for a given text, using cache if available."""
        if not text:
            return None
            
        text_hash = self._generate_hash(text, lang, slow)
        filename = f"feedback_{text_hash}.mp3"
        filepath = os.path.join(self.output_dir, filename)
        
        if os.path.exists(filepath):
            logger.debug(f"TTS cache hit for {filename}")
            return filepath
            
        try:
            logger.info(f"Generating new TTS audio: {filename}")
            tts = gTTS(text=text, lang=lang, slow=slow)
            tts.save(filepath)
            return filepath
        except Exception as e:
            logger.error(f"Failed to generate TTS audio: {e}")
            return None

def apply_tts(features: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts feedback issues, combines them into a single text, and generates audio.
    """
    feedback_data = features.get("feedback", {})
    issues = feedback_data.get("issues", [])
    
    if not issues:
        return features
        
    # Combine top feedback into one string
    messages = [issue.get("message", "") for issue in issues if issue.get("message")]
    combined_text = " ".join(messages)
    
    if combined_text:
        engine = TTSEngine()
        # Use slow rate if mode is 'child'
        mode = feedback_data.get("mode", "advanced")
        is_slow = (mode == "child")
        
        audio_path = engine.generate_audio(combined_text, lang='en', slow=is_slow)
        
        # Fail-safe gracefully handles None audio_path
        features["audio_feedback"] = {
            "text_spoken": combined_text,
            "audio_file": audio_path,
            "status": "success" if audio_path else "failed_text_only"
        }
            
    return features
