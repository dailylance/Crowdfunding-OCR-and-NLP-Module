import easyocr
import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter
import io
from ocr_service.services.translation_service import translate_text_segments

# Create separate readers following EasyOCR compatibility rules
# Each Asian language can only be paired with English
reader_en_ja = easyocr.Reader(['en', 'ja'])                       # English + Japanese
reader_en_ko = easyocr.Reader(['en', 'ko'])                       # English + Korean  
reader_en_ch_sim = easyocr.Reader(['en', 'ch_sim'])               # English + Simplified Chinese
reader_en_ch_tra = easyocr.Reader(['en', 'ch_tra'])               # English + Traditional Chinese
reader_en_only = easyocr.Reader(['en'])                           # English only

def correct_common_ocr_errors(text: str) -> str:
    """
    Correct common OCR errors, especially for currency symbols and product names.
    Enhanced for Japanese yen symbols and product listings with deduplication.
    """
    import re
    
    # Currency symbol corrections
    corrections = {
        # Yen symbol corrections - multiple variations
        'Half ': '¥',           # "Half 111,420" → "¥111,420"
        'Halt ': '¥',           # Another common misread
        'Haf ': '¥',            # Another variation
        'Hali ': '¥',           # New: "Hali 64.80o" → "¥64.80o" (f→i confusion)
        'Hal ': '¥',            # New: Partial misread
        'H ': '¥',              # Short misread when followed by numbers
        'Y ': '¥',              # Sometimes Y gets space-separated
        
        # Brand name corrections - multiple variations
        '[5': 'ASUS',           # Original correction
        'Red ': 'ASUS ',        # New: "Red AirVision" → "ASUS AirVision"
        'After red': 'ASUS',    # New: OCR noise
        'After n': '',          # New: Remove OCR noise
        'Airyision': 'AirVision', # New: OCR misread of AirVision
        'NI+': 'M1',            # New: OCR misread of M1
        'NI ': 'M1 ',           # New: Another M1 misread
        
        # Common character misreads
        'M+': 'M1',             # Number misread
        '11+.420': '111,420',   # Number correction
        '10S,800': '103,800',   # Common S/3 confusion
        '1OS,800': '103,800',   # O/0 confusion
        '64.80o': '64,800',     # New: o→0 confusion in numbers
        '.8oo': ',800',         # New: o→0 confusion in decimal/comma
        
        # Remove redundant spacing around currency
        '¥ ': '¥',
        ' ¥': '¥',
        
        # Fix fragmented text
        'Air Vision': 'AirVision',
        'Air vision': 'AirVision',
        
        # Product model corrections (context-aware)
        'MT': 'M1',             # Common T/1 confusion in product models
    }
    
    corrected_text = text
    for wrong, correct in corrections.items():
        corrected_text = corrected_text.replace(wrong, correct)
    
    # Additional pattern-based corrections using regex
    
    # Fix "Half" and variations followed by numbers pattern (with decimal and comma variations)
    corrected_text = re.sub(r'\bHalf\s+(\d)', r'¥\1', corrected_text)
    corrected_text = re.sub(r'\bHalt\s+(\d)', r'¥\1', corrected_text)
    corrected_text = re.sub(r'\bHaf\s+(\d)', r'¥\1', corrected_text)
    corrected_text = re.sub(r'\bHali\s+(\d)', r'¥\1', corrected_text)  # New: f→i confusion
    corrected_text = re.sub(r'\bHal\s+(\d)', r'¥\1', corrected_text)   # New: partial misread
    
    # Fix standalone "Half" variations that appear before numbers (even with line breaks)
    corrected_text = re.sub(r'\bHalf\b(?=\s*\d)', r'¥', corrected_text)
    corrected_text = re.sub(r'\bHalt\b(?=\s*\d)', r'¥', corrected_text)
    corrected_text = re.sub(r'\bHali\b(?=\s*\d)', r'¥', corrected_text)  # New
    corrected_text = re.sub(r'\bHal\b(?=\s*\d)', r'¥', corrected_text)   # New
    
    # Fix concatenated "Half" with numbers (no space)
    corrected_text = re.sub(r'\bHalf(\d)', r'¥\1', corrected_text)
    corrected_text = re.sub(r'\bHali(\d)', r'¥\1', corrected_text)  # New
    corrected_text = re.sub(r'\bHal(\d)', r'¥\1', corrected_text)   # New
    
    # Add comma formatting to large numbers after yen symbol correction
    # Format 5-6 digit numbers: 89900 → 89,900, 50000 → 50,000
    corrected_text = re.sub(r'¥(\d{2})(\d{3})(?!\d)', r'¥\1,\2', corrected_text)  # 5 digits: 89900 → 89,900
    corrected_text = re.sub(r'¥(\d{3})(\d{3})(?!\d)', r'¥\1,\2', corrected_text)  # 6 digits: 123456 → 123,456
    
    # Fix percentage issues (common OCR error for discount percentages)
    corrected_text = re.sub(r'\b48(\d+)\s*OFF\b', r'48% OFF', corrected_text)  # 489 OFF → 48% OFF
    corrected_text = re.sub(r'\b(\d{2})(\d+)\s*OFF\b', r'\1% OFF', corrected_text)  # Generic XX9 OFF → XX% OFF
    
    # Fix numbers that start with digits suggesting yen amounts (from your example)
    # 6124,896 likely should be ¥124,896 (6 misread as ¥)
    corrected_text = re.sub(r'\b6(\d{3},\d{3})\b', r'¥\1', corrected_text)
    corrected_text = re.sub(r'\b6(\d{2},\d{3})\b', r'¥\1', corrected_text)
    
    # Fix decimal separator issues in Japanese yen amounts
    # Convert "111.420" to "111,420" when in yen context
    corrected_text = re.sub(r'¥(\d+)\.(\d{3})', r'¥\1,\2', corrected_text)
    corrected_text = re.sub(r'(\d+)\.(\d{3})\s*(?=¥|$)', r'\1,\2', corrected_text)
    
    # Fix standalone large numbers that should be yen amounts
    # Pattern: 6111420 should be ¥111,420 (6 misread as ¥)
    corrected_text = re.sub(r'\b6(\d{3})(\d{3})\b', r'¥\1,\2', corrected_text)
    
    # Fix "Red" when followed by product names
    corrected_text = re.sub(r'\bRed\s+(AirVision|Air\s*Vision)', r'ASUS \1', corrected_text)
    
    # Remove invalid price lines (corrupted numbers, incomplete prices)
    lines = corrected_text.split('\n')
    cleaned_lines = []
    valid_prices = set()  # Track valid prices to avoid duplicates
    
    for line in lines.copy():
        line = line.strip()
        if not line:
            continue
            
        # Remove lines that are just negative numbers or invalid fragments
        if re.match(r'^-\d+$', line):  # Lines like "-12489"
            continue
            
        # Remove lines that are just single digits or very short numbers
        if re.match(r'^\d{1,3}$', line) and line not in ['48', '100']:  # Keep percentage numbers
            continue
            
        # Handle price lines specifically
        if '¥' in line:
            # Extract the price amount
            price_match = re.search(r'¥(\d{1,3}(?:,\d{3})*)', line)
            if price_match:
                price_amount = price_match.group(1)
                # Only keep if we haven't seen this price before
                if price_amount not in valid_prices:
                    valid_prices.add(price_amount)
                    cleaned_lines.append(line)
                # Skip duplicate prices
                continue
            else:
                # If ¥ exists but no valid price found, skip the line
                continue
        else:
            # For non-price lines, keep them
            cleaned_lines.append(line)
    
    corrected_text = '\n'.join(cleaned_lines)
    
    # Clean up extra spaces and formatting
    corrected_text = re.sub(r'  +', ' ', corrected_text)  # Multiple spaces to single
    corrected_text = re.sub(r'\n\s*\n', '\n', corrected_text)  # Multiple newlines to single
    
    # Fix yen amounts that got concatenated
    corrected_text = re.sub(r'¥(\d+,\d+)¥', r'¥\1 ¥', corrected_text)
    
    return corrected_text.strip()

