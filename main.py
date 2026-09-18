import cv2
import numpy as np
import pytesseract
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import re

app = FastAPI()

# Enable CORS so your mobile browser can talk to the cloud server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def process_image_with_opencv(image_bytes):
    # Decode image bytes into a NumPy array for OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return ""

    # 1. SPEED OPTIMIZATION: Resize large phone images if width > 1200px
    h, w = img.shape[:2]
    max_dim = 1200
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)

    # 2. Convert to Grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 3. Gentle contrast enhancement to protect text details from clipping
    gray = cv2.equalizeHist(gray)

    # 4. HIGH-SPEED SINGLE PASS OCR: --psm 3 reads full layout without multi-angle lag
    config = "--oem 3 --psm 3"
    extracted_text = pytesseract.image_to_string(gray, config=config)

    return extracted_text

def audit_rules(text):
    text_lower = text.lower()
    cleaned_text = re.sub(r'\s+', ' ', text_lower)

    # Simple 6-Rule Evaluation Matrix Checks
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
        "raw_text": text[:500]  # Preview snippet of OCR text
    }

@app.post("/audit")
async def audit_package(file: UploadFile = File(...)):
    contents = await file.read()
    extracted_text = process_image_with_opencv(contents)
    audit_results = audit_rules(extracted_text)
    return audit_results