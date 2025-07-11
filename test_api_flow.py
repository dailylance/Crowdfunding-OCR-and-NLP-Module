import sys
import os
sys.path.append('d:/Codes/freelance/crowdfunding-ocr')

from ocr_service.services.ocr_service import run_ocr
import io
from PIL import Image, ImageDraw, ImageFont

def test_api_flow():
    """Test the exact API flow that's causing the issue"""
    
    # Create a test image similar to your Japanese product image
    img = Image.new('RGB', (400, 200), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    
    # Draw text that should trigger our corrections
    draw.text((10, 30), "Early bird price 48% OFF", fill='black', font=font)
    draw.text((10, 60), "¥124,896", fill='black', font=font)
    draw.text((10, 90), "Half 64,800", fill='black', font=font)  # This should be corrected
    draw.text((10, 120), "48% OFF", fill='black', font=font)
    draw.text((10, 150), "Early Bill Price", fill='black', font=font)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    print("🧪 TESTING EXACT API FLOW")
    print("=" * 60)
    
    # Test the OCR function exactly as the API calls it
    print("1. Testing run_ocr with translate_to_english=True (API default):")
    result_translated = run_ocr(img_bytes, language="multi", translate_to_english=True)
    
    print(f"   Original text: {repr(result_translated['original_text'])}")
    print(f"   English text:  {repr(result_translated['english_text'])}")
    print(f"   Languages:     {result_translated['detected_languages']}")
    print(f"   Confidence:    {result_translated['translation_confidence']}")
    
    # Check for issues
    print("\n2. Issue Analysis:")
    if "Half" in result_translated['english_text']:
        print("   ❌ 'Half' still present in english_text (this is what API returns!)")
    else:
        print("   ✅ 'Half' correctly replaced in english_text")
        
    if "Half" in result_translated['original_text']:
        print("   ❌ 'Half' still present in original_text")
    else:
        print("   ✅ 'Half' correctly replaced in original_text")
    
    print("\n3. Testing run_ocr with translate_to_english=False:")
    result_no_translate = run_ocr(img_bytes, language="multi", translate_to_english=False)
    
    print(f"   Original text: {repr(result_no_translate['original_text'])}")
    print(f"   English text:  {repr(result_no_translate['english_text'])}")
    
    if "Half" in result_no_translate['original_text']:
        print("   ❌ 'Half' still present (correction not working)")
    else:
        print("   ✅ 'Half' correctly replaced (correction working)")
    
    print("\n" + "=" * 60)
    print("🎯 ROOT CAUSE ANALYSIS:")
    
    if "Half" in result_translated['english_text'] and "Half" not in result_no_translate['original_text']:
        print("   🔍 ISSUE: Translation service is overriding OCR corrections!")
        print("   💡 SOLUTION: Apply corrections AFTER translation, not before")
    elif "Half" in result_no_translate['original_text']:
        print("   🔍 ISSUE: OCR corrections are not being applied at all")
        print("   💡 SOLUTION: Fix the correction function application")
    else:
        print("   ✅ All corrections working properly")

if __name__ == "__main__":
    test_api_flow()
