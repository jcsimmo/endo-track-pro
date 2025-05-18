from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import databutton as db
import json
import math
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from collections import deque, defaultdict
from app.apis.zoho_data_extractor import generate_serial_history_data
import sys

router = APIRouter()

# --- Configuration Constants (moved outside function) ---
TARGET_ENDOSCOPE_SKU = 'P313N00'
SPECULATIVE_REPLACEMENT_WINDOW_DAYS = 30 # Days to look forward for an orphan replacement
DEFAULT_RETURN_PRICE = 1200.0 # Used for savings calculation
# Keywords to identify CSA orders/items
CSA_SKU_KEYWORDS = ['hifcsa-1yr', 'hifcsa-2yr', 'hifcsa-m2m']
CSA_ITEM_NAME_KEYWORDS = ['csa', 'prepaid']

# --- Helper Functions (defined at module level) ---
def parse_date_flexible(datestr):
    """Attempt to parse a date string in a few common formats; return date object or None."""
    if not datestr or not isinstance(datestr, str):
        return None
    datestr_clean = datestr.strip().lower()
    if datestr_clean in ['not shipped', 'not recorded', '', 'n/a', 'none']:
        return None

    possible_formats = [
        '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y',
        '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M',
        '%b %d, %Y', '%d-%b-%Y'
    ]
    for fmt in possible_formats:
        try:
            base_part = datestr.split('T')[0].split(' ')[0]
            dt = datetime.strptime(base_part, fmt.split('T')[0].split(' ')[0])
            return dt.date()
        except ValueError:
            continue
        except Exception as e:
            print(f"Warning [parse_date]: Unexpected error parsing '{datestr}' with format '{fmt}': {e}")
            continue
    return None

def dt_to_str(dt_obj):
    """Convert date or datetime object to 'YYYY-MM-DD' string or 'N/A' if invalid."""
    if isinstance(dt_obj, (date, datetime)):
        return dt_obj.strftime('%Y-%m-%d')
    return 'N/A'

def get_status_description(status_code):
    status_map = {
        "inField": "In Field",
        "returned_replaced": "Returned & Replaced",
        "returned_no_replacement_found": "Returned (No Replacement Found)",
        "returned_no_replacement_available": "Returned (No Replacements Left)",
        "returned_error_no_cohort": "Returned (Error: Cohort Issue)",
        "Unknown": "Unknown"
    }
    return status_map.get(status_code, status_code)

def build_speculative_orphan_chains(orphan_instance_keys, shipmentInstanceMap, window_days, csa_order_ids):
    if not orphan_instance_keys:
        return []
    speculative_chains = []
    processed_in_spec_chain = set()
    returned_orphan_details = []
    potential_replacements = []

    for instance_key in orphan_instance_keys:
        instance = shipmentInstanceMap.get(instance_key)
        if not instance:
            continue


        rma_dt = instance.get('rmaDateObj')
        if rma_dt:
            returned_orphan_details.append({'instance_key': instance_key, 'rma_date': rma_dt})
        ship_dt = instance.get('originalShipmentDateObj')
        if ship_dt:
            potential_replacements.append({'instance_key': instance_key, 'ship_date': ship_dt})

    returned_orphan_details.sort(key=lambda x: x['rma_date'])
    potential_replacements.sort(key=lambda x: x['ship_date'])

    for returned_detail in returned_orphan_details:
        start_instance_key = returned_detail['instance_key']
        if start_instance_key in processed_in_spec_chain:
            continue
        current_chain = []
        current_handoffs = []
        current_instance_key = start_instance_key
        visited_in_this_chain_attempt = set()

        while current_instance_key and current_instance_key in orphan_instance_keys and current_instance_key not in visited_in_this_chain_attempt:
            visited_in_this_chain_attempt.add(current_instance_key)
            current_chain.append(current_instance_key)
            instance = shipmentInstanceMap.get(current_instance_key)
            if not instance:
                break

            rma_dt = instance.get('rmaDateObj')
            if rma_dt:
                best_replacement_key = None
                best_replacement_date = None
                for rep_detail in potential_replacements:
                    cand_key = rep_detail['instance_key']
                    cand_ship_dt = rep_detail['ship_date']
                    if (cand_key != current_instance_key and
                        cand_key not in processed_in_spec_chain and
                        cand_ship_dt > rma_dt and
                        cand_ship_dt <= rma_dt + timedelta(days=window_days) and
                        cand_key[1] not in csa_order_ids):
                        best_replacement_key = cand_key
                        best_replacement_date = cand_ship_dt
                        break
                if best_replacement_key:
                    rep_ship_str = dt_to_str(best_replacement_date)
                    rma_str = dt_to_str(rma_dt)
                    returned_sn = shipmentInstanceMap.get(current_instance_key, {}).get('serial', 'N/A')
                    replacement_sn = shipmentInstanceMap.get(best_replacement_key, {}).get('serial', 'N/A')
                    current_handoffs.append(f"Returned {returned_sn} on {rma_str}, potentially replaced by {replacement_sn} shipped on {rep_ship_str}")
                    processed_in_spec_chain.add(best_replacement_key)
                    current_instance_key = best_replacement_key
                else:
                    current_instance_key = None
            else:
                current_instance_key = None
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

def associate_orphans_to_cohorts(orphan_chains, shipmentInstanceMap, csa_cohorts):
    if not csa_cohorts:
        for chain in orphan_chains:
            chain['assigned_cohort'] = "No CSA Cohorts Defined"
            chain['assignment_reason'] = "N/A"
        return orphan_chains
    valid_cohorts = [c for c in csa_cohorts if isinstance(c.get('startDateObj'), date)]
    if not valid_cohorts:
         for chain in orphan_chains:
            chain['assigned_cohort'] = "No Valid CSA Cohorts Found"
            chain['assignment_reason'] = "N/A"
         return orphan_chains
    valid_cohorts.sort(key=lambda x: x['startDateObj'])

    for chain_data in orphan_chains:
        starter_instance_key = chain_data.get('starter_instance_key')
        if not starter_instance_key:
             chain_data['assigned_cohort'] = "Error: Missing Starter Instance"
             chain_data['assignment_reason'] = "Orphan chain data is missing the starter instance key."
             continue
        starter_instance = shipmentInstanceMap.get(starter_instance_key)
        initial_ship_dt = starter_instance.get('originalShipmentDateObj') if starter_instance else None
        if not initial_ship_dt:
             chain_data['assigned_cohort'] = "Error: Invalid Ship Date"
             starter_sn = starter_instance.get('serial', 'N/A') if starter_instance else 'N/A'
             chain_data['assignment_reason'] = f"No valid initial ship date found for starter instance {starter_instance_key} (Serial: {starter_sn})."
             continue


        best_cohort = None
        for cohort in reversed(valid_cohorts):
            if cohort['startDateObj'] <= initial_ship_dt:
                best_cohort = cohort
                break
        if best_cohort:
            chain_data['assigned_cohort'] = best_cohort['orderId']
            chain_data['assignment_reason'] = (f"Initial ship date {dt_to_str(initial_ship_dt)} >= cohort {best_cohort['orderId']} start {dt_to_str(best_cohort['startDateObj'])}.")
        else:
             earliest_cohort_start_str = dt_to_str(valid_cohorts[0]['startDateObj'])
             chain_data['assigned_cohort'] = "Pre-CSA / Unknown"
             chain_data['assignment_reason'] = (f"Initial ship date {dt_to_str(initial_ship_dt)} is before earliest cohort start {earliest_cohort_start_str}.")
    return orphan_chains

