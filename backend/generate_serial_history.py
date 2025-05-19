import os
import json
import requests
import sys
from datetime import datetime
from collections import defaultdict
from dateutil.relativedelta import relativedelta # For CSA calculations if needed later
import argparse

# CONFIGURATION
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'config_inventory.json')
ZOHO_API_BASE_URL = "https://www.zohoapis.com/inventory/v1"

def load_config():
    """Loads configuration from the JSON file."""
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: Configuration file not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def get_headers(config):
    """Generates authorization headers."""
    return {
        'Authorization': f"Zoho-oauthtoken {config['access_token']}",
        'X-com-zoho-organizationid': config['organization_id']
    }

def refresh_access_token(config):
    """Refreshes the Zoho OAuth access token."""
    print("Refreshing access token...")
    url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        'refresh_token': config['refresh_token'],
        'client_id': config['client_id'],
        'client_secret': config['client_secret'],
        'grant_type': 'refresh_token'
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        tokens = response.json()
        if 'access_token' not in tokens:
            print(f"Error: Failed to refresh token. Response: {tokens}", file=sys.stderr)
            # Attempt to provide more specific error messages from Zoho
            if "error" in tokens:
                print(f"Zoho Error: {tokens['error']}", file=sys.stderr)
            return None # Indicate failure
        config['access_token'] = tokens['access_token']
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        print("Access token refreshed successfully.")
        return config['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error refreshing access token: {e}", file=sys.stderr)
        if response is not None:
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text}", file=sys.stderr)
        return None # Indicate failure

def zoho_get(url, config, raw_data_accumulator, params=None):
    """Makes a GET request to the Zoho API, handling token refresh and storing raw response."""
    headers = get_headers(config)
    try:
        response = requests.get(url, headers=headers, params=params or {})
        if response.status_code == 401: # Unauthorized
            print("Token expired or invalid, attempting to refresh...")
            if not refresh_access_token(config):
                 print("Failed to refresh token. Cannot proceed with API call.", file=sys.stderr)
                 raise Exception("Zoho token refresh failed.") # Critical error
            headers = get_headers(config) # Get updated headers
            response = requests.get(url, headers=headers, params=params or {}) # Retry request

        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx) other than 401
        data = response.json()
        raw_data_accumulator.append({"url": url, "params": params, "response": data, "timestamp": datetime.now().isoformat()})
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error during Zoho API GET request to {url}: {e}", file=sys.stderr)
        if 'response' in locals() and response is not None:
            print(f"Response status: {response.status_code}", file=sys.stderr)
            print(f"Response body: {response.text}", file=sys.stderr)
        # Depending on the error, you might want to re-raise or handle differently
        # For now, re-raising to make it evident if something goes wrong during fetching
        raise

def parse_date_string(date_str, date_format='%Y-%m-%d'):
    """Safely parses a date string to a datetime object."""
    if not date_str or date_str == 'N/A':
        return None
    try:
        return datetime.strptime(date_str, date_format)
    except ValueError:
        print(f"Warning: Could not parse date string: {date_str} with format {date_format}")
        return None

def format_date_for_output(dt_obj):
    """Formats a datetime object to YYYY-MM-DD string, or returns None."""
    if dt_obj:
        return dt_obj.strftime('%Y-%m-%d')
    return None

# --- Phase 1: Data Extraction and Event Generation ---

def fetch_all_items(config, raw_data_accumulator):
    """Fetches all inventory items from Zoho Inventory."""
    print("Fetching all items...")
    all_items_list = []
    page = 1
    has_more_pages = True
    url = f"{ZOHO_API_BASE_URL}/items"

    while has_more_pages:
        params = {'page': page, 'per_page': 200} # Max per_page is 200
        try:
            data = zoho_get(url, config, raw_data_accumulator, params)
            items = data.get('items', [])
            all_items_list.extend(items)
            print(f"  Fetched page {page} of items, total items so far: {len(all_items_list)}")
            has_more_pages = data.get('page_context', {}).get('has_more_page', False)
            page += 1
        except Exception as e:
            print(f"  Error fetching page {page} of items: {e}")
            has_more_pages = False # Stop on error

    # Filter for inventory items
    inventory_items = [
        item for item in all_items_list
        if item.get('item_type') == 'inventory'
    ]
    print(f"Finished fetching items. Found {len(all_items_list)} total items, {len(inventory_items)} are inventory items.")
    return inventory_items

