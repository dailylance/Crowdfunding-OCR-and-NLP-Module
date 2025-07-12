from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from ocr_service.models.schemas import NLPResponse
from ocr_service.services.ocr_service import run_ocr
from ocr_service.services.nlp_service import parse_text, extract_crowdfunding_data
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import json
import os
import requests
from datetime import datetime
from PIL import Image
from io import BytesIO
import re

router = APIRouter()

# Pydantic models for the new endpoint
class ImageInfo(BaseModel):
    url: str
    alt: str = ""
    width: int = 0
    height: int = 0

class CrowdfundingEnhancementRequest(BaseModel):
    project_data: Dict[str, Any]
    images: List[ImageInfo]
    missing_fields: List[str]

@router.get("/health")
async def health_check():
    return {"status": "healthy", "message": "OCR service is running"}

@router.post("/ocr")
async def ocr_endpoint(file: UploadFile = File(...), translate: bool = True, show_original: bool = False):
    """
    OCR endpoint with automatic English translation
    Parameters:
    - translate: Whether to translate to English (default: True)
    - show_original: Whether to include original text in response (default: False)
    """
    try:
        print(f"Received file: {file.filename}, content_type: {file.content_type}")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        content = await file.read()
        print(f"File size: {len(content)} bytes")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file provided")
        
        ocr_result = run_ocr(content, language="multi", translate_to_english=translate)
        
        # Prepare response based on user preference
        response = {
            "text": ocr_result["english_text"],  # Default to English
            "detected_languages": ocr_result["detected_languages"],
            "translation_confidence": ocr_result["translation_confidence"],
            "ocr_successful": ocr_result["ocr_successful"]
        }
        
        # Include original text only if requested
        if show_original:
            response["original_text"] = ocr_result["original_text"]
        
        return response
        
    except Exception as e:
        print(f"Error in OCR endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR processing failed: {str(e)}")

@router.post("/parse-ocr")
async def parse_ocr_endpoint(file: UploadFile = File(...), translate: bool = True, show_original: bool = False):
    """
    OCR + NLP parsing endpoint with automatic English translation
    Parameters:
    - translate: Whether to translate to English (default: True)
    - show_original: Whether to include original text in response (default: False)
    """
    try:
        print(f"Received file: {file.filename}, content_type: {file.content_type}")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        content = await file.read()
        print(f"File size: {len(content)} bytes")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file provided")
        
        ocr_result = run_ocr(content, language="multi", translate_to_english=translate)
        structured = parse_text(ocr_result)
        
        response = {"structured_data": structured}
        
        # Include original text only if requested
        if show_original:
            response["original_text"] = ocr_result["original_text"]
            response["english_text"] = ocr_result["english_text"]
        
        return response
        
    except Exception as e:
        print(f"Error in parse-OCR endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"OCR parsing failed: {str(e)}")

@router.post("/test-upload")
async def test_upload(file: UploadFile = File(...)):
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(await file.read())
    }

