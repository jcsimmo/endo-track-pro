# CSA_REPLACEMENT_CHAIN_PLAN_NOTE
# ---------------------------------
# Development Status:
# This script (csa_replacement_chain.py) now reads data EXCLUSIVELY
# from the 'oasis_orders_returns.json' file to build and print
# the CSA replacement chains for the customer 'Oasis ENT'.
# It DOES NOT make any API calls.
# It is filtered to ONLY process and report on SKU 'P313N00'.
# CSA Length determination prioritizes "1 year" or "2 year" in Name over SKU.
# Calculates End Date and 60-Day Warning Date for cohorts.
# Prioritizes delivery_date, falls back to shipment_date for shipment events.
# **UPDATED**: Includes speculative orphan chain building and cohort association.
# ---------------------------------

import os
import json
import sys
from datetime import datetime, timedelta, date # Ensure date is imported
from dateutil.relativedelta import relativedelta
from collections import deque, defaultdict
from io import StringIO
import argparse # Add argparse

# Target SKU for filtering
TARGET_ENDOSCOPE_SKU = 'P313N00'
ENDOSCOPE_SKUS = {TARGET_ENDOSCOPE_SKU} # Use a set for efficient lookup
SPECULATIVE_REPLACEMENT_WINDOW_DAYS = 30 # Days to look forward for an orphan replacement


# Create a class to capture output to both console and a string
class TeeOutput:
    def __init__(self, filename=None):
        self.terminal = sys.stdout
        self.output = StringIO()
        self.filename = filename
        self._original_stdout = sys.stdout
        self._original_stderr = sys.stderr

    def write(self, message):
        # Ensure message is treated as string, handle potential non-string inputs gracefully
        try:
            message_str = str(message)
            # Add newline automatically like print() does
            # Check if the message already ends with a newline
            if not message_str.endswith('\n'):
                 message_str += '\n'
        except Exception:
            message_str = "[TeeOutput: Error converting message to string]\n"

        self.terminal.write(message_str)
        self.output.write(message_str)

    def flush(self):
        self.terminal.flush()

    def save_to_file(self):
        if self.filename:
            output_dir = os.path.dirname(self.filename)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            try:
                with open(self.filename, 'w') as f:
                    f.write(self.output.getvalue())
                print(f"\nOutput saved to {self.filename}", file=self._original_stdout) # Print save confirmation to original stdout
            except Exception as e:
                print(f"\nError saving output to {self.filename}: {e}", file=self._original_stderr) # Print error to original stderr

    # Allow using TeeOutput with 'with' statement for cleaner redirection
    def __enter__(self):
        sys.stdout = self
        sys.stderr = self
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
        sys.stdout = self._original_stdout
        sys.stderr = self._original_stderr
        # Optionally handle exceptions here if needed
        # if exc_type:
        #    print(f"Exception occurred: {exc_val}", file=self._original_stderr)
        self.save_to_file() # Save when exiting the 'with' block


def parse_date_flexible(datestr):
    """Attempt to parse a date string in a few common formats; return datetime object or None."""
    if not datestr or not isinstance(datestr, str):
        return None
    if datestr.strip().lower() in ['not shipped', 'not recorded', '']:
        return None

    # Handle potential Excel date numbers (simple check for now)
    if datestr.isdigit() and len(datestr) == 5: # Basic check for Excel date numbers
         try:
             # Excel date origin: December 30, 1899 (or Jan 1, 1900 depending on system)
             # Python's datetime origin: January 1, 1900 is day 1
             # This conversion assumes the 1900 date system (most common)
             # Subtract 2 because Excel considers 1900 a leap year incorrectly AND difference in origin day count
             excel_date_number = int(datestr)
             if excel_date_number > 60: # Adjust for Excel leap year bug
                 dt = datetime(1899, 12, 30) + timedelta(days=excel_date_number)
             else: # For dates before Feb 29, 1900
                  dt = datetime(1899, 12, 30) + timedelta(days=excel_date_number-1) # incorrect original implementation?
                  # Safer to just handle common formats if excel numbers are rare/uncertain
                  # Let's revert to format parsing unless Excel dates are confirmed
             # print(f"Warning: Interpreted '{datestr}' as Excel date number.", file=sys.stderr)
             # return dt # Return if enabling Excel date parsing
         except ValueError:
             pass # Ignore if it's not a simple integer


    possible_formats = [
        '%Y-%m-%d',        # 2023-10-26
        '%m/%d/%Y',        # 10/26/2023
        '%m/%d/%y',        # 10/26/23
        '%Y-%m-%dT%H:%M:%S', # ISO format-like (ignore time part)
        '%Y-%m-%d %H:%M:%S', # Date and Time (ignore time part)
        '%Y-%m-%d %H:%M',   # Date and Time short (ignore time part)
        '%b %d, %Y',       # Oct 26, 2023
        '%d-%b-%Y',       # 26-Oct-2023
    ]
    for fmt in possible_formats:
        try:
            # Try parsing only the date part if format includes time or 'T'
            base_part = datestr.split('T')[0].split(' ')[0]
            dt = datetime.strptime(base_part, fmt.split('T')[0].split(' ')[0])
            return dt.date() # Return only the date part
        except ValueError:
            continue
        except Exception as e:
             print(f"Warning: Error parsing date '{datestr}' with format '{fmt}': {e}", file=sys.stderr)
    print(f"Warning: Could not parse date '{datestr}' with any known format.", file=sys.stderr)
    return None

def dt_to_str(dt):
    """Convert date or datetime object to 'YYYY-MM-DD' string, return 'N/A' if input is None."""
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d')
    elif isinstance(dt, date): # Handle date objects too
        return dt.strftime('%Y-%m-%d')
    else:
        return 'N/A'

# --- NEW HELPER FUNCTIONS for ORPHAN ANALYSIS ---

