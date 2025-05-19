import os
import re
import json
import sys
import traceback
import shutil # Added for file copying

# Add the parent directory to sys.path to find STEP1.py and STEP2.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import STEP1
import STEP2

# Define Clinic Groupings (as per clinic_processing_plan.md)
CLINIC_GROUPS = {
    "Arizona_Breathe_Free": [
        "3565249000003554329", # Arizona Breathe Free Sinus Allergy Centers
        "3565249000007665001", # Arizona Breathe Free Sinus and Allergy Centers-Casa Grande
        "3565249000008197001", # Arizona Breathe Free-Central
        "3565249000011800001", # Arizona Breathe Free-Westside
    ],
    "Bella_Vista_ENT": [
        "3565249000008251001",
    ],
    "Capital_Group": [
        "3565249000001094007", # Capital Breathe Free Sinus & Allergy Centers / Sinus & Allergy Centers
        "3565249000002700126", # Capital Breathe Free Sinus & Allergy Centers
        "3565249000008278001", # Capital ENT & Sinus Center
        "3565249000002700177", # Capitol Breathe Free Woodbridge
    ],
    "Columbia_Breathe_Free": [
        "3565249000001746001", # Columbia Breathe Free Sinus and Allergy
        "3565249000005956001", # Columbia Breathe Free Sinus and Allergy Clinnics
    ],
    "Del_Rey_Marina": [
        "3565249000001931001", # Del Rey MD
        "3565249000001964035", # Marina Del Rey ENT and Allergy
    ],
    "National_Breathe_Free_Jacksonville": [
        "3565249000007975003", # National Breathe free & Allergy Centers Jacksonville, Fl
        "3565249000007073019", # National Breathe Free Jacksonville, FL
    ],
    "National_Breathe_Free_General": [
        "3565249000003777111", # National Breathe Free Sinus and Allergy
        "3565249000003463001", # National BreatheFree Sinus and Allergy Centers
        "3565249000009070630", # National BreatheFree Sinus and Allergy Centers, Casa Grande, AZ
    ],
    "Jupiter_Breathe_Free": [
        "3565249000001405050",
    ],
    "Oasis": [
        "3565249000001061039",
        "3565249000009055755",
    ],
    "San_Antonio_Group": [
        "3565249000009055348", # San Antonio ENT and Sinus Specialist
        "3565249000010510031", # San Antonio-National BreatheFree
    ],
    "Tampa_Bay_Breathe_Free": [
        "3565249000001405001",
    ],
    "Trinity_ENT": [
        "3565249000000433155",
    ],
    "CT_ENT_Sinus_Center": [
        "3565249000002110089",
    ],
    "Dallas_Breathe_Free": [
        "3565249000006071067",
    ],
    "St_Louis_Sinus_Center": [
        "3565249000000451007",
    ],
    "Vegas_Breathe_Free": [
        "3565249000004892001",
    ]
}

# Base directory for all output
BASE_OUTPUT_DIR = "clinic_output"

def sanitize_filename(name):
    """Removes invalid characters and replaces spaces for filenames."""
    name = name.lower()
    name = re.sub(r'\s+', '_', name) # Replace spaces with underscores
    name = re.sub(r'[^\w\-]+', '', name) # Remove non-alphanumeric characters (except underscore and hyphen)
    return name