@router.post("/extract-crowdfunding")
async def extract_crowdfunding_endpoint(file: UploadFile = File(...), translate: bool = True, show_original: bool = False):
    """
    Enhanced endpoint for extracting detailed crowdfunding information
    with automatic English translation and saving results to JSON file
    Parameters:
    - translate: Whether to translate to English (default: True)
    - show_original: Whether to include original text in response (default: False)
    """
    try:
        print(f"Processing crowdfunding data from: {file.filename}")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        content = await file.read()
        print(f"File size: {len(content)} bytes")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file provided")
        
        # Extract text using multi-language OCR with translation
        ocr_result = run_ocr(content, language="multi", translate_to_english=translate)
        print(f"Extracted text length: {len(ocr_result['english_text'])} characters")
        
        # Extract detailed crowdfunding data
        crowdfunding_data = extract_crowdfunding_data(ocr_result)
        
        # Create results directory if it doesn't exist
        results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "results")
        os.makedirs(results_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crowdfunding_data_{timestamp}.json"
        filepath = os.path.join(results_dir, filename)
        
        # Prepare data for JSON file
        json_data = {
            "extracted_text": ocr_result["english_text"],  # Always save English version
            "crowdfunding_data": crowdfunding_data,
            "processing_info": {
                "source_file": file.filename,
                "processed_at": datetime.now().isoformat(),
                "file_size_bytes": len(content),
                "detected_languages": ocr_result["detected_languages"],
                "translation_confidence": ocr_result["translation_confidence"],
                "translation_used": translate
            }
        }
        
        # Include original text in JSON if it's different from English
        if ocr_result["original_text"] != ocr_result["english_text"]:
            json_data["original_text"] = ocr_result["original_text"]
        
        # Save to JSON file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, indent=2, ensure_ascii=False)
        
        # Prepare response
        response = {
            "success": True,
            "crowdfunding_data": crowdfunding_data,
            "saved_to": filepath,
            "extracted_text_preview": ocr_result["english_text"][:500] + "..." if len(ocr_result["english_text"]) > 500 else ocr_result["english_text"],
            "detected_languages": ocr_result["detected_languages"],
            "translation_confidence": ocr_result["translation_confidence"]
        }
        
        # Include original text only if requested
        if show_original and ocr_result["original_text"] != ocr_result["english_text"]:
            response["original_text_preview"] = ocr_result["original_text"][:500] + "..." if len(ocr_result["original_text"]) > 500 else ocr_result["original_text"]
        
        return response
        
    except Exception as e:
        print(f"Error in crowdfunding extraction endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Crowdfunding extraction failed: {str(e)}")

@router.post("/debug-ocr")
async def debug_ocr_endpoint(file: UploadFile = File(...), translate: bool = True, show_original: bool = True):
    """
    Debug OCR endpoint that shows detailed extraction information
    This helps troubleshoot OCR issues by showing all intermediate results
    """
    try:
        print(f"DEBUG: Processing file: {file.filename}")
        
        if not file:
            raise HTTPException(status_code=400, detail="No file provided")
        
        content = await file.read()
        print(f"DEBUG: File size: {len(content)} bytes")
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file provided")
        
        # Get detailed OCR results
        ocr_result = run_ocr(content, language="multi", translate_to_english=translate)
        
        # Extract crowdfunding data
        crowdfunding_data = extract_crowdfunding_data(ocr_result)
        
        # Prepare detailed debug response
        response = {
            "debug_info": {
                "file_name": file.filename,
                "file_size_bytes": len(content),
                "total_ocr_results_found": ocr_result.get("total_results_found", 0),
                "ocr_successful": ocr_result["ocr_successful"],
                "detected_languages": ocr_result["detected_languages"],
                "translation_confidence": ocr_result["translation_confidence"],
                "extraction_confidence": crowdfunding_data.get("extraction_confidence", 0.0),
                "raw_text_length": len(ocr_result["english_text"])
            },
            "extracted_text": {
                "english_text": ocr_result["english_text"],
                "english_text_preview": ocr_result["english_text"][:1000] + "..." if len(ocr_result["english_text"]) > 1000 else ocr_result["english_text"]
            },
            "crowdfunding_data": crowdfunding_data,
            "extraction_tips": {
                "message": "If key information is missing, try:",
                "suggestions": [
                    "1. Ensure the image is clear and high resolution",
                    "2. Check if the text is clearly visible in the image", 
                    "3. Make sure funding amounts, percentages, and dates are readable",
                    "4. Verify the crowdfunding platform name is visible",
                    "5. Consider cropping the image to focus on key information"
                ]
            }
        }
        
        # Include original text if requested
        if show_original and ocr_result["original_text"] != ocr_result["english_text"]:
            response["extracted_text"]["original_text"] = ocr_result["original_text"]
            response["extracted_text"]["original_text_preview"] = ocr_result["original_text"][:1000] + "..." if len(ocr_result["original_text"]) > 1000 else ocr_result["original_text"]
        
        return response
        
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Debug OCR failed: {str(e)}")

@router.post("/enhance-crowdfunding")
async def enhance_crowdfunding(request: CrowdfundingEnhancementRequest):
    """
    Enhanced endpoint for crowdfunding data extraction from multiple images
    Takes project data and images, extracts missing information using OCR/NLP
    Returns both English and original language versions
    """
    try:
        project_data = request.project_data
        images = request.images
        missing_fields = request.missing_fields
        
        print(f"Enhancing project: {project_data.get('title', 'Unknown')}")
        print(f"Processing {len(images)} images for missing fields: {missing_fields}")
        
        enhanced_data_english = project_data.copy()
        enhanced_data_original = project_data.copy()
        confidence_scores = {}
        processed_images = 0
        
        # ALWAYS translate existing fields for language separation
        # Translate key fields from project_data for English version
        fields_to_translate = ['title', 'description', 'project_owner']
        for field in fields_to_translate:
            if field in project_data and project_data[field]:
                original_text = project_data[field]
                print(f"🌐 Translating field '{field}': {original_text[:50]}...")
                
                # Use translation service to get English version
                from ocr_service.services.translation_service import translate_to_english
                translation_result = translate_to_english(original_text)
                
                # Update English version with translation
                enhanced_data_english[field] = translation_result['english_text']
                confidence_scores[f"{field}_translation"] = translation_result['translation_confidence']
                
                print(f"✅ Translated '{field}': {translation_result['english_text'][:50]}...")
        
        # Process images for additional information extraction if needed
        
        for image_info in images:
            try:
                # Download and process image
                image_url = image_info.url
                print(f"📸 Processing image: {image_url}")
                
                response = requests.get(image_url, timeout=15, headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })
                
                if response.status_code == 200:
                    # Convert to PIL Image
                    image = Image.open(BytesIO(response.content))
                    
                    # Convert image to bytes for OCR processing
                    img_byte_arr = BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    img_bytes = img_byte_arr.getvalue()
                    
                    # Extract text using OCR with translation
                    ocr_result_english = run_ocr(img_bytes, language="multi", translate_to_english=True)
                    ocr_result_original = run_ocr(img_bytes, language="multi", translate_to_english=False)
                    
                    extracted_text_english = ocr_result_english.get('english_text', '')
                    extracted_text_original = ocr_result_original.get('original_text', '')
                    
                    if extracted_text_english.strip() or extracted_text_original.strip():
                        print(f"✅ Extracted English text length: {len(extracted_text_english)} characters")
                        print(f"✅ Extracted original text length: {len(extracted_text_original)} characters")
                        
                        # Extract missing information for English version
                        extracted_info_english = extract_crowdfunding_info_from_text(
                            extracted_text_english, 
                            missing_fields,
                            project_data.get('title', ''),
                            'en'
                        )
                        
                        # Extract missing information for original version
                        extracted_info_original = extract_crowdfunding_info_from_text(
                            extracted_text_original, 
                            missing_fields,
                            project_data.get('title', ''),
                            'original'
                        )
                        
                        # Update enhanced_data with extracted information
                        for field, value in extracted_info_english.items():
                            if field in missing_fields and value:
                                current_value = enhanced_data_english.get(field)
                                if not current_value or current_value in ['', '-', 'Unknown', 'N/A']:
                                    enhanced_data_english[field] = value
                                    confidence_scores[field] = 0.8
                                    print(f"📝 Enhanced English field '{field}': {value}")
                        
                        # Update original data with original language extraction
                        for field, value in extracted_info_original.items():
                            if field in missing_fields and value:
                                current_value = enhanced_data_original.get(field)
                                if not current_value or current_value in ['', '-', 'Unknown', 'N/A']:
                                    enhanced_data_original[field] = value
                                    print(f"📝 Enhanced original field '{field}': {value}")
                                    
                        processed_images += 1
                        
                else:
                    print(f"❌ Failed to download image: HTTP {response.status_code}")
                        
            except Exception as e:
                print(f"Error processing image {image_info.url}: {str(e)}")
                continue
        
        # Calculate overall confidence
        overall_confidence = len(confidence_scores) / len(missing_fields) if missing_fields else 1.0
        
        return {
            'success': True,
            'enhanced_data': enhanced_data_english,  # Main enhanced data (English)
            'enhanced_data_english': enhanced_data_english,  # Explicit English version
            'enhanced_data_original': enhanced_data_original,  # Original language version
            'confidence_scores': confidence_scores,
            'images_processed': processed_images,
            'fields_enhanced': list(confidence_scores.keys()),
            'overall_confidence': round(overall_confidence, 2),
            'processing_summary': {
                'total_images': len(images),
                'successfully_processed': processed_images,
                'fields_requested': len(missing_fields),
                'fields_enhanced': len(confidence_scores)
            }
        }
        
    except Exception as e:
        print(f"Error in enhance_crowdfunding: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'enhanced_data': request.project_data,
            'confidence_scores': {}
        }

