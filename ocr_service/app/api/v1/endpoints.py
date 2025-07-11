from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from ocr_service.models.schemas import NLPResponse
from ocr_service.services.ocr_service import run_ocr
from ocr_service.services.nlp_service import parse_text, extract_crowdfunding_data
import logging
import json
import os
from datetime import datetime

router = APIRouter()

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
