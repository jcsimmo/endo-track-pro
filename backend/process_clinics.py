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

def load_data_from_disk():
    """Attempts to load aggregated clinic data from existing _step2_analysis.json files."""
    print("Attempting to load aggregated clinic data from disk...")
    all_clinics_csa_data = {}
    all_files_found = True

    for clinic_name in CLINIC_GROUPS.keys():
        sanitized_name = sanitize_filename(clinic_name)
        clinic_output_dir = os.path.join(BASE_OUTPUT_DIR, sanitized_name)
        step1_json_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step1_data.json")
        step2_json_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step2_analysis.json")

        clinic_data_loaded_for_group = False
        if os.path.exists(step2_json_path):
            try:
                with open(step2_json_path, 'r') as f:
                    clinic_csa_data = json.load(f)
                
                # Also load Step 1 data for CSA quantity extraction
                step1_data = None
                if os.path.exists(step1_json_path):
                    try:
                        with open(step1_json_path, 'r') as f1:
                            step1_data = json.load(f1)
                    except Exception as e:
                        print(f"WARNING: Could not load Step 1 data for {clinic_name}: {e}", file=sys.stderr)
                
                # Combine Step 1 and Step 2 data
                combined_data = {
                    **clinic_csa_data,
                    'step1_data': step1_data
                }
                all_clinics_csa_data[clinic_name] = combined_data
                print(f"Successfully loaded existing {step2_json_path} from disk for {clinic_name}")
                clinic_data_loaded_for_group = True
            except Exception as e:
                print(f"ERROR reading or parsing existing {step2_json_path} for {clinic_name}: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                # If Step 2 file is corrupted, try to regenerate from Step 1
                print(f"Attempting to regenerate {step2_json_path} from {step1_json_path}...")
        
        if not clinic_data_loaded_for_group:
            if os.path.exists(step1_json_path):
                print(f"Found {step1_json_path}, attempting to run STEP2 for {clinic_name} to generate {step2_json_path}...")
                try:
                    STEP2.build_csa_replacement_chains(step1_json_path, step2_json_path, None) # None for md_path
                    print(f"Successfully ran STEP2 for {clinic_name} using existing Step 1 data.")
                    # Now try to load the newly generated Step 2 file
                    if os.path.exists(step2_json_path):
                        with open(step2_json_path, 'r') as f:
                            clinic_csa_data = json.load(f)
                        
                        # Also load Step 1 data for CSA quantity extraction
                        step1_data = None
                        if os.path.exists(step1_json_path):
                            try:
                                with open(step1_json_path, 'r') as f1:
                                    step1_data = json.load(f1)
                            except Exception as e:
                                print(f"WARNING: Could not load Step 1 data for {clinic_name}: {e}", file=sys.stderr)
                        
                        # Combine Step 1 and Step 2 data
                        combined_data = {
                            **clinic_csa_data,
                            'step1_data': step1_data
                        }
                        all_clinics_csa_data[clinic_name] = combined_data
                        print(f"Successfully loaded regenerated {step2_json_path} for {clinic_name}")
                        clinic_data_loaded_for_group = True
                    else:
                        print(f"ERROR: {step2_json_path} not found after STEP2 regeneration for {clinic_name}.", file=sys.stderr)
                except Exception as e:
                    print(f"ERROR running STEP2 for {clinic_name} using {step1_json_path}: {e}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
            else:
                print(f"WARNING: Neither {step2_json_path} nor {step1_json_path} found for {clinic_name}. Cannot load or regenerate data from disk.", file=sys.stderr)

        if not clinic_data_loaded_for_group:
            all_files_found = False # Mark that data for this group could not be loaded/regenerated

    if not all_files_found:
        print("One or more clinic analysis files were not found or failed to load. Returning partial dataset from disk.")
        print(f"Successfully loaded data for {len(all_clinics_csa_data)} out of {len(CLINIC_GROUPS)} clinic groups.")
    
    if not all_clinics_csa_data: # Handles case where CLINIC_GROUPS is empty or all files were missing
        print("No clinic data loaded from disk (either no groups defined or no files found).")
        return None

    if all_files_found:
        print("Successfully loaded all available clinic data from disk.")
    else:
        print(f"Successfully loaded partial clinic data from disk: {list(all_clinics_csa_data.keys())}")
    return all_clinics_csa_data

def get_aggregated_clinic_data():
    """
    Orchestrates FRESH data fetching from Zoho and processing for all defined clinic groups.
    This will always run STEP1 and STEP2, overwriting existing JSON files.
    Returns the aggregated data.
    """
    print("Starting FRESH clinic data sync from Zoho and processing for API...")
    all_clinics_csa_data = {} # Initialize aggregator for all clinic data

    # Ensure base output directory exists (still needed for intermediate files)
    if not os.path.exists(BASE_OUTPUT_DIR):
        os.makedirs(BASE_OUTPUT_DIR)
        print(f"Created base output directory: {BASE_OUTPUT_DIR}")

    # Load Zoho configuration once
    try:
        # Assuming STEP1.load_config() is still relevant or handled within STEP1.run_step1
        # If config is only used by run_step1, this explicit call might not be needed here.
        # For now, keeping it to ensure STEP1 has its requirements met if it expects a pre-loaded config.
        # config = STEP1.load_config() # This might be redundant if STEP1.run_step1 handles its own config
        print("Zoho configuration loading (handled by STEP1)...")
    except Exception as e:
        # This error handling might be too aggressive if config loading is truly internal to STEP1
        # print(f"FATAL ERROR: Could not load Zoho configuration. Exiting.", file=sys.stderr)
        # print(f"Error details: {e}", file=sys.stderr)
        # sys.exit(1) # Avoid sys.exit in a library function
        print(f"Warning: Zoho configuration loading issue (details: {e}). STEP1 will attempt to load.", file=sys.stderr)


    # Process each clinic group
    for clinic_name, contact_ids in CLINIC_GROUPS.items():
        print(f"\n{'='*20} Processing Group: {clinic_name} {'='*20}")
        sanitized_name = sanitize_filename(clinic_name)

        # Create clinic-specific output directory for intermediate files
        clinic_output_dir = os.path.join(BASE_OUTPUT_DIR, sanitized_name)
        if not os.path.exists(clinic_output_dir):
            os.makedirs(clinic_output_dir)
            print(f"Created output directory for intermediate files: {clinic_output_dir}")

        # Define file paths for this group (intermediate files)
        step1_json_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step1_data.json")
        # step1_md_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step1_log.md") # Log files might not be needed for API
        step2_json_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step2_analysis.json")
        # step2_md_path = os.path.join(clinic_output_dir, f"{sanitized_name}_step2_report.md") # Log files might not be needed for API

        try:
            # --- Run Step 1 ---
            print(f"\n--- Running Step 1 for {clinic_name} ---")
            STEP1.run_step1(contact_ids, step1_json_path) # Assuming config is handled within
            print(f"--- Step 1 completed for {clinic_name} ---")

            # --- Run Step 2 ---
            print(f"\n--- Running Step 2 for {clinic_name} ---")
            from datetime import date # Keep import local if only used here
            # Pass None for md_path if logging to markdown is not required for API
            STEP2.build_csa_replacement_chains(step1_json_path, step2_json_path, None)
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
                    
                    # Also load Step 1 data for CSA quantity extraction
                    step1_data = None
                    if os.path.exists(step1_json_path):
                        try:
                            with open(step1_json_path, 'r') as f1:
                                step1_data = json.load(f1)
                        except Exception as e:
                            print(f"WARNING: Could not load Step 1 data for {clinic_name}: {e}", file=sys.stderr)
                    
                    # Combine Step 1 and Step 2 data
                    combined_data = {
                        **clinic_csa_data,
                        'step1_data': step1_data
                    }
                    all_clinics_csa_data[clinic_name] = combined_data
                    print(f"Successfully aggregated CSA data for {clinic_name}")
                except Exception as e:
                    print(f"ERROR reading or aggregating {step2_json_path} for {clinic_name}", file=sys.stderr)
                    print(f"Error details: {e}", file=sys.stderr)
                    traceback.print_exc(file=sys.stderr)
            else:
                print(f"WARNING: No analysis file found for {clinic_name}, skipping aggregation.", file=sys.stderr)

    print(f"\n{'='*20} All clinic processing finished. Returning data. {'='*20}")
    # print(f"Check the '{BASE_OUTPUT_DIR}' directory for intermediate output files if needed.")
    return all_clinics_csa_data

if __name__ == "__main__":
    print("Running process_clinics.py as a standalone script for testing...")
    data = get_aggregated_clinic_data()
    if data:
        print("\nSuccessfully retrieved aggregated data:")
        # Print a summary or a few items for brevity
        for clinic, clinic_data in list(data.items())[:2]: # Print first 2 clinics
            print(f"\nClinic: {clinic}")
            # print(json.dumps(clinic_data, indent=2)) # Can be very verbose
            print(f"  Number of cohorts/keys: {len(clinic_data.keys()) if isinstance(clinic_data, dict) else 'N/A (not a dict)'}")
        if len(data) > 2:
            print(f"\n... and {len(data) - 2} more clinics.")
    else:
        print("\nNo data retrieved or an error occurred.")
    print("\nStandalone script execution finished.")
