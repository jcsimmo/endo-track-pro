
import databutton as db
import json
import requests
import sys
from datetime import datetime
from collections import defaultdict
# from dateutil.relativedelta import relativedelta # Keep if CSA calculations are ever re-introduced

# ZOHO_API_BASE_URL remains the same
ZOHO_API_BASE_URL = "https://www.zohoapis.com/inventory/v1"

def get_zoho_config_from_secrets():
    """Loads Zoho configuration from Databutton secrets."""
    print("Loading Zoho configuration from Databutton secrets...")
    try:
        config = {
            "access_token": db.secrets.get("ZOHO_ACCESS_TOKEN"), 
            "refresh_token": db.secrets.get("ZOHO_REFRESH_TOKEN"),
            "client_id": db.secrets.get("ZOHO_CLIENT_ID"),
            "client_secret": db.secrets.get("ZOHO_CLIENT_SECRET"),
            "organization_id": db.secrets.get("ZOHO_ORGANIZATION_ID")
        }
        if not all([config["refresh_token"], config["client_id"], config["client_secret"], config["organization_id"]]):
            missing_keys = [k for k, v in config.items() if not v and k != "access_token"]
            print(f"ERROR: Missing critical Zoho secrets: {missing_keys}. Ensure all are set.", file=sys.stderr)
            return None
        print("Zoho configuration loaded successfully from secrets.")
        return config
    except Exception as e:
        print(f"ERROR: Failed to load Zoho configuration from secrets: {e}", file=sys.stderr)
        return None

