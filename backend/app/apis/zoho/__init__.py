from fastapi import APIRouter, HTTPException, Depends
import requests
import time
import databutton as db
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

router = APIRouter()

# Fixed configuration values
API_DOMAIN = "https://www.zohoapis.com"
ORGANIZATION_ID = "792214781"

# Service endpoints
SERVICES = {
    "inventory": {
        "endpoint": "/inventory/v1"
    }
}

# Models for requests and responses
class ZohoTokenResponse(BaseModel):
    access_token: str
    api_domain: str
    token_type: str
    expires_in: int

class ZohoInventoryItem(BaseModel):
    item_id: str
    name: str
    description: Optional[str] = None
    sku: Optional[str] = None
    status: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    # Add more fields as needed based on actual Zoho response

class ZohoInventoryResponse(BaseModel):
    items: List[ZohoInventoryItem]
    page_context: Optional[Dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    message: str

# Make zoho_get function available for import
__all__ = ["zoho_get"]

# Helper function to refresh the access token
def refresh_zoho_token():
    """Refresh the Zoho access token using the refresh token"""
    client_id = db.secrets.get("ZOHO_CLIENT_ID")
    client_secret = db.secrets.get("ZOHO_CLIENT_SECRET")
    refresh_token = db.secrets.get("ZOHO_REFRESH_TOKEN")
    
    if not all([client_id, client_secret, refresh_token]):
        raise HTTPException(status_code=500, detail="Zoho credentials not configured")
    
    url = "https://accounts.zoho.com/oauth/v2/token"  # Fixed URL for token endpoint
    data = {  # Changed from params to data for POST request
        "refresh_token": refresh_token,
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token"
    }
    
    response = requests.post(url, data=data)  # Changed params to data
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, 
                            detail=f"Failed to refresh token: {response.text}")
    
    token_data = response.json()
    
    # Store the new access token in secrets
    db.secrets.put("ZOHO_ACCESS_TOKEN", token_data.get("access_token"))
    
    return token_data

# Dependency for getting a valid access token
def get_zoho_access_token():
    """Get a valid Zoho access token, refreshing if needed"""
    try:
        access_token = db.secrets.get("ZOHO_ACCESS_TOKEN")
        if not access_token:
            token_data = refresh_zoho_token()
            return token_data.get("access_token")
        return access_token
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting Zoho token: {str(e)}") from e

# Function to get headers for API requests (added for consistency with the original script)
def get_headers(access_token=None):
    """Generates authorization headers using Databutton secrets."""
    if access_token is None:
        access_token = get_zoho_access_token()
    return {
        'Authorization': f"Zoho-oauthtoken {access_token}",
        'X-com-zoho-inventory-organizationid': ORGANIZATION_ID
    }

# Consistent API request function (added to match the original script pattern)
def zoho_get(url, params=None):
    """Makes a GET request to the Zoho API, handling token refresh."""
    access_token = get_zoho_access_token()
    headers = get_headers(access_token)
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 401:
            print("Token expired, refreshing...")
            access_token = refresh_zoho_token().get("access_token")
            headers = get_headers(access_token)
            response = requests.get(url, headers=headers, params=params)
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error during Zoho API GET request to {url}: {e}")
        if hasattr(response, 'status_code') and hasattr(response, 'text'):
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
        raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

@router.get("/health", response_model=HealthResponse)
def check_zoho_health():
    """Check the health of the Zoho API connection"""
    try:
        # Just validate we can get a token
        get_zoho_access_token()
        return HealthResponse(
            status="ok",
            message="Zoho API connection is healthy"
        )
    except Exception as e:
        return HealthResponse(
            status="error",
            message=f"Zoho API connection error: {str(e)}"
        )

@router.get("/inventory/items", response_model=ZohoInventoryResponse)
def get_inventory_items():
    """Get inventory items from Zoho Inventory"""
    url = f"{API_DOMAIN}{SERVICES['inventory']['endpoint']}/items"
    
    # Using our zoho_get function to handle token refresh automatically
    data = zoho_get(url)
    
    return ZohoInventoryResponse(
        items=[ZohoInventoryItem(item_id=item.get("item_id"), 
                                name=item.get("name"),
                                description=item.get("description"),
                                sku=item.get("sku"),
                                status=item.get("status"),
                                custom_fields=item.get("custom_fields"))
               for item in data.get("items", [])],
        page_context=data.get("page_context")
    )

@router.get("/configure-prompt")
def configure_zoho_prompt():
    """Check which Zoho secrets are missing and provide instructions"""
    # List of required secrets
    secret_keys = [
        "ZOHO_CLIENT_ID",
        "ZOHO_CLIENT_SECRET",
        "ZOHO_REFRESH_TOKEN",
        "ZOHO_ACCESS_TOKEN"
    ]
    
    # Check which secrets are missing
    missing_secrets = []
    for key in secret_keys:
        try:
            value = db.secrets.get(key)
            if not value:
                missing_secrets.append(key)
        except Exception:
            missing_secrets.append(key)
    
    if not missing_secrets:
        return {"status": "ok", "message": "All Zoho secrets are configured."}
    
    return {
        "status": "missing_secrets",
        "missing_secrets": missing_secrets,
        "instructions": "Please add these secrets in the Databutton secrets management interface."
    }