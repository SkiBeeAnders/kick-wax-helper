import csv
import json
from pathlib import Path

# Input and output paths
CSV_PATH = Path("GripTipData - Blad1.csv")
OUT_JSON_PATH = Path("wax_data.json")

# Expected column names in the CSV:
# brand, line, code, product_name, type,
# temp_new_min, temp_new_max,
# temp_old_min, temp_old_max,
# temp_wet_min, temp_wet_max,
# notes, image_file, priority, active

def parse_number(value):
    """
    Parse a string to int/float or return None if empty.
    Handles '.', ',', unicode minus and stray degree symbols.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    # Normalize unicode minus to normal hyphen-minus
    s = s.replace("\u2212", "-")  # Unicode minus → '-'

    # Remove degree symbols and 'C'/'°C'
    s = s.replace("°", "").replace("C", "").replace("c", "")

    # Replace comma with dot in case of Swedish-style decimals
    s = s.replace(",", ".")

    try:
        num = float(s)
    except ValueError:
        return None

    if num.is_integer():
        return int(num)
    return num


def build_temp_range(min_val, max_val):
    """
    Build a {"min": x, "max": y} object, or return None if both missing.
    This is where missing wet spans will become null in JSON.
    """
    if min_val is None and max_val is None:
        return None
    return {"min": min_val, "max": max_val}

def parse_bool(value):
    if value is None:
        return True  # default to active
    s = str(value).strip().lower()
    if s in ("no", "nej", "false", "0"):
        return False
    return True

def make_id(brand, code):
    """
    Create a stable ID like 'swix_vp30' from brand + code.
    """
    b = (brand or "").strip().lower().replace(" ", "")
    c = (code or "").strip().lower().replace(" ", "")
    if not b and not c:
        return None
    if not c:
        return b
    return f"{b}_{c}"

def main():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Could not find CSV file: {CSV_PATH}")

    products = []

    # Try to auto-detect delimiter (',' vs ';')
    with CSV_PATH.open("r", encoding="utf-8", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        sniffer = csv.Sniffer()
        dialect = sniffer.sniff(sample, delimiters=";,")
        reader = csv.DictReader(f, dialect=dialect)

        for row in reader:
            brand = row.get("brand", "").strip()
            line = row.get("line", "").strip()

            segment_raw = row.get("Race/Training", "") or row.get("race_training", "") or ""
            segment = segment_raw.strip().lower()
            if segment in ("race", "r"):
                segment = "race"
            elif segment in ("training", "touring", "t"):
                segment = "training"
            else:
                # if blank or unknown, leave as empty string -> treated as "both"
                segment = ""

            code = row.get("code", "").strip()
            product_name = row.get("product_name", "").strip()
            wax_type = row.get("type", "").strip().lower() or "hardwax"

            # Temperatures
            t_new_min = parse_number(row.get("temp_new_min"))
            t_new_max = parse_number(row.get("temp_new_max"))
            t_old_min = parse_number(row.get("temp_old_min"))
            t_old_max = parse_number(row.get("temp_old_max"))
            t_wet_min = parse_number(row.get("temp_wet_min"))
            t_wet_max = parse_number(row.get("temp_wet_max"))

            temp_ranges = {
                "new": build_temp_range(t_new_min, t_new_max),
                "old": build_temp_range(t_old_min, t_old_max),
                # This is where missing wet span becomes null
                "wet": build_temp_range(t_wet_min, t_wet_max),
            }

            notes_raw = row.get("notes", "") or ""
            notes = [notes_raw.strip()] if notes_raw.strip() else []

            image_file = row.get("image_file", "").strip() or None

            priority_val = parse_number(row.get("priority"))
            priority = int(priority_val) if priority_val is not None else 70

            active = parse_bool(row.get("active"))

            # Skip completely empty rows
            if not brand and not code and not product_name:
                continue

            product_id = make_id(brand, code) or f"prod_{len(products)+1}"

            products.append({
                "id": product_id,
                "brand": brand,
                "line": line,
                "code": code,
                "product": product_name or f"{brand} {code}".strip(),
                "type": wax_type,
                "segment": segment,  # <-- "race", "training", or ""
                "temp_ranges": temp_ranges,
                "priority": priority,
                "notes": notes,
                "imageFile": image_file,
                "active": active,
            })

    # Filter out products with active == False (if you want them hidden in app)
    active_products = [p for p in products if p.get("active", True)]

    wax_data = {
        "version": "2.0",
        "scope": "Classic grip – new/old/wet",
        "products": active_products,
    }

    with OUT_JSON_PATH.open("w", encoding="utf-8") as out_f:
        json.dump(wax_data, out_f, ensure_ascii=False, indent=2)

    print(f"✔ Wrote {OUT_JSON_PATH} with {len(active_products)} active products.")

if __name__ == "__main__":
    main()
