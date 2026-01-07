import csv
import random
from datetime import datetime, timedelta
from typing import List, Dict

# Configuration
VEHICLES_PER_COMPANY = {"Lahav": 14, "Mahatz": 12, "Hod": 14}
DAYS_BACK = 3
FAULT_CATALOG = [
    "Engine Overheat", "Track Tension Low", "Comm System Fail", "Oil Leak 10W",
    "Turret Stabilizer", "Night Vision Drift", "Battery Low", "Fire Control Error"
]

def generate_mock_data(output_path: str = "data.csv"):
    """
    Generates a CSV file with realistic battalion data.
    Includes:
    - 40 Vehicles
    - 3 Days of history
    - PII columns (to test Airlock)
    - "Bad Actors" (Copy-Paste patterns)
    - "Chronic Faults" (Erosion patterns)
    """
    rows = []
    
    # 1. Generate Base Fleet
    vehicles = []
    for company, count in VEHICLES_PER_COMPANY.items():
        for i in range(1, count + 1):
            vid = f"{company[0]}-{i:02d}" # e.g., L-01
            vehicles.append({"id": vid, "company": company})

    start_date = datetime.now() - timedelta(days=DAYS_BACK)

    # 2. Iterate Days
    for day_offset in range(DAYS_BACK + 1):
        current_date = start_date + timedelta(days=day_offset)
        timestamp_str = current_date.strftime("%Y-%m-%d %H:%M:%S")
        
        for v in vehicles:
            vid = v["id"]
            company = v["company"]
            
            # Default: Healthy
            status = "OPERATIONAL"
            faults = []
            logistics = ""
            notes = "All good"
            
            # --- ADVERSARIAL PATTERNS ---
            
            # A. The "Slacker" (L-03): Always copies the exact same report
            if vid == "L-03":
                # Always reports this exact state, ignoring date changes in reality
                status = "OPERATIONAL"
                notes = "Checked ok, ready for mission" # consistent text
            
            # B. The "Eroding Vehicle" (M-07): Reports "OPERATIONAL" but has repeated minor faults
            elif vid == "M-07":
                status = "OPERATIONAL" # Technically operational
                faults = ["Engine Overheat"] # But keeps overheating
                notes = "Fills water and runs"

            # C. The "Broken" (H-10): Legitimately broken
            elif vid == "H-10":
                status = "UNAVAILABLE"
                faults = ["Track Broken"]
                logistics = "Track Link x10"

            # D. Random Noise
            elif random.random() < 0.1:
                status = "DEGRADED"
                faults = [random.choice(FAULT_CATALOG)]

            # --- ROW ASSEMBLY ---
            row = {
                "timestamp": timestamp_str,
                "vehicle_id": vid,
                "company": company,
                "readiness": status,
                "fault_codes": ",".join(faults),
                "logistics_gap": logistics,
                # PII / Forbidden Columns for Airlock Testing
                "Soldier Name": f"Sgt. {random.choice(['Cohen', 'Levi', 'Mizrahi'])}",
                "Phone": f"050-{random.randint(1000000, 9999999)}",
                "Notes": notes # Should be dropped by Airlock (input column "Notes")
            }
            rows.append(row)

    # Write CSV
    headers = [
        "timestamp", "vehicle_id", "company", "readiness", 
        "fault_codes", "logistics_gap",
        "Soldier Name", "Phone", "Notes" # Mix of valid and PII
    ]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Generated {len(rows)} rows to {output_path}")

if __name__ == "__main__":
    generate_mock_data()
