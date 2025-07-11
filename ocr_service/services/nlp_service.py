import spacy
import re
from typing import Dict, List
from datetime import datetime

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

def clean_and_merge_text(raw_text: str) -> str:
    """
    Clean OCR text and merge related information for better extraction.
    """
    # Split into lines and clean
    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
    
    # Remove duplicate lines (common in OCR)
    unique_lines = []
    seen = set()
    for line in lines:
        if line.lower() not in seen:
            seen.add(line.lower())
            unique_lines.append(line)
    
    # Try to merge money amounts that might be split across lines
    merged_lines = []
    i = 0
    while i < len(unique_lines):
        current_line = unique_lines[i]
        
        # Check if current line might be part of a monetary amount
        if i < len(unique_lines) - 1:
            next_line = unique_lines[i + 1]
            
            # Merge cases like "$" on one line and "123,456" on the next
            if re.match(r'^[\$¥€£NT]$', current_line) and re.match(r'^[\d,]+$', next_line):
                merged_lines.append(current_line + next_line)
                i += 2
                continue
            
            # Merge cases like "123,456" and "$" or currency
            if re.match(r'^[\d,]+$', current_line) and re.match(r'^[\$¥€£NT].*', next_line):
                merged_lines.append(next_line + current_line)
                i += 2
                continue
        
        merged_lines.append(current_line)
        i += 1
    
    return '\n'.join(merged_lines)

def extract_enhanced_amounts(text: str) -> List[Dict]:
    """
    Enhanced monetary amount extraction with context - now supports more formats.
    """
    amounts = []
    
    # Enhanced money patterns with better currency support
    patterns = [
        # Crowdfunding specific patterns
        r'(?:goal|target|funding goal|目標|目标)[:\s]*([NT]?\$?[Y¥]?€?£?[\d,]+)',
        r'(?:raised|funded|current|現在|现在)[:\s]*([NT]?\$?[Y¥]?€?£?[\d,]+)',
        
        # Japanese Yen patterns (multiple formats)
        r'([¥Y][\d,]+)',           # ¥103,800 or Y103,800
        r'([\d,]+)\s*(?:yen|円|YEN)',  # 103,800 yen or 103,800円
        
        # Handle missing currency symbols - detect Y followed by numbers
        r'Y([\d,]+)',              # Y64,800 (missing ¥ symbol)
        r'([¥￥][\d,]+)',          # Full-width and regular yen
        
        # Other currency patterns
        r'([NT]?\$[\d,]+)',        # $123,456 or NT$123,456  
        r'(€[\d,]+)',              # €123,456
        r'(£[\d,]+)',              # £123,456
        r'(₹[\d,]+)',              # ₹123,456 (Indian Rupee)
        r'(₩[\d,]+)',              # ₩123,456 (Korean Won)
        r'(￥[\d,]+)',             # ￥123,456 (Full-width Yen)
        r'(CNY[\d,]+)',            # CNY123,456
        r'(HKD[\d,]+)',            # HKD123,456
        r'(SGD[\d,]+)',            # SGD123,456
        
        # Generic currency with context
        r'([\d,]+)\s*(?:dollars?|USD|usd)',  # 123,456 dollars
        r'([\d,]+)\s*(?:euros?|EUR|eur)',    # 123,456 euros
        r'([\d,]+)\s*(?:pounds?|GBP|gbp)',   # 123,456 pounds
        r'([\d,]+)\s*(?:rupees?|INR|inr)',   # 123,456 rupees
        r'([\d,]+)\s*(?:won|KRW|krw)',       # 123,456 won
        
        # Discount patterns
        r'(\d+)%\s*(?:off|OFF|discount)',     # 7% OFF
        r'(?:off|OFF|discount)[:\s]*(\d+)%',  # OFF: 7%
        
        # Generic number patterns with currency symbols (as fallback)
        r'([NT]?\$?[Y¥￥]?€?£?₹?₩?[\d,]+)(?:\s*(?:raised|funded|goal|target|price|cost|value))?',
    ]
    
    # Find all amounts with their context
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            amount_str = match.group(1) if match.groups() else match.group(0)
            
            # Extract numeric value
            numbers = re.findall(r'[\d,]+', amount_str)
            if numbers:
                try:
                    value = int(numbers[0].replace(',', ''))
                    
                    # Skip very small values that are likely not prices (like single digits)
                    if value < 10:
                        continue
                    
                    # Determine context from surrounding text
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end].lower()
                    
                    amount_type = "unknown"
                    if any(word in context for word in ['goal', 'target', '目標', '目标']):
                        amount_type = "goal"
                    elif any(word in context for word in ['raised', 'funded', 'current', '現在', '现在']):
                        amount_type = "current"
                    elif any(word in context for word in ['price', 'cost', 'value', '価格', '値段']):
                        amount_type = "price"
                    elif any(word in context for word in ['off', 'discount', '割引']):
                        amount_type = "discount"
                    
                    # Enhanced currency detection
                    currency = ""
                    if (any(symbol in amount_str for symbol in ["¥", "Y", "￥"]) or 
                        any(word in context for word in ["yen", "円", "jpy"]) or
                        # Special handling for Y prefix
                        amount_str.startswith('Y') and amount_str[1:].replace(',', '').isdigit()):
                        currency = "JPY"
                    elif "$" in amount_str or any(word in context for word in ["dollar", "usd"]):
                        currency = "USD" 
                    elif "€" in amount_str or any(word in context for word in ["euro", "eur"]):
                        currency = "EUR"
                    elif "£" in amount_str or any(word in context for word in ["pound", "gbp"]):
                        currency = "GBP"
                    elif "₹" in amount_str or any(word in context for word in ["rupee", "inr"]):
                        currency = "INR"
                    elif "₩" in amount_str or any(word in context for word in ["won", "krw"]):
                        currency = "KRW"
                    elif "NT" in amount_str:
                        currency = "TWD"
                    elif any(code in amount_str for code in ["CNY", "HKD", "SGD"]):
                        currency = amount_str[:3]  # Extract the currency code
                    elif any(word in context for word in ["cny", "yuan", "rmb"]):
                        currency = "CNY"
                    elif any(word in context for word in ["hkd", "hong kong"]):
                        currency = "HKD"
                    elif any(word in context for word in ["sgd", "singapore"]):
                        currency = "SGD"
                    
                    # Skip standalone numbers that look like product codes rather than prices
                    if (not currency and not any(char in amount_str for char in ['$', '¥', 'Y', '€', '£']) 
                        and value < 1000000 and len(str(value)) in [5, 6, 7]):
                        # This might be a product code rather than a price
                        continue
                    
                    amounts.append({
                        "value": value,
                        "formatted": amount_str,
                        "type": amount_type,
                        "currency": currency,
                        "context": context.strip()
                    })
                except:
                    continue
    
    # Sort by value descending and remove duplicates
    amounts = sorted(amounts, key=lambda x: x["value"], reverse=True)
    unique_amounts = []
    seen_values = set()
    for amt in amounts:
        if amt["value"] not in seen_values:
            seen_values.add(amt["value"])
            unique_amounts.append(amt)
    
    return unique_amounts

