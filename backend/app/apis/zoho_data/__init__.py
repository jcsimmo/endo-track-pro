from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
import databutton as db
import json
import os
import sys
import time
import re
from io import StringIO
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

router = APIRouter()

# Models
class CustomerResponse(BaseModel):
    contact_id: str
    contact_name: str

class DataExtractionResponse(BaseModel):
    task_id: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # "running", "completed", "failed"
    progress: Optional[int] = None
    error: Optional[str] = None
    output: Optional[str] = None
    json_key: Optional[str] = None

class CustomerListResponse(BaseModel):
    customers: List[CustomerResponse]

# In-memory storage for task status
tasks_status = {}

# Helper function to sanitize storage key
def sanitize_storage_key(key: str) -> str:
    """Sanitize storage key to only allow alphanumeric and ._- symbols"""
    return re.sub(r'[^a-zA-Z0-9._-]', '', key)

@router.get("/customers", response_model=CustomerListResponse)
def list_customers():
    """List available customers from Zoho"""
    from app.apis.zoho import zoho_get
    
    try:
        url = "https://www.zohoapis.com/inventory/v1/contacts"
        data = zoho_get(url)
        contacts = data.get('contacts', [])
        
        return CustomerListResponse(
            customers=[CustomerResponse(
                contact_id=contact.get('contact_id'),
                contact_name=contact.get('contact_name')
            ) for contact in contacts]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch customers: {str(e)}")

@router.get("/run-extraction")
def run_data_extraction(background_tasks: BackgroundTasks, customer_name: str = Query("Oasis")):
    """Run the data extraction for a specific customer"""
    # Generate a unique task ID
    task_id = f"extraction_{int(time.time())}"
    
    # Store the script from storage
    script_text = db.storage.text.get(key='zoho_extraction_script')
    if not script_text:
        raise HTTPException(status_code=404, detail="Zoho extraction script not found in storage")
    
    # Update the script to use the customer_name parameter
    script_text = script_text.replace('customer_name = "Oasis"', f'customer_name = "{customer_name}"')
    
    # Update the script to store JSON in Databutton storage instead of local file
    script_text = script_text.replace(
        'json_output_filename = os.path.join(os.path.dirname(os.path.abspath(__file__)), "oasis_orders_returns.json")',
        'json_output_filename = "zoho_data.json"'
    )
    
    # Replace file writing with storage API
    script_text = script_text.replace(
        'with open(json_output_filename, \'w\') as f:\n            json.dump(output_data, f, indent=4)',
        'json_key = sanitize_storage_key(f"{customer_name.lower()}_data_{int(time.time())}")\n        db.storage.json.put(json_key, output_data)\n        print(f"\\nData saved to storage with key: {json_key}")'
    )
    
    # Start the task in the background
    background_tasks.add_task(execute_extraction, task_id, script_text, customer_name)
    
    return DataExtractionResponse(
        task_id=task_id,
        message=f"Data extraction started for customer {customer_name}"
    )

def execute_extraction(task_id: str, script_text: str, customer_name: str):
    """Execute the extraction script in the background"""
    # Initialize task status
    tasks_status[task_id] = {
        "status": "running",
        "progress": 0,
        "output": "",
        "json_key": None
    }
    
    # Capture stdout
    original_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output
    
    try:
        # Initialize locals to capture json_key
        local_vars = {}
        
        # Add the sanitize_storage_key function to the local variables
        local_vars['sanitize_storage_key'] = sanitize_storage_key
        local_vars['db'] = db
        
        # Execute the script
        exec(script_text, globals(), local_vars)
        
        # Capture the output
        output = captured_output.getvalue()
        
        # Attempt multiple ways to get the json_key
        json_key = None
        
        # Method 1: Check if json_key is in local_vars
        if 'json_key' in local_vars:
            json_key = local_vars['json_key']
            print(f"Got json_key from locals: {json_key}")
        
        # Method 2: Look for pattern in the output
        if not json_key:
            match = re.search(r"Data saved to storage with key: ([\w.-]+)", output)
            if match:
                json_key = match.group(1)
                print(f"Got json_key from output pattern: {json_key}")
        
        # Method 3: Construct a key based on customer name and time
        if not json_key:
            # Find any keys that match our naming pattern
            all_files = db.storage.json.list()
            customer_prefix = customer_name.lower()
            
            # Look for recently created files with the customer name
            for file in all_files:
                if file.name.startswith(customer_prefix):
                    json_key = file.name
                    print(f"Found json_key from storage list: {json_key}")
                    break
        
        # Method 4: Last resort - check for any new json files
        if not json_key:
            # Try to find the most recently created json file
            all_files = db.storage.json.list()
            if all_files:
                # Sort by name, assuming newer files have higher timestamps in the name
                sorted_files = sorted(all_files, key=lambda x: x.name, reverse=True)
                json_key = sorted_files[0].name
                print(f"Using most recent json file as fallback: {json_key}")
        
        # Update task status
        tasks_status[task_id] = {
            "status": "completed",
            "progress": 100,
            "output": output,
            "json_key": json_key
        }
        
        print(f"Task {task_id} completed with json_key: {json_key}")
        
    except Exception as e:
        import traceback
        error_msg = f"Error executing script: {str(e)}\n{traceback.format_exc()}"
        tasks_status[task_id] = {
            "status": "failed",
            "progress": 0,
            "output": captured_output.getvalue(),
            "error": error_msg
        }
        print(f"Task {task_id} failed: {error_msg}")
    finally:
        # Restore stdout
        sys.stdout = original_stdout

@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    """Get the status of a running task"""
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    
    task_data = tasks_status[task_id]
    
    return TaskStatusResponse(
        task_id=task_id,
        status=task_data.get("status", "unknown"),
        progress=task_data.get("progress"),
        error=task_data.get("error"),
        output=task_data.get("output"),
        json_key=task_data.get("json_key")
    )

@router.get("/download-json/{json_key}") # Add leading slash back
def download_json(json_key: str):
    """Download the generated JSON data"""
    try:
        if not json_key or json_key == "undefined":
            print(f"Invalid JSON key received: '{json_key}'")
            raise HTTPException(status_code=400, detail=f"Invalid JSON key: '{json_key}'")
            
        print(f"Attempting to retrieve JSON data with key: {json_key}")
        # Sanitize the key before using it
        safe_key = sanitize_storage_key(json_key)
        
        try:
            data = db.storage.json.get(safe_key)
            if not data:
                print(f"JSON data not found for key: {safe_key}")
                raise HTTPException(status_code=404, detail=f"JSON data with key {safe_key} not found")
            return data
        except FileNotFoundError:
            print(f"FileNotFoundError for key: {safe_key}")
            raise HTTPException(status_code=404, detail=f"JSON file with key {safe_key} not found")
    except Exception as e:
        error_msg = f"Error retrieving JSON data: {str(e)}"
        print(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)

# Utility function to sanitize storage keys - mirroring the one in the script
def sanitize_storage_key(key: str) -> str:
    """Sanitize storage key to only allow alphanumeric and ._- symbols"""
    return re.sub(r'[^a-zA-Z0-9._-]', '', key)
