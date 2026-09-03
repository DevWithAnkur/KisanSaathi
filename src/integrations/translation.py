import logging
import json
import os
from pathlib import Path
from typing import Dict

logger = logging.getLogger(__name__)

class TranslationClient:
    def __init__(self, glossary_path: str = None):
        if not glossary_path:
            base_dir = Path(__file__).parent.parent
            glossary_path = base_dir / "data" / "agri_glossary.json"
            
        self.glossary: Dict[str, Dict[str, str]] = {}
        try:
            with open(glossary_path, "r", encoding="utf-8") as f:
                self.glossary = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load glossary: {e}")

    async def translate(self, text: str, target_lang: str, retries: int = 2) -> str:
        """
        Translates text to the target language (e.g., 'hi', 'mr').
        Implements basic retry/fallback if the translation API fails.
        """
        if target_lang == "en":
            return text
            
        # 1. Attempt API translation with retries
        translated_text = None
        for attempt in range(retries + 1):
            try:
                # Mock API call to Bhashini/GCP
                translated_text = self._mock_api_call(text, target_lang)
                break # Success
            except Exception as e:
                logger.warning(f"Translation API attempt {attempt+1} failed: {e}")
                
        # 2. Fallback to English if API completely fails
        if not translated_text:
            logger.error(f"Translation to {target_lang} failed after {retries} retries. Falling back to English.")
            return text
            
        # 3. Fine-tuning: Post-process with agri glossary
        return self._apply_glossary(translated_text, target_lang)

    def _mock_api_call(self, text: str, target_lang: str) -> str:
        """Mocks a successful translation."""
        # For MVP testing, if "simulate_failure" is in text, raise Exception
        if "simulate_failure" in text:
            raise ConnectionError("Mock Bhashini API timeout")
            
        # In a real app, this would be a httpx.AsyncClient post to Bhashini
        if target_lang == "hi":
            return f"[HI] {text}"
        elif target_lang == "mr":
            return f"[MR] {text}"
        return text

    def _apply_glossary(self, text: str, target_lang: str) -> str:
        """Replaces english domain words in the translated text with specific local terms if they accidentally leaked, or just formats them."""
        # Since our mock translation just prepends [LANG], let's actually swap english words found in the text for demonstration
        glossary_key = f"en_to_{target_lang}"
        if glossary_key not in self.glossary:
            return text
            
        dict_map = self.glossary[glossary_key]
        for en_word, local_word in dict_map.items():
            # Basic replacement
            text = text.replace(en_word, local_word)
            text = text.replace(en_word.capitalize(), local_word)
            
        return text
