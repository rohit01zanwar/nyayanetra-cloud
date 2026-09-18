import cv2
import numpy as np
import pytesseract
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import re

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_image_with_opencv(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return ""

    # Resize large images for speed
    h, w = img.shape[:2]
    max_dim = 1200
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    # Standard OCR pass for normal horizontal text
    config = "--oem 3 --psm 3"
    text_normal = pytesseract.image_to_string(gray, config=config)

    # Secondary pass with 90-degree rotation to catch vertical side-panel text
    rotated = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)
    text_rotated = pytesseract.image_to_string(rotated, config=config)

    return text_normal + "\n" + text_rotated

def audit_rules(text):
    text_lower = text.lower()
    cleaned_text = re.sub(r'\s+', ' ', text_lower)

    # Flexible keyword checks to prevent false violations
    mrp_pass = bool(re.search(r'(mrp|rs\.?|₹|price|inclusive|taxes)', cleaned_text))
    qty_pass = bool(re.search(r'(net|qty|weight|wt|g|kg|ml|l|pcs|gram)', cleaned_text))
    mfg_pass = bool(re.search(r'(manufactured|mfg|mfd|pkd|packer|marketed|consumer service)', cleaned_text))
    date_pass = bool(re.search(r'(batch|b\.no|exp|best before|month|year|packed|date)', cleaned_text))
    care_pass = bool(re.search(r'(customer care|helpline|consumer|email|phone|contact|query|queries)', cleaned_text))
    ing_pass = bool(re.search(r'(ingredients|composition|contains)', cleaned_text))

    return {
        "MRP Declaration": "PASS" if mrp_pass else "VIOLATION",
        "Net Quantity": "PASS" if qty_pass else "VIOLATION",
        "Manufacturer/Packer Details": "PASS" if mfg_pass else "VIOLATION",
        "Month & Year of Packing/Mfg": "PASS" if date_pass else "VIOLATION",
        "Consumer Care Details": "PASS" if care_pass else "VIOLATION",
        "Ingredients Declaration": "PASS" if ing_pass else "VIOLATION",
        "raw_text": text[:800]
    }

@app.post("/audit")
async def audit_package(file: UploadFile = File(...)):
    contents = await file.read()
    extracted_text = process_image_with_opencv(contents)
    audit_results = audit_rules(extracted_text)
    return audit_results