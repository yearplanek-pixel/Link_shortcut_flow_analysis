from pydantic import BaseModel
from typing import Optional, List

class URLCreate(BaseModel):
    original_url: str
    custom_slug: Optional[str] = None
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None

class URLResponse(BaseModel):
    short_code: str
    original_url: str
    short_url: str
    qr_url: str
    qr_code_base64: Optional[str] = None
    created_at: str
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None

class BulkGenerationItem(BaseModel):
    original_url: str
    custom_slug: Optional[str] = None
    custom_name: Optional[str] = None
    campaign_name: Optional[str] = None

class BulkGenerationRequest(BaseModel):
    items: List[BulkGenerationItem]