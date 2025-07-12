#!/usr/bin/env python3
"""
Debug the actual English translation in the OCR service endpoint
"""

import requests
import json

# Test the enhance-crowdfunding endpoint with actual Japanese data
test_data = {
    "project_data": {
        "title": "COLO GCS｜自宅で極上のエンタメ体験！超没入型360°サラウンドスピーカー",
        "description": "次世代のPC向け360°サラウンドスピーカーシステム、◢◤COLO GCS◢◤（コロ ジーシーエス）",
        "project_owner": "COLO LIGHT事務局",
        "image_url": "https://images.greenfunding.jp/store/005ca9a09fbddf9f69ce38d373440da1d67797530c4889234876de9a495a"
    },
    "missing_fields": ["title", "description", "project_owner"],
    "images": [
        {
            "url": "https://images.greenfunding.jp/store/005ca9a09fbddf9f69ce38d373440da1d67797530c4889234876de9a495a",
            "alt": "Main project image",
            "width": 800,
            "height": 600,
            "source": "project_data"
        }
    ]
}

print("=== Testing OCR Service enhance-crowdfunding Endpoint ===")
print(f"Input data: {json.dumps(test_data, indent=2, ensure_ascii=False)}")
print("")

try:
    response = requests.post(
        "http://localhost:5000/v1/enhance-crowdfunding",
        json=test_data,
        timeout=60
    )
    
    if response.status_code == 200:
        result = response.json()
        print("✅ OCR Service Response:")
        print(f"Success: {result.get('success')}")
        print("")
        
        if result.get('enhanced_data_english'):
            print("📝 Enhanced Data English:")
            english_data = result['enhanced_data_english']
            print(f"Title: {english_data.get('title', 'N/A')}")
            print(f"Description: {english_data.get('description', 'N/A')}")
            print(f"Project Owner: {english_data.get('project_owner', 'N/A')}")
            print("")
            
        if result.get('enhanced_data_original'):
            print("📝 Enhanced Data Original:")
            original_data = result['enhanced_data_original']
            print(f"Title: {original_data.get('title', 'N/A')}")
            print(f"Description: {original_data.get('description', 'N/A')}")
            print(f"Project Owner: {original_data.get('project_owner', 'N/A')}")
            print("")
            
        print("🔍 Full Response Structure:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    else:
        print(f"❌ Request failed with status {response.status_code}")
        print(f"Response: {response.text}")
        
except Exception as e:
    print(f"❌ Error: {e}")