def build_speculative_orphan_chains(orphan_serials, scope_map, window_days):
    """
    Attempts to build chains from orphan serials based on return/ship dates.

    Args:
        orphan_serials (set): Set of serial numbers identified as orphans (cohort=None).
        scope_map (dict): The fully populated scopeMap containing status and dates.
        window_days (int): The time window (in days) to look for a replacement.

    Returns:
        list: A list of speculative chains, where each chain is a dictionary.
              Returns empty list if no orphans.
    """
    if not orphan_serials:
        return []

    speculative_chains = []
    processed_in_spec_chain = set() # Track serials already part of a built speculative chain

    # Separate orphans that have been returned from those only shipped
    returned_orphans = {
        sn for sn in orphan_serials
        if scope_map.get(sn, {}).get('currentStatus', '').startswith('returned')
        or scope_map.get(sn, {}).get('rmaDate') is not None
    }
    # Need return dates for sorting and window calculation
    returned_orphan_details = []
    for sn in returned_orphans:
        details = scope_map.get(sn)
        if details and details.get('rmaDate') and details['rmaDate'] != 'N/A':
            try:
                # Ensure rmaDate is datetime.date for comparison
                rma_dt = parse_date_flexible(details['rmaDate'])
                if rma_dt:
                    returned_orphan_details.append({'serial': sn, 'rma_date': rma_dt})
                else:
                     print(f"Warning [Orphan Chain Build]: Could not parse RMA date '{details['rmaDate']}' for orphan {sn}.", file=sys.stderr)
            except Exception as e:
                 print(f"Error parsing RMA date for orphan {sn}: {e}", file=sys.stderr)

    # Sort returned orphans by RMA date to process chronologically
    returned_orphan_details.sort(key=lambda x: x['rma_date'])

    # Create a lookup for potential replacements (orphans with ship dates)
    potential_replacements = []
    for sn in orphan_serials:
         details = scope_map.get(sn)
         # Use originalShipmentDate as the key date
         ship_date_str = details.get('originalShipmentDate')
         if details and ship_date_str and ship_date_str != 'N/A':
             ship_dt = parse_date_flexible(ship_date_str)
             if ship_dt:
                 potential_replacements.append({'serial': sn, 'ship_date': ship_dt})

    potential_replacements.sort(key=lambda x: x['ship_date']) # Sort by ship date


    # Iterate through chronologically sorted *returned* orphans to start chains
    for returned_detail in returned_orphan_details:
        start_sn = returned_detail['serial']

        # Skip if this serial was already included in another speculative chain
        if start_sn in processed_in_spec_chain:
            continue

        # Try to build a chain starting from this returned orphan
        current_chain = []
        current_handoffs = []
        current_sn = start_sn
        visited_in_this_chain_attempt = set() # Local cycle detection

        while current_sn and current_sn in orphan_serials and current_sn not in visited_in_this_chain_attempt:
            visited_in_this_chain_attempt.add(current_sn)
            current_chain.append(current_sn)

            details = scope_map.get(current_sn)
            if not details: # Should not happen if scopeMap is complete
                 print(f"Error [Orphan Chain Build]: Orphan {current_sn} not found in scopeMap!", file=sys.stderr)
                 break # Stop this chain attempt

            # Is this serial returned?
            rma_date_str = details.get('rmaDate')
            if rma_date_str and rma_date_str != 'N/A':
                rma_dt = parse_date_flexible(rma_date_str)
                if not rma_dt:
                    # Cannot proceed without a valid return date to calculate window
                    current_sn = None # End the chain here
                    continue

                # Look for the earliest available *orphan* replacement shipped within the window
                best_replacement_sn = None
                best_replacement_date = None

                for rep_detail in potential_replacements:
                    cand_sn = rep_detail['serial']
                    cand_ship_dt = rep_detail['ship_date']

                    # Check conditions:
                    # 1. Must not be the same serial
                    # 2. Must not be already used in *any* speculative chain started so far
                    # 3. Must be shipped *after* the return date (or same day?) -> Strictly after for safety
                    # 4. Must be shipped within the window
                    if (cand_sn != current_sn and
                        cand_sn not in processed_in_spec_chain and
                        cand_ship_dt > rma_dt and # Ship date > RMA date
                        cand_ship_dt <= rma_dt + timedelta(days=window_days)):

                        # Found a potential candidate, is it the earliest?
                        if best_replacement_sn is None or cand_ship_dt < best_replacement_date:
                            best_replacement_sn = cand_sn
                            best_replacement_date = cand_ship_dt
                        # Since potential_replacements is sorted by ship_date, the first one found is the best.
                        break # Found the earliest

                if best_replacement_sn:
                     # Found replacement, add handoff, mark used, continue chain
                     replacement_ship_date_str = dt_to_str(best_replacement_date)
                     current_handoffs.append(f"Returned {current_sn} on {rma_date_str}, potentially replaced by {best_replacement_sn} shipped on {replacement_ship_date_str}")
                     processed_in_spec_chain.add(best_replacement_sn) # Mark as used
                     current_sn = best_replacement_sn # Move to next link
                else:
                     # No replacement found for this returned orphan
                     current_sn = None # End the chain here
            else:
                 # Current serial was not returned (it's an in-field orphan ending a chain)
                 current_sn = None # End the chain here


        # After the loop, store the constructed chain if it's non-empty
        if current_chain:
            final_sn_in_chain = current_chain[-1]
            final_details = scope_map.get(final_sn_in_chain, {})
            # Determine final status based on scopeMap (might be inField or returned_...)
            final_status = final_details.get('currentStatus', 'Unknown')
            status_desc = get_status_description(final_status)

            speculative_chains.append({
                "chain": current_chain,
                "handoffs": current_handoffs,
                "final_status": final_status,
                "final_status_description": status_desc,
                "final_serial_number": final_sn_in_chain,
                "starter_serial": current_chain[0] # Keep track of the first serial
            })
            # Mark all serials in this *successfully* built chain as processed
            for sn in current_chain:
                 processed_in_spec_chain.add(sn)


    # Add any remaining orphans that were never returned and didn't start a chain
    remaining_unlinked_orphans = orphan_serials - processed_in_spec_chain
    for sn in sorted(list(remaining_unlinked_orphans)):
         details = scope_map.get(sn, {})
         final_status = details.get('currentStatus', 'Unknown')
         # Ensure it wasn't actually returned
         if not final_status.startswith('returned') and details.get('rmaDate') is None:
              status_desc = get_status_description(final_status)
              speculative_chains.append({
                  "chain": [sn],
                  "handoffs": [],
                  "final_status": final_status,
                  "final_status_description": status_desc,
                  "final_serial_number": sn,
                  "starter_serial": sn
              })

    return speculative_chains

