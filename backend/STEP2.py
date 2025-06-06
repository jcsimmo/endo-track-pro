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
import re
from datetime import datetime, timedelta, date # Ensure date is imported
from dateutil.relativedelta import relativedelta
from collections import deque, defaultdict
from io import StringIO
import argparse # Add argparse
from scipy.optimize import linear_sum_assignment
import numpy as np

# Helper function to create the serial details map from Step 1 data
def _create_serial_step1_details_map(sales_orders_data):
    serial_map = {}
    if not sales_orders_data:
        return serial_map

    for so in sales_orders_data:
        so_customer_name = so.get('customer_name')
        sales_order_number = so.get('salesorder_number')
        sales_order_date = so.get('date')

        for pkg in so.get('packages', []):
            package_number = pkg.get('package_number')
            # Prioritize shipment_date from package, fallback to shipment_order's date
            shipment_date = pkg.get('shipment_date')
            if not shipment_date and pkg.get('shipment_order'):
                shipment_date = pkg.get('shipment_order', {}).get('date')

            for item in pkg.get('detailed_line_items', []):
                item_name = item.get('name')
                item_sku = item.get('sku')
                serial_numbers = item.get('serial_numbers', [])
                if isinstance(serial_numbers, list):
                    for serial in serial_numbers:
                        if serial: # Ensure serial is not None or empty
                            serial_map[str(serial).strip()] = {
                                'itemName': item_name,
                                'itemSku': item_sku,
                                'salesOrderNumber': sales_order_number,
                                'soCustomerName': so_customer_name,
                                'salesOrderDate': sales_order_date,
                                'packageNumber': package_number,
                                'shipmentDate': shipment_date,
                            }
                elif serial_numbers: # Handle if it's a single string
                    serial = str(serial_numbers).strip()
                    if serial:
                        serial_map[serial] = {
                            'itemName': item_name,
                            'itemSku': item_sku,
                            'salesOrderNumber': sales_order_number,
                            'soCustomerName': so_customer_name,
                            'salesOrderDate': sales_order_date,
                            'packageNumber': package_number,
                            'shipmentDate': shipment_date,
                        }
    return serial_map

# Target SKUs for filtering - support multiple endoscope types
TARGET_ENDOSCOPE_SKUS = ['P313N00', 'P417N00']
ENDOSCOPE_SKUS = set(TARGET_ENDOSCOPE_SKUS) # Use a set for efficient lookup
# Keep backward compatibility
TARGET_ENDOSCOPE_SKU = TARGET_ENDOSCOPE_SKUS[0] if TARGET_ENDOSCOPE_SKUS else None
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

def find_rma_or_serial_in_so_text(so_object, target_sn, target_rma_num):
    """
    Helper function to search for RMA or serial references in Sales Order text fields.
    
    Args:
        so_object (dict): Sales Order object from the JSON data
        target_sn (str): Target serial number to search for
        target_rma_num (str): Target RMA number to search for
    
    Returns:
        bool: True if a link is found, False otherwise
    """
    if not so_object or not target_sn:
        return False
    
    # Get text fields from SO
    terms = so_object.get('terms', '') or ''
    notes = so_object.get('notes', '') or ''
    reference_number = so_object.get('reference_number', '') or ''
    
    # Combine all text fields for searching
    combined_text = f"{terms} {notes} {reference_number}".lower()
    
    if not combined_text.strip():
        return False
    
    # Clean target serial for regex (escape special characters)
    escaped_sn = re.escape(target_sn.lower())
    
    # Pattern for serial number (with optional "SN" prefix and various separators)
    sn_patterns = [
        rf'\bsn\s*{escaped_sn}\b',  # "SN 380.3372" or "SN380.3372"
        rf'\b{escaped_sn}\b',       # Just "380.3372"
        rf'serial\s*{escaped_sn}\b', # "serial 380.3372"
        rf'{escaped_sn}\s*(?:returned|replaced|rma)', # "380.3372 returned"
        rf'(?:replacement\s+(?:of|for)\s*){escaped_sn}\b' # "replacement of 380.3372"
    ]
    
    # Check serial number patterns
    for pattern in sn_patterns:
        if re.search(pattern, combined_text):
            return True
    
    # If we have a target RMA number, check for it too
    if target_rma_num:
        escaped_rma = re.escape(target_rma_num.lower())
        rma_patterns = [
            rf'\brma[-\s]*{escaped_rma}\b',  # "RMA-00305" or "RMA 00305"
            rf'\b{escaped_rma}\b',           # Just "00305"
        ]
        
        for pattern in rma_patterns:
            if re.search(pattern, combined_text):
                return True
    
    return False

# --- NEW HELPER FUNCTIONS for ORPHAN ANALYSIS ---

def build_optimal_orphan_chains_bipartite(orphan_serials, scope_map, window_days):
    """
    Build optimal orphan chains using bipartite matching with Hungarian algorithm.
    This applies the same optimization approach used for regular cohorts to orphan serials.

    Args:
        orphan_serials (set): Set of serial numbers identified as orphans (cohort=None).
        scope_map (dict): The fully populated scopeMap containing status and dates.
        window_days (int): The time window (in days) to look for a replacement.

    Returns:
        list: A list of optimally matched orphan chains.
    """
    print("\n--- Building Optimal Orphan Chains using Bipartite Matching ---")
    
    if not orphan_serials:
        print("No orphan serials to process.")
        return []

    # Debug: Analyze orphan serials before processing
    print(f"Debug: Total orphan serials: {len(orphan_serials)}")
    # Initial details print can remain, shows raw state
    print("Debug: Initial orphan serial details (first 10):")
    for sn_idx, sn_val in enumerate(sorted(list(orphan_serials))):
        if sn_idx >= 10: break
        details = scope_map.get(sn_val, {})
        status = details.get('currentStatus', 'Unknown')
        rma_date_val = details.get('rmaDate', 'None') # Renamed to avoid conflict
        orig_ship_date_val = details.get('originalShipmentDate', 'N/A')
        print(f"  Orphan {sn_val}: status='{status}', rmaDate='{rma_date_val}', shipped='{orig_ship_date_val}'")
    if len(orphan_serials) > 10:
        print(f"  ... and {len(orphan_serials) - 10} more orphan serials")

    # --- MODIFIED LOGIC FOR INFERENTIAL ORPHAN RETURNS AND REPLACEMENTS ---
    
    # 1. Gather all potentially shippable items from scope_map (not just orphans)
    # These will form the pool of potential_replacements.
    # Assumes scope_map is already filtered for the relevant customer group.
    all_shipped_items_for_matching = []
    for sn, details in scope_map.items():
        ship_date_str = details.get('originalShipmentDate')
        item_sku = details.get('csaItemSku') # Assuming this field exists and is correct
        
        # Only consider items with a ship date and SKU (relevant for matching)
        if ship_date_str and ship_date_str != 'N/A' and item_sku:
            ship_dt = parse_date_flexible(ship_date_str)
            if ship_dt:
                # Exclude items that are explicitly marked as returned from being replacements initially
                # The cost matrix will handle if a "replacement" was itself later returned.
                # current_status = details.get('currentStatus', '')
                # if not current_status.lower().startswith('returned'):
                all_shipped_items_for_matching.append({
                    'serial': sn,
                    'date': ship_dt, # This is originalShipmentDate
                    'sku': item_sku,
                    'details': details
                })
    all_shipped_items_for_matching.sort(key=lambda x: x['date'])
    print(f"Debug: Found {len(all_shipped_items_for_matching)} total shippable items for matching pool.")

    # 2. Identify inferentially "returned" orphans
    # An orphan is "inferentially returned" if a compatible replacement was shipped after it within window_days.
    # Its "return date" for matching will be its own originalShipmentDate.
    inferred_returned_orphans_for_matching = []
    processed_inferred_orphan_returns = set() # To add each orphan only once as a "returned" item

    for orphan_sn in orphan_serials:
        orphan_details = scope_map.get(orphan_sn, {})
        orphan_ship_date_str = orphan_details.get('originalShipmentDate')
        orphan_sku = orphan_details.get('csaItemSku')

        if not orphan_ship_date_str or orphan_ship_date_str == 'N/A' or not orphan_sku:
            continue # Orphan needs a ship date and SKU to be considered for inferred return
        
        orphan_ship_dt = parse_date_flexible(orphan_ship_date_str)
        if not orphan_ship_dt:
            continue

        # Check against all potential replacements from the broader pool
        for rep_candidate in all_shipped_items_for_matching:
            rep_sn = rep_candidate['serial']
            rep_ship_dt = rep_candidate['date'] # This is originalShipmentDate of replacement
            rep_sku = rep_candidate['sku']

            if orphan_sn == rep_sn: # Cannot replace itself
                continue
            
            # SKU compatibility check (e.g., must be same SKU or from a list of compatible SKUs)
            # Using same check as in cost matrix: returned_sku == replacement_sku
            if orphan_sku != rep_sku:
                continue

            # Temporal check: replacement must be shipped AFTER orphan and within window_days
            if rep_ship_dt > orphan_ship_dt and (rep_ship_dt - orphan_ship_dt).days <= window_days:
                # This orphan is now a candidate for an "inferred return"
                if orphan_sn not in processed_inferred_orphan_returns:
                    inferred_returned_orphans_for_matching.append({
                        'serial': orphan_sn,
                        'date': orphan_ship_dt, # Use orphan's own ship date as its "return point" for matching
                        'sku': orphan_sku,
                        'details': orphan_details
                    })
                    processed_inferred_orphan_returns.add(orphan_sn)
                # An orphan can be "inferentially returned" by multiple later shipments.
                # The Hungarian algorithm will pick the best one. So, we don't break here.
    
    inferred_returned_orphans_for_matching.sort(key=lambda x: x['date'])
    print(f"Debug: Identified {len(inferred_returned_orphans_for_matching)} inferentially returned orphans for matching.")
    if inferred_returned_orphans_for_matching:
         print(f"Debug: Inferentially returned orphan serials (first 10): {[item['serial'] for item in inferred_returned_orphans_for_matching[:10]]}")

    # 3. Assign to valid_orphan_returns and valid_orphan_shipments
    valid_orphan_returns = inferred_returned_orphans_for_matching
    valid_orphan_shipments = all_shipped_items_for_matching # All shippable items are potential replacements
    
    # The rest of the original debug for these lists can be adapted or removed if too verbose.
    # For example, printing all replacement candidates might be too much.
    print(f"Debug: Populated valid_orphan_returns with {len(valid_orphan_returns)} items.")
    print(f"Debug: Populated valid_orphan_shipments with {len(valid_orphan_shipments)} items (all shippable items).")

    print(f"Valid orphan returns: {len(valid_orphan_returns)}, Valid orphan replacement candidates: {len(valid_orphan_shipments)}")
    
    if not valid_orphan_returns or not valid_orphan_shipments:
        print("No valid orphan returns or shipments for bipartite matching.")
        # Pass a specific assignment_method_override to the fallback if needed,
        # or let the fallback set its own default.
        return build_orphan_chains_fallback(orphan_serials, scope_map, assignment_method_override="fallback_greedy_no_inferred_returns")
    
    # Sort for consistent ordering
    valid_orphan_returns.sort(key=lambda x: x['date'])
    valid_orphan_shipments.sort(key=lambda x: x['date'])
    
    # Build cost matrix for bipartite matching
    n_returns = len(valid_orphan_returns)
    n_shipments = len(valid_orphan_shipments)
    
    # Use larger dimension for rectangular matrix
    matrix_size = max(n_returns, n_shipments)
    cost_matrix = np.full((matrix_size, matrix_size), 1e6)  # High cost for invalid pairs
    
    print(f"Building {matrix_size}x{matrix_size} cost matrix for orphan matching...")
    
    for i, rma in enumerate(valid_orphan_returns):
        returned_sn = rma['serial']
        rma_date = rma['date']
        returned_sku = rma['sku']
        
        for j, ship in enumerate(valid_orphan_shipments):
            replacement_sn = ship['serial']
            ship_date = ship['date']
            replacement_sku = ship['sku']
            
            # Hard constraints (infinite cost if violated)
            window_end = rma_date + timedelta(days=window_days)
            if (ship_date < rma_date or  # Temporal constraint
                ship_date > window_end or  # Window constraint
                replacement_sn == returned_sn or  # No self-replacement
                returned_sku != replacement_sku):  # SKU compatibility
                continue
            
            # Calculate cost for valid pairs
            time_gap_days = (ship_date - rma_date).days
            
            # Cost components:
            # 1. Time gap penalty (prefer shorter gaps)
            time_cost = min(time_gap_days * 10, 1000)  # Cap at 1000
            
            # 2. Prefer earlier returns and shipments for stability
            return_date_cost = i * 5  # Earlier returns get lower cost
            shipment_date_cost = j * 5  # Earlier shipments get lower cost
            
            # 3. Small random factor for tie-breaking
            random_cost = (hash(f"{returned_sn}-{replacement_sn}") % 100) / 100.0
            
            total_cost = time_cost + return_date_cost + shipment_date_cost + random_cost
            cost_matrix[i, j] = total_cost
    
    # Apply Hungarian algorithm
    print("Applying Hungarian algorithm for optimal orphan matching...")
    row_indices, col_indices = linear_sum_assignment(cost_matrix)
    
    # Extract valid assignments
    assignments = []
    for i, j in zip(row_indices, col_indices):
        if (i < n_returns and j < n_shipments and
            cost_matrix[i, j] < 1e5):  # Valid assignment
            assignments.append((valid_orphan_returns[i], valid_orphan_shipments[j]))
    
    print(f"Found {len(assignments)} optimal orphan replacement assignments")
    
    # Build chains from assignments
    orphan_chains = []
    used_serials = set()
    
    for rma, ship in assignments:
        returned_sn = rma['serial']
        replacement_sn = ship['serial']
        rma_date = rma['date']
        ship_date = ship['date']
        
        # Skip if already used
        if returned_sn in used_serials or replacement_sn in used_serials:
            continue
        
        # Create chain entry
        chain_data = {
            "chain": [
                {"serial": returned_sn, "sku": rma['sku']},
                {"serial": replacement_sn, "sku": ship['sku']}
            ],
            "handoffs": [f"Returned {returned_sn} on {dt_to_str(rma_date)}, optimally replaced by {replacement_sn} shipped on {dt_to_str(ship_date)}"],
            "final_status": "inField",
            "final_status_description": "In Field",
            "final_serial_number": replacement_sn,
            "starter_serial": returned_sn,
            "assignment_method": f"hungarian_algorithm_{match_context}"
        }
        
        orphan_chains.append(chain_data)
        used_serials.add(returned_sn)
        used_serials.add(replacement_sn)
        
        print(f"  Optimal orphan chain: {returned_sn} (returned {dt_to_str(rma_date)}) → {replacement_sn} (shipped {dt_to_str(ship_date)})")
    
    # Add remaining unmatched orphans as single-item chains
    remaining_orphans = orphan_serials - used_serials
    for sn in sorted(list(remaining_orphans)):
        details = scope_map.get(sn, {})
        final_status = details.get('currentStatus', 'Unknown')
        status_desc = get_status_description(final_status)
        
        orphan_chains.append({
            "chain": [{"serial": sn, "sku": details.get('csaItemSku', 'UNKNOWN_ORPHAN_SKU')}],
            "handoffs": [],
            "final_status": final_status,
            "final_status_description": status_desc,
            "final_serial_number": sn,
            "starter_serial": sn,
            "assignment_method": "unmatched_orphan"
        })
    
    print(f"Orphan bipartite matching complete. Created {len(orphan_chains)} orphan chains.")
    return orphan_chains