def fetch_in_stock_serials_for_item(config, item_id, item_sku, item_name, raw_data_accumulator):
    """Fetches in-stock serial numbers for a given item_id."""
    print(f"  Fetching in-stock serials for item ID: {item_id} (SKU: {item_sku}, Name: {item_name})...") # DEBUG: Added item_name
    in_stock_events = []
    page = 1
    has_more_pages = True
    url = f"{ZOHO_API_BASE_URL}/items/serialnumbers"
    script_execution_date = datetime.now().strftime('%Y-%m-%d') # As per plan

    while has_more_pages:
        params = {'item_id': item_id, 'page': page, 'per_page': 200} # Fetch all serials for the item
        try:
            data = zoho_get(url, config, raw_data_accumulator, params)
            serial_numbers_data = data.get('serial_numbers', [])

            for sn_data in serial_numbers_data:
                # DEBUG: Print details for each serial number record from API
                print(f"    DEBUG sn_data: {sn_data}")
                is_transacted_out = sn_data.get('is_transacted_out', False)
                print(f"    DEBUG is_transacted_out: {is_transacted_out}")
                
                # Try 'serial_number_formatted' first, then fallback to 'serialnumber'
                serial_to_use = sn_data.get('serial_number_formatted') or sn_data.get('serialnumber')
                print(f"    DEBUG serial_to_use (from 'serial_number_formatted' or 'serialnumber'): {serial_to_use}")

                if not is_transacted_out: # Corrected in-stock logic
                    if not serial_to_use:
                        print(f"    DEBUG: Skipped InStock event creation - serial_to_use is missing.")
                        continue

                    event = {
                        "event_type": "InStock",
                        "event_date": script_execution_date, # Using script execution date as planned
                        "serial_number": serial_to_use, # Use the resolved serial number
                        "details": {
                            "item_id": item_id,
                            "item_sku": item_sku,
                            "item_name": item_name,
                            "status": sn_data.get('status'),
                            "warehouse_name": sn_data.get('warehouse_name')
                            # Add other relevant fields from sn_data if needed
                        }
                    }
                    in_stock_events.append(event)
                    print(f"    DEBUG: Created InStock event for SN: {serial_to_use}")
                else:
                    print(f"    DEBUG: Skipped InStock event for SN: {serial_to_use} (is_transacted_out: {is_transacted_out})")

            print(f"    Fetched page {page} of serials for item {item_id}. Found {len(serial_numbers_data)} serials on page, {len(in_stock_events)} in-stock events so far for this item.")
            has_more_pages = data.get('page_context', {}).get('has_more_page', False)
            page += 1
        except Exception as e:
            print(f"    Error fetching page {page} of serial numbers for item ID {item_id}: {e}")
            has_more_pages = False # Stop for this item on error
    return in_stock_events

