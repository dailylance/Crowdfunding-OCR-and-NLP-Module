import sys
import os
sys.path.append('d:/Codes/freelance/crowdfunding-ocr')

from ocr_service.services.ocr_service import run_ocr

# Test with a simulated Japanese product image scenario
# Let's create a mock test to see what's happening

def test_ocr_with_mock_data():
    """
    Test the OCR function to see where the issue might be occurring
    """
    
    # Let's create a simple test with some text that should be corrected
    import io
    from PIL import Image, ImageDraw, ImageFont
    
    # Create a simple test image with "Half 64,800"
    img = Image.new('RGB', (400, 100), color='white')
    draw = ImageDraw.Draw(img)
    
    # Try to use a font (fallback to default if not available)
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()
    
    # Draw the problematic text
    draw.text((10, 30), "Half 64,800", fill='black', font=font)
    draw.text((10, 60), "Red AirVision M+", fill='black', font=font)
    
    # Convert to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes = img_bytes.getvalue()
    
    print("Testing OCR with synthetic image containing 'Half 64,800'...")
    
    # Test the OCR function
    result = run_ocr(img_bytes, language="ja", translate_to_english=False)
    
    print("OCR Result:")
    print(f"Original text: {result['original_text']}")
    print(f"English text: {result['english_text']}")
    print(f"OCR successful: {result['ocr_successful']}")
    print(f"Total results: {result['total_results_found']}")
    
    # Check if the correction worked
    if "Half" in result['original_text']:
        print("❌ ISSUE FOUND: 'Half' still present in output!")
    else:
        print("✅ 'Half' was correctly replaced")
        
    if "¥" in result['original_text']:
        print("✅ Yen symbol found in output")
    else:
        print("❌ No yen symbol found in output")

if __name__ == "__main__":
    test_ocr_with_mock_data()