def build_orphan_chains_fallback(orphan_serials, scope_map, assignment_method_override=None):
    """
    Fallback function for building orphan chains when bipartite matching is not applicable.
    This maintains the original greedy approach as a backup.
    assignment_method_override allows the caller to specify the reason for fallback.
    """
    print("Using fallback greedy approach for orphan chains...")
    
    default_assignment_method = "fallback_greedy"
    if assignment_method_override:
        print(f"  Fallback reason: {assignment_method_override}")
        default_assignment_method = assignment_method_override

    orphan_chains = []
    for sn in sorted(list(orphan_serials)):
        details = scope_map.get(sn, {})
        final_status = details.get('currentStatus', 'Unknown')
        status_desc = get_status_description(final_status)
        
        orphan_chains.append({
            "chain": [{"serial": sn, "sku": details.get('csaItemSku', 'UNKNOWN_ORPHAN_SKU')}],
            "handoffs": [],
            "final_status": final_status,
            "final_status_description": status_desc,
            "final_serial_number": sn,
            "starter_serial": sn,
            "assignment_method": "fallback_greedy"
        })
    
    return orphan_chains

def build_speculative_orphan_chains_new_logic(orphan_instance_keys, shipmentInstanceMap, window_days, csa_order_ids, sales_orders, csa_cohorts=None, is_validated_chains=False):
    """
    Builds potential chains starting from returned instances by looking for subsequent
    shipment instances within a specified window. Also includes single, in-field instances.
    Uses instance keys (serial, so_num, pkg_num) for tracking.
    
    This implements the enhanced logic with explicit link search and flexible date windows.
    
    Args:
        orphan_instance_keys: Set of instance keys to process as chain starters
        shipmentInstanceMap: Map of all shipment instances
        window_days: Days to look forward/backward for replacements
        csa_order_ids: List of CSA order IDs for context
        sales_orders: Sales orders data for explicit link search
        csa_cohorts: CSA cohorts data (required if is_validated_chains=True)
        is_validated_chains: If True, handles cohort assignment and replacement count decrementing
    """
    if not orphan_instance_keys:
        return []

    speculative_chains = []
    processed_in_spec_chain = set()

    # 1. Prepare lists of returned orphan instances and potential replacements
    returned_orphan_details = []
    potential_replacements = []
    # Populate returned_orphan_details from the provided orphan_instance_keys (these are the designated starters)
    for starter_key in orphan_instance_keys:
        instance = shipmentInstanceMap.get(starter_key)
        if not instance:
            continue
        rma_dt = instance.get('rmaDateObj')
        if rma_dt: # Only starters that have been returned can initiate a chain of replacements
            returned_orphan_details.append({
                'instance_key': starter_key,
                'rma_date': rma_dt,
                'sku': instance.get('csaItemSku', instance.get('sku', 'UNKNOWN_SKU')) # SKU of the item being replaced
            })

    # Populate potential_replacements from the entire shipmentInstanceMap
    for instance_key, instance_data in shipmentInstanceMap.items():
        ship_dt = instance_data.get('originalShipmentDateObj')
        if ship_dt:
            sku = instance_data.get('csaItemSku', instance_data.get('sku', 'UNKNOWN_SKU'))
            potential_replacements.append({
                'instance_key': instance_key,
                'ship_date': ship_dt,
                'sku': sku
            })

    # Sort returned orphan instances by RMA date (earliest first)
    returned_orphan_details.sort(key=lambda x: x['rma_date'])
    # Sort potential replacements by ship date (earliest first)
    # This helps in picking the earliest valid replacement
    potential_replacements.sort(key=lambda x: x['ship_date'])

    # Create a lookup for sales orders for efficient access
    so_lookup = {so.get('salesorder_number'): so for so in sales_orders if so.get('salesorder_number')}

    # 2. Build chains starting from each returned orphan instance
    for returned_detail in returned_orphan_details:
        start_instance_key = returned_detail['instance_key']
        if start_instance_key in processed_in_spec_chain:
            continue

        current_chain = []
        current_handoffs = []
        current_instance_key = start_instance_key
        visited_in_this_chain_attempt = set()

        # Track if this is the first link in the chain for date window logic
        is_first_link = True

        # Trace the chain
        while current_instance_key and current_instance_key not in visited_in_this_chain_attempt:
            # For validated chains, the first link MUST be one of the initial validated starters.
            # For orphan chains, or subsequent links in validated chains, this check is not needed here
            # as current_instance_key would be a found replacement.
            if is_validated_chains and is_first_link:
                if current_instance_key not in orphan_instance_keys: # 'orphan_instance_keys' holds validated_chain_starters here
                    # This should ideally not happen if starters are chosen correctly, but as a safeguard:
                    print(f"Debug: Validated chain first link {current_instance_key} is not in the initial starter set. Breaking chain.", file=sys.stderr)
                    break
            
            visited_in_this_chain_attempt.add(current_instance_key)
            current_chain.append(current_instance_key)
            instance = shipmentInstanceMap.get(current_instance_key)

            if not instance: # Should not happen if current_instance_key is valid
                print(f"Debug: current_instance_key {current_instance_key} not found in shipmentInstanceMap. Breaking chain.", file=sys.stderr)
                break

            rma_dt = instance.get('rmaDateObj')
            if rma_dt:
                # This link was returned, look for a replacement
                returned_sn = instance.get('serial', 'N/A')
                # SKU of the item that was returned and needs replacement
                sku_to_match = instance.get('csaItemSku', instance.get('sku', 'UNKNOWN_SKU'))
                
                # First try explicit link search in SO text fields
                best_replacement_key = None
                best_replacement_date = None
                found_explicit_link = False

                for rep_detail in potential_replacements:
                    cand_key = rep_detail['instance_key']
                    cand_ship_dt = rep_detail['ship_date']
                    cand_sku = rep_detail['sku']

                    if (cand_key != current_instance_key and
                        cand_key not in processed_in_spec_chain and
                        cand_sku == sku_to_match): # SKU must match
                        
                        # Check for explicit link in SO text fields
                        cand_so_num = cand_key[1]  # SO number from instance key tuple
                        cand_so = so_lookup.get(cand_so_num)
                        
                        # Search for the returned_sn in the candidate SO's text.
                        # We don't have a specific RMA number for returned_sn here, so pass None.
                        # SKU matching (cand_sku == sku_to_match) is already done.
                        if cand_so and find_rma_or_serial_in_so_text(cand_so, returned_sn, None):
                            # Found explicit link!
                            best_replacement_key = cand_key
                            best_replacement_date = cand_ship_dt
                            found_explicit_link = True
                            break

                # If no explicit link found, fall back to date-based search
                if not found_explicit_link:
                    # Determine date bounds for replacement
                    upper_bound_date = rma_dt + timedelta(days=window_days)
                    
                    if is_first_link:
                        # First scope in this chain attempt, replacement must be after RMA
                        lower_bound_date = rma_dt + timedelta(days=1) # Ensure replacement is strictly after RMA
                    else:
                        # Subsequent scope in this chain, can be 7 days before
                        lower_bound_date = rma_dt - timedelta(days=7)

                    for rep_detail in potential_replacements:
                        cand_key = rep_detail['instance_key']
                        cand_ship_dt = rep_detail['ship_date']
                        cand_sku = rep_detail['sku']

                        # Check conditions for a valid replacement:
                        if (cand_key != current_instance_key and
                            cand_key not in processed_in_spec_chain and
                            cand_sku == sku_to_match and # SKU must match
                            lower_bound_date <= cand_ship_dt <= upper_bound_date):
                            # Note: Removed the csa_order_ids restriction as requested
                            
                            best_replacement_key = cand_key
                            best_replacement_date = cand_ship_dt
                            break

                if best_replacement_key:
                    # Found a replacement
                    rep_ship_str = dt_to_str(best_replacement_date)
                    rma_str = dt_to_str(rma_dt)
                    replacement_sn = shipmentInstanceMap.get(best_replacement_key, {}).get('serial', 'N/A')
                    
                    link_type = "explicit link" if found_explicit_link else "date-based"
                    current_handoffs.append(f"Returned {returned_sn} on {rma_str}, replaced by {replacement_sn} shipped on {rep_ship_str} ({link_type})")

                    processed_in_spec_chain.add(best_replacement_key)
                    current_instance_key = best_replacement_key
                    is_first_link = False  # No longer the first link
                    
                    # Handle cohort assignment and replacement count if this is for validated chains
                    if is_validated_chains and csa_cohorts:
                        # Get the cohort of the returned instance
                        returned_cohort_id = instance.get('cohort')
                        if returned_cohort_id:
                            # Assign replacement to same cohort
                            shipmentInstanceMap[best_replacement_key]['cohort'] = returned_cohort_id
                            
                            # Decrement remaining replacements for the cohort
                            for cohort in csa_cohorts:
                                if cohort['orderId'] == returned_cohort_id:
                                    if cohort['remainingReplacements'] > 0:
                                        cohort['remainingReplacements'] -= 1
                                    break
                else:
                    # No replacement found for this returned link
                    current_instance_key = None
            else:
                # This link was not returned (it's the last one shipped in this orphan chain)
                current_instance_key = None

        # Store the completed chain
        if current_chain:
            final_instance_key = current_chain[-1]
            final_instance = shipmentInstanceMap.get(final_instance_key, {})
            final_status = final_instance.get('currentStatus', 'Unknown')

            speculative_chains.append({
                "chain": current_chain,
                "handoffs": current_handoffs,
                "final_status": final_status,
                "final_serial_number": final_instance.get('serial', 'N/A'),
                "starter_serial": shipmentInstanceMap.get(current_chain[0], {}).get('serial', 'N/A'),
                "starter_instance_key": current_chain[0]
            })
            
            for key in current_chain:
                processed_in_spec_chain.add(key)

    # 3. Add remaining single, in-field orphan instances
    remaining_orphan_keys = orphan_instance_keys - processed_in_spec_chain

    for instance_key in sorted(list(remaining_orphan_keys)):
        instance = shipmentInstanceMap.get(instance_key, {})
        status = instance.get('currentStatus', 'Unknown')
        
        if status == 'inField':
            speculative_chains.append({
                "chain": [instance_key],
                "handoffs": [],
                "final_status": status,
                "final_serial_number": instance.get('serial', 'N/A'),
                "starter_serial": instance.get('serial', 'N/A'),
                "starter_instance_key": instance_key
            })

    return speculative_chains

