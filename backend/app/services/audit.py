from datetime import datetime
from app.models.document import DocumentMetadata
from app.schemas.audit import AuditReport, Discrepancy, TemporalAlert, HowToGuide

class AuditService:
    @staticmethod
    def generate_report(documents: list[DocumentMetadata]) -> AuditReport:
        discrepancies = []
        temporal_alerts = []
        
        # 1. Group Data by Document Type
        profiles = {}
        for doc in documents:
            if doc.extracted_name or doc.extracted_dob:
                profiles[doc.document_type] = doc

        # 2. Cross-Reference Engine (Discrepancies)
        if "PAN Card" in profiles and "Aadhaar Card" in profiles:
            pan = profiles["PAN Card"]
            aadhaar = profiles["Aadhaar Card"]
            
            # Name Check (Critical for Financial KYC)
            if pan.extracted_name and aadhaar.extracted_name:
                if pan.extracted_name.lower().strip() != aadhaar.extracted_name.lower().strip():
                    discrepancies.append(Discrepancy(
                        severity="Critical",
                        title="PAN / Aadhaar Name Mismatch",
                        description=f"PAN shows '{pan.extracted_name}', but Aadhaar shows '{aadhaar.extracted_name}'. This will cause strict KYC failures in mutual funds and banking."
                    ))
            
            # DOB Check
            if pan.extracted_dob and aadhaar.extracted_dob:
                if pan.extracted_dob != aadhaar.extracted_dob:
                    discrepancies.append(Discrepancy(
                        severity="Moderate",
                        title="DOB Mismatch",
                        description=f"PAN DOB ({pan.extracted_dob}) differs from Aadhaar ({aadhaar.extracted_dob})."
                    ))
                    
        if "Passport" in profiles and "Aadhaar Card" in profiles:
            pass_doc = profiles["Passport"]
            aadhaar = profiles["Aadhaar Card"]
            if pass_doc.extracted_name and aadhaar.extracted_name:
                if pass_doc.extracted_name.lower().strip() != aadhaar.extracted_name.lower().strip():
                    discrepancies.append(Discrepancy(
                        severity="Low",
                        title="Passport / Aadhaar Name Variation",
                        description="Minor variations are generally acceptable, but exact matches are recommended for international visas."
                    ))

        # 3. Temporal Tracking Engine
        for doc in documents:
            if doc.document_type == "Aadhaar Card":
                if doc.biometric_update_date:
                    try:
                        update_date = datetime.strptime(doc.biometric_update_date, "%Y-%m-%d")
                        days_since = (datetime.now() - update_date).days
                        if days_since > 3650: # 10 Years
                            temporal_alerts.append(TemporalAlert(
                                document_type="Aadhaar Card",
                                message=f"Biometrics were last updated {days_since // 365} years ago. UIDAI mandates updates every 10 years."
                            ))
                    except ValueError:
                        pass
                else:
                    temporal_alerts.append(TemporalAlert(
                        document_type="Aadhaar Card",
                        message="Missing biometric update date. Please edit this document to track your 10-year UIDAI refresh cycle."
                    ))

        # 4. Hardcoded Civic Resolution Guides
        guides = [
            HowToGuide(
                title="PAN Card Name/DOB Correction",
                content="Updating demographic details on your PAN via the Protean (NSDL) e-Gov portal.",
                dos=["Use your Aadhaar as proof of identity if Aadhaar details are correct.", "Apply via 'Changes or Correction in existing PAN Data'."],
                donts=["Do not submit old affidavits.", "Do not apply for a New PAN (this is illegal if you already have one)."],
                link="https://www.onlineservices.nsdl.com/paam/endUserRegisterContact.html"
            ),
            HowToGuide(
                title="Aadhaar Biometric/Photo Update",
                content="Biometrics (Fingerprints/Iris/Photo) cannot be updated online. You must visit a center.",
                dos=["Book an appointment via the UIDAI portal to skip queues.", "Bring your original current Aadhaar card."],
                donts=["Do not pay more than Rs. 100 (standard UIDAI fee).", "Do not share OTPs with agents outside the center."],
                link="https://myaadhaar.uidai.gov.in/"
            )
        ]

        return AuditReport(
            discrepancies=discrepancies,
            temporal_alerts=temporal_alerts,
            guides=guides
        )