def fetch_all_sales_orders_detailed(config, raw_data_accumulator):
    """Fetches all sales orders and their details, generating 'Sale' events."""
    print("Fetching all sales orders...")
    sale_events = []
    page = 1
    has_more_pages = True
    url_so_list = f"{ZOHO_API_BASE_URL}/salesorders"

    while has_more_pages:
        params_list = {'page': page, 'per_page': 200}
        try:
            so_list_data = zoho_get(url_so_list, config, raw_data_accumulator, params_list)
            sales_orders_summary = so_list_data.get('salesorders', [])
            print(f"  Fetched page {page} of SO summaries, {len(sales_orders_summary)} orders on this page.")

            for so_summary in sales_orders_summary:
                so_id = so_summary.get('salesorder_id')
                if not so_id:
                    continue
                
                print(f"    Processing SO ID: {so_id} (Number: {so_summary.get('salesorder_number')})")
                try:
                    so_detail_data = zoho_get(f"{ZOHO_API_BASE_URL}/salesorders/{so_id}", config, raw_data_accumulator)
                    so_detail = so_detail_data.get('salesorder')
                    if not so_detail:
                        print(f"      Warning: Could not fetch details for SO ID: {so_id}")
                        continue

                    so_number = so_detail.get('salesorder_number')
                    so_date_obj = parse_date_string(so_detail.get('date'))
                    # Use shipment date as primary event date if available, else SO date
                    event_date_obj = parse_date_string(so_detail.get('shipment_date')) or so_date_obj
                    
                    customer_id = so_detail.get('customer_id')
                    customer_name = so_detail.get('customer_name')

                    # Simplified CSA check (can be expanded later if needed from process_all_sales_serial_numbers.py)
                    # For now, we focus on serials from packages. CSA details can be added to sale event if required.

                    for package_summary in so_detail.get('packages', []):
                        package_id = package_summary.get('package_id')
                        if not package_id:
                            continue
                        
                        # print(f"      Fetching package details for Package ID: {package_id}")
                        pkg_detail_data = zoho_get(f"{ZOHO_API_BASE_URL}/packages/{package_id}", config, raw_data_accumulator)
                        pkg_detail = pkg_detail_data.get('package')
                        if not pkg_detail:
                            print(f"        Warning: Could not fetch details for Package ID: {package_id}")
                            continue
                        
                        package_number = pkg_detail.get('package_number')
                        pkg_shipment_date_obj = parse_date_string(pkg_detail.get('shipment_date'))
                        pkg_delivery_date_obj = parse_date_string(pkg_detail.get('shipment_order', {}).get('delivery_date'))

                        for line_item in pkg_detail.get('line_items', []):
                            item_sku = line_item.get('sku')
                            item_name = line_item.get('name')
                            # product_type = get_product_type(item_name) # Placeholder if needed

                            serials = line_item.get('serial_numbers', [])
                            # Fallback for serials in inventory_detail (from process_all_sales_serial_numbers.py)
                            if not serials:
                                inventory_detail = line_item.get('inventory_detail', {})
                                if isinstance(inventory_detail, list) and inventory_detail:
                                     inventory_detail = inventory_detail[0]
                                if isinstance(inventory_detail, dict):
                                    serials = inventory_detail.get('serial_numbers', [])

                            for serial_number in serials:
                                if not serial_number: continue
                                sale_event = {
                                    "event_type": "Sale",
                                    "event_date": format_date_for_output(pkg_shipment_date_obj or event_date_obj), # Prioritize package shipment date
                                    "serial_number": serial_number,
                                    "details": {
                                        "sales_order_id": so_id,
                                        "sales_order_number": so_number,
                                        "sales_order_date": format_date_for_output(so_date_obj),
                                        "customer_id": customer_id,
                                        "customer_name": customer_name,
                                        "item_sku": item_sku,
                                        "item_name": item_name,
                                        # "product_type": product_type,
                                        "package_id": package_id,
                                        "package_number": package_number,
                                        "shipment_date": format_date_for_output(pkg_shipment_date_obj or parse_date_string(so_detail.get('shipment_date'))),
                                        "delivery_date": format_date_for_output(pkg_delivery_date_obj),
                                        # Add CSA details here if parsed
                                    }
                                }
                                sale_events.append(sale_event)
                                # print(f"          Added Sale event for SN: {serial_number}")
                except Exception as e_so_detail:
                    print(f"      Error processing detail for SO ID {so_id}: {e_so_detail}")
            
            has_more_pages = so_list_data.get('page_context', {}).get('has_more_page', False)
            page += 1
            if not sales_orders_summary and page > 1 and not has_more_pages : # Break if empty page and no more pages
                 print("  No more sales orders found in subsequent pages.")
                 break
        except Exception as e_so_list:
            print(f"  Error fetching page {page} of sales order summaries: {e_so_list}")
            has_more_pages = False # Stop on error
    
    print(f"Finished fetching sales orders. Generated {len(sale_events)} sale events.")
    return sale_events