# Keep the original function for backward compatibility but rename it
def build_speculative_orphan_chains(orphan_serials, scope_map, window_days):
    """
    Legacy function - now delegates to the optimized bipartite matching approach.
    """
    return build_optimal_orphan_chains_bipartite(orphan_serials, scope_map, window_days)

def associate_orphans_to_cohorts_with_isolation(orphan_chains, scope_map, csa_cohorts, original_cohort_membership, isolation_stats):
    """
    Enhanced orphan association that respects original cohort membership.
    Prevents cross-cohort contamination by prioritizing original cohort assignments.
    """
    print("  Using cohort isolation logic for orphan association...")
    
    orphan_analysis = []
    
    for chain in orphan_chains:
        starter_serial = chain.get('starter_serial', 'N/A')
        final_status = chain.get('final_status', 'Unknown')
        
        # Check original cohort membership first
        original_cohort_id = original_cohort_membership.get(starter_serial)
        assigned_cohort = None
        assignment_reason = ""
        assignment_type = "unassigned"
        
        if original_cohort_id:
            print(f"    Orphan {starter_serial}: Checking original cohort {original_cohort_id}...")
            # Try original cohort first
            original_cohort = next((c for c in csa_cohorts if c['orderId'] == original_cohort_id), None)
            
            if original_cohort:
                total_slots = original_cohort.get('total_CSA_slots', 0)
                validated_count = original_cohort.get('current_validated_in_field_count', 0)
                assigned_orphans = original_cohort.get('current_assigned_in_field_orphans', 0)
                
                if (validated_count + assigned_orphans) < total_slots and final_status == 'inField':
                    assigned_cohort = original_cohort_id
                    assignment_reason = f"Assigned to original cohort {original_cohort_id}. Cohort isolation respected."
                    assignment_type = "same_cohort_preferred"
                    original_cohort['current_assigned_in_field_orphans'] += 1
                    isolation_stats['orphan_same_cohort_assignments'] += 1
                    print(f"    ✓ Orphan {starter_serial}: Assigned to original cohort {original_cohort_id}")
                else:
                    if final_status != 'inField':
                        assigned_cohort = original_cohort_id  # Can still track returned items in original cohort
                        assignment_reason = f"Tracked in original cohort {original_cohort_id} (status: {final_status})."
                        assignment_type = "same_cohort_tracking"
                        isolation_stats['orphan_same_cohort_assignments'] += 1
                    else:
                        assignment_reason = f"Original cohort {original_cohort_id} at capacity ({validated_count + assigned_orphans}/{total_slots}). Preserving isolation - not reassigned."
                        assignment_type = "isolation_preserved"
                        isolation_stats['orphan_cross_cohort_blocked'] += 1
                        print(f"    🛡 Orphan {starter_serial}: Cohort isolation preserved (capacity constraint)")
        
        if not assigned_cohort and not original_cohort_id:
            # Only assign to other cohorts if no original cohort exists (truly orphaned)
            print(f"    Orphan {starter_serial}: No original cohort found, checking date-based assignment...")
            starter_details = scope_map.get(starter_serial, {})
            initial_ship_date_str = starter_details.get('originalShipmentDate', 'N/A')
            
            if initial_ship_date_str != 'N/A' and final_status == 'inField':
                initial_ship_date = parse_date_flexible(initial_ship_date_str)
                
                # Find best cohort by date (latest start <= ship date)
                best_cohort = None
                for cohort in csa_cohorts:
                    cohort_start_obj = cohort.get('startDateObj')
                    if cohort_start_obj and initial_ship_date and cohort_start_obj <= initial_ship_date:
                        total_slots = cohort.get('total_CSA_slots', 0)
                        validated_count = cohort.get('current_validated_in_field_count', 0)
                        assigned_orphans = cohort.get('current_assigned_in_field_orphans', 0)
                        
                        if (validated_count + assigned_orphans) < total_slots:
                            if not best_cohort or cohort_start_obj > best_cohort.get('startDateObj'):
                                best_cohort = cohort
                
                if best_cohort:
                    assigned_cohort = best_cohort['orderId']
                    assignment_reason = f"Initial ship date {initial_ship_date_str} is on or after cohort {assigned_cohort} start date {best_cohort.get('startDate', 'N/A')}. Assigned as in-field, capacity OK."
                    assignment_type = "date_based_new_assignment"
                    best_cohort['current_assigned_in_field_orphans'] += 1
                    print(f"    ✓ Orphan {starter_serial}: New assignment to cohort {assigned_cohort} (date-based)")
                else:
                    assigned_cohort = "No Suitable Cohort Found (Capacity)"
                    assignment_reason = "All date-suitable cohorts are at in-field capacity for orphan."
                    assignment_type = "capacity_constrained"
            else:
                if final_status != 'inField':
                    assigned_cohort = "No Cohort Assignment Required"
                    assignment_reason = f"Orphan status is {final_status}, no cohort assignment needed."
                    assignment_type = "status_based_skip"
                else:
                    assigned_cohort = "No Suitable Cohort Found (Date)"
                    assignment_reason = "No ship date available for cohort assignment."
                    assignment_type = "missing_data"
        
        # Create analysis entry
        chain_copy = chain.copy()
        chain_copy['assigned_cohort'] = assigned_cohort or "Unassigned"
        chain_copy['assignment_reason'] = assignment_reason
        chain_copy['cohort_isolation_status'] = assignment_type
        chain_copy['original_cohort'] = original_cohort_id
        
        orphan_analysis.append(chain_copy)
    
    return orphan_analysis
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
        # This will now be a list of candidate cohorts, ordered by preference (latest start date first)
        candidate_cohorts = [c for c in reversed(valid_cohorts) if c['startDateObj'] <= initial_ship_dt]
        
        assigned_to_cohort = False
        if not candidate_cohorts:
            chain_data['assigned_cohort'] = "No Suitable Cohort Found (Date)"
            chain_data['assignment_reason'] = f"Initial ship date {dt_to_str(initial_ship_dt)} is before all known cohort start dates."
        else:
            for cohort_candidate in candidate_cohorts:
                # Rule #2: Cohort Capacity Limit for Orphans
                # This applies if the orphan chain ends 'inField'
                can_assign_to_candidate = True # Assume yes initially
                if chain_data.get('final_status') == 'inField':
                    # These fields were initialized on cohort objects earlier
                    total_slots = cohort_candidate.get('total_CSA_slots', 0)
                    validated_in_field = cohort_candidate.get('current_validated_in_field_count', 0)
                    # current_assigned_in_field_orphans needs to be incremented if this assignment happens
                    
                    # Check if adding this orphan would exceed capacity
                    # The current_assigned_in_field_orphans is for *other* orphans already assigned to this cohort.
                    # So, we check if (validated_in_field + current_assigned_in_field_orphans + 1_for_this_one) <= total_slots
                    if (validated_in_field + cohort_candidate.get('current_assigned_in_field_orphans', 0)) >= total_slots:
                        can_assign_to_candidate = False
                        print(f"  Orphan Assoc: Cohort {cohort_candidate['orderId']} is full for in-field items. Validated: {validated_in_field}, Assigned Orphans: {cohort_candidate.get('current_assigned_in_field_orphans', 0)}, Total Slots: {total_slots}. Cannot assign in-field orphan {starter_sn}.")
                
                if can_assign_to_candidate:
                    chain_data['assigned_cohort'] = cohort_candidate['orderId']
                    chain_data['assignment_reason'] = f"Initial ship date {dt_to_str(initial_ship_dt)} is on or after cohort {cohort_candidate['orderId']} start date {cohort_candidate['startDate']}."
                    
                    # If it was an in-field orphan that got assigned, increment the count for this cohort
                    if chain_data.get('final_status') == 'inField':
                        cohort_candidate['current_assigned_in_field_orphans'] = cohort_candidate.get('current_assigned_in_field_orphans', 0) + 1
                        chain_data['assignment_reason'] += " Assigned as in-field, capacity OK."
                    
                    assigned_to_cohort = True
                    break # Found a suitable cohort and assigned

            if not assigned_to_cohort:
                # This means all date-suitable cohorts were full for in-field items (if this orphan was inField)
                # or no date-suitable cohorts were found in the first place (handled above)
                if chain_data.get('final_status') == 'inField' and any(candidate_cohorts): # It was inField and there were candidates
                    chain_data['assigned_cohort'] = "No Suitable Cohort Found (Capacity)"
                    chain_data['assignment_reason'] = f"All date-suitable cohorts are at in-field capacity for orphan {starter_sn}."
                elif not any(candidate_cohorts): # Should be caught by the earlier check, but as a fallback
                     chain_data['assigned_cohort'] = "No Suitable Cohort Found (Date)"
                     chain_data['assignment_reason'] = f"Initial ship date {dt_to_str(initial_ship_dt)} is before all known cohort start dates."
                else: # Not inField, but still couldn't assign (should not happen if date candidates exist)
                    chain_data['assigned_cohort'] = "Assignment Logic Error"
                    chain_data['assignment_reason'] = f"Orphan {starter_sn} (not inField) could not be assigned despite date candidates."

            # Check for ambiguity (optional but helpful)
            # This requires knowing replacement dates for cohorts - more complex
            # Simple check: if ship date matches another cohort's start? Less reliable.
            # We'll skip ambiguity flag for now based *purely* on date logic.

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


