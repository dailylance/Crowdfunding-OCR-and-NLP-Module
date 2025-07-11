#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'ocr_service'))

from services.ocr_service import correct_common_ocr_errors

def test_ocr_corrections():
    print("=== Testing OCR Error Corrections ===")
    
    # Test the original problematic OCR output
    test_text = """Half 111,420 Half 103,800
[5 AirVision MT
AirVision MT
AirVision
Half 111,420
Half 103,800
Half 11+.420
7% OFF
OFF
[5
7%
M1
cs
MT"""
    
    print("Original OCR:")
    print(test_text)
    print("\n" + "="*50)
    
    corrected = correct_common_ocr_errors(test_text)
    print("Corrected OCR:")
    print(corrected)
    
    print("\n" + "="*50)
    print("Key corrections made:")
    corrections_made = []
    
    if "Half " in test_text and "¥" in corrected:
        corrections_made.append("✅ 'Half' → '¥' (Currency symbol)")
    if "[5" in test_text and "ASUS" in corrected:
        corrections_made.append("✅ '[5' → 'ASUS' (Brand name)")
    if "11+.420" in test_text and "111,420" in corrected:
        corrections_made.append("✅ '11+.420' → '111,420' (Number fix)")
    
    for correction in corrections_made:
        print(correction)
    
    # Test individual patterns
    print("\n=== Individual Pattern Tests ===")
    patterns = [
        "Half 111,420",
        "Half 103,800", 
        "[5 AirVision",
        "11+.420",
        "MT model",
        "Air Vision Pro"
    ]
    
    for pattern in patterns:
        corrected_pattern = correct_common_ocr_errors(pattern)
        print(f"'{pattern}' → '{corrected_pattern}'")

if __name__ == "__main__":
    test_ocr_corrections()