def main():
    """Orchestrates the processing for all defined clinic groups."""
    print("Starting clinic data processing...")
    all_clinics_csa_data = {} # Initialize aggregator for all clinic data

    # Ensure base output directory exists
    if not os.path.exists(BASE_OUTPUT_DIR):
        os.makedirs(BASE_OUTPUT_DIR)
        print(f"Created base output directory: {BASE_OUTPUT_DIR}")

    # Load Zoho configuration once
    try:
        config = STEP1.load_config()
        print("Zoho configuration loaded successfully.")
    except Exception as e:
        print(f"FATAL ERROR: Could not load Zoho configuration from {STEP1.CONFIG_PATH}. Exiting.", file=sys.stderr)
        print(f"Error details: {e}", file=sys.stderr)
        sys.exit(1)

    # Process each clinic group
    for clinic_name, contact_ids in CLINIC_GROUPS.items():
        print(f"\n{'='*20} Processing Group: {clinic_name} {'='*20}")
        sanitized_name = sanitize_filename(clinic_name)

        # Create clinic-specific output directory
        clinic_output_dir = os.path.join(BASE_OUTPUT_DIR, sanitized_name)
        if not os.path.exists(clinic_output_dir):
            os.makedirs(clinic_output_dir)
            print(f"Created output directory: {clinic_output_dir}")

        # Define file paths for this group
        step1_json_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step1_data.json")
        step1_md_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step1_log.md")
        step2_json_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step2_analysis.json")
        step2_md_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step2_report.md")

        try:
            # --- Run Step 1 ---
            print(f"\n--- Running Step 1 for {clinic_name} ---")
            # STEP1.run_step1 now takes 2 arguments: contact_ids and output_json_path
            # Config is loaded internally in STEP1.run_step1
            # Logging to step1_md_path needs to be handled by this script if STEP1 no longer does it.
            # For now, just correcting the call signature.
            STEP1.run_step1(contact_ids, step1_json_path)
            print(f"--- Step 1 completed for {clinic_name} ---")

            # --- Run Step 2 ---
            print(f"\n--- Running Step 2 for {clinic_name} ---")
            # Ensure STEP2 uses the correct date class if needed within its scope
            from datetime import date
            STEP2.build_csa_replacement_chains(step1_json_path, step2_json_path, step2_md_path)
            print(f"--- Step 2 completed for {clinic_name} ---")

            print(f"\nSuccessfully processed group: {clinic_name}")

        except Exception as e:
            print(f"\nERROR processing group: {clinic_name}", file=sys.stderr)
            print(f"Error details: {e}", file=sys.stderr)
            print("Traceback:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print(f"Skipping to next group...")
            # Optionally, continue to the next group or halt execution
            # continue
        else:
            # If processing was successful, read the step2_analysis.json and add to aggregator if exists
            if os.path.exists(step2_json_path):
                try:
                    with open(step2_json_path, 'r') as f:
                        clinic_csa_data = json.load(f)
                    all_clinics_csa_data[clinic_name] = clinic_csa_data
                    print(f"Successfully aggregated CSA data for {clinic_name}")
                except Exception as e:
                    print(f"ERROR reading or aggregating {step2_json_path} for {clinic_name}", file=sys.stderr)
                    print(f"Error details: {e}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
            else:
                print(f"WARNING: No analysis file found for {clinic_name}, skipping aggregation.", file=sys.stderr)

    # After processing all groups, write the aggregated data to a single file
    aggregated_output_path = os.path.join(BASE_OUTPUT_DIR, "all_clinics_aggregated_csa_data.json")
    try:
        with open(aggregated_output_path, 'w') as f:
            json.dump(all_clinics_csa_data, f, indent=4)
        print(f"\nSuccessfully wrote aggregated CSA data to: {aggregated_output_path}")

        # --- ADDED: Copy aggregated data to frontend public directory ---
        frontend_public_data_path = os.path.join(BASE_OUTPUT_DIR, "csa-dashboard-frontend", "public", "all_clinics_aggregated_csa_data.json")
        frontend_public_dir = os.path.dirname(frontend_public_data_path)

        try:
            if not os.path.exists(frontend_public_dir):
                os.makedirs(frontend_public_dir)
                print(f"Created frontend public data directory: {frontend_public_dir}")
            
            shutil.copy2(aggregated_output_path, frontend_public_data_path)
            print(f"Successfully copied aggregated data to frontend public directory: {frontend_public_data_path}")
        except Exception as copy_e:
            print(f"\nERROR copying aggregated data to {frontend_public_data_path}", file=sys.stderr)
            print(f"Copy error details: {copy_e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
        # --- END OF ADDED SECTION ---

    except Exception as e:
        print(f"\nERROR writing aggregated CSA data to {aggregated_output_path}", file=sys.stderr)
        print(f"Error details: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)

    print(f"\n{'='*20} All clinic processing finished. {'='*20}")
    print(f"Check the '{BASE_OUTPUT_DIR}' directory for output files.")

if __name__ == "__main__":
    main()