def build_optimal_replacement_chains_bipartite(rma_events, shipment_events, scopeMap, csa_cohorts):
    """
    Build optimal replacement chains using bipartite matching with Hungarian algorithm.
    This solves the temporal validity issue by considering all possible return-shipment
    combinations and finding the globally optimal assignment.
    """
    print("\n--- Building Optimal Replacement Chains using Bipartite Matching ---")
    
    # Filter valid returns (scopes that are currently inField)
    valid_returns = []
    for rma in rma_events:
        returned_sn = rma['serial']
        if (returned_sn in scopeMap and
            scopeMap[returned_sn]['currentStatus'] == 'inField'):
            
            # Check if cohort has replacements available
            cohort_id = scopeMap[returned_sn]['cohort']
            if cohort_id:
                cohort = next((c for c in csa_cohorts if c['orderId'] == cohort_id), None)
                if cohort and cohort['remainingReplacements'] > 0:
                    valid_returns.append(rma)
    
    # Filter valid shipments (potential replacements)
    valid_shipments = []
    shipped_serials = set()
    for ship in shipment_events:
        if (ship['serial'] and
            ship.get('sku') in ENDOSCOPE_SKUS and
            ship['date'] is not None and
            ship['serial'] in scopeMap and
            scopeMap[ship['serial']]['currentStatus'] == 'inField'):
            
            # Avoid duplicate serials (take earliest shipment)
            if ship['serial'] not in shipped_serials:
                valid_shipments.append(ship)
                shipped_serials.add(ship['serial'])
    
    print(f"Valid returns: {len(valid_returns)}, Valid replacement candidates: {len(valid_shipments)}")
    
    if not valid_returns or not valid_shipments:
        print("No valid returns or shipments for bipartite matching.")
        return
    
    # Sort for consistent ordering
    valid_returns.sort(key=lambda x: x['date'])
    valid_shipments.sort(key=lambda x: x['date'])
    
    # Build cost matrix for bipartite matching
    n_returns = len(valid_returns)
    n_shipments = len(valid_shipments)
    
    # Use larger dimension for rectangular matrix
    matrix_size = max(n_returns, n_shipments)
    cost_matrix = np.full((matrix_size, matrix_size), 1e6)  # High cost for invalid pairs
    
    print(f"Building {matrix_size}x{matrix_size} cost matrix...")
    
    for i, rma in enumerate(valid_returns):
        returned_sn = rma['serial']
        rma_date = rma['date']
        returned_sku = scopeMap[returned_sn].get('csaItemSku')
        
        for j, ship in enumerate(valid_shipments):
            replacement_sn = ship['serial']
            ship_date = ship['date']
            replacement_sku = scopeMap.get(replacement_sn, {}).get('csaItemSku')
            
            # Hard constraints (infinite cost if violated)
            if (ship_date < rma_date or  # Temporal constraint
                replacement_sn == returned_sn or  # No self-replacement
                returned_sku != replacement_sku):  # SKU compatibility
                continue
            
            # Calculate cost for valid pairs
            time_gap_days = (ship_date - rma_date).days
            
            # Cost components:
            # 1. Time gap penalty (prefer shorter gaps)
            time_cost = min(time_gap_days * 10, 1000)  # Cap at 1000
            
            # 2. Chain length balancing (prefer orphan scopes as replacements)
            replacement_chain_length = 0
            temp_sn = replacement_sn
            visited = set()
            while temp_sn and temp_sn not in visited and temp_sn in scopeMap:
                visited.add(temp_sn)
                temp_sn = scopeMap[temp_sn].get('replacedScope')
                replacement_chain_length += 1
            
            # Prefer orphans (chain length 1) as replacements
            chain_length_cost = (replacement_chain_length - 1) * 50
            
            # 3. Small random factor for tie-breaking
            random_cost = (hash(f"{returned_sn}-{replacement_sn}") % 100) / 100.0
            
            total_cost = time_cost + chain_length_cost + random_cost
            cost_matrix[i, j] = total_cost
    
    # Apply Hungarian algorithm
    print("Applying Hungarian algorithm for optimal matching...")
    row_indices, col_indices = linear_sum_assignment(cost_matrix)
    
    # Extract valid assignments
    assignments = []
    for i, j in zip(row_indices, col_indices):
        if (i < n_returns and j < n_shipments and
            cost_matrix[i, j] < 1e5):  # Valid assignment
            assignments.append((valid_returns[i], valid_shipments[j]))
    
    print(f"Found {len(assignments)} optimal replacement assignments")
    
    # Apply the assignments to update scopeMap
    used_replacement_serials = set()
    
    for rma, ship in assignments:
        returned_sn = rma['serial']
        replacement_sn = ship['serial']
        rma_date_obj = rma['date']
        ship_date_obj = ship['date']
        
        # Double-check constraints
        if (replacement_sn in used_replacement_serials or
            replacement_sn == returned_sn or
            ship_date_obj < rma_date_obj):
            continue
        
        # Find and update cohort
        cohort_id = scopeMap[returned_sn]['cohort']
        cohort = next((c for c in csa_cohorts if c['orderId'] == cohort_id), None)
        
        if cohort and cohort['remainingReplacements'] > 0:
            # Update returned scope
            scopeMap[returned_sn]['currentStatus'] = 'returned_replaced'
            scopeMap[returned_sn]['replacedBy'] = replacement_sn
            scopeMap[returned_sn]['rmaDate'] = dt_to_str(rma_date_obj)
            scopeMap[returned_sn]['rmaDateObj'] = rma_date_obj
            scopeMap[returned_sn]['replacementShipDate'] = dt_to_str(ship_date_obj)
            scopeMap[returned_sn]['replacementShipDateObj'] = ship_date_obj
            
            # Update replacement scope
            scopeMap[replacement_sn]['currentStatus'] = 'inField'
            scopeMap[replacement_sn]['replacedScope'] = returned_sn
            scopeMap[replacement_sn]['cohort'] = cohort_id
            
            # Update cohort
            cohort['remainingReplacements'] -= 1
            used_replacement_serials.add(replacement_sn)
            
            print(f"  Assigned: {returned_sn} (returned {dt_to_str(rma_date_obj)}) → {replacement_sn} (shipped {dt_to_str(ship_date_obj)})")
    
    # Process remaining returns without replacements
    for rma in valid_returns:
        returned_sn = rma['serial']
        if scopeMap[returned_sn]['currentStatus'] == 'inField':  # Not processed
            rma_date_obj = rma['date']
            cohort_id = scopeMap[returned_sn]['cohort']
            cohort = next((c for c in csa_cohorts if c['orderId'] == cohort_id), None)
            
            scopeMap[returned_sn]['rmaDate'] = dt_to_str(rma_date_obj)
            scopeMap[returned_sn]['rmaDateObj'] = rma_date_obj
            
            if cohort and cohort['remainingReplacements'] > 0:
                scopeMap[returned_sn]['currentStatus'] = 'returned_no_replacement_found'
                # Note: Do NOT decrement remainingReplacements here - only when replacement is actually made
            else:
                scopeMap[returned_sn]['currentStatus'] = 'returned_no_replacement_available'
    
    print(f"Bipartite matching complete. Used {len(used_replacement_serials)} replacement scopes.")