def associate_orphans_to_cohorts(orphan_chains, scope_map, csa_cohorts):
    """
    Assigns speculative orphan chains/units to the most likely CSA cohort.

    Args:
        orphan_chains (list): List of speculative chains from build_speculative_orphan_chains.
        scope_map (dict): The fully populated scopeMap.
        csa_cohorts (list): List of known CSA cohort dictionaries (must include startDateObj).

    Returns:
        list: The input orphan_chains list with an added 'assigned_cohort' field.
    """
    if not csa_cohorts: # Cannot associate if no cohorts exist
        for chain in orphan_chains:
            chain['assigned_cohort'] = "No CSA Cohorts Defined"
            chain['assignment_reason'] = "N/A"
        return orphan_chains

    # Sort cohorts by start date (earliest first) for easier processing
    # Ensure startDateObj is a date object for comparison
    valid_cohorts = []
    for c in csa_cohorts:
        if isinstance(c.get('startDateObj'), date):
             valid_cohorts.append(c)
        else:
            print(f"Warning [Orphan Assoc]: Cohort {c.get('orderId')} missing valid startDateObj. Cannot use for association.", file=sys.stderr)

    valid_cohorts.sort(key=lambda x: x['startDateObj'])

    for chain_data in orphan_chains:
        starter_sn = chain_data['starter_serial']
        starter_details = scope_map.get(starter_sn)

        if not starter_details:
            chain_data['assigned_cohort'] = "Error: Starter Not Found"
            chain_data['assignment_reason'] = f"Starter serial {starter_sn} missing from scopeMap."
            continue

        initial_ship_date_str = starter_details.get('originalShipmentDate')
        initial_ship_dt = parse_date_flexible(initial_ship_date_str)

        if not initial_ship_dt:
            chain_data['assigned_cohort'] = "Error: Invalid Ship Date"
            chain_data['assignment_reason'] = f"Cannot parse initial ship date '{initial_ship_date_str}' for starter {starter_sn}."
            continue

        # Find the latest cohort that started *on or before* the initial shipment date
        best_cohort = None
        for cohort in reversed(valid_cohorts): # Check latest first
            if cohort['startDateObj'] <= initial_ship_dt:
                best_cohort = cohort
                break # Found the latest applicable cohort

        if best_cohort:
            chain_data['assigned_cohort'] = best_cohort['orderId']
            chain_data['assignment_reason'] = f"Initial ship date {dt_to_str(initial_ship_dt)} is on or after cohort {best_cohort['orderId']} start date {best_cohort['startDate']}."

            # Check for ambiguity (optional but helpful)
            # This requires knowing replacement dates for cohorts - more complex
            # Simple check: if ship date matches another cohort's start? Less reliable.
            # We'll skip ambiguity flag for now based *purely* on date logic.

        else:
            # Shipped before the earliest known cohort
             chain_data['assigned_cohort'] = "Pre-CSA / Unknown"
             earliest_cohort_start = valid_cohorts[0]['startDate'] if valid_cohorts else 'N/A'
             chain_data['assignment_reason'] = f"Initial ship date {dt_to_str(initial_ship_dt)} is before the earliest known cohort start date ({earliest_cohort_start})."

    return orphan_chains


def get_status_description(status_code):
    """Helper function to get a user-friendly status description."""
    return {
        "inField": "In Field",
        "returned_replaced": "Returned & Replaced",
        "returned_no_replacement_found": "Returned (No Replacement Shipment Found)",
        "returned_no_replacement_available": "Returned (No Replacements Left in Cohort)",
        "returned_error_no_cohort": "Returned (Error: Cohort Issue)",
         # Add statuses for orphan chains if needed, though they often end 'inField' or use above 'returned' codes
        "Unknown": "Unknown"
    }.get(status_code, status_code) # Default to the code itself if not mapped


