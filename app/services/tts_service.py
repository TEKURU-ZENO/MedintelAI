from gtts import gTTS
import hashlib
import os

AUDIO_DIR = "audio"
os.makedirs(AUDIO_DIR, exist_ok=True)


class TTSService:

    def generate(self, text: str):
        if not text:
            return None
            
        key = hashlib.md5(text.encode()).hexdigest()
        path = os.path.join(AUDIO_DIR, f"{key}.mp3")

        if os.path.exists(path):
            return path

        try:
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(path)
            return path
        except Exception as e:
            print(f"TTS Error: {e}")
            return None
