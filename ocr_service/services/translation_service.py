from deep_translator import GoogleTranslator
import re
from typing import Dict, Tuple

def detect_language(text: str) -> str:
    """
    Simple language detection based on character patterns
    """
    try:
        # Simple pattern-based language detection
        if re.search(r'[\u4e00-\u9fff]', text):  # Chinese characters
            return 'zh'
        elif re.search(r'[\u3040-\u309f\u30a0-\u30ff]', text):  # Japanese hiragana/katakana
            return 'ja'
        elif re.search(r'[\uac00-\ud7af]', text):  # Korean
            return 'ko'
        elif re.search(r'[a-zA-Z]', text):  # Latin characters
            return 'en'
        else:
            return 'unknown'
    except:
        return 'unknown'

def translate_to_english(text: str) -> Dict[str, str]:
    """
    Translate text to English while preserving the original
    Returns both original and translated text
    """
    if not text or text.strip() == "":
        return {
            "original_text": text,
            "english_text": text,
            "detected_language": "unknown",
            "translation_confidence": 0.0
        }
    
    try:
        # Detect the language
        detected_lang = detect_language(text)
        
        # If already English, return as is
        if detected_lang == 'en' or not re.search(r'[\u4e00-\u9fff\u3040-\u309f\u30a0-\u30ff\uac00-\ud7af]', text):
            return {
                "original_text": text,
                "english_text": text,
                "detected_language": detected_lang,
                "translation_confidence": 1.0
            }
        
        # Try translation
        try:
            translator = GoogleTranslator(source='auto', target='en')
            english_text = translator.translate(text)
            confidence = 0.8
        except Exception as e:
            print(f"Translation failed: {e}")
            # If translation fails, return original
            return {
                "original_text": text,
                "english_text": text,
                "detected_language": detected_lang,
                "translation_confidence": 0.0
            }
        
        return {
            "original_text": text,
            "english_text": english_text,
            "detected_language": detected_lang,
            "translation_confidence": confidence
        }
        
    except Exception as e:
        print(f"Translation error: {str(e)}")
        return {
            "original_text": text,
            "english_text": text,
            "detected_language": "unknown",
            "translation_confidence": 0.0
        }

def translate_text_segments(text: str) -> Dict:
    """
    Translate text while preserving formatting and handling mixed languages
    """
    # Split text into lines to handle mixed language content better
    lines = text.split('\n')
    translated_lines = []
    original_lines = []
    
    detected_languages = set()
    total_confidence = 0
    translation_count = 0
    
    for line in lines:
        line = line.strip()
        if line:
            translation_result = translate_to_english(line)
            translated_lines.append(translation_result["english_text"])
            original_lines.append(translation_result["original_text"])
            detected_languages.add(translation_result["detected_language"])
            total_confidence += translation_result["translation_confidence"]
            translation_count += 1
        else:
            translated_lines.append("")
            original_lines.append("")
    
    avg_confidence = total_confidence / translation_count if translation_count > 0 else 0
    
    return {
        "original_text": '\n'.join(original_lines),
        "english_text": '\n'.join(translated_lines),
        "detected_languages": list(detected_languages),
        "translation_confidence": avg_confidence,
        "line_count": len([l for l in lines if l.strip()])
    }