def extract_crowdfunding_info_from_text(text, missing_fields, project_title, target_language):
    """Enhanced extraction for crowdfunding specific fields"""
    extracted = {}
    
    # Amount patterns (multiple currencies)
    if 'amount' in missing_fields or 'support_amount' in missing_fields:
        amount_patterns = [
            r'[\$¥€£₩]\s*[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*円',
            r'raised\s*[\$¥€£₩]\s*[\d,]+(?:\.\d{2})?',
            r'goal\s*[\$¥€£₩]\s*[\d,]+(?:\.\d{2})?',
            r'target\s*[\$¥€£₩]\s*[\d,]+(?:\.\d{2})?',
            r'[\d,]+(?:\.\d{2})?\s*(?:USD|EUR|JPY|KRW|GBP)',
        ]
        
        for pattern in amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                if 'amount' in missing_fields:
                    extracted['amount'] = matches[0]
                if 'support_amount' in missing_fields and len(matches) > 1:
                    extracted['support_amount'] = matches[1]
                break
    
    # Supporters/backers
    if 'supporters' in missing_fields:
        supporter_patterns = [
            r'(\d+)\s*(?:supporters?|backers?|people|supporters)',
            r'(\d+)\s*人(?:が支援|の支援者)',
            r'支援者\s*(\d+)',
            r'(\d+)\s*명\s*(?:의\s*)?후원자',
            r'(\d+)\s*位贊助者',
        ]
        
        for pattern in supporter_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted['supporters'] = match.group(1)
                break
    
    # Achievement rate
    if 'achievement_rate' in missing_fields:
        rate_patterns = [
            r'(\d+(?:\.\d+)?)\s*%\s*(?:達成|achieved|funded)',
            r'達成率\s*(\d+(?:\.\d+)?)\s*%',
            r'(\d+(?:\.\d+)?)\s*%\s*of\s*goal',
            r'목표\s*(\d+(?:\.\d+)?)\s*%\s*달성',
        ]
        
        for pattern in rate_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                extracted['achievement_rate'] = f"{match.group(1)}%"
                break
    
    # Email addresses
    if 'contact_info' in missing_fields:
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        if emails:
            extracted['contact_info'] = emails[0]
    
    # Project owner/creator
    if 'project_owner' in missing_fields:
        owner_patterns = [
            r'(?:by|created by|project by|made by)\s*([A-Za-z\s\-\.]+)',
            r'創作者[：:]\s*([^\n\r]+)',
            r'提案者[：:]\s*([^\n\r]+)',
            r'프로젝트\s*개설자[：:]\s*([^\n\r]+)',
            r'Creator[：:]\s*([^\n\r]+)',
        ]
        
        for pattern in owner_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                owner_name = match.group(1).strip()
                if len(owner_name) > 2 and len(owner_name) < 50:
                    extracted['project_owner'] = owner_name
                    break
    
    # Website URLs
    if 'owner_website' in missing_fields:
        url_patterns = [
            r'https?://(?:www\.)?[A-Za-z0-9\-\.]+\.[A-Za-z]{2,}(?:/[^\s]*)?',
            r'www\.[A-Za-z0-9\-\.]+\.[A-Za-z]{2,}(?:/[^\s]*)?',
        ]
        
        for pattern in url_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for url in matches:
                if not any(excluded in url.lower() for excluded in ['facebook', 'twitter', 'instagram', 'youtube']):
                    extracted['owner_website'] = url if url.startswith('http') else f'https://{url}'
                    break
            if 'owner_website' in extracted:
                break
    
    # Social media
    if 'owner_sns' in missing_fields:
        sns_patterns = [
            r'(?:facebook\.com|fb\.com)/([A-Za-z0-9\.]+)',
            r'(?:twitter\.com|x\.com)/([A-Za-z0-9_]+)',
            r'(?:instagram\.com)/([A-Za-z0-9_\.]+)',
            r'(?:youtube\.com/(?:c/|channel/|user/))([A-Za-z0-9_\-]+)'
        ]
        
        sns_links = []
        for pattern in sns_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            sns_links.extend(matches)
        
        if sns_links:
            extracted['owner_sns'] = ', '.join(sns_links[:3])
    
    # Dates (start and end dates)
    if 'crowdfund_start_date' in missing_fields or 'crowdfund_end_date' in missing_fields:
        date_patterns = [
            r'\d{4}[-/]\d{1,2}[-/]\d{1,2}',
            r'\d{1,2}[-/]\d{1,2}[-/]\d{4}',
            r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}',
            r'\d{4}年\d{1,2}月\d{1,2}日',
        ]
        
        dates = []
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            dates.extend(matches)
        
        if dates:
            unique_dates = list(set(dates))
            if 'crowdfund_start_date' in missing_fields:
                extracted['crowdfund_start_date'] = unique_dates[0]
            if 'crowdfund_end_date' in missing_fields and len(unique_dates) > 1:
                extracted['crowdfund_end_date'] = unique_dates[-1]
    
    return extracted
