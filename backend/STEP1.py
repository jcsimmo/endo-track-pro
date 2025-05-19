# New Oasis Orders and Returns Debug Script
import os
import json
import requests
import sys
from datetime import datetime, timedelta
from pprint import pprint
from io import StringIO
import argparse # Add argparse

# CONFIGURATION
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config_inventory.json')

def load_config():
    """Loads configuration from the JSON file."""
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
            raise Exception(f"Failed to refresh token. Response: {tokens}")
        config['access_token'] = tokens['access_token']
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        print("Access token refreshed successfully.")
        return config['access_token']
    except requests.exceptions.RequestException as e:
        print(f"Error refreshing access token: {e}")
        if response is not None:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        raise

def zoho_get(url, config, params=None, max_retries=5, backoff_factor=2):
    """Makes a GET request to the Zoho API, handling token refresh and 429 rate limits."""
    import time
    headers = get_headers(config)
    retries = 0
    while retries <= max_retries:
        try:
            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 401:
                print("Token expired, refreshing...")
                refresh_access_token(config)
                headers = get_headers(config) # Get updated headers
                response = requests.get(url, headers=headers, params=params) # Retry request

            if response.status_code == 429:
                wait_time = backoff_factor ** retries
                print(f"Rate limit hit (429). Waiting {wait_time} seconds before retrying (attempt {retries+1}/{max_retries})...")
                time.sleep(wait_time)
                retries += 1
                continue

            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error during Zoho API GET request to {url}: {e}")
            if 'response' in locals() and response is not None:
                print(f"Response status: {response.status_code}")
                print(f"Response body: {response.text}")
            if isinstance(e, requests.exceptions.HTTPError) and getattr(e.response, 'status_code', None) == 429:
                # Already handled above, but just in case
                wait_time = backoff_factor ** retries
                print(f"Rate limit hit (429) in exception. Waiting {wait_time} seconds before retrying (attempt {retries+1}/{max_retries})...")
                time.sleep(wait_time)
                retries += 1
                continue
            raise # Re-raise the exception to halt execution if needed
    print(f"FATAL: Exceeded maximum retries ({max_retries}) for {url}. Skipping this request.")
    return {}  # Return empty dict to allow script to continue

# Removed fetch_customer_by_name as it's no longer needed when using IDs directly.

def fetch_salesorders_for_customer(config, customer_id):
    """Fetch all sales orders for a customer using server-side filtering."""
    print(f"Fetching sales orders for customer ID: {customer_id}...")
    url = "https://www.zohoapis.com/inventory/v1/salesorders"
    params = {'customer_id': customer_id}
    all_salesorders = []
    page = 1
    has_more_pages = True

    while has_more_pages:
        params['page'] = page
        data = zoho_get(url, config, params)
        salesorders = data.get('salesorders', [])
        all_salesorders.extend(salesorders)
        has_more_pages = data.get('page_context', {}).get('has_more_page', False)
        page += 1
        print(f"  Fetched page {page-1}, total SOs so far: {len(all_salesorders)}")

    return all_salesorders

def fetch_package_detail(config, package_id):
    """Fetch detailed information for a specific package."""
    print(f"Fetching details for Package ID: {package_id}...")
    url = f"https://www.zohoapis.com/inventory/v1/packages/{package_id}"
    return zoho_get(url, config).get('package', {})

def fetch_salesreturns_for_customer(config, customer_id):
    """Fetch all sales returns for a customer using server-side filtering."""
    print(f"Fetching sales returns for customer ID: {customer_id}...")
    url = "https://www.zohoapis.com/inventory/v1/salesreturns"
    params = {'customer_id': customer_id}
    all_salesreturns = []
    page = 1
    has_more_pages = True

    while has_more_pages:
        params['page'] = page
        data = zoho_get(url, config, params)
        salesreturns = data.get('salesreturns', [])
        all_salesreturns.extend(salesreturns)
        has_more_pages = data.get('page_context', {}).get('has_more_page', False)
        page += 1
        print(f"  Fetched page {page-1}, total RMAs so far: {len(all_salesreturns)}")

    return all_salesreturns