# --- MAIN FUNCTION ---
def build_csa_replacement_chains(input_json_path, output_json_path, output_md_path):
    print(f"STEP2_VERSION_CHECK: Executing build_csa_replacement_chains - version with explicit save debugs - 6/1/2025 PM") # Unique version check
    """
    Loads data from input_json_path, builds CSA replacement chains,
    builds speculative orphan chains, associates orphans, prints results,
    and saves structured data to JSON.
    FILTERED for SKUs: {', '.join(TARGET_ENDOSCOPE_SKUS)}.
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
    print(f"\n--- Filtering all processing for SKUs: {', '.join(TARGET_ENDOSCOPE_SKUS)} ---")
    results_data["processing_info"]["target_skus"] = TARGET_ENDOSCOPE_SKUS

    # --- Create and add serialStep1DetailsMap ---
    serial_step1_details_map = _create_serial_step1_details_map(sales_orders)
    results_data["serialStep1DetailsMap"] = serial_step1_details_map
    print(f"Built serialStep1DetailsMap with {len(serial_step1_details_map)} entries.")

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
                if line_sku in ENDOSCOPE_SKUS: # MODIFIED
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
    print(f"Extracted {len(shipment_events)} shipment events for SKUs {', '.join(TARGET_ENDOSCOPE_SKUS)}.")
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
            'csaItemSku': initial_shipment['sku'] if initial_shipment else None, # Use SKU from the earliest shipment
            'csaItemName': f"{initial_shipment['sku']}" if initial_shipment else "N/A" # Use SKU from the earliest shipment
        }
    print(f"Initialized scopeMap with {len(scopeMap)} unique shipped serials.")

    # --- Step 2b: Initialize shipmentInstanceMap for instance-based tracking ---
    # This is needed for the enhanced orphan chain logic that tracks individual shipment instances
    shipmentInstanceMap = {}
    for event in shipment_events:
        sn = event.get('serial')
        so_num = event.get('so_number')
        pkg_num = event.get('package_number')
        ship_dt = event.get('date')
        sku = event.get('sku')

        if not sn or not so_num or not pkg_num:
            continue

        instance_key = (sn, so_num, pkg_num)
        
        # Avoid processing duplicate events for the exact same shipment line item
        if instance_key in shipmentInstanceMap:
            continue

        shipmentInstanceMap[instance_key] = {
            'instance_key': instance_key,
            'serial': sn,
            'so_number': so_num,
            'package_number': pkg_num,
            'currentStatus': 'inField',
            'replacedBy': None,
            'replacedScope': None,
            'cohort': None,
            'rmaDate': None,
            'rmaDateObj': None,
            'replacementShipDate': None,
            'replacementShipDateObj': None,
            'originalShipmentDate': dt_to_str(ship_dt),
            'originalShipmentDateObj': ship_dt,
            'csaItemSku': sku,
            'csaItemName': sku
        }
    
    print(f"Initialized shipmentInstanceMap with {len(shipmentInstanceMap)} unique shipment instances.")

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
                    # Crucial Filter: Only consider returns if the serial was previously shipped as one of the target SKUs
                    # We also need to know WHICH SKU it was shipped as to correctly attribute the return.
                    # This requires all_shipped_target_serials to store (serial, sku) tuples or a dict.
                    # For now, let's assume all_shipped_target_serials will be enhanced.
                    # The SKU for the RMA event should be the SKU of the *original shipment* of that serial.
                    original_shipment_sku = None
                    # Find the original shipment SKU for this serial
                    for ship_event in shipment_events:
                        if ship_event['serial'] == sn:
                            original_shipment_sku = ship_event['sku']
                            break
                    
                    if sn in all_shipped_target_serials and original_shipment_sku:
                        rma_events.append({
                            'date': dt, # date obj
                            'rma_number': rma_number,
                            'receipt_number': receipt_number,
                            'serial': sn,
                            'sku': original_shipment_sku # MODIFIED - Use the SKU from the original shipment
                        })

    # Sort by date object
    rma_events.sort(key=lambda x: x['date'])
    print(f"Extracted {len(rma_events)} RMA events potentially related to SKUs {', '.join(TARGET_ENDOSCOPE_SKUS)} (out of {unfiltered_rma_count} total serials found in receipts).")
    all_returned_target_serials = {evt['serial'] for evt in rma_events if evt['serial']}

    # --- Step 3b: Update shipmentInstanceMap with RMA events ---
    # For each RMA event, find the most recently shipped instance of that serial and mark it as returned
    for rma_event in rma_events:
        rma_sn = rma_event['serial']
        rma_dt = rma_event['date']
        rma_dt_str = dt_to_str(rma_dt)
        
        # Find the most recently shipped instance of this serial that is still inField
        most_recent_instance_key = None
        most_recent_ship_date = None
        
        for instance_key, instance_data in shipmentInstanceMap.items():
            if (instance_data['serial'] == rma_sn and
                instance_data['currentStatus'] == 'inField' and
                instance_data['originalShipmentDateObj']):
                
                ship_dt = instance_data['originalShipmentDateObj']
                if ship_dt <= rma_dt:  # Only consider instances shipped before or on the RMA date
                    if most_recent_ship_date is None or ship_dt > most_recent_ship_date:
                        most_recent_instance_key = instance_key
                        most_recent_ship_date = ship_dt
        
        # Update the most recent instance with RMA information
        if most_recent_instance_key:
            shipmentInstanceMap[most_recent_instance_key]['currentStatus'] = 'returned'
            shipmentInstanceMap[most_recent_instance_key]['rmaDate'] = rma_dt_str
            shipmentInstanceMap[most_recent_instance_key]['rmaDateObj'] = rma_dt
    
    print(f"Updated shipmentInstanceMap with RMA information for {len(rma_events)} RMA events.")


    # --- Step 4: Identify CSA cohorts and Update scopeMap ---
    csa_sku_keywords = ['HiFCSA-1yr', 'HiFCSA-2yr']
    csa_cohorts = []
    serial_to_cohort_map = {} # Use this specific map for original cohort members only
    # COHORT ISOLATION FIX: Track original cohort membership
    original_cohort_membership = {}  # serial -> original_cohort_id
    cross_cohort_violations = []     # Track violations for reporting
    cohort_isolation_stats = {       # Statistics for reporting
        'sro_same_cohort_assignments': 0,
        'sro_cross_cohort_assignments': 0,
        'orphan_same_cohort_assignments': 0,
        'orphan_cross_cohort_blocked': 0
    }

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
                if detailed_line.get('sku') in ENDOSCOPE_SKUS: # MODIFIED
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
             print(f"Warning: SO {so_number} has a CSA plan but no shipped SKUs matching {', '.join(TARGET_ENDOSCOPE_SKUS)} found in its packages.", file=sys.stderr)
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
                # COHORT ISOLATION FIX: Track original cohort membership
                if sn not in original_cohort_membership:
                    original_cohort_membership[sn] = so_number
                    print(f"Debug: Serial {sn} assigned to original cohort {so_number}")
                elif original_cohort_membership[sn] != so_number:
                    # Detect conflicting initial assignments
                    cross_cohort_violations.append({
                        'serial': sn,
                        'original_cohort': original_cohort_membership[sn],
                        'conflicting_cohort': so_number,
                        'violation_type': 'initial_assignment_conflict',
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"Warning: Serial {sn} conflicting cohort assignments: {original_cohort_membership[sn]} vs {so_number}")
                
                # Check if already assigned - log warning, keep first assignment
                if scopeMap[sn]['cohort'] is not None and scopeMap[sn]['cohort'] != so_number:
                     print(f"Warning: Serial {sn} reassigned from cohort {scopeMap[sn]['cohort']} to {so_number}. Check data.", file=sys.stderr)
                scopeMap[sn]['cohort'] = so_number # Assign cohort ID
                serial_to_cohort_map[sn] = cohort_data # Map original serial to its cohort
            else:
                 # This should not happen if scopeMap initialization was complete
                 print(f"Error: Serial {sn} from cohort {so_number} not found in initialized scopeMap!", file=sys.stderr)

        # --- ALSO: Update shipmentInstanceMap with cohort assignments ---
        for sn in cohort_data['csaScopes']:
            # Find all instances of this serial and assign them to the cohort
            for instance_key, instance_data in shipmentInstanceMap.items():
                if instance_data['serial'] == sn:
                    if instance_data['cohort'] is not None and instance_data['cohort'] != so_number:
                        print(f"Warning: Instance {instance_key} reassigned from cohort {instance_data['cohort']} to {so_number}. Check data.", file=sys.stderr)
                    instance_data['cohort'] = so_number

    # Initialize new fields for cohort capacity and tracking (Phase 0)
    for cohort_obj in csa_cohorts:
        cohort_obj['total_CSA_slots'] = cohort_obj.get('initialScopeCount', 0)
        cohort_obj['current_validated_in_field_count'] = 0
        cohort_obj['current_assigned_in_field_orphans'] = 0

    print(f"Identified {len(csa_cohorts)} relevant CSA cohorts for SKUs {', '.join(TARGET_ENDOSCOPE_SKUS)}.")
    if not csa_cohorts:
        print("No relevant CSA cohorts found. Exiting chain building.")
        return

    # Extract CSA order IDs for use in orphan chain logic
    csa_order_ids = {cohort['orderId'] for cohort in csa_cohorts}
    print(f"CSA Order IDs: {sorted(list(csa_order_ids))}")

    # --- Step 5: Build Optimal Replacement Chains using Enhanced Logic ---
    print("\n--- Building Optimal Replacement Chains using Enhanced Logic ---")
    
    # Gather RMA'd cohort instances as starters for validated chains
    validated_chain_starters = set()
    for instance_key, instance_data in shipmentInstanceMap.items():
        # An instance is a starter for validated chains if:
        # 1. It belongs to a CSA cohort (cohort is not None)
        # 2. It has been returned (has rmaDateObj and currentStatus indicates returned)
        if (instance_data.get('cohort') is not None and
            instance_data.get('rmaDateObj') is not None and
            instance_data.get('currentStatus') == 'returned'):
            validated_chain_starters.add(instance_key)
    
    print(f"Found {len(validated_chain_starters)} RMA'd cohort instances to process as validated chain starters")
    
    # Build validated chains using the enhanced logic
    if validated_chain_starters:
        validated_chains_new = build_speculative_orphan_chains_new_logic(
            validated_chain_starters,
            shipmentInstanceMap,
            SPECULATIVE_REPLACEMENT_WINDOW_DAYS,
            csa_order_ids,
            sales_orders,
            csa_cohorts=csa_cohorts,
            is_validated_chains=True
        )
        print(f"Built {len(validated_chains_new)} validated replacement chains using enhanced logic")
        
        # Convert the new chain format to be compatible with the existing validated chain display
        # Update scopeMap to create the chain links for display
        for chain_data in validated_chains_new:
            chain_instance_keys = chain_data.get('chain', [])
            handoffs = chain_data.get('handoffs', [])
            
            # Update scopeMap to create the chain links
            for i, instance_key in enumerate(chain_instance_keys):
                if isinstance(instance_key, tuple):  # Instance key format
                    instance_data = shipmentInstanceMap.get(instance_key, {})
                    serial = instance_data.get('serial')
                    if serial and serial in scopeMap:
                        if i == len(chain_instance_keys) - 1:  # Last in chain
                            # Determine final status based on chain final_status
                            final_status = chain_data.get('final_status', 'inField')
                            if final_status == 'returned':
                                scopeMap[serial]['currentStatus'] = 'returned_no_replacement_found'
                            else:
                                scopeMap[serial]['currentStatus'] = 'inField'
                        else:  # Not last, so was replaced
                            next_instance_key = chain_instance_keys[i + 1]
                            next_instance_data = shipmentInstanceMap.get(next_instance_key, {})
                            next_serial = next_instance_data.get('serial')
                            next_ship_date = next_instance_data.get('originalShipmentDateObj')
                            
                            scopeMap[serial]['currentStatus'] = 'returned_replaced'
                            scopeMap[serial]['replacedBy'] = next_serial
                            scopeMap[serial]['replacementShipDate'] = dt_to_str(next_ship_date) if next_ship_date else 'N/A'
                            
                            # Set RMA date from the instance data if available
                            if instance_data.get('rmaDateObj'):
                                scopeMap[serial]['rmaDate'] = dt_to_str(instance_data['rmaDateObj'])
        
        # Phase 2: Calculate Current Validated In-Field Count
        if 'validated_chains_new' in locals() and validated_chains_new:
            for v_chain_data in validated_chains_new:
                starter_instance_key = v_chain_data.get('starter_instance_key')
                final_status = v_chain_data.get('final_status')
                
                if starter_instance_key and final_status == 'inField':
                    starter_instance = shipmentInstanceMap.get(starter_instance_key)
                    if starter_instance:
                        cohort_id = starter_instance.get('cohort')
                        if cohort_id:
                            target_cohort = next((c for c in csa_cohorts if c['orderId'] == cohort_id), None)
                            if target_cohort:
                                target_cohort['current_validated_in_field_count'] += 1
            print(f"Calculated current_validated_in_field_count for {len(csa_cohorts)} cohorts.")

    else:
        print("No RMA'd cohort instances found for validated chain building")

    # --- Step 6: Build and Print Validated CSA Chains ---
    print("\n" + "="*30 + f" Validated CSA Replacement Chains ({', '.join(TARGET_ENDOSCOPE_SKUS)}) " + "="*25) # Adjusted title
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
                # Store error as an object for consistency, though SKU might be unknown
                chain.append({"serial": f"{current_sn} (Error: Not Mapped)", "sku": "UNKNOWN_ERROR"})
                all_serials_in_validated_chains.add(current_sn.split(" ")[0]) # Add base serial for tracking
                break

            details = scopeMap[current_sn]
            # Ensure correct SKU (should be guaranteed by filtering, but check)
            # This check might need to be more nuanced if a chain can legitimately switch SKUs (e.g. upgrade)
            # For now, assume a chain is for a single SKU defined by its start.
            # The csaItemSku in scopeMap is now dynamic, so this check should be against the chain's starting SKU.
            # We'll need to pass the chain's starting SKU or retrieve it.
            # For simplicity in this step, we'll compare against the ENDOSCOPE_SKUS set.
            # A more robust solution would track the specific SKU for each chain.
            if details.get('csaItemSku') not in ENDOSCOPE_SKUS:
                 print(f"Error: Chain starting {orig_sn} encountered non-target SKU serial {current_sn} (SKU: {details.get('csaItemSku')}). Stopping.", file=sys.stderr)
                 # Store error as an object
                 chain.append({"serial": f"{current_sn} (Error: Wrong SKU)", "sku": details.get('csaItemSku', 'UNKNOWN_SKU_ERROR')})
                 all_serials_in_validated_chains.add(current_sn.split(" ")[0]) # Add base serial for tracking
                 break

            chain.append({"serial": current_sn, "sku": details.get('csaItemSku')})
            all_serials_in_validated_chains.add(current_sn) # Add base serial for tracking

            next_sn = details.get('replacedBy')
            if next_sn:
                rma_date_str = details.get('rmaDate', 'N/A')
                ship_date_str = details.get('replacementShipDate', 'N/A')
                handoffs.append(f"Returned {current_sn} on {rma_date_str}, replaced by {next_sn} shipped on {ship_date_str}")
                current_sn = next_sn
            else:
                current_sn = None

        # Store the constructed chain if valid
        # Check the 'serial' field of the last object in the chain for errors
        if chain and not chain[-1]["serial"].split(" ")[0].endswith(("(Error", "(Error: Not Mapped)", "(Error: Wrong SKU)")):
            final_sn_in_chain = chain[-1]["serial"] # Get serial from the last object
            final_status = scopeMap.get(final_sn_in_chain, {}).get('currentStatus', 'Unknown')
            chains_by_cohort[cohort_data['orderId']].append({
                "cohort": cohort_data,
                "chain": chain,
                "handoffs": handoffs,
                "final_status": final_status,
                "final_sn": final_sn_in_chain
            })

    # Recalculate correct current_validated_in_field_count using actual chain data
    # This fixes the flawed calculation from lines 1524-1537 and ensures orphan assignment uses correct counts
    for cohort_id, chains in chains_by_cohort.items():
        correct_in_field_count = sum(1 for chain in chains if chain.get('final_status') == 'inField')
        target_cohort = next((c for c in csa_cohorts if c['orderId'] == cohort_id), None)
        if target_cohort:
            target_cohort['current_validated_in_field_count'] = correct_in_field_count
    print(f"Recalculated correct current_validated_in_field_count for {len(chains_by_cohort)} cohorts using actual chain data.")
    
    # Sort and print validated chains - separated by SKU
    sorted_cohort_ids = sorted(chains_by_cohort.keys())
    print("\n--- Detailed Chains by Cohort ---")
    
    for cohort_id in sorted_cohort_ids:
        chains_to_process = chains_by_cohort[cohort_id]
        def chain_sort_key(item):
            status = item["final_status"]; sort_order = {"inField": 0, "returned_replaced": 1, "returned_no_replacement_found": 2, "returned_no_replacement_available": 3, "returned_error_no_cohort": 98, "Unknown": 99}.get(status, 100); return (sort_order, item["chain"][0]["serial"])
        chains_to_process.sort(key=chain_sort_key)
        # Fetch the definitive cohort data from csa_cohorts list, which has updated counts
        definitive_cohort_data = next((c for c in csa_cohorts if c['orderId'] == cohort_id), None)
        
        if not definitive_cohort_data:
            print(f"Critical Error: Definitive cohort data not found for cohort_id {cohort_id} in csa_cohorts list. Skipping.", file=sys.stderr)
            continue

        # Use definitive_cohort_data for counts, but original cohort_data for other metadata if needed,
        # though ideally definitive_cohort_data should have everything. For now, let's assume
        # definitive_cohort_data has all necessary fields like orderId, csaLength, startDate etc.
        # If not, we might need to merge or be more selective.
        # For safety, let's use definitive_cohort_data as the primary source.
        
        # Separate chains by starting SKU (using chains_to_process from chains_by_cohort)
        chains_by_sku = defaultdict(list)
        for item in chains_to_process:
            starting_sku = item["chain"][0]["sku"] if item["chain"] else "UNKNOWN"
            chains_by_sku[starting_sku].append(item)
        
        # Create cohort JSON data with separated chains
        # Use definitive_cohort_data for all summary fields
        initial_scope_count_json = definitive_cohort_data.get('initialScopeCount', 0)
        # Count actual in-field chains from the processed chain data
        validated_in_field_json = sum(1 for chain in chains_to_process if chain.get('final_status') == 'inField')
        available_slots_json = initial_scope_count_json - validated_in_field_json

        cohort_json_data = {
            "cohort_summary": {
                "orderId": definitive_cohort_data['orderId'],
                "csaLength": definitive_cohort_data.get('csaLength', 'Unknown'),
                "startDate": definitive_cohort_data.get('startDate', 'N/A'), # Ensure these are present
                "startSource": definitive_cohort_data.get('startSource', 'Unknown'), # Ensure these are present
                "endDate": definitive_cohort_data.get('endDate', 'N/A'),
                "warningDate": definitive_cohort_data.get('warningDate', 'N/A'),
                "remainingReplacements": definitive_cohort_data.get('remainingReplacements', 0), # Max replacement events left
                "totalReplacements": definitive_cohort_data.get('totalReplacements', 0), # Max replacement events total
                "initialScopeCount": initial_scope_count_json,
                "currentValidatedInFieldCount": validated_in_field_json,
                "available_slots_pre_orphan_assignment": available_slots_json
            },
            "chains_by_sku": {}
        }
        
        # Calculate for print statement using actual chain data
        initial_slots_print = definitive_cohort_data.get('initialScopeCount', 0)
        # Count actual in-field chains from the processed chain data
        validated_in_field_print = sum(1 for chain in chains_to_process if chain.get('final_status') == 'inField')
        available_slots_calc_print = initial_slots_print - validated_in_field_print
        
        print(f"\nCohort: {definitive_cohort_data['orderId']} | CSA Length: {definitive_cohort_data.get('csaLength', 'Unknown')} | Start: {definitive_cohort_data.get('startDate', 'N/A')} ({definitive_cohort_data.get('startSource', 'Unknown')}) | End: {definitive_cohort_data.get('endDate', 'N/A')} | Warn: {definitive_cohort_data.get('warningDate', 'N/A')} | Initial Slots: {initial_slots_print} | Validated In-Field: {validated_in_field_print} | Available Slots (Pre-Orphan): {available_slots_calc_print}/{initial_slots_print} | Max Repl. Events Left: {definitive_cohort_data.get('remainingReplacements',0)}/{definitive_cohort_data.get('totalReplacements',0)}")
        
        # Process chains separated by SKU
        for sku in sorted(chains_by_sku.keys()):
            sku_chains = chains_by_sku[sku]
            cohort_json_data["chains_by_sku"][sku] = []
            print(f"\n  --- {sku} Chains ---")
            
            for item in sku_chains:
                serial_list_for_str = [entry["serial"] if isinstance(entry, dict) else entry for entry in item["chain"]]
                chain_str = ' -> '.join(serial_list_for_str)
                final_status = item["final_status"]
                final_sn = item["final_sn"]
                status_desc = get_status_description(final_status)
                
                chain_json_data = {
                    "chain": item["chain"],
                    "final_status": final_status,
                    "final_status_description": status_desc,
                    "final_serial_number": final_sn,
                    "handoffs": item["handoffs"]
                }
                cohort_json_data["chains_by_sku"][sku].append(chain_json_data)
                print(f"    Chain: {chain_str} | Final Status: {status_desc}")
                if item["handoffs"]:
                    for h in item["handoffs"]:
                        print(f"      - {h}")
                if final_status in ['returned_no_replacement_found', 'returned_no_replacement_available', 'returned_error_no_cohort']:
                    if final_sn in scopeMap:
                        rma_date = scopeMap[final_sn].get('rmaDate', 'N/A')
                        print(f"      (Final serial {final_sn} returned on {rma_date})")
        
        results_data["csa_replacement_chains"].append(cohort_json_data)

    print("\n" + "="*27 + " End of Validated CSA Chains " + "="*27) # Adjusted title

    # --- Phase 3: Handle "Standalone Returned Orphans" (SROs) with Cohort Isolation ---
    print("\n--- Handling Standalone Returned Orphans (SROs) with Cohort Isolation ---")
    sro_events_for_report = []
    sro_processed_instance_keys = set() # Track instances processed as SROs

    # Ensure validated_chain_instances is defined, even if no validated chains were built
    if 'validated_chain_instances' not in locals():
        validated_chain_instances = set()

    for instance_key, instance_data in shipmentInstanceMap.items():
        if (instance_data.get('cohort') is None and
            instance_data.get('rmaDateObj') is not None and
            instance_data.get('currentStatus') == 'returned' and # Ensure it's marked as returned
            instance_key not in validated_chain_instances):

            sro_serial = instance_data.get('serial')
            sro_initial_ship_date_obj = instance_data.get('originalShipmentDateObj')
            sro_rma_date_obj = instance_data.get('rmaDateObj')

            if not sro_initial_ship_date_obj or not sro_rma_date_obj:
                print(f"  Skipping potential SRO {sro_serial} due to missing dates.")
                continue

            # COHORT ISOLATION FIX: Check original cohort membership first
            original_cohort_id = original_cohort_membership.get(sro_serial)
            assigned = False
            
            if original_cohort_id:
                print(f"  SRO {sro_serial}: Checking original cohort {original_cohort_id} first...")
                # Try to assign to original cohort first
                original_cohort = next((c for c in csa_cohorts if c['orderId'] == original_cohort_id), None)
                
                if original_cohort and original_cohort['remainingReplacements'] > 0:
                    # PREFERRED: Assign to original cohort
                    original_cohort['remainingReplacements'] -= 1
                    instance_data['cohort'] = original_cohort['orderId']
                    instance_data['currentStatus'] = 'SRO_slot_consumed'
                    
                    if sro_serial in scopeMap:
                        scopeMap[sro_serial]['cohort'] = original_cohort['orderId']

                    sro_events_for_report.append({
                        "serial": sro_serial,
                        "original_ship_date": dt_to_str(sro_initial_ship_date_obj),
                        "rma_date": dt_to_str(sro_rma_date_obj),
                        "assigned_cohort_id": original_cohort['orderId'],
                        "action": "SRO assigned to original cohort.",
                        "cohort_isolation": "respected",
                        "assignment_type": "same_cohort_preferred"
                    })
                    sro_processed_instance_keys.add(instance_key)
                    cohort_isolation_stats['sro_same_cohort_assignments'] += 1
                    print(f"  ✓ SRO: {sro_serial} assigned to ORIGINAL cohort {original_cohort['orderId']}. Isolation respected.")
                    assigned = True
                else:
                    capacity_msg = "no capacity" if original_cohort else "not found"
                    print(f"  SRO {sro_serial}: Original cohort {original_cohort_id} {capacity_msg}. Checking alternatives...")
            
            if not assigned:
                # FALLBACK: Find best alternative cohort by date
                best_cohort_for_sro = None
                latest_start_date_for_sro = None

                for cohort_obj in csa_cohorts:
                    cohort_start_date_obj = cohort_obj.get('startDateObj')
                    if (cohort_start_date_obj and
                        cohort_start_date_obj <= sro_initial_ship_date_obj and
                        cohort_obj['remainingReplacements'] > 0):
                        
                        if latest_start_date_for_sro is None or cohort_start_date_obj > latest_start_date_for_sro:
                            latest_start_date_for_sro = cohort_start_date_obj
                            best_cohort_for_sro = cohort_obj
                
                if best_cohort_for_sro:
                    # CROSS-COHORT ASSIGNMENT - Track as violation
                    best_cohort_for_sro['remainingReplacements'] -= 1
                    instance_data['cohort'] = best_cohort_for_sro['orderId']
                    instance_data['currentStatus'] = 'SRO_slot_consumed'
                    
                    if sro_serial in scopeMap:
                        scopeMap[sro_serial]['cohort'] = best_cohort_for_sro['orderId']
                    
                    # Track cross-cohort violation
                    violation_reason = 'original_cohort_no_capacity' if original_cohort_id else 'no_original_cohort'
                    cross_cohort_violations.append({
                        'serial': sro_serial,
                        'original_cohort': original_cohort_id,
                        'assigned_cohort': best_cohort_for_sro['orderId'],
                        'violation_type': 'sro_cross_cohort_assignment',
                        'reason': violation_reason,
                        'timestamp': datetime.now().isoformat()
                    })

                    sro_events_for_report.append({
                        "serial": sro_serial,
                        "original_ship_date": dt_to_str(sro_initial_ship_date_obj),
                        "rma_date": dt_to_str(sro_rma_date_obj),
                        "assigned_cohort_id": best_cohort_for_sro['orderId'],
                        "original_cohort_id": original_cohort_id,
                        "action": f"SRO cross-cohort assignment ({violation_reason}).",
                        "cohort_isolation": "violated",
                        "assignment_type": "cross_cohort_fallback"
                    })
                    sro_processed_instance_keys.add(instance_key)
                    cohort_isolation_stats['sro_cross_cohort_assignments'] += 1
                    print(f"  ⚠ SRO: {sro_serial} CROSS-COHORT assignment to {best_cohort_for_sro['orderId']} (was {original_cohort_id}). Violation logged.")
                else:
                    print(f"  ✗ SRO: {sro_serial} - no suitable cohort with capacity found.")
                    sro_events_for_report.append({
                        "serial": sro_serial,
                        "original_ship_date": dt_to_str(sro_initial_ship_date_obj),
                        "rma_date": dt_to_str(sro_rma_date_obj),
                        "action": "SRO identified, but no cohort capacity available.",
                        "cohort_isolation": "n/a",
                        "assignment_type": "unassigned"
                    })

    print(f"Processed {len(sro_processed_instance_keys)} instances as SROs.")
    print(f"Cohort Isolation - Same-cohort SRO assignments: {cohort_isolation_stats['sro_same_cohort_assignments']}")
    print(f"Cohort Isolation - Cross-cohort SRO assignments: {cohort_isolation_stats['sro_cross_cohort_assignments']}")
    # Add sro_events_for_report to results_data later if needed for JSON output

    # --- Step 7: Identify Orphans ---
    # Original orphan identification logic based on scopeMap might still be useful for a general overview
    # but primary orphan chain building will use shipmentInstanceMap.
    orphan_serials = {sn for sn, details in scopeMap.items() if details.get('cohort') is None}
    print(f"\nIdentified {len(orphan_serials)} potential orphan serials (never assigned to a cohort).")

    # Gather all instances that were used in validated chains
    validated_chain_instances = set()
    if 'validated_chains_new' in locals() and validated_chains_new: # Check if it exists and is not empty
        for chain in validated_chains_new: # Use the correct variable name
            for instance_key in chain.get('chain', []):
                if isinstance(instance_key, tuple):
                    validated_chain_instances.add(instance_key)
    
    # Convert orphan serials to orphan instance keys for the new logic
    # Exclude instances that were already processed in validated chains
    orphan_instance_keys = {
        instance_key for instance_key, instance_data in shipmentInstanceMap.items()
        if (instance_data.get('cohort') is None and # Still no cohort after SRO processing
            instance_key not in validated_chain_instances and
            instance_key not in sro_processed_instance_keys) # Exclude SROs
    }
    print(f"Identified {len(orphan_instance_keys)} remaining orphan instance keys for enhanced chain building (after SRO processing).")

    # --- Step 8: Build Speculative Orphan Chains (Enhanced Logic) ---
    print(f"\nBuilding orphan chains using enhanced logic with explicit SO text field search...")
    speculative_orphan_chains_new = build_speculative_orphan_chains_new_logic(
        orphan_instance_keys, shipmentInstanceMap, SPECULATIVE_REPLACEMENT_WINDOW_DAYS,
        csa_order_ids, sales_orders, csa_cohorts=None, is_validated_chains=False
    )

    # Convert the new chain format to be compatible with the existing associate_orphans_to_cohorts function
    speculative_orphan_chains = []
    for chain_data in speculative_orphan_chains_new:
        chain_instance_keys = chain_data.get('chain', [])
        handoffs = chain_data.get('handoffs', [])
        
        # Convert instance keys to serial-based format for backward compatibility
        chain_serials = []
        for instance_key in chain_instance_keys:
            instance = shipmentInstanceMap.get(instance_key, {})
            serial = instance.get('serial', 'N/A')
            sku = instance.get('csaItemSku', 'UNKNOWN')
            chain_serials.append({"serial": serial, "sku": sku})
        
        compatible_chain = {
            "chain": chain_serials,
            "handoffs": handoffs,
            "final_status": chain_data.get('final_status', 'Unknown'),
            "final_status_description": f"Status: {chain_data.get('final_status', 'Unknown')}",
            "final_serial_number": chain_data.get('final_serial_number', 'N/A'),
            "starter_serial": chain_data.get('starter_serial', 'N/A'),
            "assignment_method": "enhanced_logic_with_explicit_links"
        }
        speculative_orphan_chains.append(compatible_chain)
    
    print(f"Built {len(speculative_orphan_chains)} orphan chains using enhanced logic.")

    # --- Step 9: Associate Orphan Chains to Cohorts ---
    # --- Step 9: Associate Orphan Chains to Cohorts with Isolation ---
    print("Associating orphan chains to cohorts with cohort isolation...")
    speculative_orphan_analysis = associate_orphans_to_cohorts_with_isolation(
        speculative_orphan_chains, scopeMap, csa_cohorts, original_cohort_membership, cohort_isolation_stats
    )
    results_data["speculative_orphan_analysis"] = speculative_orphan_analysis # Store original results for backward compatibility

    # --- Step 10: Output Orphan Analysis (Separated by SKU) ---
    print("\n" + "="*28 + f" Speculative Orphan Analysis ({', '.join(TARGET_ENDOSCOPE_SKUS)}) " + "="*28)
    if speculative_orphan_analysis:
        print(f"(Attempting to link {len(orphan_serials)} orphans using a {SPECULATIVE_REPLACEMENT_WINDOW_DAYS}-day replacement window and associating based on initial ship date)")

        # Sort orphan chains for consistent output, e.g., by assigned cohort then starter serial
        speculative_orphan_analysis.sort(key=lambda x: (x.get('assigned_cohort', 'Z'), x['starter_serial']))

        # Group orphan chains by cohort and then by SKU
        orphan_chains_by_cohort = defaultdict(lambda: defaultdict(list))
        for item in speculative_orphan_analysis:
            assigned_cohort = item.get('assigned_cohort', 'Unknown')
            starting_sku = item["chain"][0]["sku"] if item["chain"] else "UNKNOWN"
            orphan_chains_by_cohort[assigned_cohort][starting_sku].append(item)

        # Update JSON structure to separate orphan chains by SKU
        orphan_analysis_by_cohort = {}
        for cohort_id in sorted(orphan_chains_by_cohort.keys()):
            orphan_analysis_by_cohort[cohort_id] = {}
            sku_chains = orphan_chains_by_cohort[cohort_id]
            
            print(f"\n--- Orphan Chains/Units Assigned to Cohort: {cohort_id} ---")
            
            for sku in sorted(sku_chains.keys()):
                orphan_analysis_by_cohort[cohort_id][sku] = []
                print(f"\n  --- {sku} Orphan Chains ---")
                
                for item in sku_chains[sku]:
                    # Extract serial numbers for chain_str if chain items are now objects
                    serial_list_for_str = [entry["serial"] if isinstance(entry, dict) else entry for entry in item["chain"]]
                    chain_str = ' -> '.join(serial_list_for_str)
                    status_desc = item["final_status_description"]
                    starter_sn = item["starter_serial"]
                    initial_ship_date = scopeMap.get(starter_sn, {}).get('originalShipmentDate', 'N/A')
                    reason = item.get('assignment_reason', '')

                    # Add to JSON structure
                    orphan_analysis_by_cohort[cohort_id][sku].append(item)

                    print(f"    Chain/Unit: {chain_str} | Final Status: {status_desc}")
                    print(f"      (Starts with: {starter_sn}, Initially Shipped: {initial_ship_date})")
                    print(f"      (Assignment Reason: {reason})")

                    if item["handoffs"]:
                        for h in item["handoffs"]:
                            print(f"      - {h}")
                    # Add final return date if applicable
                    final_sn = item["final_serial_number"]
                    final_status = item["final_status"]
                    if final_status.startswith('returned'):
                        rma_date = scopeMap.get(final_sn, {}).get('rmaDate', 'N/A')
                        print(f"      (Final serial {final_sn} returned on {rma_date})")

        # Update the results_data structure
        results_data["speculative_orphan_analysis_by_cohort"] = orphan_analysis_by_cohort

    else:
        print("No orphan serials found or no speculative chains could be built.")

    print("\n" + "="*28 + " End of Speculative Orphan Analysis " + "="*29)


    # --- Step 11: Summary Reporting ---
    shipped_target = {sn for sn, details in scopeMap.items() if details.get('originalShipmentDate') != 'N/A'}
    returned_target = {sn for sn, details in scopeMap.items() if details.get('rmaDate') is not None}
    serials_in_any_chain = all_serials_in_validated_chains.union(
         {item["serial"] if isinstance(item, dict) else item for chain_info in speculative_orphan_analysis for item in chain_info['chain']}
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

    print("\n" + "="*22 + f" {', '.join(TARGET_ENDOSCOPE_SKUS)} Status Summary " + "="*22)
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
    skus_str_for_len = ', '.join(TARGET_ENDOSCOPE_SKUS) if TARGET_ENDOSCOPE_SKUS else ""
    print("=" * (22 + len(f" {skus_str_for_len} Status Summary ") + 22))
# --- Cohort Isolation Summary ---
    print("\n" + "="*25 + " Cohort Isolation Summary " + "="*25)
    print(f"Cross-Cohort Violations Detected: {len(cross_cohort_violations)}")
    print(f"SRO Assignments - Same Cohort: {cohort_isolation_stats['sro_same_cohort_assignments']}")
    print(f"SRO Assignments - Cross Cohort: {cohort_isolation_stats['sro_cross_cohort_assignments']}")
    print(f"Orphan Assignments - Same Cohort: {cohort_isolation_stats['orphan_same_cohort_assignments']}")
    print(f"Orphan Assignments - Blocked (Isolation): {cohort_isolation_stats['orphan_cross_cohort_blocked']}")

    if cross_cohort_violations:
        print("\nDetailed Cross-Cohort Violations:")
        for i, violation in enumerate(cross_cohort_violations[:10]):  # Show first 10
            print(f"  {i+1}. Serial {violation['serial']}: {violation['violation_type']}")
            print(f"      Original: {violation['original_cohort']} → Assigned: {violation.get('assigned_cohort', 'N/A')}")
            print(f"      Reason: {violation.get('reason', 'N/A')}")
    
        if len(cross_cohort_violations) > 10:
            print(f"  ... and {len(cross_cohort_violations) - 10} more violations")

    print("=" * (25 + len(" Cohort Isolation Summary ") + 25))

    # Add violation data to results
    results_data["cohort_isolation_analysis"] = {
        "statistics": cohort_isolation_stats,
        "violations": cross_cohort_violations,
        "violation_count": len(cross_cohort_violations),
        "isolation_effectiveness": {
            "sro_isolation_rate": cohort_isolation_stats['sro_same_cohort_assignments'] / 
                                 (cohort_isolation_stats['sro_same_cohort_assignments'] + cohort_isolation_stats['sro_cross_cohort_assignments']) 
                                 if (cohort_isolation_stats['sro_same_cohort_assignments'] + cohort_isolation_stats['sro_cross_cohort_assignments']) > 0 else 1.0,
            "orphan_isolation_rate": cohort_isolation_stats['orphan_same_cohort_assignments'] / 
                                    (cohort_isolation_stats['orphan_same_cohort_assignments'] + cohort_isolation_stats['orphan_cross_cohort_blocked']) 
                                    if (cohort_isolation_stats['orphan_same_cohort_assignments'] + cohort_isolation_stats['orphan_cross_cohort_blocked']) > 0 else 1.0
        }
    }


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
    
    print(f"STEP2 DEBUG: Attempting to write JSON to: {output_json_path}")
    if not results_data.get("csa_replacement_chains"):
        print(f"STEP2 DEBUG: 'csa_replacement_chains' is empty or not present in results_data before saving.")
    else:
        print(f"STEP2 DEBUG: 'csa_replacement_chains' has {len(results_data['csa_replacement_chains'])} items before saving.")


    try:
        with open(output_json_path, 'w') as json_f:
            # Use default=str to handle date objects during JSON serialization
            json.dump(results_data, json_f, indent=4, default=str)
        print(f"\nStructured output successfully saved to {output_json_path}") # Changed for clarity
        print(f"STEP2 DEBUG: Successfully wrote JSON to: {output_json_path}")
    except Exception as e:
        print(f"Error saving JSON output to {output_json_path}: {e}", file=sys.stderr)
        print(f"STEP2 DEBUG: FAILED to write JSON to: {output_json_path} due to {e}")


if __name__ == "__main__":
    # Setup argument parser for direct execution/testing
    parser = argparse.ArgumentParser(description=f"Analyze CSA replacement chains for SKUs: {', '.join(TARGET_ENDOSCOPE_SKUS)}.")
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
