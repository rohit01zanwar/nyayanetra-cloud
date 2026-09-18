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

    # Resize large phone images for speed
    h, w = img.shape[:2]
    max_dim = 1200
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    # MULTI-ORIENTATION SCANNING: Capture both horizontal and vertical text labels
    extracted_text = ""
    angles = [0, 90, 270]
    
    for angle in angles:
        if angle == 90:
            rotated = cv2.rotate(gray, cv2.ROTATE_90_CLOCKWISE)
        elif angle == 270:
            rotated = cv2.rotate(gray, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            rotated = gray

        config = "--oem 3 --psm 3"
        text = pytesseract.image_to_string(rotated, config=config)
        extracted_text += "\n" + text

    return extracted_text

def audit_rules(text):
    text_lower = text.lower()
    cleaned_text = re.sub(r'\s+', ' ', text_lower)

    mrp_pass = bool(re.search(r'(mrp|rs\.?|₹|inclusive of all taxes)', cleaned_text))
    qty_pass = bool(re.search(r'(net qty|net weight|nt\.?wt\.?|g|kg|ml|l|pcs)', cleaned_text))
    mfg_pass = bool(re.search(r'(manufactured by|mfg|mfd|pkd|packer|marketed by)', cleaned_text))
    date_pass = bool(re.search(r'(b\.no|batch|exp|best before|month|year|packed on)', cleaned_text))
    care_pass = bool(re.search(r'(customer care|helpline|consumer|email|phone|contact)', cleaned_text))
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