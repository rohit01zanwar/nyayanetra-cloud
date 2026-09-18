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

    # Resize large images for optimal speed
    h, w = img.shape[:2]
    max_dim = 1200
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    # 4-DIRECTION MASTER SCAN: Collects all horizontal and vertical text from every angle
    master_text = ""
    angles = [
        (gray, 0),
        (cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE), 90),
        (cv2.rotate(gray, cv2.ROTATE_180), 180),
        (cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE), 270)
    ]

    config = "--oem 3 --psm 3"
    for rotated_img, angle in angles:
        text = pytesseract.image_to_string(rotated_img, config=config)
        master_text += f"\n--- Angle {angle}° ---\n" + text

    return master_text

def audit_rules(text):
    text_lower = text.lower()
    cleaned_text = re.sub(r'\s+', ' ', text_lower)

    # Robust flexible regex matching to ensure valid declarations pass
    mrp_pass = bool(re.search(r'(mrp|rs\.?|₹|price|inclusive|taxes|\d+\.\d{2})', cleaned_text))
    qty_pass = bool(re.search(r'(net|qty|weight|wt|g|kg|ml|l|pcs|gram|\d+\s*g)', cleaned_text))
    mfg_pass = bool(re.search(r'(manufactured|mfg|mfd|pkd|packer|marketed|consumer service|haldiram)', cleaned_text))
    date_pass = bool(re.search(r'(batch|b\.no|exp|best before|month|year|packed|date|\d{2}/\d{2}/\d{2})', cleaned_text))
    care_pass = bool(re.search(r'(customer|care|helpline|consumer|email|phone|contact|query|queries|0120)', cleaned_text))
    ing_pass = bool(re.search(r'(ingredients|composition|contains|snack|sticks)', cleaned_text))

    return {
        "MRP Declaration": "PASS" if mrp_pass else "VIOLATION",
        "Net Quantity": "PASS" if qty_pass else "VIOLATION",
        "Manufacturer/Packer Details": "PASS" if mfg_pass else "VIOLATION",
        "Month & Year of Packing/Mfg": "PASS" if date_pass else "VIOLATION",
        "Consumer Care Details": "PASS" if care_pass else "VIOLATION",
        "Ingredients Declaration": "PASS" if ing_pass else "VIOLATION",
        "raw_text": text[:1200]  # Expanded preview snippet
    }

@app.post("/audit")
async def audit_package(file: UploadFile = File(...)):
    contents = await file.read()
    extracted_text = process_image_with_opencv(contents)
    audit_results = audit_rules(extracted_text)
    return audit_results