def fetch_salesreturn_detail(config, salesreturn_id):
    """Fetch detailed information for a specific sales return."""
    print(f"Fetching details for Sales Return ID: {salesreturn_id}...")
    url = f"https://www.zohoapis.com/inventory/v1/salesreturns/{salesreturn_id}"
    return zoho_get(url, config).get('salesreturn', {})

def run_step1(contact_ids, output_json_path):
    """
    Fetches sales orders and returns for a list of contact IDs,
    aggregates them, and saves the results to JSON.
    Loads configuration internally.
    Logging/stdout capture is handled by the calling script.
    """
    # Output capture is now handled by the calling script (process_clinics_alt.py)

    all_salesorders_data = []
    all_salesreturns_data = []
    detailed_salesorders = []
    detailed_salesreturns = []

    try:
        # Load configuration internally
        config = load_config()
        print("Configuration loaded within run_step1.")

        print(f"Starting Step 1 processing for contact IDs: {', '.join(contact_ids)}")

        for customer_id in contact_ids:
            print(f"\n--- Processing Contact ID: {customer_id} ---")

            # PART 1: Get all sales orders for the current customer_id
            print("\n" + "="*40 + f" Sales Orders for {customer_id} " + "="*40)
            current_salesorders = fetch_salesorders_for_customer(config, customer_id)
            print(f"Found {len(current_salesorders)} sales orders for {customer_id}")
            all_salesorders_data.extend(current_salesorders)

            # Fetch detailed data for each sales order for JSON output
            for so in current_salesorders: # Process only the current customer's orders here for details
                so_id = so.get('salesorder_id')
                so_number = so.get('salesorder_number')
                so_date = so.get('date')
                so_status = so.get('status')
                print(f"\n--- Sales Order: {so_number} (ID: {so_id}, Date: {so_date}, Status: {so_status}) ---")

                # Fetch detailed sales order info to get line items, packages, and shipment date
                print(f"  Fetching details for SO ID: {so_id}...")
                so_detail_data = zoho_get(
                    f"https://www.zohoapis.com/inventory/v1/salesorders/{so_id}",
                    config,
                    {'organization_id': config['organization_id']}
                )
                so_detail = so_detail_data.get('salesorder', {})
                detailed_salesorders.append(so_detail) # Collect detailed data

                if not so_detail:
                    print("  Failed to fetch sales order details.")
                    # Print basic info even if details fail
                    continue

                # Extract shipment_date directly from sales order detail AFTER fetching
                shipment_date_so = so_detail.get('shipment_date', 'N/A')
                print(f"  Sales Order Shipment Date: {shipment_date_so}") # Print shipment date after fetching details

                # Display line items from the detailed sales order
                line_items = so_detail.get('line_items', [])
                print(f"  Line Items ({len(line_items)}):")
                for item in line_items:
                    item_name = item.get('name', 'N/A')
                    item_sku = item.get('sku', 'N/A')
                    item_qty = item.get('quantity', 0)
                    print(f"    - {item_name} (SKU: {item_sku}, Qty: {item_qty})")

                # Get packages from the detailed sales order
                packages = so_detail.get('packages', [])
                if packages:
                    print(f"  Packages ({len(packages)}):")
                    for i, pkg_from_so in enumerate(packages):
                        pkg_id = pkg_from_so.get('package_id')
                        pkg_number = pkg_from_so.get('package_number')
                        pkg_status = pkg_from_so.get('status')
                        shipment = pkg_from_so.get('shipment_order', {})
                        delivery_date = shipment.get('delivery_date', 'N/A')
                        tracking_number = shipment.get('tracking_number', 'N/A')

                        print(f"\n    Package: {pkg_number} (ID: {pkg_id}, Status: {pkg_status})")
                        print(f"      Delivery Date: {delivery_date}")
                        print(f"      Tracking Number: {tracking_number}")

                        if pkg_id:
                            # Fetch package details to get line items with serial numbers
                            print(f"      Fetching details for Package ID: {pkg_id}...")
                            pkg_detail_data = zoho_get(
                                f"https://www.zohoapis.com/inventory/v1/packages/{pkg_id}",
                                config,
                                {'organization_id': config['organization_id']}
                            )

                            # Check if line_items are directly in the response or nested under 'package'
                            pkg_line_items = None
                            if 'line_items' in pkg_detail_data:
                                pkg_line_items = pkg_detail_data['line_items']
                            elif 'package' in pkg_detail_data and 'line_items' in pkg_detail_data['package']:
                                pkg_line_items = pkg_detail_data['package']['line_items']

                            if pkg_line_items:
                                # Store detailed line items in the package object for JSON output
                                pkg_from_so['detailed_line_items'] = pkg_line_items

                                print(f"      Line Items in Package ({len(pkg_line_items)}):")
                                for line in pkg_line_items:
                                    line_name = line.get('name', 'N/A')
                                    line_sku = line.get('sku', 'N/A')
                                    line_qty = line.get('quantity', 0)
                                    line_serials = line.get('serial_numbers', [])
                                    # Check if this is an endoscope item
                                    is_endoscope = "endoscope" in line_name.lower() or "scope" in line_name.lower()

                                    print(f"        - {line_name} (SKU: {line_sku}, Qty: {line_qty})") # Corrected SKU reference
                                    if line_serials:
                                        print(f"          Serial Numbers: {', '.join(line_serials)}")
                                    elif is_endoscope:
                                        print(f"          No serial numbers recorded for this endoscope")
                                        # print(f"          Serial Numbers: {', '.join(line_serials)}") # Redundant print removed
                            else:
                                print("      No line items found in package details.")
                        else:
                            print("      Package ID not available, cannot fetch details.")
                else:
                    print("  No packages found for this sales order.")

            # PART 2: Get all sales returns (RMAs) for the current customer_id
            print("\n" + "="*40 + f" Sales Returns (RMAs) for {customer_id} " + "="*40)
            current_salesreturns = fetch_salesreturns_for_customer(config, customer_id)
            print(f"Found {len(current_salesreturns)} sales returns for {customer_id}")
            all_salesreturns_data.extend(current_salesreturns)

            # Fetch detailed data for each sales return for JSON output
            for rma in current_salesreturns: # Process only the current customer's returns here for details
                rma_id = rma.get('salesreturn_id')
                rma_number = rma.get('salesreturn_number')
                rma_date = rma.get('date')
                rma_status = rma.get('status')
                rma_receive_status = rma.get('receive_status', 'N/A') # Check if this field exists in list view
                rma_so_number = rma.get('salesorder_number', 'N/A')

                print(f"\n--- RMA: {rma_number} (ID: {rma_id}, Date: {rma_date}, Status: {rma_status}) ---")
                print(f"  Associated Sales Order: {rma_so_number}")
                # print(f"  Receive Status: {rma_receive_status}") # May need detail view

                # Fetch detailed RMA info to get line items, receive status, and salesreturnreceives
                print(f"  Fetching details for RMA ID: {rma_id}...")
                rma_detail_data = zoho_get(
                    f"https://www.zohoapis.com/inventory/v1/salesreturns/{rma_id}",
                    config,
                    {'organization_id': config['organization_id']}
                )
                rma_detail = rma_detail_data.get('salesreturn', {})
                detailed_salesreturns.append(rma_detail) # Collect detailed data

                if not rma_detail:
                    print("  Failed to fetch sales return details.")
                    continue

                line_items = rma_detail.get('line_items', [])
                detailed_receive_status = rma_detail.get('receive_status', 'N/A')
                print(f"  Receive Status (Detail): {detailed_receive_status}")

                # Display line items - include all endoscope items regardless of serial numbers
                print(f"  Line Items ({len(line_items)}):")
                for item in line_items:
                    item_name = item.get('name', 'N/A')
                    item_sku = item.get('sku', 'N/A')
                    item_qty = item.get('quantity', 0)
                    item_serials = item.get('serial_numbers', [])

                    # Check if this is an endoscope item
                    is_endoscope = "endoscope" in item_name.lower() or "scope" in item_name.lower()

                    print(f"    - {item_name} (SKU: {item_sku}, Qty: {item_qty})")
                    if item_serials:
                        print(f"      Serial Numbers: {', '.join(item_serials)}")
                    elif is_endoscope:
                        print(f"      No serial numbers recorded for this endoscope")

                # Display salesreturnreceives information (return receipts)
                salesreturnreceives = rma_detail.get('salesreturnreceives', [])
                if salesreturnreceives:
                    print(f"  Return Receipts ({len(salesreturnreceives)}):")
                    for receive in salesreturnreceives:
                        receive_id = receive.get('receive_id')
                        receive_number = receive.get('receive_number')
                        receive_date = receive.get('date')
                        receive_notes = receive.get('notes', 'N/A')

                        print(f"    Receipt: {receive_number} (ID: {receive_id}, Date: {receive_date})")
                        if receive_notes != 'N/A':
                            print(f"      Notes: {receive_notes}")

                        # Display line items in the receipt
                        receive_items = receive.get('line_items', [])
                        if receive_items:
                            print(f"      Items Received ({len(receive_items)}):")
                            for item in receive_items:
                                item_name = item.get('name', 'N/A')
                                item_qty = item.get('quantity', 0)
                                item_serials = item.get('serial_numbers', [])

                                # Check if this is an endoscope item
                                is_endoscope = "endoscope" in item_name.lower() or "scope" in item_name.lower()

                                print(f"        - {item_name} (Qty: {item_qty})")
                                if item_serials:
                                    print(f"          Serial Numbers: {', '.join(item_serials)}")
                                elif is_endoscope:
                                    print(f"          No serial numbers recorded for this endoscope")
                else:
                    print("  No return receipts found for this RMA.")


        # --- Aggregation and Saving (after loop for contact_ids) ---
        print(f"\n--- Aggregation Summary ---")
        print(f"Total sales orders fetched across all IDs: {len(all_salesorders_data)}")
        print(f"Total sales returns fetched across all IDs: {len(all_salesreturns_data)}")
        print(f"Total detailed sales orders processed: {len(detailed_salesorders)}")
        print(f"Total detailed sales returns processed: {len(detailed_salesreturns)}")

        # Save aggregated detailed data to JSON file
        output_data = {
            "contact_ids_processed": contact_ids,
            "salesorders": detailed_salesorders, # Contains details fetched inside the loop
            "salesreturns": detailed_salesreturns # Contains details fetched inside the loop
        }
        with open(output_json_path, 'w') as f:
            json.dump(output_data, f, indent=4)
        print(f"\nAggregated data saved to {output_json_path}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        import traceback
        traceback.print_exc()
    # finally block removed as stdout redirection is handled externally

if __name__ == "__main__":
   # This part is primarily for testing STEP1.py directly.
   # The orchestrator script will import and call run_step1 directly.
   parser = argparse.ArgumentParser(description="Fetch Zoho Inventory data for specific contact IDs.")
   parser.add_argument('--contact-ids', required=True, nargs='+', help='List of Zoho contact IDs to process.')
   parser.add_argument('--output-json', required=True, help='Path to save the aggregated JSON data.')
   # --output-md argument removed as logging is handled externally

   args = parser.parse_args()

   try:
       # Config is now loaded inside run_step1
       # Call run_step1 without the md path
       run_step1(args.contact_ids, args.output_json)
   except Exception as e:
       print(f"An error occurred during script execution: {e}")
       import traceback
       traceback.print_exc()
       sys.exit(1)