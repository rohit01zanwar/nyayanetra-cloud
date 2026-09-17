import re

def audit_label(text: str):
    text_lower = text.lower()
    
    # Flatten all newlines and multiple spaces into single spaces to bridge vertical text line breaks
    flat_text = re.sub(r'\s+', ' ', text_lower)
    
    # 1. MRP Check
    mrp_found = bool(re.search(r'(mrp|rs\.?|₹|max\.?\s*retail\s*price|retail\s*price|price|incl\.?\s*of\s*all\s*taxes|taxes)', flat_text))
    
    # 2. Net Quantity Check
    net_qty_found = bool(re.search(r'(net\s*(qty|quantity|wt|weight|content)?|nt\.?\s*wt\.?|net\s*weight|weight|qty\.?|wt\.?|gms?|kgs?|ml|ltr?|pcs?|pieces?|\b\d+\s*(g|kg|ml|l|pc)\b)', flat_text))
    
    # 3. Manufacturer / Packer / Marketer Details Check
    mfg_details_found = bool(re.search(r'(mfg\.?\s*by?|mfd\.?\s*by?|manufactured\s*(by|for|unit)?|mfd\s*for|marketed\s*(by|for)?|mktg?\.?\s*by?|packed\s*(by)?|pkd\s*by?|packer|manufacturer|address|mfd\s*unit|imported\s*by|producer|pvt\.?\s*ltd\.?|private\s*limited|limited|llp|inc\.?|regd\.?\s*office)', flat_text))
    
    # 4. Manufacturing / Packaging / Expiry Date Check
    date_found = bool(re.search(r'(mfg\.?\s*(dt|date)?|mfd\.?\s*(dt|date)?|pkd\.?\s*(dt|date)?|packed\s*on|batch|b\.?\s*no\.?|lot\s*no|month\s*and\s*year|best\s*before|exp\.?\s*date?|use\s*by|expiry)', flat_text))
    
    # 5. Consumer Care Details Check (Includes feedback, queries, customer service, email, phone numbers)
    consumer_care_found = bool(re.search(r'(consumer\s*care|customer\s*care|customer\s*service|consumer\s*service|care\s*cell|care\s*executive|helpline|complaints?|email|toll[\s-]*free|feedback|queries|grievance|contact\s*(us|our|executive|with)|write\s*to\s*us)', flat_text))

    # 6. Ingredients / Composition Check
    ingredients_found = bool(re.search(r'(ingredients?|composition|contains?:?|nutritional\s*(value|info)?|allergen|wheat|sugar|edible|milk|oil|flour)', flat_text))

    return {
        "mrp": {
            "name": "1. Retail Sale Price (MRP)",
            "status": "PASS" if mrp_found else "FAIL",
            "details": "MRP declaration detected." if mrp_found else "Missing MRP statement."
        },
        "net_quantity": {
            "name": "2. Net Quantity",
            "status": "PASS" if net_qty_found else "FAIL",
            "details": "Net quantity specification detected." if net_qty_found else "Missing net quantity declaration."
        },
        "manufacturer_details": {
            "name": "3. Manufacturer/Packer Details",
            "status": "PASS" if mfg_details_found else "FAIL",
            "details": "Manufacturer, packer or marketer details found." if mfg_details_found else "Missing manufacturer name and address."
        },
        "mfg_date": {
            "name": "4. Month & Year of Mfg/Packing/Expiry",
            "status": "PASS" if date_found else "FAIL",
            "details": "Manufacturing, packing, or expiry date found." if date_found else "Missing packaging date or batch details."
        },
        "consumer_care": {
            "name": "5. Consumer Care Details",
            "status": "PASS" if consumer_care_found else "FAIL",
            "details": "Customer care / executive contact info detected." if consumer_care_found else "Missing consumer care contact information."
        },
        "ingredients": {
            "name": "6. Ingredients / Composition Declaration",
            "status": "PASS" if ingredients_found else "FAIL",
            "details": "Ingredients list / composition declared." if ingredients_found else "Missing mandatory ingredients or composition declaration."
        }
    }