def refresh_and_get_new_access_token(config):
    print("Attempting to refresh Zoho access token...")
    if not config or not config.get("refresh_token") or not config.get("client_id") or not config.get("client_secret"):
        print("ERROR: Missing credentials for token refresh.", file=sys.stderr)
        return None

    url = "https://accounts.zoho.com/oauth/v2/token"
    data = {
        "refresh_token": config["refresh_token"],
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "grant_type": "refresh_token"
    }
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        tokens = response.json()
        if "access_token" in tokens:
            new_access_token = tokens["access_token"]
            print("Access token refreshed successfully (for current session).")
            return new_access_token
        else:
            print(f"ERROR: Failed to refresh token. Response: {tokens}", file=sys.stderr)
            return None
    except requests.exceptions.RequestException as e:
        print(f"ERROR: RequestException during token refresh: {e}", file=sys.stderr)
        if hasattr(response, 'status_code'): print(f"Status: {response.status_code}, Body: {response.text}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"ERROR: Unexpected error during token refresh: {e}", file=sys.stderr)
        return None

def get_headers(current_access_token, organization_id):
    if not current_access_token or not organization_id:
        print("ERROR: Missing token/org_id for headers.", file=sys.stderr)
        return None
    return {
        "Authorization": f"Zoho-oauthtoken {current_access_token}",
        "X-com-zoho-organizationid": organization_id
    }

def zoho_get(url, config, current_access_token, params=None):
    headers = get_headers(current_access_token, config["organization_id"])
    if not headers:
        raise Exception("Failed to generate Zoho API headers.")

    updated_token_in_session = current_access_token
    try:
        response = requests.get(url, headers=headers, params=params or {})
        if response.status_code == 401:
            print("Token expired (401), refreshing...")
            new_token = refresh_and_get_new_access_token(config)
            if not new_token:
                raise Exception("Zoho token refresh failed critically after 401.")
            updated_token_in_session = new_token
            headers = get_headers(updated_token_in_session, config["organization_id"])
            if not headers: raise Exception("Failed to get headers after refresh.")
            response = requests.get(url, headers=headers, params=params or {})
        response.raise_for_status()
        return response.json(), updated_token_in_session
    except requests.exceptions.RequestException as e:
        err_msg = f"Error in Zoho GET to {url}: {e}"
        if hasattr(response, 'status_code'): err_msg += f" | Status: {response.status_code}, Body: {response.text}"
        print(err_msg, file=sys.stderr)
        raise

def parse_date_string(date_str, date_format='%Y-%m-%d'):
    if not date_str or date_str == 'N/A': return None
    try: return datetime.strptime(date_str, date_format)
    except ValueError: return None

def format_date_for_output(dt_obj):
    if dt_obj: return dt_obj.strftime('%Y-%m-%d')
    return None

def fetch_all_items(config, token):
    print("Fetching all items...")
    items_list, page, more_pages = [], 1, True
    url = f"{ZOHO_API_BASE_URL}/items"
    while more_pages:
        try:
            data, token = zoho_get(url, config, token, params={'page': page, 'per_page': 200})
            items_list.extend(data.get('items', []))
            more_pages = data.get('page_context', {}).get('has_more_page', False)
            page += 1
        except Exception as e:
            print(f"Error fetching items page {page}: {e}", file=sys.stderr); more_pages = False
    inv_items = [i for i in items_list if i.get('item_type') == 'inventory']
    print(f"Fetched {len(items_list)} total, {len(inv_items)} inventory items.")
    return inv_items, token

def fetch_in_stock_serials_for_item(config, token, item_id, sku, name):
    events, page, more_pages = [], 1, True
    url = f"{ZOHO_API_BASE_URL}/items/serialnumbers"
    exec_date = datetime.now().strftime('%Y-%m-%d')
    while more_pages:
        try:
            data, token = zoho_get(url, config, token, params={'item_id': item_id, 'page': page, 'per_page': 200})
            for sn_data in data.get('serial_numbers', []):
                if not sn_data.get('is_transacted_out', False) and (s_num := sn_data.get('serial_number_formatted') or sn_data.get('serialnumber')):
                    events.append({"event_type": "InStock", "event_date": exec_date, "serial_number": s_num,
                                   "details": {"item_id": item_id, "item_sku": sku, "item_name": name,
                                               "status": sn_data.get('status'), "warehouse_name": sn_data.get('warehouse_name')}})
            more_pages = data.get('page_context', {}).get('has_more_page', False); page += 1
        except Exception as e:
            print(f"Error fetching serials for item {item_id} page {page}: {e}", file=sys.stderr); more_pages = False
    return events, token

def fetch_all_sales_orders_detailed(config, token):
    print("Fetching sales orders...")
    sale_events, page, more_pages = [], 1, True
    url_list = f"{ZOHO_API_BASE_URL}/salesorders"
    while more_pages:
        try:
            so_list_data, token = zoho_get(url_list, config, token, params={'page': page, 'per_page': 200})
            for so_sum in so_list_data.get('salesorders', []):
                if not (so_id := so_sum.get('salesorder_id')): continue
                try:
                    so_detail_data, token = zoho_get(f"{ZOHO_API_BASE_URL}/salesorders/{so_id}", config, token)
                    if not (so_detail := so_detail_data.get('salesorder')): continue
                    so_num = so_detail.get('salesorder_number'); so_date = parse_date_string(so_detail.get('date'))
                    evt_date = parse_date_string(so_detail.get('shipment_date')) or so_date
                    cust_id = so_detail.get('customer_id'); cust_name = so_detail.get('customer_name')
                    for pkg_sum in so_detail.get('packages', []):
                        if not (pkg_id := pkg_sum.get('package_id')): continue
                        pkg_detail_data, token = zoho_get(f"{ZOHO_API_BASE_URL}/packages/{pkg_id}", config, token)
                        if not (pkg_detail := pkg_detail_data.get('package')): continue
                        pkg_num = pkg_detail.get('package_number'); 
                        pkg_ship_date = parse_date_string(pkg_detail.get('shipment_date'))
                        pkg_del_date = parse_date_string(pkg_detail.get('shipment_order', {}).get('delivery_date'))
                        for li in pkg_detail.get('line_items', []):
                            sku = li.get('sku'); name = li.get('name'); serials = li.get('serial_numbers', [])
                            if not serials and (inv_det := li.get('inventory_detail', {})):
                                if isinstance(inv_det, list) and inv_det: inv_det = inv_det[0]
                                if isinstance(inv_det, dict): serials = inv_det.get('serial_numbers', [])
                            for s_num in serials:
                                if not s_num: continue
                                sale_events.append({"event_type": "Sale", "event_date": format_date_for_output(pkg_ship_date or evt_date),
                                                    "serial_number": s_num, "details": {"sales_order_id": so_id, "sales_order_number": so_num,
                                                                                         "sales_order_date": format_date_for_output(so_date), "customer_id": cust_id,
                                                                                         "customer_name": cust_name, "item_sku": sku, "item_name": name, "package_id": pkg_id,
                                                                                         "package_number": pkg_num, "shipment_date": format_date_for_output(pkg_ship_date or parse_date_string(so_detail.get('shipment_date'))),
                                                                                         "delivery_date": format_date_for_output(pkg_del_date)}})
                except Exception as e_detail: print(f"Error processing SO detail {so_id}: {e_detail}", file=sys.stderr)
            more_pages = so_list_data.get('page_context', {}).get('has_more_page', False); page += 1
            if not so_list_data.get('salesorders', []) and page > 1 and not more_pages: break
        except Exception as e_list: print(f"Error fetching SO list page {page}: {e_list}", file=sys.stderr); more_pages = False
    print(f"Fetched {len(sale_events)} sale events.")
    return sale_events, token

def fetch_all_sales_returns_detailed(config, token):
    print("Fetching sales returns...")
    return_events, page, more_pages = [], 1, True
    url_list = f"{ZOHO_API_BASE_URL}/salesreturns"
    while more_pages:
        try:
            sr_list_data, token = zoho_get(url_list, config, token, params={'page': page, 'per_page': 200})
            for sr_sum in sr_list_data.get('salesreturns', []):
                if not (sr_id := sr_sum.get('salesreturn_id')): continue
                try:
                    sr_detail_data, token = zoho_get(f"{ZOHO_API_BASE_URL}/salesreturns/{sr_id}", config, token)
                    if not (sr_detail := sr_detail_data.get('salesreturn')): continue
                    rma_num = sr_detail.get('salesreturn_number'); cust_id = sr_detail.get('customer_id')
                    cust_name = sr_detail.get('customer_name'); link_so_id = sr_detail.get('salesorder_id'); link_so_num = sr_detail.get('salesorder_number')
                    for rec_info in sr_detail.get('salesreturnreceives', []):
                        rec_date = parse_date_string(rec_info.get('date')); rec_num = rec_info.get('receive_number')
                        for li in rec_info.get('line_items', []):
                            sku = li.get('sku'); name = li.get('name'); serials = li.get('serial_numbers', [])
                            for s_num in serials:
                                if not s_num: continue
                                return_events.append({"event_type": "Return", "event_date": format_date_for_output(rec_date), "serial_number": s_num,
                                                      "details": {"sales_return_id": rec_info.get('receive_id') or sr_id, "rma_number": rma_num,
                                                                  "receive_number": rec_num, "customer_id": cust_id, "customer_name": cust_name,
                                                                  "item_sku": sku, "item_name": name, "linked_sales_order_id": link_so_id,
                                                                  "linked_sales_order_number": link_so_num}})
                except Exception as e_detail: print(f"Error processing SR detail {sr_id}: {e_detail}", file=sys.stderr)
            more_pages = sr_list_data.get('page_context', {}).get('has_more_page', False); page += 1
            if not sr_list_data.get('salesreturns', []) and page > 1 and not more_pages: break
        except Exception as e_list: print(f"Error fetching SR list page {page}: {e_list}", file=sys.stderr); more_pages = False
    print(f"Fetched {len(return_events)} return events.")
    return return_events, token

def aggregate_and_sort_events(all_events_lists):
    print("Aggregating and sorting events...")
    serial_map = defaultdict(list)
    for events_list in all_events_lists:
        for event in events_list: # Corrected variable name here
            if (s_num := event.get("serial_number")): serial_map[s_num].append(event)
    for s_num, events in serial_map.items():
        serial_map[s_num] = sorted(events, key=lambda e: datetime.strptime(e['event_date'], '%Y-%m-%d') if e.get('event_date') else datetime.min)
    return dict(serial_map)

def generate_serial_history_data():
    print("Serial Number History Generation Started (Databutton Adapted).")
    config = get_zoho_config_from_secrets()
    if not config: return None
    token = refresh_and_get_new_access_token(config)
    if not token:
        print("CRITICAL: Failed initial token refresh. Trying fallback from secrets...")
        token = config.get("access_token") # Try direct token from secrets
        if not token: print("CRITICAL: No access token available. Aborting.", file=sys.stderr); return None
    
    all_events = []
    try:
        items, token = fetch_all_items(config, token)
        in_stock_events = []
        for item in items:
            if (item_id := item.get('item_id')):
                item_events, token = fetch_in_stock_serials_for_item(config, token, item_id, item.get('sku'), item.get('name'))
                in_stock_events.extend(item_events)
        all_events.append(in_stock_events); print(f"Total InStock events: {len(in_stock_events)}")
        
        sales_events, token = fetch_all_sales_orders_detailed(config, token)
        all_events.append(sales_events); print(f"Total Sale events: {len(sales_events)}")
        
        return_events, token = fetch_all_sales_returns_detailed(config, token)
        all_events.append(return_events); print(f"Total Return events: {len(return_events)}")
        
        final_history = aggregate_and_sort_events(all_events)
        print("Serial Number History Generation Completed Successfully.")
        return final_history
    except Exception as e:
        print(f"Critical error in generate_serial_history_data: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    print("Running zoho_data_extractor.py directly (for testing - requires Databutton context or mocks).")
    # result = generate_serial_history_data()
    # if result:
    #     with open("local_test_serial_history.json", "w") as f: json.dump(result, f, indent=4)
    #     print("Saved data to local_test_serial_history.json")
    # else: print("Failed to generate data.")
    pass