def calculate_performance_metrics(csa_cohorts_final, shipmentInstanceMap):
    total_handoffs = 0
    final_unreplaced_returns = 0
    accrued_years = 0.0
    total_csa_value = 0.0
    total_csa_items = 0
    today = date.today()
    all_chains_data = []

    for cohort_id, cohort_info in csa_cohorts_final.items():
        all_chains_data.extend(cohort_info.get('validated_chains', []))
        all_chains_data.extend(cohort_info.get('assigned_orphan_chains_data', []))
        summary = cohort_info.get('summary', {})
        start_dt = summary.get('startDateObj')
        end_dt = summary.get('endDateObj')
        csa_len_str = summary.get('csaLength', 'Unknown')
        csa_item_price = summary.get('csaItemPrice', 0.0)
        total_csa_value += csa_item_price
        total_csa_items += 1
        years = 0
        if csa_len_str == '1 year':
            years = 1

        elif csa_len_str == '2 year':
            years = 2

        if start_dt and end_dt and years > 0:
            total_duration_days = (end_dt - start_dt).days
            if total_duration_days <= 0:
                continue


            if end_dt <= today:
                accrued_years += years
            elif start_dt < today:
                 days_active = (today - start_dt).days
                 accrued_fraction = max(0, days_active) / total_duration_days
                 accrued_years += years * accrued_fraction

    for chain_data in all_chains_data:
        handoffs = chain_data.get('handoffs', [])
        total_handoffs += len(handoffs)
        final_status = chain_data.get('final_status', '')
        if isinstance(final_status, str) and final_status.startswith('returned'):
              final_unreplaced_returns += 1

    total_returns = total_handoffs + final_unreplaced_returns
    break_rate = (total_returns / accrued_years) if accrued_years > 0 else 0
    savings = total_returns * DEFAULT_RETURN_PRICE
    r = break_rate
    annual_price = 258.3333 * (r**2) - 58.3333 * r + 900.0
    annual_price = max(900.0, min(annual_price, 4800.0))
    average_csa_item_price = (total_csa_value / total_csa_items) if total_csa_items > 0 else 0.0

    return {
        "accrued_years": round(accrued_years, 2),
        "total_returns": total_returns,
        "total_handoffs": total_handoffs,
        "final_unreplaced_returns": final_unreplaced_returns,
        "break_rate": round(break_rate, 2),
        "savings": round(savings, 2),
        "extension_cost": round(annual_price, 2),
        "average_csa_item_price": round(average_csa_item_price, 2)
    }

def get_in_field_serials(csa_cohorts_final):
    in_field_serials = set()
    for cohort_id, cohort_info in csa_cohorts_final.items():
        chains_to_check = cohort_info.get('validated_chains', []) + \
                          cohort_info.get('assigned_orphan_chains_data', [])
        for chain_info in chains_to_check:
             if isinstance(chain_info, dict) and chain_info.get('final_status') == 'inField':
                  final_sn = chain_info.get('final_serial_number')
                  if final_sn:
                      in_field_serials.add(final_sn)
    return sorted(list(in_field_serials))

\
# --- New Transformation Function ---
def transform_serial_history_to_expected_format(serial_history_dict: dict) -> dict:
    print(f"Starting transformation of serial history. Input serials: {len(serial_history_dict)}")
    orders_data_dict = {}
    returns_data_dict = {}
    # The Zoho data has customer_name per event, we should pick one representative or make it generic.
    # For initial pass, let's try to use the one from the sale event, or a general default.
    customer_name_overall = "Prosidio Health (from Zoho Events)"

    for serial_number, events in serial_history_dict.items():
        for event in events:
            event_type = event.get("event_type")
            details = event.get("details", {})
            event_date = event.get("event_date") 

            if event_type == "Sale":
                so_num = details.get("sales_order_number")
                pkg_num = details.get("package_number")
                
                if not so_num or not pkg_num:
                    print(f"Warning (Transform-Sale): Missing SO number '{so_num}' or Package number '{pkg_num}' for event on SN {serial_number}. Details: {details}")
                    continue

                # Ensure order exists
                if so_num not in orders_data_dict:
                    orders_data_dict[so_num] = {
                        "salesorder_number": so_num,
                        "date": details.get("sales_order_date"), 
                        "customer_name": details.get("customer_name", customer_name_overall),
                        "line_items": [], 
                        "packages": {}
                    }
                
                order_entry = orders_data_dict[so_num]
                # Update customer name if a more specific one is found and it was the default
                if details.get("customer_name") and order_entry["customer_name"] == customer_name_overall:
                    order_entry["customer_name"] = details.get("customer_name")

                # Ensure package exists in the order
                if pkg_num not in order_entry["packages"]:
                    order_entry["packages"][pkg_num] = {
                        "package_number": pkg_num,
                        "shipment_date": details.get("shipment_date"),
                        "delivery_date": details.get("delivery_date"), 
                        "line_items": [] 
                    }
                
                package_entry = order_entry["packages"][pkg_num]
                # Update package shipment/delivery dates if a more recent/valid one is found
                if details.get("shipment_date") and (not package_entry["shipment_date"] or details.get("shipment_date") > package_entry["shipment_date"]):
                    package_entry["shipment_date"] = details.get("shipment_date")
                if details.get("delivery_date") and (not package_entry["delivery_date"] or details.get("delivery_date") > package_entry["delivery_date"]):
                    package_entry["delivery_date"] = details.get("delivery_date")

                package_line_item = {
                    "sku": details.get("item_sku"),
                    "name": details.get("item_name"),
                    "serial_number": serial_number, 
                    "quantity": 1, 
                }
                package_entry["line_items"].append(package_line_item)

                # Add a general line item to the SO, attempt to aggregate quantity for same SKU
                existing_so_line_item = next((li for li in order_entry["line_items"] if li["sku"] == details.get("item_sku")), None)
                if existing_so_line_item:
                    existing_so_line_item["quantity"] = existing_so_line_item.get("quantity", 0) + 1
                else:
                    so_level_line_item = {
                        "sku": details.get("item_sku"),
                        "name": details.get("item_name"),
                        "quantity": 1,
                    }
                    order_entry["line_items"].append(so_level_line_item)

            elif event_type == "Return":
                # Use rma_number if available, otherwise try receive_number or sales_return_id as fallback
                rma_num = details.get("rma_number") or details.get("receive_number") or details.get("sales_return_id")
                if not rma_num:
                    print(f"Warning (Transform-Return): Missing RMA identifier for event on SN {serial_number}. Details: {details}")
                    continue

                if rma_num not in returns_data_dict:
                    returns_data_dict[rma_num] = {
                        "rma_number": rma_num, 
                        "rma_date": event_date, 
                        "customer_name": details.get("customer_name", customer_name_overall),
                        "items": []
                    }
                
                return_entry = returns_data_dict[rma_num]
                if event_date and (not return_entry["rma_date"] or event_date > return_entry["rma_date"]): # Should be event_date for RMA
                    return_entry["rma_date"] = event_date
                if details.get("customer_name") and return_entry["customer_name"] == customer_name_overall:
                    return_entry["customer_name"] = details.get("customer_name")

                returned_item = {
                    "serial_number": serial_number,
                    "sku": details.get("item_sku"), 
                    "name": details.get("item_name")
                }
                return_entry["items"].append(returned_item)

    final_orders_data = []
    for so_num, order_details in orders_data_dict.items():
        order_details["packages"] = list(order_details["packages"].values())
        final_orders_data.append(order_details)
    
    final_returns_data = list(returns_data_dict.values())
    
    # Determine the most common customer name from orders if one wasn't consistently found.
    # This is a simple heuristic. A more robust approach might be needed if customer names vary wildly.
    if final_orders_data and customer_name_overall == "Prosidio Health (from Zoho Events)":
        customer_names_in_orders = [order.get("customer_name") for order in final_orders_data if order.get("customer_name")]
        if customer_names_in_orders:
            from collections import Counter
            most_common_customer = Counter(customer_names_in_orders).most_common(1)
            if most_common_customer:
                customer_name_overall = most_common_customer[0][0]


    print(f"Transformation complete. Orders created: {len(final_orders_data)}, Returns created: {len(final_returns_data)}, Final Customer: {customer_name_overall}")
    return {"orders": final_orders_data, "returns": final_returns_data, "customer_name": customer_name_overall}


