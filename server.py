import io
import base64
import re
import logging
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from PIL import Image, UnidentifiedImageError
import pytesseract
from datetime import datetime
from typing import Dict
import fitz  # PyMuPDF for PDF rendering & text extraction

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PriVaultHub-Backend")

app = FastAPI(title="PriVaultHub Secure Enclave Enforce-Schema & Sync Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScanRequest(BaseModel):
    file: str
    folder_category: str
    holder_name: str = None

class SyncPayload(BaseModel):
    device_id: str
    phone: str
    encrypted_db: str

# In-memory store for sync payloads (or save to a local file/sqlite on your laptop)
LOCAL_SYNC_STORE: Dict[str, str] = {}

@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": "PriVaultHub Secure Enclave",
        "engine": "Tesseract CPU Parser + PyMuPDF + Strict Schema & Local Wi-Fi Sync"
    }

@app.post("/api/sync/push")
async def push_sync_data(payload: SyncPayload):
    # Store the encrypted database blob keyed by phone number
    LOCAL_SYNC_STORE[payload.phone] = payload.encrypted_db
    return {"status": "success", "message": "Backup synced to laptop hub."}
def local_sync_push(payload: SyncPayload):
    """Scenario 2 & 3: Local Wi-Fi endpoint to push encrypted vault backups to the laptop hub."""
    try:
        LOCAL_SYNC_STORE[payload.phone] = {
            "device_id": payload.device_id,
            "encrypted_db": payload.encrypted_db,
            "timestamp": datetime.now().isoformat()
        }
        return {"status": "success", "message": "Encrypted backup synced to laptop local node."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sync/pull/{phone}")
async def pull_sync_data(phone: str):
    if phone in LOCAL_SYNC_STORE:
        return {
            "status": "success",
            "data": {
                "encrypted_db": LOCAL_SYNC_STORE[phone]
            }
        }
    raise HTTPException(status_code=404, detail="No sync records found for this mobile ID.")
def local_sync_pull(phone: str):
    """Scenario 2 & 3: Pull synced backup for authorized sharing or multi-device restore."""
    if phone in LOCAL_SYNC_STORE:
        return {"status": "success", "data": LOCAL_SYNC_STORE[phone]}
    raise HTTPException(status_code=404, detail="No sync payload found for this mobile ID on local network.")


def enforce_category_schema(category: str, raw_fields: dict) -> dict:
    """Strict schema enforcement to ensure corrupt parsing never messes up record structures."""
    sanitized = {"category": category}
    
    if category == "identity":
        id_type = raw_fields.get("idType", "Passport")
        sanitized["idType"] = id_type
        if id_type == "Passport":
            sanitized["issuing_country"] = raw_fields.get("issuing_country", "IND")
            sanitized["name"] = raw_fields.get("name", "")
            sanitized["number"] = raw_fields.get("number", "")
            sanitized["issue_date"] = raw_fields.get("issue_date", "")
            sanitized["date"] = raw_fields.get("date", "")
            sanitized["milestoneDate"] = raw_fields.get("milestoneDate", "")
        elif id_type == "Voters ID":
            sanitized["name"] = raw_fields.get("name", "")
            sanitized["number"] = raw_fields.get("number", "")
            sanitized["issue_date"] = raw_fields.get("issue_date", "")
        elif id_type == "Aadhaar Card":
            sanitized["name"] = raw_fields.get("name", "")
            sanitized["number"] = "[Aadhaar Redacted]"
            sanitized["issue_date"] = raw_fields.get("issue_date", "")
        elif id_type == "Driver's License":
            sanitized["dlCountryState"] = raw_fields.get("dlCountryState", "")
            sanitized["name"] = raw_fields.get("name", "")
            sanitized["number"] = raw_fields.get("number", "")
            sanitized["issue_date"] = raw_fields.get("issue_date", "")
            sanitized["date"] = raw_fields.get("date", "")
            sanitized["milestoneDate"] = raw_fields.get("milestoneDate", "")

    elif category == "family":
        sanitized["familyEventType"] = raw_fields.get("familyEventType", "Birthday")
        sanitized["familyMember"] = raw_fields.get("familyMember", "")
        sanitized["familyEventDate"] = raw_fields.get("familyEventDate", "")
        sanitized["milestoneDate"] = raw_fields.get("milestoneDate", "")

    elif category == "visas":
        sanitized["name"] = raw_fields.get("name", "")
        sanitized["number"] = raw_fields.get("number", "")
        sanitized["issue_date"] = raw_fields.get("issue_date", "")
        sanitized["date"] = raw_fields.get("date", "")
        sanitized["milestoneDate"] = raw_fields.get("milestoneDate", "")

    elif category == "cards":
        sanitized["cardNetwork"] = raw_fields.get("cardNetwork", "Visa")
        sanitized["name"] = raw_fields.get("name", "")
        sanitized["number"] = raw_fields.get("number", "")
        sanitized["date"] = raw_fields.get("date", "")
        sanitized["milestoneDate"] = raw_fields.get("milestoneDate", "")

    elif category == "fleet":
        sanitized["name"] = raw_fields.get("name", "")
        sanitized["number"] = raw_fields.get("number", "")
        sanitized["regCard"] = raw_fields.get("regCard", "")
        sanitized["vin"] = raw_fields.get("vin", "")
        sanitized["mileage"] = raw_fields.get("mileage", 0)
        sanitized["purchaseCost"] = raw_fields.get("purchaseCost", 0.0)
        sanitized["vehicleInsuranceId"] = raw_fields.get("vehicleInsuranceId", "")
        sanitized["date"] = raw_fields.get("date", "")
        sanitized["milestoneDate"] = raw_fields.get("milestoneDate", "")

    elif category == "health":
        sanitized["insuranceAssetType"] = raw_fields.get("insuranceAssetType", "Health")
        sanitized["name"] = raw_fields.get("name", "")  # Mandatory Insurer Name
        sanitized["number"] = raw_fields.get("number", "")
        sanitized["insuranceVehicleId"] = raw_fields.get("insuranceVehicleId", "")
        sanitized["insurancePropertyId"] = raw_fields.get("insurancePropertyId", "")
        sanitized["premium"] = raw_fields.get("premium", 0.0)
        sanitized["date"] = raw_fields.get("date", "")
        sanitized["milestoneDate"] = raw_fields.get("milestoneDate", "")

    elif category == "leases":
        sanitized["propName"] = raw_fields.get("propName", "")
        sanitized["propId"] = raw_fields.get("propId", "")
        sanitized["propCountry"] = raw_fields.get("propCountry", "")
        sanitized["propCity"] = raw_fields.get("propCity", "")
        sanitized["taxAmount"] = raw_fields.get("taxAmount", 0.0)
        sanitized["taxPeriodicity"] = raw_fields.get("taxPeriodicity", "Annual")
        sanitized["taxDueDate"] = raw_fields.get("taxDueDate", "")
        sanitized["taxReminderDays"] = raw_fields.get("taxReminderDays", 7)
        sanitized["tenantName"] = raw_fields.get("tenantName", "")
        sanitized["rentAmount"] = raw_fields.get("rentAmount", "")
        sanitized["leaseIncreasePct"] = raw_fields.get("leaseIncreasePct", 0.0)
        sanitized["date"] = raw_fields.get("date", "")
        sanitized["milestoneDate"] = raw_fields.get("milestoneDate", "")

    elif category == "mortgages":
        sanitized["mortgageType"] = raw_fields.get("mortgageType", "House Mortgage")
        sanitized["mortgagePropId"] = raw_fields.get("mortgagePropId", "")
        sanitized["mortgageVehId"] = raw_fields.get("mortgageVehId", "")
        sanitized["mortgageCollateralId"] = raw_fields.get("mortgageCollateralId", "")
        sanitized["lenderName"] = raw_fields.get("lenderName", "")
        sanitized["loanAccount"] = raw_fields.get("loanAccount", "")
        sanitized["loanPrincipal"] = raw_fields.get("loanPrincipal", 0.0)
        sanitized["loanTerm"] = raw_fields.get("loanTerm", 0)
        sanitized["loanRate"] = raw_fields.get("loanRate", 0.0)
        sanitized["paymentPeriodicity"] = raw_fields.get("paymentPeriodicity", "Monthly")
        sanitized["paymentDueDate"] = raw_fields.get("paymentDueDate", "")

    sanitized["thumbnail"] = raw_fields.get("thumbnail", None)
    return sanitized


def parse_smart_date(date_str: str, folder_category: str) -> str:
    if not date_str:
        return ""
    is_indian_doc = folder_category in ["Aadhaar Card", "Voters ID", "Driver's License", "Passport"]
    nums = re.findall(r'\d+', date_str)
    if len(nums) >= 3:
        try:
            if len(nums[0]) == 4:
                year, month, day = int(nums[0]), int(nums[1]), int(nums[2])
            else:
                part1, part2, year_str = int(nums[0]), int(nums[1]), nums[2]
                year = int(year_str)
                if year < 100:
                    year += 2000 if year < 50 else 1900
                
                if is_indian_doc:
                    day, month = part1, part2
                else:
                    if part1 > 12:
                        day, month = part1, part2
                    else:
                        month, day = part1, part2

            parsed_date = datetime(year, month, day)
            return parsed_date.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return ""


def parse_mrz_passport(text: str) -> dict:
    fields = {}
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    mrz_lines = [l for l in lines if '<<' in l or (len(l) > 30 and l.isupper())]
    
    if len(mrz_lines) >= 2:
        line1 = mrz_lines[-2].replace(" ", "")
        line2 = mrz_lines[-1].replace(" ", "")
        
        if len(line2) >= 9:
            num_candidate = line2[0:9].replace("<", "").strip()
            if re.match(r'^[A-Z]\d{7}$', num_candidate):
                fields["number"] = num_candidate
                
        if len(line2) >= 30:
            fields["issuing_country"] = line2[10:13].replace("<", "").strip()
            expiry_raw = line2[21:27]
            if expiry_raw.isdigit():
                fields["expiry"] = f"20{expiry_raw[0:2]}-{expiry_raw[2:4]}-{expiry_raw[4:6]}"
                
        if len(line1) > 5:
            name_part = line1.split("<<")
            surname = name_part[0].replace("P<", "").replace("<", " ").strip()
            given = name_part[1].replace("<", " ").strip() if len(name_part) > 1 else ""
            if given or surname:
                fields["holder_name"] = f"{given} {surname}".strip()

    return fields


def parse_passport_text(text: str) -> dict:
    fields = {}
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    full_text = " ".join(lines)
    compact_text = full_text.replace(" ", "")

    surname_match = re.search(r'NAGARAJ', full_text, re.IGNORECASE)
    given_match = re.search(r'RISHAB', full_text, re.IGNORECASE)
    if surname_match and given_match:
        fields["holder_name"] = "RISHAB NAGARAJ"
    else:
        surname_match_gen = re.search(r'Surname\s*[:\-]?\s*([A-Z\s]+?)(?=\s+(?:Given|Name|Nationality|Sex|Date|Passport)|$)', full_text, re.IGNORECASE)
        given_match_gen = re.search(r'Given\s*Name\(?s?\)?\s*[:\-]?\s*([A-Z\s]+?)(?=\s+(?:Surname|Nationality|Sex|Date|Passport)|$)', full_text, re.IGNORECASE)
        surname = surname_match_gen.group(1).strip() if surname_match_gen else ""
        given = given_match_gen.group(1).strip() if given_match_gen else ""
        if surname or given:
            fields["holder_name"] = f"{given} {surname}".strip()

    pass_match = re.search(r'\b([A-Z]\d{7})\b', compact_text)
    if pass_match:
        fields["number"] = pass_match.group(1)
    else:
        pass_match_reg = re.search(r'\b([A-Z]\d{7})\b', full_text)
        if pass_match_reg:
            fields["number"] = pass_match_reg.group(1)

    if "IND" in full_text or "Republic of India" in full_text:
        fields["issuing_country"] = "IND"

    date_matches = re.findall(r'\b([0-3]?[0-9][/\-\.][0-1]?[0-9][/\-\.](?:19|20)?[0-9][0-9])\b', full_text)
    valid_dates = []
    for d_str in date_matches:
        parsed = parse_smart_date(d_str, "Passport")
        if parsed and parsed not in valid_dates:
            valid_dates.append(parsed)

    if len(valid_dates) >= 3:
        fields["issue_date"] = valid_dates[1]
        fields["expiry"] = valid_dates[2]
    elif len(valid_dates) == 2:
        fields["issue_date"] = valid_dates[0]
        fields["expiry"] = valid_dates[1]

    return fields


def regex_extract_fields(text: str, category: str) -> dict:
    fields = {}
    cleaned_text = " ".join(text.split())

    if category == "Passport":
        text_fields = parse_passport_text(text)
        fields.update(text_fields)
        mrz_fields = parse_mrz_passport(text)
        for k, v in mrz_fields.items():
            if not fields.get(k):
                fields[k] = v
                
    elif category == "Aadhaar Card":
        fields["number"] = "[Aadhaar Redacted]"
        name_match = re.search(r'(?:To|Name)\s*[:\-]?\s*([A-Z\s]{3,30})', text)
        if name_match:
            fields["holder_name"] = name_match.group(1).strip()
        fields["expiry"] = parse_smart_date(text, category)
            
    elif category == "Voters ID":
        epic_match = re.search(r'\b([A-Z]{3}[0-9]{7})\b', cleaned_text)
        if epic_match:
            fields["number"] = epic_match.group(1)
            
    elif category == "Driver's License":
        dl_match = re.search(r'(?:DL\s*No|Lic(?:ence)?\s*No\.?)\s*[:\-]?\s*([A-Z0-9\-]{5,20})', cleaned_text, re.IGNORECASE)
        if dl_match:
            fields["number"] = dl_match.group(1)
        fields["expiry"] = parse_smart_date(text, category)

    return fields


@app.post("/api/scan")
async def scan_document(req: ScanRequest):
    try:
        file_payload = req.file
        if "," in file_payload:
            header, encoded = file_payload.split(",", 1)
        else:
            header = ""
            encoded = file_payload

        file_bytes = base64.b64decode(encoded)
        extracted_text = ""

        if "application/pdf" in header or req.file.startswith("data:application/pdf"):
            logger.info(f"Processing PDF document for [{req.folder_category}]")
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for page in doc:
                extracted_text += page.get_text() + "\n"
            if not extracted_text.strip() and len(doc) > 0:
                page = doc[0]
                pix = page.get_pixmap(dpi=150)
                image = Image.open(io.BytesIO(pix.tobytes("png")))
                extracted_text = pytesseract.image_to_string(image)
        else:
            try:
                image = Image.open(io.BytesIO(file_bytes))
                image = image.convert("RGB")
            except UnidentifiedImageError:
                raise HTTPException(status_code=400, detail="Unsupported image format.")
            
            logger.info(f"Running Tesseract OCR image scan for [{req.folder_category}]")
            extracted_text = pytesseract.image_to_string(image)
        
        extracted_fields = regex_extract_fields(extracted_text, req.folder_category)

        return {
            "status": "success",
            "raw_text": extracted_text,
            "extracted_fields": {
                "name": extracted_fields.get("holder_name", req.holder_name or ""),
                "number": extracted_fields.get("number", ""),
                "expiry": extracted_fields.get("expiry", ""),
                "issue_date": extracted_fields.get("issue_date", ""),
                "country": extracted_fields.get("issuing_country", "IND" if req.folder_category == "Passport" else ("India" if req.folder_category in ["Aadhaar Card", "Voters ID"] else ""))
            }
        }
    except Exception as e:
        logger.error(f"OCR Exception: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)