# --- MAIN FUNCTION ---
def build_csa_replacement_chains(input_json_path, output_json_path, output_md_path):
    """
    Loads data from input_json_path, builds CSA replacement chains,
    builds speculative orphan chains, associates orphans, prints results,
    and saves structured data to JSON.
    FILTERED for TARGET_ENDOSCOPE_SKU.
    """
    results_data = {
        "processing_info": {},
        "warnings_errors": [],
        "csa_replacement_chains": [],
        "speculative_orphan_analysis": [], # Renamed from orphan_replacement_chains
        "status_summary": {},
        # "orphan_serials": {} # Removed, orphans are now part of the analysis output
    }

    # Use the provided input path
    print(f"Loading data from: {input_json_path}")
    results_data["processing_info"]["json_file_path"] = input_json_path

    if not os.path.exists(input_json_path):
        print(f"ERROR: JSON file not found at {input_json_path}", file=sys.stderr)
        return

    try:
        with open(input_json_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading or parsing JSON file {input_json_path}: {e}", file=sys.stderr)
        return

    sales_orders = data.get('sales_orders', data.get('salesorders', []))
    sales_returns = data.get('sales_returns', data.get('salesreturns', []))
    # Try to get a meaningful name if available from Step 1, otherwise use a placeholder
    contact_ids_processed = data.get('contact_ids_processed', [])
    customer_name = f"Group ({','.join(contact_ids_processed)})" # Placeholder name

    print(f"Processing data for customer group: {customer_name}")
    results_data["processing_info"]["customer_name_or_group"] = customer_name
    results_data["processing_info"]["contact_ids_processed"] = contact_ids_processed
    print(f"Found {len(sales_orders)} sales orders and {len(sales_returns)} sales returns in the JSON file.")
    results_data["processing_info"]["sales_order_count"] = len(sales_orders)
    results_data["processing_info"]["sales_return_count"] = len(sales_returns)
    print(f"\n--- Filtering all processing for SKU: {TARGET_ENDOSCOPE_SKU} ---")
    results_data["processing_info"]["target_sku"] = TARGET_ENDOSCOPE_SKU

    # --- Step 1: Extract and sort shipment events (FILTERED BY SKU) ---
    shipment_events = []
    # ... (Keep the existing shipment extraction logic using parse_date_flexible) ...
    # (Code identical to user's original shipment extraction - omitted for brevity)
    for so in sales_orders:
        so_number = so.get('salesorder_number')
        for pkg in so.get('packages', []):
            pkg_number = pkg.get('package_number')
            shipment_order = pkg.get('shipment_order', {})

            # --- MODIFIED DATE LOGIC ---
            date_str_to_parse = None
            date_type_used = "unknown" # Track which date was used
            # 1. Try delivery_date from shipment_order
            delivery_date_so = shipment_order.get('delivery_date')
            if delivery_date_so and str(delivery_date_so).strip().lower() not in ['not shipped', 'not recorded', '']:
                date_str_to_parse = delivery_date_so
                date_type_used = "delivery_date (shipment_order)"
            else:
                # 2. Try delivery_date from package level
                delivery_date_pkg = pkg.get('delivery_date')
                if delivery_date_pkg and str(delivery_date_pkg).strip().lower() not in ['not shipped', 'not recorded', '']:
                    date_str_to_parse = delivery_date_pkg
                    date_type_used = "delivery_date (package)"
                else:
                    # 3. Try shipment_date from shipment_order as FINAL fallback
                    shipment_date_so = shipment_order.get('shipment_date')
                    if shipment_date_so and str(shipment_date_so).strip().lower() not in ['not shipped', 'not recorded', '']:
                        date_str_to_parse = shipment_date_so
                        date_type_used = "shipment_date (shipment_order)"
                        print(f"Info: Using shipment_date '{shipment_date_so}' as fallback for SO {so_number} PKG {pkg_number}", file=sys.stderr)

            # Parse the determined date string (or None if none were found/valid)
            dt = parse_date_flexible(date_str_to_parse) # Returns date object or None
            # --- END OF MODIFIED DATE LOGIC ---

            for line in pkg.get('detailed_line_items', []):
                line_sku = line.get('sku')
                if line_sku == TARGET_ENDOSCOPE_SKU:
                    serial_numbers = line.get('serial_numbers', [])
                    processed_serials = []
                    if isinstance(serial_numbers, list):
                         processed_serials = [str(sn).strip() for sn in serial_numbers if sn]
                    elif serial_numbers: # Handle case where it might be a single string
                         sn = str(serial_numbers).strip()
                         if sn:
                             processed_serials.append(sn)

                    for sn in processed_serials:
                        shipment_events.append({
                            'date': dt, # date obj or None based on new logic
                            'so_number': so_number,
                            'package_number': pkg_number,
                            'serial': sn,
                            'sku': line_sku,
                            'date_type': date_type_used # Store which date type was parsed
                        })

    # Sort events: put events with None dates last, then by date
    shipment_events.sort(key=lambda x: (x['date'] is None, x['date']))
    print(f"Extracted {len(shipment_events)} shipment events for SKU {TARGET_ENDOSCOPE_SKU}.")
    all_shipped_target_serials = {evt['serial'] for evt in shipment_events if evt['serial']}

    # --- Step 2: Initialize scopeMap with ALL shipped target serials ---
    scopeMap = {} # Stores details for every serial involved
    for sn in all_shipped_target_serials:
        # Find the earliest shipment event for this serial to get its initial ship date
        initial_shipment = min(
            (ship for ship in shipment_events if ship['serial'] == sn and ship['date'] is not None),
            key=lambda x: x['date'],
            # Fallback: find *any* shipment event if none have dates (less ideal)
            default=next((ship for ship in shipment_events if ship['serial'] == sn), None)
        )
        initial_ship_date = dt_to_str(initial_shipment['date']) if initial_shipment and initial_shipment['date'] else 'N/A'
        initial_ship_date_obj = initial_shipment['date'] if initial_shipment and initial_shipment['date'] else None

        scopeMap[sn] = {
            'serial': sn,
            'currentStatus': 'inField',     # Initial status
            'replacedBy': None,             # Serial number that replaced this one
            'replacedScope': None,          # Serial number that this one replaced
            'cohort': None,                 # Initialize cohort as None
            'rmaDate': None,                # Date this specific serial was returned (as string)
            'rmaDateObj': None,             # Date this specific serial was returned (as date obj)
            'replacementShipDate': None,    # Date the *replacement* for this serial was shipped (as string)
            'replacementShipDateObj': None, # Date the *replacement* for this serial was shipped (as date obj)
            'originalShipmentDate': initial_ship_date, # Date this serial was first shipped (as string)
            'originalShipmentDateObj': initial_ship_date_obj, # Date this serial was first shipped (as date obj)
            'csaItemSku': TARGET_ENDOSCOPE_SKU,
            'csaItemName': f'{TARGET_ENDOSCOPE_SKU}' # Simple name
        }
    print(f"Initialized scopeMap with {len(scopeMap)} unique shipped serials.")


    # --- Step 3: Extract and sort RMA events (FILTERED BY PLAUSIBILITY) ---
    rma_events = []
    unfiltered_rma_count = 0
    # ... (Keep the existing RMA extraction logic using parse_date_flexible) ...
    # ... (It correctly filters for serials present in all_shipped_target_serials) ...
    # (Code identical to user's original RMA extraction - omitted for brevity)
    for rma in sales_returns:
        rma_number = rma.get('salesreturn_number')
        receipts_key = 'salesreturnreceives' if 'salesreturnreceives' in rma else 'return_receipts'
        receipts_data = rma.get(receipts_key, [])
        if not isinstance(receipts_data, list):
             print(f"Warning: Expected list for receipts key '{receipts_key}' in RMA {rma_number}, got {type(receipts_data)}. Skipping.", file=sys.stderr)
             continue

        for receipt in receipts_data:
            receipt_number = receipt.get('receive_number')
            receipt_date_str = receipt.get('date')
            dt = parse_date_flexible(receipt_date_str) # Returns date obj or None
            if not dt:
                print(f"Warning: Skipping receipt {receipt_number} in RMA {rma_number} due to unparseable date '{receipt_date_str}'.", file=sys.stderr)
                continue

            line_items_data = receipt.get('line_items', [])
            if not isinstance(line_items_data, list):
                print(f"Warning: Expected list for 'line_items' in receipt {receipt_number} RMA {rma_number}, got {type(line_items_data)}. Skipping.", file=sys.stderr)
                continue

            for line in line_items_data:
                serial_numbers = line.get('serial_numbers', [])
                processed_serials = []
                if isinstance(serial_numbers, list):
                     processed_serials = [str(sn).strip() for sn in serial_numbers if sn]
                elif serial_numbers:
                     sn = str(serial_numbers).strip()
                     if sn:
                         processed_serials.append(sn)

                for sn in processed_serials:
                    unfiltered_rma_count += 1
                    # Crucial Filter: Only consider returns if the serial was previously shipped as the target SKU
                    if sn in all_shipped_target_serials:
                        rma_events.append({
                            'date': dt, # date obj
                            'rma_number': rma_number,
                            'receipt_number': receipt_number,
                            'serial': sn,
                            'sku': TARGET_ENDOSCOPE_SKU # Assume returned item is the target SKU if serial matches
                        })

    # Sort by date object
    rma_events.sort(key=lambda x: x['date'])
    print(f"Extracted {len(rma_events)} RMA events potentially related to SKU {TARGET_ENDOSCOPE_SKU} (out of {unfiltered_rma_count} total serials found in receipts).")
    all_returned_target_serials = {evt['serial'] for evt in rma_events if evt['serial']}


    # --- Step 4: Identify CSA cohorts and Update scopeMap ---
    csa_sku_keywords = ['HiFCSA-1yr', 'HiFCSA-2yr']
    csa_cohorts = []
    serial_to_cohort_map = {} # Use this specific map for original cohort members only

    # ... (Keep the existing CSA cohort identification and length determination logic) ...
    # ... (It correctly identifies cohorts and finds start dates using parse_date_flexible) ...
    # (Code identical to user's original cohort finding logic - omitted for brevity, but included below)
    for so in sales_orders:
        so_number = so.get('salesorder_number')
        so_line_items = so.get('line_items', [])
        if not isinstance(so_line_items, list):
             print(f"Warning: Expected list for 'line_items' in SO {so_number}, got {type(so_line_items)}. Skipping cohort check.", file=sys.stderr)
             continue

        has_any_csa_plan = any(
            any(kw in (item.get('sku', '') or '') for kw in csa_sku_keywords)
            or ('csa' in (item.get('name','') or '').lower() and 'prepaid' in (item.get('name','') or '').lower()) # Broader name check
            for item in so_line_items if isinstance(item, dict) # Ensure item is a dict
        )
        if not has_any_csa_plan:
            continue

        # --- Determine CSA Length (Prioritize Name over SKU) ---
        csa_length = "Unknown"
        found_csa_item_for_length = False
        temp_length_from_sku = None

        for item in so_line_items:
            if not isinstance(item, dict): continue # Skip non-dict items
            item_sku = item.get("sku", "") or "" # Ensure string
            item_name = (item.get("name", "") or "").lower() # Ensure string and lower

            is_this_a_csa_item = False
            if any(kw in item_sku for kw in csa_sku_keywords): is_this_a_csa_item = True
            if 'csa' in item_name and 'prepaid' in item_name: is_this_a_csa_item = True

            if is_this_a_csa_item:
                 found_csa_item_for_length = True
                 if "2 year" in item_name:
                     csa_length = "2 year"; break
                 elif "1 year" in item_name:
                     csa_length = "1 year"
                     # Continue checking in case a 2yr item exists

                 if "hifcsa-2yr" in item_sku.lower():
                      temp_length_from_sku = "2 year"
                 elif "hifcsa-1yr" in item_sku.lower():
                      if temp_length_from_sku != "2 year":
                          temp_length_from_sku = "1 year"

        if csa_length == "Unknown" and temp_length_from_sku:
            csa_length = temp_length_from_sku
        if csa_length == "Unknown" and found_csa_item_for_length:
             print(f"Warning: SO {so_number} has a CSA item, but length ('1 year'/'2 year') could not be determined from name or SKU.", file=sys.stderr)
        # --- End of Length Determination ---

        cohort_serials = []
        shipment_dates = [] # List of date objects for *this* cohort's shipments
        found_target_scopes_in_so = False
        packages_data = so.get('packages', [])
        if not isinstance(packages_data, list):
             print(f"Warning: Expected list for 'packages' in SO {so_number}, got {type(packages_data)}. Skipping serial collection.", file=sys.stderr)
             continue

        for pkg in packages_data:
            # --- RE-APPLY MODIFIED DATE LOGIC ---
            pkg_shipment_order = pkg.get('shipment_order', {})
            pkg_date_str = None; pkg_date_type="unknown"
            pkg_delivery_so = pkg_shipment_order.get('delivery_date')
            if pkg_delivery_so and str(pkg_delivery_so).strip().lower() not in ['not shipped', 'not recorded', '']:
                pkg_date_str = pkg_delivery_so; pkg_date_type="delivery (SO)"
            else:
                pkg_delivery_pkg = pkg.get('delivery_date')
                if pkg_delivery_pkg and str(pkg_delivery_pkg).strip().lower() not in ['not shipped', 'not recorded', '']:
                     pkg_date_str = pkg_delivery_pkg; pkg_date_type="delivery (PKG)"
                else:
                     pkg_shipment_so = pkg_shipment_order.get('shipment_date')
                     if pkg_shipment_so and str(pkg_shipment_so).strip().lower() not in ['not shipped', 'not recorded', '']:
                         pkg_date_str = pkg_shipment_so; pkg_date_type="shipment (SO)"
            pkg_dt = parse_date_flexible(pkg_date_str) # date obj or None
            # --- END OF RE-APPLIED DATE LOGIC ---

            detailed_lines_data = pkg.get('detailed_line_items', [])
            if not isinstance(detailed_lines_data, list): continue

            for detailed_line in detailed_lines_data:
                if not isinstance(detailed_line, dict): continue
                if detailed_line.get('sku') == TARGET_ENDOSCOPE_SKU:
                    serials = detailed_line.get('serial_numbers', [])
                    processed_pkg_serials = []
                    if isinstance(serials, list):
                         processed_pkg_serials = [str(sn).strip() for sn in serials if sn]
                    elif serials:
                         sn_str = str(serials).strip()
                         if sn_str : processed_pkg_serials.append(sn_str)

                    if processed_pkg_serials:
                        found_target_scopes_in_so = True
                        for sn in processed_pkg_serials:
                            cohort_serials.append(sn)
                            if pkg_dt: shipment_dates.append(pkg_dt)


        if not found_target_scopes_in_so:
             print(f"Warning: SO {so_number} has a CSA plan but no shipped SKU {TARGET_ENDOSCOPE_SKU} found in its packages.", file=sys.stderr)
             continue

        start_date_obj = None; start_source = "Unknown"
        if shipment_dates:
            start_date_obj = min(shipment_dates)
            start_source = "Earliest ship/delivery date"
        else:
            so_date_str = so.get('date'); temp_dt = parse_date_flexible(so_date_str)
            if temp_dt:
                 start_date_obj = temp_dt; start_source = "SO date (fallback)"
                 print(f"Warning: Using SO date '{dt_to_str(start_date_obj)}' as start for cohort {so_number}.", file=sys.stderr)
            else: print(f"Critical Warning: Cannot determine start date for cohort {so_number}.", file=sys.stderr)

        end_date_obj = None; warning_date_obj = None
        if start_date_obj:
            years_to_add = 1 if csa_length == "1 year" else (2 if csa_length == "2 year" else 0)
            if years_to_add > 0:
                end_date_obj = start_date_obj + relativedelta(years=years_to_add)
                warning_date_obj = end_date_obj - timedelta(days=60)
            else: print(f"Warning: Unknown CSA length for {so_number}. Cannot calc end/warn dates.", file=sys.stderr)

        initial_scope_count = len(set(s for s in cohort_serials if s))
        replacements_per_scope = 4 # Assume 4
        total_replacements = initial_scope_count * replacements_per_scope

        cohort_data = {
            'orderId': so_number,
            'startDate': dt_to_str(start_date_obj),
            'startDateObj': start_date_obj, # Keep date object
            'startSource': start_source,
            'csaScopes': sorted(list(set(s for s in cohort_serials if s))),
            'initialScopeCount': initial_scope_count,
            'totalReplacements': total_replacements,
            'remainingReplacements': total_replacements,
            'csaLength': csa_length,
            'endDate': dt_to_str(end_date_obj),
            'warningDate': dt_to_str(warning_date_obj)
        }
        csa_cohorts.append(cohort_data)

        # --- IMPORTANT: Update scopeMap and build serial_to_cohort_map ---
        for sn in cohort_data['csaScopes']:
            if sn in scopeMap:
                # Check if already assigned - log warning, keep first assignment
                if scopeMap[sn]['cohort'] is not None and scopeMap[sn]['cohort'] != so_number:
                     print(f"Warning: Serial {sn} reassigned from cohort {scopeMap[sn]['cohort']} to {so_number}. Check data.", file=sys.stderr)
                scopeMap[sn]['cohort'] = so_number # Assign cohort ID
                serial_to_cohort_map[sn] = cohort_data # Map original serial to its cohort
            else:
                 # This should not happen if scopeMap initialization was complete
                 print(f"Error: Serial {sn} from cohort {so_number} not found in initialized scopeMap!", file=sys.stderr)


    print(f"Identified {len(csa_cohorts)} relevant CSA cohorts for SKU {TARGET_ENDOSCOPE_SKU}.")
    if not csa_cohorts:
        print("No relevant CSA cohorts found. Exiting chain building.")
        return

    # --- Step 5: Process RMAs & Build Validated Chains (using updated scopeMap) ---
    # Create a pool of potential replacement shipments (target SKU, *ANY* serial, with a date)
    # We filter later based on whether it's used
    available_shipments = deque(
        ship for ship in shipment_events
        if ship['serial'] and ship.get('sku') == TARGET_ENDOSCOPE_SKU and ship['date'] is not None
    )
    available_shipments = deque(sorted(available_shipments, key=lambda x: x['date']))

    used_replacement_serials = set() # Track serials used *as replacements* in validated chains

    print(f"Processing {len(rma_events)} relevant RMA events against {len(available_shipments)} potentially available {TARGET_ENDOSCOPE_SKU} shipments.")

    for rma in rma_events:
        returned_sn = rma['serial']
        rma_date_obj = rma['date'] # date object

        if returned_sn not in scopeMap: continue # Should not happen now
        if scopeMap[returned_sn]['currentStatus'] != 'inField': continue # Already processed

        scopeMap[returned_sn]['rmaDate'] = dt_to_str(rma_date_obj) # Store return date string
        scopeMap[returned_sn]['rmaDateObj'] = rma_date_obj        # Store return date object

        # Find the cohort associated with the returned serial (could be None if it's an orphan)
        cohort_id = scopeMap[returned_sn]['cohort']
        cohort = None
        if cohort_id:
             cohort = next((c for c in csa_cohorts if c['orderId'] == cohort_id), None)

        # If it belongs to a cohort, check for replacements left
        can_replace_under_csa = False
        if cohort and cohort['remainingReplacements'] > 0:
            can_replace_under_csa = True
        elif cohort and cohort['remainingReplacements'] <= 0:
            # print(f"Info: Serial {returned_sn} (Cohort {cohort_id}) returned on {dt_to_str(rma_date_obj)}, but no replacements left.", file=sys.stderr)
            scopeMap[returned_sn]['currentStatus'] = 'returned_no_replacement_available'
            # Don't look for replacement if none available under CSA
            continue # Skip to next RMA


        # If it can be replaced (under CSA or potentially as an orphan swap - though less likely needed now)
        # Find the earliest available replacement shipped on or after the RMA date
        replacement = None
        replacement_idx = -1
        for idx, ship in enumerate(available_shipments):
            # Ship date must be on or after RMA date
            if ship['date'] >= rma_date_obj:
                # Replacement cannot be the same serial
                if ship['serial'] == returned_sn: continue
                # Check if the candidate serial has already been used as a replacement *in a validated chain*
                if ship['serial'] in used_replacement_serials: continue
                # Check if the candidate is currently 'inField' (it might have been returned itself already)
                if ship['serial'] in scopeMap and scopeMap[ship['serial']]['currentStatus'] != 'inField': continue

                replacement = ship
                replacement_idx = idx
                break # Found the best match (earliest available)

        if replacement:
            new_sn = replacement['serial']
            replacement_ship_date_obj = replacement['date']

            # Decrement cohort replacements IF this return was under a valid cohort
            if cohort and can_replace_under_csa:
                cohort['remainingReplacements'] -= 1

            # Update status of the returned scope
            scopeMap[returned_sn]['currentStatus'] = 'returned_replaced'
            scopeMap[returned_sn]['replacedBy'] = new_sn
            scopeMap[returned_sn]['replacementShipDate'] = dt_to_str(replacement_ship_date_obj)
            scopeMap[returned_sn]['replacementShipDateObj'] = replacement_ship_date_obj

            # Update the replacement scope in scopeMap
            if new_sn not in scopeMap:
                 # This should not happen if scopeMap init was complete
                 print(f"CRITICAL Error: Replacement serial {new_sn} not found in scopeMap!", file=sys.stderr)
                 continue # Skip this replacement

            scopeMap[new_sn]['currentStatus'] = 'inField' # It's now the active scope
            scopeMap[new_sn]['replacedScope'] = returned_sn # Link back
            # IMPORTANT: Assign cohort ID to the replacement only if the returned item was part of a cohort
            if cohort:
                 scopeMap[new_sn]['cohort'] = cohort_id
            # Otherwise, the replacement remains without a cohort unless it started with one

            # Mark this serial as used *as a replacement* in the main chain logic
            used_replacement_serials.add(new_sn)
            # Remove from *available* pool (can't be used again)
            del available_shipments[replacement_idx]

        else:
            # No suitable replacement found in the available shipments
            # print(f"Info: Serial {returned_sn} returned on {dt_to_str(rma_date_obj)}, but no suitable replacement shipment found.", file=sys.stderr)
            scopeMap[returned_sn]['currentStatus'] = 'returned_no_replacement_found'
            # Decrement cohort replacements if applicable (opportunity used)
            if cohort and can_replace_under_csa:
                 cohort['remainingReplacements'] -= 1


    # --- Step 6: Build and Print Validated CSA Chains ---
    print("\n" + "="*30 + f" Validated CSA Replacement Chains ({TARGET_ENDOSCOPE_SKU} Only) " + "="*25) # Adjusted title
    chains_by_cohort = defaultdict(list)
    all_serials_in_validated_chains = set() # Track serials in *validated* chains

    # Iterate through original scopes mapped to cohorts
    for orig_sn, cohort_data in serial_to_cohort_map.items():
        if not orig_sn or orig_sn not in scopeMap: continue

        chain = []
        handoffs = []
        current_sn = orig_sn
        visited_in_chain = set()

        while current_sn and current_sn not in visited_in_chain:
            visited_in_chain.add(current_sn)
            if current_sn not in scopeMap:
                print(f"Error: Serial {current_sn} in validated chain from {orig_sn} not found in scopeMap. Breaking.", file=sys.stderr)
                chain.append(f"{current_sn} (Error: Not Mapped)")
                all_serials_in_validated_chains.add(current_sn.split(" ")[0])
                break

            details = scopeMap[current_sn]
            # Ensure correct SKU (should be guaranteed by filtering, but check)
            if details.get('csaItemSku') != TARGET_ENDOSCOPE_SKU:
                 print(f"Error: Chain starting {orig_sn} encountered non-{TARGET_ENDOSCOPE_SKU} serial {current_sn}. Stopping.", file=sys.stderr)
                 chain.append(f"{current_sn} (Error: Wrong SKU)")
                 all_serials_in_validated_chains.add(current_sn.split(" ")[0])
                 break

            chain.append(current_sn)
            all_serials_in_validated_chains.add(current_sn)

            next_sn = details.get('replacedBy')
            if next_sn:
                rma_date_str = details.get('rmaDate', 'N/A')
                ship_date_str = details.get('replacementShipDate', 'N/A')
                handoffs.append(f"Returned {current_sn} on {rma_date_str}, replaced by {next_sn} shipped on {ship_date_str}")
                current_sn = next_sn
            else:
                current_sn = None

        # Store the constructed chain if valid
        if chain and not chain[-1].startswith(f"{chain[-1].split(' ')[0]} (Error"):
            final_sn_in_chain = chain[-1]
            final_status = scopeMap.get(final_sn_in_chain, {}).get('currentStatus', 'Unknown')
            chains_by_cohort[cohort_data['orderId']].append({
                "cohort": cohort_data,
                "chain": chain,
                "handoffs": handoffs,
                "final_status": final_status,
                "final_sn": final_sn_in_chain
            })

    # Sort and print validated chains
    sorted_cohort_ids = sorted(chains_by_cohort.keys())
    print("\n--- Detailed Chains by Cohort ---")
    # ... (Keep the existing printing logic for validated chains) ...
    # (Code identical to user's original chain printing - omitted for brevity, but included below)
    for cohort_id in sorted_cohort_ids:
        chains_to_process = chains_by_cohort[cohort_id]
        def chain_sort_key(item):
            status = item["final_status"]; sort_order = {"inField": 0, "returned_replaced": 1, "returned_no_replacement_found": 2, "returned_no_replacement_available": 3, "returned_error_no_cohort": 98, "Unknown": 99}.get(status, 100); return (sort_order, item["chain"][0])
        chains_to_process.sort(key=chain_sort_key)
        cohort_data = chains_to_process[0]["cohort"]
        cohort_json_data = {"cohort_summary": {"orderId": cohort_data['orderId'],"csaLength": cohort_data.get('csaLength', 'Unknown'),"startDate": cohort_data['startDate'],"startSource": cohort_data['startSource'],"endDate": cohort_data.get('endDate', 'N/A'),"warningDate": cohort_data.get('warningDate', 'N/A'),"remainingReplacements": cohort_data['remainingReplacements'],"totalReplacements": cohort_data['totalReplacements']}, "chains": []}
        print(f"\nCohort: {cohort_data['orderId']} | CSA Length: {cohort_data.get('csaLength', 'Unknown')} | Start: {cohort_data['startDate']} ({cohort_data['startSource']}) | End: {cohort_data.get('endDate', 'N/A')} | Warn: {cohort_data.get('warningDate', 'N/A')} | Replacements Left: {cohort_data['remainingReplacements']}/{cohort_data['totalReplacements']}")
        for item in chains_to_process:
            chain_str = ' -> '.join(item["chain"]); final_status = item["final_status"]; final_sn = item["final_sn"]; status_desc = get_status_description(final_status)
            chain_json_data = {"chain": item["chain"],"final_status": final_status,"final_status_description": status_desc,"final_serial_number": final_sn,"handoffs": item["handoffs"]}
            cohort_json_data["chains"].append(chain_json_data)
            print(f"  Chain: {chain_str} | Final Status: {status_desc}")
            if item["handoffs"]:
                for h in item["handoffs"]: print(f"    - {h}")
            if final_status in ['returned_no_replacement_found', 'returned_no_replacement_available', 'returned_error_no_cohort']:
                 if final_sn in scopeMap: rma_date = scopeMap[final_sn].get('rmaDate', 'N/A'); print(f"    (Final serial {final_sn} returned on {rma_date})")
        results_data["csa_replacement_chains"].append(cohort_json_data)

    print("\n" + "="*27 + " End of Validated CSA Chains " + "="*27) # Adjusted title

    # --- Step 7: Identify Orphans ---
    orphan_serials = {sn for sn, details in scopeMap.items() if details.get('cohort') is None}
    print(f"\nIdentified {len(orphan_serials)} potential orphan serials (never assigned to a cohort).")

    # --- Step 8: Build Speculative Orphan Chains ---
    speculative_orphan_chains = build_speculative_orphan_chains(
        orphan_serials, scopeMap, SPECULATIVE_REPLACEMENT_WINDOW_DAYS
    )

    # --- Step 9: Associate Orphan Chains to Cohorts ---
    speculative_orphan_analysis = associate_orphans_to_cohorts(
        speculative_orphan_chains, scopeMap, csa_cohorts
    )
    results_data["speculative_orphan_analysis"] = speculative_orphan_analysis # Store results

    # --- Step 10: Output Orphan Analysis ---
    print("\n" + "="*28 + f" Speculative Orphan Analysis ({TARGET_ENDOSCOPE_SKU}) " + "="*28)
    if speculative_orphan_analysis:
        print(f"(Attempting to link {len(orphan_serials)} orphans using a {SPECULATIVE_REPLACEMENT_WINDOW_DAYS}-day replacement window and associating based on initial ship date)")

        # Sort orphan chains for consistent output, e.g., by assigned cohort then starter serial
        speculative_orphan_analysis.sort(key=lambda x: (x.get('assigned_cohort', 'Z'), x['starter_serial']))

        current_assigned_cohort = None
        for item in speculative_orphan_analysis:
            assigned_cohort = item.get('assigned_cohort', 'Unknown')
            if assigned_cohort != current_assigned_cohort:
                 print(f"\n--- Orphan Chains/Units Assigned to Cohort: {assigned_cohort} ---")
                 current_assigned_cohort = assigned_cohort

            chain_str = ' -> '.join(item["chain"])
            status_desc = item["final_status_description"]
            starter_sn = item["starter_serial"]
            initial_ship_date = scopeMap.get(starter_sn, {}).get('originalShipmentDate', 'N/A')
            reason = item.get('assignment_reason', '')

            print(f"  Chain/Unit: {chain_str} | Final Status: {status_desc}")
            print(f"    (Starts with: {starter_sn}, Initially Shipped: {initial_ship_date})")
            print(f"    (Assignment Reason: {reason})")

            if item["handoffs"]:
                for h in item["handoffs"]:
                    print(f"    - {h}")
            # Add final return date if applicable
            final_sn = item["final_serial_number"]
            final_status = item["final_status"]
            if final_status.startswith('returned'):
                 rma_date = scopeMap.get(final_sn, {}).get('rmaDate', 'N/A')
                 print(f"    (Final serial {final_sn} returned on {rma_date})")

    else:
        print("No orphan serials found or no speculative chains could be built.")

    print("\n" + "="*28 + " End of Speculative Orphan Analysis " + "="*29)


    # --- Step 11: Summary Reporting ---
    shipped_target = {sn for sn, details in scopeMap.items() if details.get('originalShipmentDate') != 'N/A'}
    returned_target = {sn for sn, details in scopeMap.items() if details.get('rmaDate') is not None}
    serials_in_any_chain = all_serials_in_validated_chains.union(
         {sn for chain_info in speculative_orphan_analysis for sn in chain_info['chain']}
    )

    suspected_in_field_target = sorted(list(shipped_target - returned_target))

    results_data["status_summary"] = {
        "total_shipped_unique": len(shipped_target),
        "total_returned_plausible_unique": len(returned_target),
        "serials_involved_in_validated_chains": len(all_serials_in_validated_chains),
        "serials_involved_in_any_chain_analysis": len(serials_in_any_chain),
        "identified_orphan_serials": len(orphan_serials),
        "suspected_in_field": {
            "count": len(suspected_in_field_target),
            "serial_numbers": suspected_in_field_target
        }
    }

    print("\n" + "="*22 + f" {TARGET_ENDOSCOPE_SKU} Status Summary " + "="*22)
    print(f"Total shipped (unique serials): {len(shipped_target)}")
    print(f"Total returned (unique serials): {len(returned_target)}")
    print(f"Serials involved in validated CSA chains: {len(all_serials_in_validated_chains)}")
    # print(f"Serials involved in *any* chain (validated + speculative): {len(serials_in_any_chain)}") # Optional detail
    print(f"Serials identified as Orphans (never in a cohort): {len(orphan_serials)}")
    print(f"Suspected currently in field (shipped - returned): {len(suspected_in_field_target)}")
    if suspected_in_field_target:
        if len(suspected_in_field_target) < 50: print(f"  -> Serials: {', '.join(suspected_in_field_target)}")
        else: print(f"  (List too long to display: {len(suspected_in_field_target)} serials)")
    else: print("  (None)")
    print("=" * (22 + len(f" {TARGET_ENDOSCOPE_SKU} Status Summary ") + 22))


    # --- Step 12: Save output to JSON file ---
    # Use the provided output path
    # Ensure the output directory exists
    output_dir = os.path.dirname(output_json_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Add captured warnings/errors BEFORE saving
    # Note: TeeOutput now captures stderr directly
    # captured_output = captured_stderr_io.getvalue()
    # results_data["warnings_errors"] = captured_output.strip().split('\n') if captured_output else []

    try:
        with open(output_json_path, 'w') as json_f:
            # Use default=str to handle date objects during JSON serialization
            json.dump(results_data, json_f, indent=4, default=str)
        print(f"\nStructured output saved to {output_json_path}")
    except Exception as e:
        print(f"Error saving JSON output to {output_json_path}: {e}", file=sys.stderr)


if __name__ == "__main__":
    # Setup argument parser for direct execution/testing
    parser = argparse.ArgumentParser(description=f"Analyze CSA replacement chains for SKU {TARGET_ENDOSCOPE_SKU}.")
    parser.add_argument('--input-json', required=True, help='Path to the input JSON file from STEP1.')
    parser.add_argument('--output-json', required=True, help='Path to save the analysis JSON output.')
    parser.add_argument('--output-md', required=True, help='Path to save the analysis report/log.')

    args = parser.parse_args()

    # Use TeeOutput with a 'with' block for automatic redirection and saving
    # Use the provided output markdown path
    with TeeOutput(args.output_md) as tee:
        try:
            # Call the main function with parsed arguments
            build_csa_replacement_chains(args.input_json, args.output_json, args.output_md)
        except Exception as e:
            # Print exception details to the captured output (and thus the file)
            print(f"\n\n!!!!!!!!!!!!!! An UNEXPECTED error occurred !!!!!!!!!!!!!!", file=sys.stderr)
            print(f"ERROR TYPE: {type(e).__name__}", file=sys.stderr)
            print(f"ERROR DETAILS: {e}", file=sys.stderr)
            import traceback
            print("\n--- Traceback ---", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!", file=sys.stderr)

    # This final message goes only to the original terminal (after redirection ends)
    print("\n--- Script Execution Finished ---")