class ProcessRequest(BaseModel):
    data_key: str # Key for the raw data in db.storage.json

@router.post("/process-sales-data", tags=["DataProcessing"], summary="Process raw sales and returns data from Zoho")
def process_sales_data_endpoint(request: ProcessRequest) -> dict:
    """
    Endpoint to trigger the processing of sales data.
    Initially, this read from a stored JSON file via request.data_key.
    Now, it fetches live data from Zoho and then processes it.
    """
    # TODO: The request.data_key is currently not used with generate_serial_history_data
    # We might simplify ProcessRequest later if this becomes the primary data source.
    print(f"Received request to process data (data_key: {request.data_key} - currently unused for Zoho live fetch)")
    
    serial_history_dict = None
    try:
        print("Attempting to fetch and generate serial history data from Zoho...")
        serial_history_dict = generate_serial_history_data()
        if serial_history_dict is None:
            print("Error: generate_serial_history_data returned None. Zoho data extraction might have failed.")
            raise HTTPException(status_code=500, detail="Failed to fetch or generate data from Zoho.")
        print(f"Successfully generated serial history data. Number of serials: {len(serial_history_dict)}")
    except HTTPException as http_exc: # Re-raise HTTPExceptions directly
        raise http_exc
    except Exception as e:
        print(f"Error during Zoho data generation: {str(e)}")
        # import traceback; traceback.print_exc(); # Uncomment for detailed debugging if needed
        raise HTTPException(status_code=500, detail=f"Error generating data from Zoho: {str(e)}") from e

    # raw_data = {"orders": [], "returns": [], "customer_name": "Prosidio Health (Live Zoho Data)"} 
    # print("Placeholder: Using empty orders/returns for now. Transformation to full raw_data pending.")
    raw_data = transform_serial_history_to_expected_format(serial_history_dict)
    print(f"Data transformed. Orders: {len(raw_data.get('orders',[]))}, Returns: {len(raw_data.get('returns',[]))}, Customer: {raw_data.get('customer_name')}")

    try:
        processed_output = process_sales_data_logic(raw_data)
        print(f"Successfully processed data (invoked with data_key: {request.data_key})")
        return processed_output
    except Exception as e:
        print(f"Critical error during data processing logic (invoked with data_key: {request.data_key}): {str(e)}")
        # import traceback; traceback.print_exc();
        raise HTTPException(status_code=500, detail=f"Error processing data: {str(e)}") from e