def fetch_all_sales_returns_detailed(config, raw_data_accumulator):
    """Fetches all sales returns and their details, generating 'Return' events."""
    print("Fetching all sales returns...")
    return_events = []
    page = 1
    has_more_pages = True
    url_sr_list = f"{ZOHO_API_BASE_URL}/salesreturns"

    while has_more_pages:
        params_list = {'page': page, 'per_page': 200}
        try:
            sr_list_data = zoho_get(url_sr_list, config, raw_data_accumulator, params_list)
            sales_returns_summary = sr_list_data.get('salesreturns', [])
            print(f"  Fetched page {page} of SR summaries, {len(sales_returns_summary)} returns on this page.")

            for sr_summary in sales_returns_summary:
                sr_id = sr_summary.get('salesreturn_id')
                if not sr_id:
                    continue

                print(f"    Processing SR ID: {sr_id} (Number: {sr_summary.get('salesreturn_number')})")
                try:
                    sr_detail_data = zoho_get(f"{ZOHO_API_BASE_URL}/salesreturns/{sr_id}", config, raw_data_accumulator)
                    sr_detail = sr_detail_data.get('salesreturn')
                    if not sr_detail:
                        print(f"      Warning: Could not fetch details for SR ID: {sr_id}")
                        continue
                    
                    rma_number = sr_detail.get('salesreturn_number')
                    customer_id = sr_detail.get('customer_id')
                    customer_name = sr_detail.get('customer_name')
                    # Original SO ID if linked on the return
                    linked_sales_order_id = sr_detail.get('salesorder_id') 
                    linked_sales_order_number = sr_detail.get('salesorder_number')

                    for receive_info in sr_detail.get('salesreturnreceives', []):
                        # specific_receive_id_attempt = receive_info.get('receive_id') # Old debug logic, now integrated below
                        receive_date_obj = parse_date_string(receive_info.get('date'))
                        receive_number = receive_info.get('receive_number')

                        for line_item in receive_info.get('line_items', []):
                            item_sku = line_item.get('sku')
                            item_name = line_item.get('name')
                            
                            serials = line_item.get('serial_numbers', [])
                            for serial_number in serials:
                                if not serial_number: continue
                                return_event = {
                                    "event_type": "Return",
                                    "event_date": format_date_for_output(receive_date_obj),
                                    "serial_number": serial_number,
                                    "details": {
                                        "sales_return_id": receive_info.get('receive_id') or sr_id, # Use specific 'receive_id' or fallback
                                        "rma_number": rma_number,
                                        "receive_number": receive_number,
                                        "customer_id": customer_id,
                                        "customer_name": customer_name,
                                        "item_sku": item_sku,
                                        "item_name": item_name,
                                        "linked_sales_order_id": linked_sales_order_id,
                                        "linked_sales_order_number": linked_sales_order_number,
                                    }
                                }
                                return_events.append(return_event)
                                # print(f"          Added Return event for SN: {serial_number}")
                except Exception as e_sr_detail:
                    print(f"      Error processing detail for SR ID {sr_id}: {e_sr_detail}")

            has_more_pages = sr_list_data.get('page_context', {}).get('has_more_page', False)
            page += 1
            if not sales_returns_summary and page > 1 and not has_more_pages:
                 print("  No more sales returns found in subsequent pages.")
                 break
        except Exception as e_sr_list:
            print(f"  Error fetching page {page} of sales return summaries: {e_sr_list}")
            has_more_pages = False # Stop on error
            
    print(f"Finished fetching sales returns. Generated {len(return_events)} return events.")
    return return_events

# --- Phase 2: Data Aggregation and Structuring ---
def aggregate_and_sort_events(all_events_lists):
    """Aggregates all events by serial number and sorts them chronologically."""
    print("Aggregating and sorting events...")
    serial_history_map = defaultdict(list)

    for events_list in all_events_lists:
        for event in events_list:
            serial_number = event.get("serial_number")
            if serial_number:
                serial_history_map[serial_number].append(event)
    
    print(f"  Aggregated events for {len(serial_history_map)} unique serial numbers.")

    for serial_number, events in serial_history_map.items():
        # Sort by event_date. Handle None dates by treating them as very old (or very new, depending on desired sort for Nones)
        # For chronological, None dates should ideally be handled or logged.
        # Here, Nones will cause an error if not handled in strptime or if strptime returns None and it's not filtered.
        # Assuming event_date is always a string 'YYYY-MM-DD' or None.
        def sort_key(e):
            date_str = e.get('event_date')
            if date_str:
                try:
                    return datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    return datetime.min # Treat unparseable/None dates as oldest
            return datetime.min

        serial_history_map[serial_number] = sorted(events, key=sort_key)
    
    print("Finished sorting events for all serial numbers.")
    return dict(serial_history_map) # Convert back to regular dict for JSON output