def extract_enhanced_dates(text: str) -> List[Dict]:
    """
    Enhanced date extraction with better pattern recognition.
    """
    dates = []
    
    # Multiple date patterns
    patterns = [
        r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})',  # MM/DD/YYYY or DD/MM/YYYY
        r'(\d{4})[/.-](\d{1,2})[/.-](\d{1,2})',  # YYYY/MM/DD
        r'(\d{1,2})\s+(\w+)\s+(\d{4})',          # DD Month YYYY
        r'(\w+)\s+(\d{1,2}),?\s+(\d{4})',        # Month DD, YYYY
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            # Get context around the date
            start = max(0, match.start() - 15)
            end = min(len(text), match.end() + 15)
            context = text[start:end].lower()
            
            date_type = "unknown"
            if any(word in context for word in ['start', 'launch', 'began', '開始', '开始']):
                date_type = "start"
            elif any(word in context for word in ['end', 'deadline', 'close', '結束', '结束', 'finish']):
                date_type = "end"
            
            dates.append({
                "raw": match.group(0),
                "groups": match.groups(),
                "type": date_type,
                "context": context.strip()
            })
    
    return dates

def extract_crowdfunding_data(ocr_result: dict) -> Dict:
    """
    Enhanced function to extract detailed crowdfunding information from OCR result.
    Works with English text for better NLP accuracy.
    """
    # Use English text for NLP processing (better accuracy)
    raw_text = ocr_result.get("english_text", ocr_result.get("original_text", ""))
    original_text = ocr_result.get("original_text", raw_text)
    
    # Clean and merge the text for better extraction
    cleaned_text = clean_and_merge_text(raw_text)
    
    doc = nlp(cleaned_text)
    
    # Initialize comprehensive data structure (handles both crowdfunding and product data)
    result = {
        "target_site": None,
        "market": None,
        "status": "Live",  # Default assumption
        "url": None,
        "image_url": None,
        "title": None,
        "original_title": None,
        "project_owner": None,
        "owner_website": None,
        "owner_sns": None,
        "owner_country": None,
        "contact_info": None,
        "achievement_rate": None,
        "supporters": None,
        "amount": None,           # Current amount raised OR product price
        "support_amount": None,   # Goal amount OR original price
        "crowdfund_start_date": None,
        "crowdfund_end_date": None,
        "start_date": None,
        "end_date": None,
        "current_or_completed_project": "Current",
        # Additional fields for product listings
        "discount_rate": None,    # For discount percentages like "7% OFF"
        "currency": None,         # Currency type (USD, JPY, EUR, etc.)
        "product_code": None,     # Product codes/SKUs
        # Additional fields for translation info
        "detected_languages": ocr_result.get("detected_languages", []),
        "translation_confidence": ocr_result.get("translation_confidence", 0.0),
        "original_text_available": original_text != raw_text,
        "extraction_confidence": 0.0,
        "raw_text_length": len(cleaned_text),
        "total_ocr_results": ocr_result.get("total_results_found", 0)
    }

    # Enhanced platform detection
    platform_patterns = {
        "indiegogo": r"indiegogo",
        "kickstarter": r"kickstarter", 
        "gofundme": r"gofundme|go fund me",
        "fundrazr": r"fundrazr",
        "crowdfunding": r"crowdfunding",
        "patreon": r"patreon",
        "wefunder": r"wefunder",
        "seedinvest": r"seedinvest"
    }
    
    text_lower = cleaned_text.lower()
    for platform, pattern in platform_patterns.items():
        if re.search(pattern, text_lower):
            result["target_site"] = platform.capitalize()
            result["market"] = platform.capitalize()
            result["extraction_confidence"] += 0.2
            break

    # Enhanced title extraction - better for both crowdfunding and product listings
    lines = [line.strip() for line in cleaned_text.splitlines() if line.strip() and len(line.strip()) > 1]
    if lines:
        # Look for title - could be project name or product name
        title_candidates = []
        for i, line in enumerate(lines[:8]):  # Check first 8 lines
            # Skip lines that are clearly not titles
            if re.match(r'^[\d\s\$\%\,\./\-¥Y\[\]]+$', line):  # Only numbers, money, dates, percentages, method tags
                continue
            if re.match(r'^\[.*\]', line):  # Skip method tags like [CURRENCY]
                continue
            if re.match(r'^\d+%\s*(?:off|OFF)$', line.lower()):  # Discount percentages
                continue
            if len(line) < 3:  # Too short
                continue
            
            # Score based on length, position, and content
            score = len(line) * 0.1  # Length bonus
            score += (8 - i) * 0.2   # Position bonus (earlier = better)
            
            # Content bonuses for crowdfunding
            if any(word in line.lower() for word in ['project', 'campaign', 'fund', 'help', 'support']):
                score += 0.5
            
            # Content bonuses for product listings
            if any(word in line.lower() for word in ['airvision', 'teus', 'mi', 'pro', 'max', 'mini']):
                score += 0.3
            
            # Bonus for Chinese product terms
            if any(char in line for char in ['早割', '価格', '商品', '製品']):
                score += 0.4
            
            # Penalize very short single words unless they look like brand names
            if len(line.split()) == 1 and len(line) < 6 and not line[0].isupper():
                score -= 0.3
            
            title_candidates.append((score, line))
        
        if title_candidates:
            title_candidates.sort(key=lambda x: x[0], reverse=True)
            best_title = title_candidates[0][1]
            
            # If the best title is still not great, try to construct from product info
            if best_title and (best_title.startswith('[') or len(best_title) < 8):
                # Look for better alternatives
                for score, candidate in title_candidates[1:]:
                    if score > 0.3 and not candidate.startswith('[') and len(candidate) > 8:
                        best_title = candidate
                        break
                
                # If still no good title, create a generic one
                if not best_title or best_title.startswith('['):
                    if any('¥' in line or 'Y' in line for line in lines):
                        best_title = "Product Listing"
                    else:
                        best_title = "Item"
            
            result["title"] = best_title
            result["original_title"] = best_title
            result["extraction_confidence"] += 0.15

    # Enhanced monetary amount extraction
    amounts = extract_enhanced_amounts(cleaned_text)
    
    if amounts:
        result["extraction_confidence"] += 0.3
        
        # Separate different types of amounts
        goals = [a for a in amounts if a["type"] == "goal"]
        currents = [a for a in amounts if a["type"] == "current"]
        prices = [a for a in amounts if a["type"] == "price"]
        discounts = [a for a in amounts if a["type"] == "discount"]
        unknowns = [a for a in amounts if a["type"] == "unknown"]
        
        # For crowdfunding: assign goal and current amounts
        if goals:
            result["support_amount"] = goals[0]["formatted"]
        elif len(amounts) >= 2 and not prices:  # Only if not product pricing
            result["support_amount"] = amounts[0]["formatted"]  # Largest
        
        if currents:
            result["amount"] = currents[0]["formatted"]
        elif len(amounts) >= 2 and not prices:  # Only if not product pricing
            result["amount"] = amounts[1]["formatted"]  # Second largest
        
        # For product listings: use price information intelligently
        if prices:
            # For product listings, usually the smaller price is the sale price
            if len(prices) >= 2:
                larger_price = max(prices, key=lambda x: x["value"])
                smaller_price = min(prices, key=lambda x: x["value"])
                result["support_amount"] = larger_price["formatted"]  # Original price (higher)
                result["amount"] = smaller_price["formatted"]        # Sale price (lower)
            else:
                result["amount"] = prices[0]["formatted"]
        elif unknowns and not goals and not currents:
            # If we only have unknown amounts and no crowdfunding context, treat as prices
            if len(unknowns) >= 2:
                # Sort by value to identify original vs sale price
                sorted_unknowns = sorted(unknowns, key=lambda x: x["value"], reverse=True)
                result["support_amount"] = sorted_unknowns[0]["formatted"]  # Higher price (original)
                result["amount"] = sorted_unknowns[1]["formatted"]          # Lower price (sale)
            else:
                result["amount"] = unknowns[0]["formatted"]
        
        # Add currency information if available
        if amounts and "currency" in amounts[0]:
            result["currency"] = amounts[0]["currency"]

    # Enhanced percentage extraction (achievement rate OR discount rate)
    percent_patterns = [
        r'(\d+(?:\.\d+)?)%\s*(?:off|OFF|discount|DISCOUNT)',  # 7% OFF
        r'(?:off|OFF|discount|DISCOUNT)[:\s]*(\d+(?:\.\d+)?)%',  # OFF: 7%
        r'(\d+(?:\.\d+)?)%',                    # 95% or 95.5%
        r'(\d+(?:\.\d+)?)\s*percent',           # 95 percent
        r'funded\s*[:\-]?\s*(\d+(?:\.\d+)?)%',  # funded: 95%
    ]
    
    for pattern in percent_patterns:
        matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
        for match in matches:
            try:
                pct_value = float(match)
                
                # Check if this is a discount percentage
                if "off" in pattern.lower() or "discount" in pattern.lower():
                    if 0 <= pct_value <= 100:  # Reasonable discount range
                        result["discount_rate"] = f"{pct_value}%"
                        result["extraction_confidence"] += 0.15
                        break
                # Otherwise treat as achievement rate
                elif 0 <= pct_value <= 1000:  # Reasonable range for funding
                    result["achievement_rate"] = f"{pct_value}%"
                    result["extraction_confidence"] += 0.2
                    break
            except:
                continue
        if result["achievement_rate"]:
            break

    # Product code/SKU extraction (for product listings)
    product_code_patterns = [
        r'\b(\d{5,8})\b',  # 5-8 digit codes like "444420"
        r'\b([A-Z]{2,4}\d{3,6})\b',  # Letter+number codes like "SKU12345"
        r'\b(Item\s*[:\#]?\s*[\w\d-]+)',  # "Item: ABC123"
        r'\b(Model\s*[:\#]?\s*[\w\d-]+)',  # "Model: XYZ456"
    ]
    
    # Get all numeric strings that might be product codes
    potential_codes = []
    for pattern in product_code_patterns:
        matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
        potential_codes.extend(matches)
    
    # Filter out amounts that we've already identified as prices
    price_values = set()
    if amounts:
        for amt in amounts:
            price_values.add(str(amt["value"]))
    
    for code in potential_codes:
        code_str = str(code).strip()
        # Skip if this number is already identified as a price
        if code_str in price_values:
            continue
        # Skip if it looks like a price or percentage
        if any(char in code_str for char in ['¥', '$', '%', '.']):
            continue
        # Skip very common small numbers
        if code_str.isdigit() and int(code_str) < 100:
            continue
        
        result["product_code"] = code_str
        result["extraction_confidence"] += 0.1
        break

    # Enhanced supporter count extraction
    supporter_patterns = [
        r'(\d+(?:,\d{3})*)\s*(?:supporters?|backers?|funders?)',
        r'(?:supporters?|backers?)[:\s]*(\d+(?:,\d{3})*)',
        r'(\d+(?:,\d{3})*)\s*人(?:が|の)',  # Japanese
        r'(\d+(?:,\d{3})*)\s*人(?:支持|支援)',  # Chinese
    ]
    
    for pattern in supporter_patterns:
        matches = re.findall(pattern, cleaned_text, re.IGNORECASE)
        if matches:
            try:
                count = int(matches[0].replace(',', ''))
                if count > 0:  # Sanity check
                    result["supporters"] = matches[0]
                    result["extraction_confidence"] += 0.15
                    break
            except:
                continue

    # Enhanced date extraction
    dates = extract_enhanced_dates(cleaned_text)
    
    if dates:
        start_dates = [d for d in dates if d["type"] == "start"]
        end_dates = [d for d in dates if d["type"] == "end"]
        
        # Assign start date
        if start_dates:
            result["start_date"] = start_dates[0]["raw"]
            result["crowdfund_start_date"] = start_dates[0]["raw"]
        elif len(dates) >= 2:
            result["start_date"] = dates[1]["raw"]  # Second date often start
            result["crowdfund_start_date"] = dates[1]["raw"]
        
        # Assign end date
        if end_dates:
            result["end_date"] = end_dates[0]["raw"]
            result["crowdfund_end_date"] = end_dates[0]["raw"]
        elif len(dates) >= 1:
            result["end_date"] = dates[0]["raw"]  # First date often deadline
            result["crowdfund_end_date"] = dates[0]["raw"]
        
        if result["start_date"] or result["end_date"]:
            result["extraction_confidence"] += 0.1

    # Enhanced location/country extraction using spaCy NER
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC"]:  # Geographic/Political entities, Locations
            if not result["owner_country"]:
                result["owner_country"] = ent.text
                result["extraction_confidence"] += 0.1
                break

    # Enhanced URL extraction
    url_patterns = [
        r'https?://[^\s<>"{}|\\^`[\]]+',
        r'www\.[^\s<>"{}|\\^`[\]]+',
    ]
    
    for pattern in url_patterns:
        urls = re.findall(pattern, cleaned_text)
        if urls:
            result["url"] = urls[0]
            result["extraction_confidence"] += 0.1
            break

    # Project owner extraction using NER
    people = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    if people:
        # Usually the first person mentioned is the owner
        result["project_owner"] = people[0]
        result["extraction_confidence"] += 0.1

    # Status detection
    status_keywords = {
        "funded": ["funded", "successful", "completed", "達成", "成功"],
        "cancelled": ["cancelled", "canceled", "failed", "unsuccessful", "中止"],
        "live": ["live", "active", "ongoing", "in progress", "進行中"]
    }
    
    for status, keywords in status_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            result["status"] = status.capitalize()
            result["extraction_confidence"] += 0.1
            break

    # Normalize confidence score
    result["extraction_confidence"] = min(1.0, result["extraction_confidence"])

    return result

# Keep the old function for backward compatibility
def parse_text(ocr_result) -> Dict:
    """
    Legacy function - calls the new enhanced extraction
    Handles both old string format and new dict format
    """
    if isinstance(ocr_result, str):
        # Old format - convert to new format
        ocr_dict = {
            "original_text": ocr_result,
            "english_text": ocr_result,
            "detected_languages": ["unknown"],
            "translation_confidence": 1.0
        }
        return extract_crowdfunding_data(ocr_dict)
    else:
        # New format
        return extract_crowdfunding_data(ocr_result)
