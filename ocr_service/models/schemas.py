from pydantic import BaseModel

class OCRResponse(BaseModel):
    text: str

class NLPResponse(BaseModel):
    structured_data: dict

class OCRRequest(BaseModel):
    image_base64: str  # optional if you want to send base64 instead of files

class NLPRequest(BaseModel):
    text: str