# This is the main logic function, renamed to avoid conflict with endpoint name
def process_sales_data_logic(raw_data: dict) -> dict:
    print("Starting process_sales_data_logic...")
    orders = raw_data.get('orders', [])
    returns = raw_data.get('returns', [])
    customer_name = raw_data.get("customer_name", "Unknown")
    print(f"Processing data for customer: {customer_name}, Orders: {len(orders)}, Returns: {len(returns)}")

    shipmentInstanceMap = defaultdict(lambda: {
        'serial': None, 'originalSoNum': None, 'originalPkgNum': None,
        'originalShipmentDate': None, 'originalShipmentDateObj': None,
        'rmaDate': None, 'rmaDateObj': None, 'replacedBySoNum': None,
        'replacedByPkgNum': None, 'replacedByInstanceKey': None,
        'isCSARelated': False, 'isOrphan': True, 'cohortId': None,
        'currentStatus': 'Unknown', 'custom_fields': {},
        'line_items': []
    })
    csa_orders = {}
    csa_order_ids = set()
    instance_key_map = {}

    print("Processing Sales Orders...")
    for order in orders:
        so_num = order.get('salesorder_number')
        order_date_str = order.get('date')
        order_date_obj = parse_date_flexible(order_date_str)
        is_csa_order = False
        csa_details = None
        for item in order.get('line_items', []):
            sku = item.get('sku', '').lower()
            name = item.get('name', '').lower()
            if any(keyword in sku for keyword in CSA_SKU_KEYWORDS) or \
               any(keyword in name for keyword in CSA_ITEM_NAME_KEYWORDS):
                is_csa_order = True
                csa_details = {
                    'sku': item.get('sku'), 'name': item.get('name'),
                    'quantity': item.get('quantity', 1), 'price': float(item.get('rate', '0'))
                }
                break
        if is_csa_order:
            csa_orders[so_num] = {
                'orderId': so_num, 'orderDate': order_date_str, 'orderDateObj': order_date_obj,
                'csaDetails': csa_details, 'linked_packages': [], 'replacementAllowance': 0,
                'endDate': None, 'endDateObj': None, 'startDate': order_date_str,
                'startDateObj': order_date_obj, 'warningDate': None, 'warningDateObj': None,
                'csaLength': 'Unknown', 'remainingReplacements': 0
            }
            csa_order_ids.add(so_num)
        for package in order.get('packages', []):
            pkg_num = package.get('package_number')
            ship_date_str = package.get('shipment_date')
            ship_date_obj = parse_date_flexible(ship_date_str)
            serials_in_package = set()
            line_items_details = []
            for item in package.get('line_items', []):
                line_items_details.append(item)
                serial = item.get('serial_number')
                item_sku = item.get('sku', '')
                if serial and item_sku == TARGET_ENDOSCOPE_SKU:
                    serials_in_package.add(serial)
            custom_fields = package.get('custom_fields', [])
            if not serials_in_package and custom_fields:
                 for field in custom_fields:
                     if field.get('label') == 'Serial Number' and field.get('value'):
                          vals = str(field.get('value')).replace(',', ' ').replace('\n', ' ').split()
                          for val in vals:
                              if val:
                                  serials_in_package.add(val)
                          break
            for serial in serials_in_package:
                instance_key = (serial, so_num, pkg_num)
                instance = shipmentInstanceMap[instance_key]
                instance['serial'] = serial
                instance['originalSoNum'] = so_num
                instance['originalPkgNum'] = pkg_num
                instance['originalShipmentDate'] = ship_date_str
                instance['originalShipmentDateObj'] = ship_date_obj
                instance['custom_fields'] = custom_fields
                instance['line_items'] = line_items_details
                instance['currentStatus'] = 'inField'
                instance['isOrphan'] = True
                instance_key_map[(so_num, pkg_num)] = instance_key
                if is_csa_order:
                    csa_orders[so_num]['linked_packages'].append(pkg_num)
                    if ship_date_obj and (not csa_orders[so_num]['startDateObj'] or ship_date_obj < csa_orders[so_num]['startDateObj']):
                         csa_orders[so_num]['startDate'] = ship_date_str
                         csa_orders[so_num]['startDateObj'] = ship_date_obj

    print("Processing Returns...")
    for rma in returns:
        rma_date_str = rma.get('rma_date')
        rma_date_obj = parse_date_flexible(rma_date_str)
        items = rma.get('items', [])
        for item in items:
            serial = item.get('serial_number')
            if not serial:
                continue


            latest_shipment_key = None
            latest_shipment_date = None
            for key, instance in shipmentInstanceMap.items():
                if key[0] == serial and instance.get('originalShipmentDateObj'):
                    ship_date = instance['originalShipmentDateObj']
                    if rma_date_obj and ship_date > rma_date_obj:
                        continue
                    if latest_shipment_date is None or ship_date > latest_shipment_date:
                        latest_shipment_date = ship_date
                        latest_shipment_key = key
            if latest_shipment_key:
                instance = shipmentInstanceMap[latest_shipment_key]
                instance['rmaDate'] = rma_date_str
                instance['rmaDateObj'] = rma_date_obj
            #else:
                #print(f"  Warning: Could not find matching shipped instance for returned serial {serial} from RMA {rma.get('rma_number', 'N/A')}")


    # --- Start of User's Script Integration ---
    print("Step 4: Defining CSA Cohorts based on new logic...")
    csa_cohorts = [] # This will be a list of cohort_info dicts
    # serial_to_cohort_map = {} # Not directly used in the final structure, cohortId is on instance

    # Using global CSA_SKU_KEYWORDS, CSA_ITEM_NAME_KEYWORDS, TARGET_ENDOSCOPE_SKU from module level

    for so in orders: # Renamed from sales_orders (which is raw_data['orders'])
        so_num = so.get('salesorder_number')
        lines = so.get('line_items', [])
        if not isinstance(lines, list):
            continue

        has_csa = False
        csa_length = "Unknown"
        temp_len_from_sku = None # To prioritize 2yr if both 1yr and 2yr indicators are present

        for item in lines:
            if not isinstance(item, dict):
                continue
            sku = (item.get('sku') or '').lower()
            name = (item.get('name') or '').lower()

            is_csa_sku = any(k in sku for k in CSA_SKU_KEYWORDS)
            # Per user: all keywords must be present in name for csa_name_keywords
            is_csa_name = all(nk_name in name for nk_name in CSA_ITEM_NAME_KEYWORDS) if CSA_ITEM_NAME_KEYWORDS else False

            if is_csa_sku or is_csa_name:
                has_csa = True
                # Determine CSA length, prioritizing 2yr if multiple indicators found
                if "2 year" in name or "2yr" in sku or "hifcsa-2yr" in sku:
                    csa_length = "2 year"
                elif ("1 year" in name or "1yr" in sku or "hifcsa-1yr" in sku) and csa_length != "2 year": # Only set to 1yr if not already 2yr
                     csa_length = "1 year"

                # Check SKU specifically for length, temp_len_from_sku helps ensure 2yr priority
                if "hifcsa-2yr" in sku:
                    temp_len_from_sku = "2 year"
                elif "hifcsa-1yr" in sku and temp_len_from_sku != "2 year": 
                    temp_len_from_sku = "1 year"

        if csa_length == "Unknown" and temp_len_from_sku: 
            csa_length = temp_len_from_sku

        if not has_csa: 
            # print(f"DEBUG: SO {so_num} - Not a CSA order. Skipping.") # Too verbose for default
            continue
        print(f"DEBUG: SO {so_num} - Identified as CSA. Determined length: {csa_length}")

        current_cohort_instance_keys = []
        current_ship_dts = []
        found_target_sku_for_this_csa_so = False

        # Iterate through packages of THIS sales order (so) to find shipped TARGET_ENDOSCOPE_SKU
        # This part matches user's logic: "for pkg in so.get('packages', []): ... for dline in pkg.get('detailed_line_items', []): ... if dline.get('sku') == TARGET_ENDOSCOPE_SKU:"
        # We rely on shipmentInstanceMap already being populated with (serial, so_num, pkg_num) keys for TARGET_ENDOSCOPE_SKU items.
        for pkg_item in so.get('packages', []):
            pkg_num_item = pkg_item.get('package_number')
            pkg_date_str_item = None 
            pkg_ship_order_item = pkg_item.get('shipment_order', {})
            pkg_date_sources_item = [
                (pkg_ship_order_item.get('delivery_date'), 'pkg_delivery (SO)'), 
                (pkg_item.get('delivery_date'), 'pkg_delivery (PKG)'),
                (pkg_ship_order_item.get('shipment_date'), 'pkg_ship (SO)'), 
                (pkg_item.get('shipment_date'), 'pkg_ship (PKG)')
            ]
            for p_date_item, p_src_item in pkg_date_sources_item:
                if p_date_item and str(p_date_item).strip().lower() not in ['not shipped', 'not recorded','']:
                    pkg_date_str_item = p_date_item
                    break
            pkg_dt_item = parse_date_flexible(pkg_date_str_item)

            for dline_item in pkg_item.get('detailed_line_items', []):
                 if dline_item.get('sku') == TARGET_ENDOSCOPE_SKU:
                      found_target_sku_for_this_csa_so = True
                      serials_item = dline_item.get('serial_numbers', []) # User script: serials
                      proc_sns_item = []
                      if isinstance(serials_item, list):
                          proc_sns_item = [str(s_item).strip() for s_item in serials_item if str(s_item).strip()]
                      elif serials_item and str(serials_item).strip():
                          proc_sns_item = [str(serials_item).strip()]

                      for sn_item in proc_sns_item:
                          if sn_item and pkg_num_item: 
                              instance_key_item = (sn_item, so_num, pkg_num_item) # Match user's (sn, so_num, pkg_num)
                              if instance_key_item in shipmentInstanceMap: # Check against pre-populated map
                                  current_cohort_instance_keys.append(instance_key_item)
                                  # Use the ship date from the pre-populated shipmentInstanceMap as it's more reliable if pkg_dt_item is None
                                  inst_ship_dt = shipmentInstanceMap[instance_key_item].get('originalShipmentDateObj')
                                  if inst_ship_dt: 
                                      current_ship_dts.append(inst_ship_dt)
                                      print(f"DEBUG: SO {so_num} - Instance {instance_key_item} added to cohort. Ship date (from map): {dt_to_str(inst_ship_dt)}")
                                  elif pkg_dt_item: 
                                      current_ship_dts.append(pkg_dt_item)
                                      print(f"DEBUG: SO {so_num} - Instance {instance_key_item} added to cohort. Ship date (from pkg_dt_item): {dt_to_str(pkg_dt_item)}")
                                  else:
                                      print(f"DEBUG: SO {so_num} - Instance {instance_key_item} has no reliable ship date. Not adding to current_ship_dts.")
                              #else: User script implies a warning if not in shipmentInstanceMap, but our map *is* the source of truth for shipped target SKUs.
                                  # So, if it's not in shipmentInstanceMap, it means this specific serial for this SO/PKG wasn't recorded as a TARGET_ENDOSCOPE_SKU shipment.

        if not found_target_sku_for_this_csa_so:
            print(f"DEBUG: SO {so_num} - CSA order, but no target SKU ({TARGET_ENDOSCOPE_SKU}) found in its packages. Skipping cohort creation.")
            continue

        start_dt_obj = min(current_ship_dts) if current_ship_dts else parse_date_flexible(so.get('date'))
        start_src = "Earliest Pkg Ship/Delivery Date" if current_ship_dts else ("SO Date" if start_dt_obj else "Unknown")
        print(f"DEBUG: SO {so_num} - Cohort Start Date: {dt_to_str(start_dt_obj)}, Source: {start_src}")

        end_dt_obj = None
        warn_dt_obj = None
        if start_dt_obj and csa_length != "Unknown":
            try:
                years_delta = 0
                if csa_length == "1 year":
                    years_delta = 1
                elif csa_length == "2 year":
                    years_delta = 2

                if years_delta > 0:
                    end_dt_obj = start_dt_obj + relativedelta(years=years_delta)
                    warn_dt_obj = end_dt_obj - timedelta(days=60)
            except Exception as e:
                 print(f"Warning (User Script Logic - Cohort Dates): Error calculating end/warning date for cohort {so_num}: {e}", file=sys.stderr)
        print(f"DEBUG: SO {so_num} - Calculated End Date: {dt_to_str(end_dt_obj)}, Warning Date: {dt_to_str(warn_dt_obj)}")

        initial_scopes_count = len(list(set(current_cohort_instance_keys))) # Count unique instance keys
        if initial_scopes_count == 0:
            print(f"DEBUG: SO {so_num} - No initial scopes identified after processing packages. Skipping cohort creation.")
            continue

        total_replacements_allowed = initial_scopes_count * 4

        cohort_info = {
            'orderId': so_num,
            'startDate': dt_to_str(start_dt_obj), 'startDateObj': start_dt_obj, 'startSource': start_src,
            'csaScopeInstanceKeys': sorted(list(set(current_cohort_instance_keys))), # Ensure unique keys & sort
            'initialScopeCount': initial_scopes_count,
            'totalReplacements': total_replacements_allowed,
            'remainingReplacements': total_replacements_allowed, 
            'csaLength': csa_length,
            'endDate': dt_to_str(end_dt_obj), 'endDateObj': end_dt_obj,
            'warningDate': dt_to_str(warn_dt_obj), 'warningDateObj': warn_dt_obj,
            'assigned_orphan_chains_data': [] 
        }
        print(f"DEBUG: SO {so_num} - Creating cohort_info: {json.dumps(cohort_info, default=str)}")
        csa_cohorts.append(cohort_info)

        for inst_key_for_tagging in cohort_info['csaScopeInstanceKeys']:
            if inst_key_for_tagging in shipmentInstanceMap:
                shipmentInstanceMap[inst_key_for_tagging]['cohort'] = so_num 
                shipmentInstanceMap[inst_key_for_tagging]['isOrphan'] = False
                shipmentInstanceMap[inst_key_for_tagging]['isCSARelated'] = True
                print(f"DEBUG: SO {so_num} - Tagged instance {inst_key_for_tagging} with cohort ID {so_num}.")
            # else: This case is unlikely if current_cohort_instance_keys came from shipmentInstanceMap correctly.

    csa_cohorts.sort(key=lambda x_sort: (x_sort['startDateObj'] is None, x_sort['startDateObj']))
    print(f"User Script Logic: Identified {len(csa_cohorts)} CSA cohorts containing the target SKU.")

    # --- User's Script Part 2: Calculate Average CSA Item Price ---
    print("Step 5: Calculating Average CSA Item Price based on new logic...")
    total_csa_item_cost = 0.0
    total_csa_item_quantity = 0.0 

    actual_csa_order_ids_with_scopes_for_price = {cohort_price['orderId'] for cohort_price in csa_cohorts}

    for so_data_for_price in orders: 
        so_number_for_price = so_data_for_price.get('salesorder_number')
        if so_number_for_price in actual_csa_order_ids_with_scopes_for_price:
            for item_for_price in so_data_for_price.get('line_items', []):
                if isinstance(item_for_price, dict) and item_for_price.get('sku') == TARGET_ENDOSCOPE_SKU:
                    try:
                        rate = float(item_for_price.get('rate', 0.0))
                        quantity = float(item_for_price.get('quantity', 0.0))
                    except ValueError:
                        print(f"Warning (User Script Logic - Avg Price): Could not parse rate/quantity for item in SO {so_number_for_price}. Item: {item_for_price}", file=sys.stderr)
                        continue
                    if rate > 0 and quantity > 0: 
                        total_csa_item_cost += rate * quantity
                        total_csa_item_quantity += quantity

    average_csa_item_price = (total_csa_item_cost / total_csa_item_quantity) if total_csa_item_quantity > 0 else 0.0
    print(f"User Script Logic: Calculated average price for non-free '{TARGET_ENDOSCOPE_SKU}' items in CSA orders: ${average_csa_item_price:,.2f}")

    # --- User's Script Part 3: Process RMAs and Link Replacements ---
    print("Step 6: Processing RMAs and Linking Replacements based on new logic...")
    available_instance_keys_list_for_deque_rma = sorted(
        [key_avail_rma for key_avail_rma, instance_avail_rma in shipmentInstanceMap.items()
         if instance_avail_rma.get('originalShipmentDateObj') and instance_avail_rma.get('cohort') is None and # Not part of any CSA cohort initial scopes
            instance_avail_rma.get('currentStatus') == 'inField' # Must be available
        ],
        key=lambda k_avail_rma: shipmentInstanceMap[k_avail_rma]['originalShipmentDateObj']
    )
    available_instance_keys_deque_rma = deque(available_instance_keys_list_for_deque_rma)
    print(f"DEBUG (Step 6): Initial available_instance_keys_deque_rma size: {len(available_instance_keys_deque_rma)}")
    used_replacement_instance_keys_set_rma = set() 

    sorted_rma_events_user = sorted(returns, key=lambda r_event_user: parse_date_flexible(r_event_user.get('rma_date')) or date.min)

    for rma_event_data_user in sorted_rma_events_user:
        rma_date_obj_current_user = parse_date_flexible(rma_event_data_user.get('rma_date'))
        rma_number_current_user = rma_event_data_user.get('rma_number', 'N/A')
        print(f"DEBUG (Step 6 - RMA Event): Processing RMA {rma_number_current_user} dated {dt_to_str(rma_date_obj_current_user) if rma_date_obj_current_user else 'Invalid Date'}")
        if not rma_date_obj_current_user:
            continue 

        for rma_item_detail_user in rma_event_data_user.get('items', []): 
            returned_sn_from_rma_user = rma_item_detail_user.get('serial_number')
            print(f"DEBUG (Step 6 - RMA Item): Processing returned SN: {returned_sn_from_rma_user or 'N/A'} from RMA {rma_number_current_user}")
            if not returned_sn_from_rma_user:
                continue

            candidate_keys_for_returned_item_user = [
                key_cand_ret_user for key_cand_ret_user, instance_cand_ret_user in shipmentInstanceMap.items()
                if instance_cand_ret_user['serial'] == returned_sn_from_rma_user and
                   instance_cand_ret_user.get('originalShipmentDateObj') and
                   instance_cand_ret_user['originalShipmentDateObj'] <= rma_date_obj_current_user and
                   instance_cand_ret_user.get('currentStatus') == 'inField' # Must be inField to be considered for RMA
            ]

            if not candidate_keys_for_returned_item_user:
                print(f"DEBUG (Step 6 - RMA Item): No valid prior shipment instance found for SN {returned_sn_from_rma_user} (RMA {rma_number_current_user}). Skipping.")
                continue

            returned_item_instance_key_user = max(candidate_keys_for_returned_item_user, key=lambda k_ret_user: shipmentInstanceMap[k_ret_user]['originalShipmentDateObj'])
            returned_item_instance_data_user = shipmentInstanceMap[returned_item_instance_key_user]
            print(f"DEBUG (Step 6 - RMA Item): Identified instance for SN {returned_sn_from_rma_user} as {returned_item_instance_key_user}")

            # This check for 'currentStatus' != 'inField' (from user script) is covered by the candidate_keys query above.
            # But if it was already processed (e.g. status changed to 'returned_replaced'), it won't be 'inField'.
            if returned_item_instance_data_user.get('currentStatus') != 'inField':
                continue

            returned_item_instance_data_user['rmaDate'] = dt_to_str(rma_date_obj_current_user)
            returned_item_instance_data_user['rmaDateObj'] = rma_date_obj_current_user

            returned_item_cohort_id_user = returned_item_instance_data_user.get('cohort')
            cohort_for_this_return_user = None
            if returned_item_cohort_id_user:
                cohort_for_this_return_user = next((c_user for c_user in csa_cohorts if c_user['orderId'] == returned_item_cohort_id_user), None)
                print(f"DEBUG (Step 6 - RMA Item SN {returned_sn_from_rma_user}): Returned item belongs to Cohort {returned_item_cohort_id_user}. Found cohort data: {cohort_for_this_return_user is not None}")
            else:
                print(f"DEBUG (Step 6 - RMA Item SN {returned_sn_from_rma_user}): Returned item does not belong to any cohort.")

            can_replace_user = False
            # replacement_reason_user = "No Cohort" # Not used in Python, more for debugging

            if cohort_for_this_return_user:
                # Check if RMA date is within cohort's active period for replacement eligibility
                c_start_user = cohort_for_this_return_user.get('startDateObj')
                c_end_user = cohort_for_this_return_user.get('endDateObj')
                if not (c_start_user and c_end_user and c_start_user <= rma_date_obj_current_user <= c_end_user):
                    returned_item_instance_data_user['currentStatus'] = 'returned_outside_csa_period'
                    print(f"DEBUG (Step 6 - RMA Item SN {returned_sn_from_rma_user}): RMA date {dt_to_str(rma_date_obj_current_user)} is outside CSA period for Cohort {returned_item_cohort_id_user} ({dt_to_str(c_start_user)}-{dt_to_str(c_end_user)}). Status set to returned_outside_csa_period.")
                    continue # Not eligible for replacement under this cohort due to timing

                if cohort_for_this_return_user['remainingReplacements'] > 0:
                    can_replace_user = True
                    print(f"DEBUG (Step 6 - RMA Item SN {returned_sn_from_rma_user}): Cohort {returned_item_cohort_id_user} has {cohort_for_this_return_user['remainingReplacements']} replacements remaining. Eligible for replacement.")
                    # replacement_reason_user = "Replacement Available"
                else:
                    returned_item_instance_data_user['currentStatus'] = 'returned_no_replacement_available'
                    print(f"DEBUG (Step 6 - RMA Item SN {returned_sn_from_rma_user}): Cohort {returned_item_cohort_id_user} has no replacements remaining. Status set to returned_no_replacement_available.")
                    # replacement_reason_user = "No Replacements Left"
                    continue 
            else: # Not part of a CSA cohort that could offer replacement
                returned_item_instance_data_user['currentStatus'] = 'returned_no_cohort_assigned' # Or a more specific non-CSA return status
                continue

            replacement_instance_key_user = None
            # replacement_instance_index_user = -1 # Not used from user script

            if can_replace_user: # Only look for replacement if cohort rules allow
                temp_available_keys_for_search_user = list(available_instance_keys_deque_rma)
                for idx_user, cand_key_user in enumerate(temp_available_keys_for_search_user):
                    # cand_key should not be in shipmentInstanceMap (typo in user script), it IS a key OF shipmentInstanceMap
                    cand_instance_user = shipmentInstanceMap.get(cand_key_user)
                    if not cand_instance_user:
                        continue # Should not happen

                    # cand_instance.get('so_number') in csa_order_ids - this check is implicitly handled because
                    # available_instance_keys_deque_rma was populated with items where instance_avail_rma.get('cohort') is None
                    if (cand_instance_user['originalShipmentDateObj'] >= rma_date_obj_current_user and
                        cand_key_user != returned_item_instance_key_user and # Cannot replace itself
                        cand_key_user not in used_replacement_instance_keys_set_rma):

                        replacement_instance_key_user = cand_key_user
                        print(f"DEBUG (Step 6 - RMA Item SN {returned_sn_from_rma_user}): Found potential replacement SN {cand_instance_user.get('serial')} (Key: {cand_key_user}) shipped {dt_to_str(cand_instance_user['originalShipmentDateObj'])}")
                        # replacement_instance_index_user = idx_user # Not used
                        break

            if replacement_instance_key_user and cohort_for_this_return_user: # CSA Replacement Occurs
                replacement_instance_data_user = shipmentInstanceMap[replacement_instance_key_user]
                rep_ship_dt_user = replacement_instance_data_user['originalShipmentDateObj']

                cohort_for_this_return_user['remainingReplacements'] -= 1
                print(f"DEBUG (Step 6 - CSA Replacement): SN {returned_sn_from_rma_user} replaced by SN {replacement_instance_data_user.get('serial')} for Cohort {returned_item_cohort_id_user}. Remaining replacements: {cohort_for_this_return_user['remainingReplacements']}")

                returned_item_instance_data_user['currentStatus'] = 'returned_replaced'
                returned_item_instance_data_user['replacedBy'] = replacement_instance_key_user 
                returned_item_instance_data_user['replacementShipDate'] = dt_to_str(rep_ship_dt_user)
                returned_item_instance_data_user['replacementShipDateObj'] = rep_ship_dt_user

                replacement_instance_data_user['currentStatus'] = 'inField' # It is now in field representing the CSA slot
                replacement_instance_data_user['replacedScope'] = returned_item_instance_key_user 
                replacement_instance_data_user['cohort'] = returned_item_cohort_id_user # Replacement inherits cohort
                replacement_instance_data_user['isCSARelated'] = True # Now part of a CSA chain
                replacement_instance_data_user['isOrphan'] = False

                used_replacement_instance_keys_set_rma.add(replacement_instance_key_user)
                try:
                    available_instance_keys_deque_rma.remove(replacement_instance_key_user) 
                except ValueError: 
                    print(f"Warning (User Script Logic - RMA Deque): Key {replacement_instance_key_user} not found for removal.", file=sys.stderr)

            elif can_replace_user and cohort_for_this_return_user: # Replacement was due, but none found
                returned_item_instance_data_user['currentStatus'] = 'returned_no_replacement_found'
                cohort_for_this_return_user['remainingReplacements'] -= 1 # Allowance still consumed
                print(f"DEBUG (Step 6 - No Replacement Found): SN {returned_sn_from_rma_user} (Cohort {returned_item_cohort_id_user}) was eligible, but no replacement found. Status: returned_no_replacement_found. Replacements consumed, remaining: {cohort_for_this_return_user['remainingReplacements']}")
            # Else (not can_replace_user): status was already set prior (e.g. no_replacement_available, outside_csa_period, no_cohort)

    print("User Script Logic: Finished processing RMAs and linking replacements.")
    # --- End of User's Script Integration ---

    # --- Step 7: New: Transform data for final output structure (for API response) ---
    print("Step 7: Transforming data for final API output structure...")
    csa_cohorts_final = defaultdict(lambda: {
        'summary': {}, 
        'validated_chains': [], 
        'assigned_orphan_chains_data': [], 
        'replacements_used': 0 
    })

    all_instance_keys_in_validated_chains = set()

    for cohort_summary_data_final in csa_cohorts: 
        cohort_id_final = cohort_summary_data_final['orderId']
        print(f"DEBUG (Step 7 - Validated Chains): Processing cohort {cohort_id_final} for validated chain building.")
        csa_cohorts_final[cohort_id_final]['summary'] = cohort_summary_data_final
        csa_cohorts_final[cohort_id_final]['summary']['averageCSAScopePrice'] = average_csa_item_price

        actual_replacements_counted_for_this_cohort = 0

        for scope_starter_key_final in cohort_summary_data_final.get('csaScopeInstanceKeys', []):
            starter_instance_details_final = shipmentInstanceMap.get(scope_starter_key_final, {})
            if starter_instance_details_final.get('replacedScope') is not None:
                all_instance_keys_in_validated_chains.add(scope_starter_key_final) 
                continue

            if scope_starter_key_final in all_instance_keys_in_validated_chains:
                continue

            current_chain_of_keys_final = []
            current_chain_handoff_descriptions_final = []
            iter_key_for_chain_build_final = scope_starter_key_final

            while iter_key_for_chain_build_final:
                current_chain_of_keys_final.append(iter_key_for_chain_build_final)
                all_instance_keys_in_validated_chains.add(iter_key_for_chain_build_final) 

                iter_instance_data_final = shipmentInstanceMap.get(iter_key_for_chain_build_final)
                if not iter_instance_data_final:
                    break 

                next_key_in_chain_final = iter_instance_data_final.get('replacedBy') 

                if next_key_in_chain_final:
                    actual_replacements_counted_for_this_cohort += 1 
                    returned_sn_desc_final = iter_instance_data_final.get('serial', 'N/A')
                    rma_date_desc_final = iter_instance_data_final.get('rmaDate', 'N/A') 
                    replacement_inst_data_desc_final = shipmentInstanceMap.get(next_key_in_chain_final)
                    replacement_sn_desc_final = replacement_inst_data_desc_final.get('serial', 'N/A') if replacement_inst_data_desc_final else 'N/A'
                    replacement_ship_date_desc_final = iter_instance_data_final.get('replacementShipDate', 'N/A')

                    current_chain_handoff_descriptions_final.append(
                        f"Returned {returned_sn_desc_final} on {rma_date_desc_final}, "
                        f"replaced by {replacement_sn_desc_final} shipped {replacement_ship_date_desc_final}"
                    )
                iter_key_for_chain_build_final = next_key_in_chain_final 

            if current_chain_of_keys_final: 
                final_key_of_this_chain_final = current_chain_of_keys_final[-1]
                final_instance_data_of_this_chain_final = shipmentInstanceMap.get(final_key_of_this_chain_final, {})
                final_status_desc_final = get_status_description(final_instance_data_of_this_chain_final.get('currentStatus', 'Unknown'))

                csa_cohorts_final[cohort_id_final]['validated_chains'].append({
                    "chain": current_chain_of_keys_final, 
                    "handoffs": current_chain_handoff_descriptions_final,
                    "final_status": final_status_desc_final,
                    "final_serial_number": final_instance_data_of_this_chain_final.get('serial', 'N/A'),
                    "starter_serial": shipmentInstanceMap.get(current_chain_of_keys_final[0], {}).get('serial', 'N/A'),
                    "starter_instance_key": current_chain_of_keys_final[0] 
                })
                print(f"DEBUG (Step 7 - Validated Chains): Added chain for cohort {cohort_id_final}. Starter SN: {shipmentInstanceMap.get(current_chain_of_keys_final[0], {}).get('serial', 'N/A')}, Final SN: {final_instance_data_of_this_chain_final.get('serial', 'N/A')}, Links: {len(current_chain_handoff_descriptions_final)}")
        csa_cohorts_final[cohort_id_final]['replacements_used'] = actual_replacements_counted_for_this_cohort

    # --- Step 8: Adapted Orphan Processing ---
    print("Step 8: Identifying and Processing Orphan Instances with adapted logic...")

    orphan_instance_keys_for_speculative_processing_final = {
        key_orphan_check_final for key_orphan_check_final, instance_orphan_check_final in shipmentInstanceMap.items()
        if instance_orphan_check_final.get('cohort') is None
    }
    print(f"DEBUG (Step 8 - Orphan Processing): Found {len(orphan_instance_keys_for_speculative_processing_final)} instance keys for speculative orphan chain building.")

    csa_order_ids_for_spec_build_final = {cohort_spec_final['orderId'] for cohort_spec_final in csa_cohorts}

    speculative_orphan_chains_built_list_final = build_speculative_orphan_chains(
        orphan_instance_keys_for_speculative_processing_final, shipmentInstanceMap, 
        SPECULATIVE_REPLACEMENT_WINDOW_DAYS, csa_order_ids_for_spec_build_final
    )
    print(f"DEBUG (Step 8 - Orphan Processing): Built {len(speculative_orphan_chains_built_list_final)} speculative orphan chains.")

    assigned_orphan_chains_list_final = associate_orphans_to_cohorts(
        speculative_orphan_chains_built_list_final, shipmentInstanceMap, csa_cohorts 
    )
    print(f"DEBUG (Step 8 - Orphan Processing): After attempting to associate orphans, {len(assigned_orphan_chains_list_final)} chains processed (includes assigned and unassignable).")

    unassigned_infield_orphans_list_final = []
    for orphan_chain_data_item_final in assigned_orphan_chains_list_final:
        assigned_cohort_id_for_orphan_final = orphan_chain_data_item_final.get('assigned_cohort')
        raw_final_status_orphan_final = orphan_chain_data_item_final.get('final_status', 'Unknown')
        orphan_chain_data_item_final['final_status'] = get_status_description(raw_final_status_orphan_final)

        if assigned_cohort_id_for_orphan_final and assigned_cohort_id_for_orphan_final in csa_cohorts_final:
            csa_cohorts_final[assigned_cohort_id_for_orphan_final]['assigned_orphan_chains_data'].append(orphan_chain_data_item_final)
            print(f"DEBUG (Step 8 - Orphan Assignment): Orphan chain starting with SN {orphan_chain_data_item_final.get('starter_serial')} assigned to Cohort {assigned_cohort_id_for_orphan_final}.")
        elif assigned_cohort_id_for_orphan_final in ["Pre-CSA / Unknown", "No Valid CSA Cohorts Found", "No CSA Cohorts Defined"] or \
             (isinstance(assigned_cohort_id_for_orphan_final, str) and assigned_cohort_id_for_orphan_final.startswith("Error:")):
            if orphan_chain_data_item_final['final_status'] == 'In Field':
                 unassigned_infield_orphans_list_final.append(orphan_chain_data_item_final)
                 print(f"DEBUG (Step 8 - Orphan Assignment): Orphan chain starting with SN {orphan_chain_data_item_final.get('starter_serial')} (Reason: {assigned_cohort_id_for_orphan_final}) added to unassigned 'In Field' list.")
        else: 
            print(f"Warning (Orphan Assignment): Orphan chain for starter SN {orphan_chain_data_item_final.get('starter_serial')} "
                  f"assigned to non-existent/unexpected cohort ID: {assigned_cohort_id_for_orphan_final}. Adding to unassigned list if in field.", file=sys.stderr)
            if orphan_chain_data_item_final['final_status'] == 'In Field': 
                 unassigned_infield_orphans_list_final.append(orphan_chain_data_item_final)
                 print(f"DEBUG (Step 8 - Orphan Assignment): Orphan chain starting with SN {orphan_chain_data_item_final.get('starter_serial')} (Unexpected Cohort ID: {assigned_cohort_id_for_orphan_final}) added to unassigned 'In Field' list.")


    print("Calculating Final Performance Metrics...")
    performance_metrics = calculate_performance_metrics(csa_cohorts_final, shipmentInstanceMap)
    print("Getting In-Field Serials...")
    in_field_serials = get_in_field_serials(csa_cohorts_final)

    final_output = {
        "customer_name": customer_name,
        "csa_cohorts_final": dict(csa_cohorts_final),
        "performance_metrics": performance_metrics,
        "in_field_serials": in_field_serials,
        "unassigned_orphans": unassigned_infield_orphans_list_final,
        # "shipmentInstanceMap": dict(shipmentInstanceMap), # Potentially too large for direct return
        "processing_timestamp": datetime.utcnow().isoformat() + "Z"
    }
    print("process_sales_data_logic finished.")
    return final_output

