from pydantic import BaseModel
from typing import List, Optional

class DocMetadataUpdate(BaseModel):
    extracted_name: Optional[str] = None
    extracted_dob: Optional[str] = None
    biometric_update_date: Optional[str] = None

class Discrepancy(BaseModel):
    severity: str  # "Critical", "Moderate", "Low"
    title: str
    description: str

class TemporalAlert(BaseModel):
    document_type: str
    message: str

class HowToGuide(BaseModel):
    title: str
    content: str
    dos: List[str]
    donts: List[str]
    link: str

class AuditReport(BaseModel):
    discrepancies: List[Discrepancy]
    temporal_alerts: List[TemporalAlert]
    guides: List[HowToGuide]