# --- Phase 3: Output ---
def save_to_json(data, output_path):
    """Saves the final data to a JSON file."""
    print(f"Saving data to {output_path}...")
    try:
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=4)
        print("Data saved successfully.")
    except Exception as e:
        print(f"Error saving JSON to {output_path}: {e}")

def main():
    parser = argparse.ArgumentParser(description="Generate a chronological history for all serial numbers from Zoho Inventory.")
    parser.add_argument('--output-json', default='Programs/serial_number_history.json',
                        help='Path to save the aggregated JSON data (default: Programs/serial_number_history.json).')
    parser.add_argument('--raw-output-json', default='Programs/zoho_raw_output.json',
                        help='Path to save all raw JSON responses from Zoho API (default: Programs/zoho_raw_output.json).')
    args = parser.parse_args()

    output_json_path = args.output_json
    if not os.path.isabs(output_json_path):
        output_json_path = os.path.join(os.getcwd(), output_json_path)

    raw_output_json_path = args.raw_output_json
    if not os.path.isabs(raw_output_json_path):
        raw_output_json_path = os.path.join(os.getcwd(), raw_output_json_path)
    
    print(f"Serial Number History Generation Started. Output will be: {output_json_path}")
    print(f"Raw Zoho API output will be saved to: {raw_output_json_path}")

    raw_zoho_data_accumulator = [] # Initialize accumulator for raw data

    try:
        config = load_config()
        if not config.get("access_token"): # Initial check
            if not refresh_access_token(config):
                print("Exiting: Could not obtain valid access token.", file=sys.stderr)
                sys.exit(1)
        
        all_events_master_list = []

        # 1. Fetch In-Stock Serials
        print("\n--- Fetching In-Stock Serial Events ---")
        tracked_items = fetch_all_items(config, raw_zoho_data_accumulator)
        in_stock_serial_events = []
        for item in tracked_items:
            item_id = item.get('item_id')
            item_sku = item.get('sku')
            item_name = item.get('name')
            if item_id:
                in_stock_events_for_item = fetch_in_stock_serials_for_item(config, item_id, item_sku, item_name, raw_zoho_data_accumulator)
                in_stock_serial_events.extend(in_stock_events_for_item)
        all_events_master_list.append(in_stock_serial_events)
        print(f"Total InStock events generated: {len(in_stock_serial_events)}")

        # 2. Fetch Sales Events
        print("\n--- Fetching Sales Events ---")
        sale_events = fetch_all_sales_orders_detailed(config, raw_zoho_data_accumulator)
        all_events_master_list.append(sale_events)
        print(f"Total Sale events generated: {len(sale_events)}")

        # 3. Fetch Return Events
        print("\n--- Fetching Return Events ---")
        return_events = fetch_all_sales_returns_detailed(config, raw_zoho_data_accumulator)
        all_events_master_list.append(return_events)
        print(f"Total Return events generated: {len(return_events)}")

        # 4. Aggregate and Sort
        print("\n--- Aggregating and Sorting All Events ---")
        final_serial_history = aggregate_and_sort_events(all_events_master_list)

        # 5. Save to JSON
        save_to_json(final_serial_history, output_json_path)
        
        # 6. Save Raw Zoho Data
        print(f"\n--- Saving Raw Zoho API Responses to {raw_output_json_path} ---")
        save_to_json(raw_zoho_data_accumulator, raw_output_json_path)


        print("\nSerial Number History Generation Completed Successfully.")

    except Exception as e:
        print(f"\nAn critical error occurred in main execution: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()