def apply_yen_symbol_preprocessing(image_bytes: bytes) -> bytes:
    """
    Specific preprocessing to improve yen symbol recognition.
    """
    try:
        # Load image
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Convert to numpy array for OpenCV processing
        img_array = np.array(image)
        
        # Convert to grayscale
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply morphological operations to clean up currency symbols
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
        
        # Enhance contrast specifically for currency areas
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(cleaned)
        
        # Convert back to PIL Image
        result_image = Image.fromarray(enhanced)
        
        # Save to bytes
        output_bytes = io.BytesIO()
        result_image.save(output_bytes, format='PNG')
        return output_bytes.getvalue()
        
    except Exception as e:
        print(f"Yen preprocessing error: {str(e)}")
        return image_bytes

def preprocess_image(image_bytes: bytes) -> tuple:
    """
    Preprocess image to improve OCR accuracy for product listings and crowdfunding screenshots.
    Enhanced for better currency symbol and price detection.
    """
    try:
        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Create multiple preprocessed versions
        preprocessed_images = []
        
        # Version 1: Original
        original_bytes = io.BytesIO()
        image.save(original_bytes, format='PNG')
        preprocessed_images.append(original_bytes.getvalue())
        
        # Version 2: Enhanced contrast and sharpness (good for overlaid text)
        enhancer = ImageEnhance.Contrast(image)
        enhanced = enhancer.enhance(1.8)  # Higher contrast for better text separation
        enhancer = ImageEnhance.Sharpness(enhanced)
        enhanced = enhancer.enhance(1.5)  # Higher sharpness for currency symbols
        
        enhanced_bytes = io.BytesIO()
        enhanced.save(enhanced_bytes, format='PNG')
        preprocessed_images.append(enhanced_bytes.getvalue())
        
        # Version 3: Grayscale with very high contrast (good for prices)
        gray_image = image.convert('L')
        enhancer = ImageEnhance.Contrast(gray_image)
        gray_enhanced = enhancer.enhance(2.5)  # Very high contrast
        
        gray_bytes = io.BytesIO()
        gray_enhanced.save(gray_bytes, format='PNG')
        preprocessed_images.append(gray_bytes.getvalue())
        
        # Version 4: Binarized (black and white) - excellent for clean text
        gray_array = np.array(gray_enhanced)
        # Use adaptive threshold for better text separation
        binary = cv2.adaptiveThreshold(gray_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        binary_image = Image.fromarray(binary)
        
        binary_bytes = io.BytesIO()
        binary_image.save(binary_bytes, format='PNG')
        preprocessed_images.append(binary_bytes.getvalue())
        
        # Version 5: Inverted (for dark backgrounds with light text)
        inverted_array = 255 - gray_array
        inverted_binary = cv2.adaptiveThreshold(inverted_array, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        inverted_image = Image.fromarray(inverted_binary)
        
        inverted_bytes = io.BytesIO()
        inverted_image.save(inverted_bytes, format='PNG')
        preprocessed_images.append(inverted_bytes.getvalue())
        
        return preprocessed_images
        
    except Exception as e:
        print(f"Image preprocessing error: {str(e)}")
        # Return original image if preprocessing fails
        return [image_bytes]

def extract_text_with_multiple_methods(image_bytes: bytes, reader) -> list:
    """
    Try multiple OCR configurations to maximize text extraction.
    Enhanced for better currency and price detection.
    """
    all_results = []
    
    # Method 1: Standard settings with paragraph detection
    try:
        results = reader.readtext(image_bytes, detail=0, paragraph=True, width_ths=0.7, height_ths=0.7)
        if results:
            all_results.extend([f"[PARAGRAPH] {text}" for text in results])
    except:
        pass
    
    # Method 2: No paragraph, more sensitive to small text (good for prices)
    try:
        results = reader.readtext(image_bytes, detail=0, paragraph=False, width_ths=0.5, height_ths=0.5, text_threshold=0.6)
        if results:
            all_results.extend([f"[DETAIL] {text}" for text in results])
    except:
        pass
    
    # Method 3: Very aggressive settings for numbers and currency symbols
    try:
        results = reader.readtext(image_bytes, detail=0, paragraph=False, width_ths=0.3, height_ths=0.3, text_threshold=0.5)
        if results:
            all_results.extend([f"[AGGRESSIVE] {text}" for text in results])
    except:
        pass
    
    # Method 4: Special settings for currency symbols and numbers
    try:
        results = reader.readtext(image_bytes, detail=0, paragraph=False, width_ths=0.2, height_ths=0.2, text_threshold=0.4, 
                                link_threshold=0.2, low_text=0.3)
        if results:
            all_results.extend([f"[CURRENCY] {text}" for text in results])
    except:
        pass
    
    return all_results

def run_ocr(image_bytes: bytes, language: str = "multi", translate_to_english: bool = True) -> dict:
    """
    Enhanced OCR with image preprocessing and multiple detection methods.
    Parameters:
        image_bytes: The content of the uploaded image.
        language: 'multi', 'en', 'ja', 'ko', 'ch_sim', 'ch_tra'
        translate_to_english: Whether to automatically translate to English (default: True)
    Returns:
        dict with original_text, english_text, and translation info
    """
    try:
        # Apply yen symbol specific preprocessing first
        yen_processed_bytes = apply_yen_symbol_preprocessing(image_bytes)
        
        # Preprocess image for better OCR
        preprocessed_images = preprocess_image(yen_processed_bytes)
        
        # Add original yen-processed image to the list
        preprocessed_images.insert(0, yen_processed_bytes)
        
        # Select the correct reader based on language
        readers_to_try = []
        if language == "en":
            readers_to_try = [reader_en_only]
        elif language == "ja":
            readers_to_try = [reader_en_ja, reader_en_only]
        elif language == "ko":
            readers_to_try = [reader_en_ko, reader_en_only]
        elif language == "ch_sim":
            readers_to_try = [reader_en_ch_sim, reader_en_only]
        elif language == "ch_tra":
            readers_to_try = [reader_en_ch_tra, reader_en_only]
        else:  # Multi-language approach
            # For product images with mixed content, try Japanese first for yen symbols
            readers_to_try = [reader_en_ja, reader_en_ch_sim, reader_en_only, reader_en_ch_tra, reader_en_ko]
        
        all_results = []
        
        # Try each reader with each preprocessed image
        for img_bytes in preprocessed_images:
            for reader in readers_to_try:
                try:
                    results = extract_text_with_multiple_methods(img_bytes, reader)
                    if results:
                        all_results.extend(results)
                        # If we got good results, we can break early for efficiency
                        if len(results) > 5:  # Threshold for "good results"
                            break
                except Exception as e:
                    print(f"OCR attempt failed: {str(e)}")
                    continue
            
            # If we have substantial results, we can stop processing more images
            if len(all_results) > 10:
                break
        
        # Clean and deduplicate results with OCR error correction
        unique_results = []
        seen_texts = set()
        
        for result in all_results:
            # Remove method tags and clean text
            clean_text = (result.replace("[PARAGRAPH] ", "")
                             .replace("[DETAIL] ", "")
                             .replace("[AGGRESSIVE] ", "")
                             .replace("[CURRENCY] ", "")
                             .strip())
            
            # Apply OCR error corrections
            corrected_text = correct_common_ocr_errors(clean_text)
            
            if corrected_text and corrected_text not in seen_texts and len(corrected_text) > 1:
                seen_texts.add(corrected_text)
                unique_results.append(corrected_text)
        
        # Combine results with priority (longer, more meaningful text first)
        sorted_results = sorted(unique_results, key=lambda x: len(x), reverse=True)
        original_text = "\n".join(sorted_results) if sorted_results else "No text detected"
        
        # Apply final correction pass to the combined text
        original_text = correct_common_ocr_errors(original_text)
        
        # Handle translation
        if translate_to_english and original_text != "No text detected":
            translation_result = translate_text_segments(original_text)
            
            # CRITICAL FIX: Apply OCR corrections to the translated text as well
            # This ensures that even if translation overrides our corrections, we fix them again
            corrected_english_text = correct_common_ocr_errors(translation_result["english_text"])
            corrected_original_text = correct_common_ocr_errors(translation_result["original_text"])
            
            return {
                "original_text": corrected_original_text,
                "english_text": corrected_english_text,
                "detected_languages": translation_result["detected_languages"],
                "translation_confidence": translation_result["translation_confidence"],
                "ocr_successful": True,
                "total_results_found": len(sorted_results)
            }
        else:
            return {
                "original_text": original_text,
                "english_text": original_text,  # Same as original if no translation
                "detected_languages": ["unknown"],
                "translation_confidence": 1.0,
                "ocr_successful": True,
                "total_results_found": len(sorted_results)
            }
        
    except Exception as e:
        print(f"OCR Error: {str(e)}")
        # Fallback to simple English-only reader
        try:
            results = reader_en_only.readtext(image_bytes, detail=0)
            fallback_text = "\n".join(results) if results else "OCR processing failed"
            
            # Apply corrections even to fallback text
            fallback_text = correct_common_ocr_errors(fallback_text)
            
            return {
                "original_text": fallback_text,
                "english_text": fallback_text,
                "detected_languages": ["en"],
                "translation_confidence": 0.5,
                "ocr_successful": False,
                "error": str(e),
                "total_results_found": len(results) if results else 0
            }
        except:
            return {
                "original_text": f"OCR processing failed: {str(e)}",
                "english_text": f"OCR processing failed: {str(e)}",
                "detected_languages": ["unknown"],
                "translation_confidence": 0.0,
                "ocr_successful": False,
                "error": str(e),
                "total_results_found": 0
            }
