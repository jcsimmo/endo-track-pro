from fastapi import APIRouter, Request, HTTPException
import logging
import traceback
import asyncio
import os
import json
from process_clinics import get_aggregated_clinic_data

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO) # Ensure basicConfig is called if not already configured globally

router = APIRouter()

@router.get("/aggregated-data") # Add leading slash back
async def get_aggregated_clinic_data_endpoint(request: Request):
    """
    Endpoint to retrieve aggregated clinic CSA data.
    This data is loaded into app.state.clinic_data on server startup.
    """
    logger.info("Endpoint /aggregated-data hit.")
    logger.info(f"ENDPOINT_DEBUG: id(request.app): {id(request.app)}, id(request.app.state): {id(request.app.state)}")
    try:
        if hasattr(request.app.state, "clinic_data"):
            clinic_data = request.app.state.clinic_data
            logger.info(f"Found clinic_data in app.state. Type: {type(clinic_data)}")
            logger.info(f"ENDPOINT_DEBUG: clinic_data is: {clinic_data}")
            logger.info(f"ENDPOINT_DEBUG: clinic_data keys: {list(clinic_data.keys()) if isinstance(clinic_data, dict) else 'Not a dict'}")
            if clinic_data: # Check if it's not None or empty
                logger.info(f"Data is present. Keys (sample): {list(clinic_data.keys())[:5] if isinstance(clinic_data, dict) else 'Not a dict or empty'}")
                return clinic_data
            else:
                logger.warning("clinic_data in app.state is None or empty.")
                raise HTTPException(status_code=503, detail="No clinic data available. Please click 'Sync Now' to load data from Zoho.")
        else:
            logger.warning("clinic_data attribute not found in app.state.")
            raise HTTPException(status_code=503, detail="Aggregated clinic data attribute not found. Server may be misconfigured or data loading failed.")
    except HTTPException as he:
        logger.error(f"HTTPException in /aggregated-data: {he.status_code} - {he.detail}")
        raise he # Re-raise HTTPException
    except Exception as e:
        logger.error(f"Unexpected error in /aggregated-data endpoint: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"An unexpected internal server error occurred: {str(e)}")

@router.get("/step2-analysis/{customer_name}")
async def get_step2_analysis(customer_name: str):
    """
    Endpoint to retrieve Step2 analysis data directly from the generated JSON files.
    This ensures we get the corrected bipartite matching results.
    """
    logger.info(f"Step2 analysis endpoint hit for customer: {customer_name}")
    
    try:
        # Convert customer name to file naming convention
        sanitized_name = customer_name.lower().replace(' ', '_').replace('-', '_')
        
        # Construct file path
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))  # Go up to backend/
        step2_file_path = os.path.join(base_dir, "clinic_output", sanitized_name, f"{sanitized_name}_step2_analysis.json")
        
        logger.info(f"Looking for Step2 file at: {step2_file_path}")
        
        if not os.path.exists(step2_file_path):
            logger.warning(f"Step2 analysis file not found: {step2_file_path}")
            raise HTTPException(status_code=404, detail=f"Step2 analysis not found for customer: {customer_name}")
        
        # Load and return the Step2 analysis data
        with open(step2_file_path, 'r') as f:
            step2_data = json.load(f)
        
        logger.info(f"Successfully loaded Step2 analysis for {customer_name}")
        logger.info(f"Step2 data keys: {list(step2_data.keys()) if isinstance(step2_data, dict) else 'Not a dict'}")
        
        return step2_data
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error loading Step2 analysis for {customer_name}: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to load Step2 analysis: {str(e)}")

@router.post("/sync-now")
async def sync_clinic_data_now(request: Request):
    """
    Endpoint to manually trigger clinic data sync.
    This will fetch fresh data from Zoho and update app.state.clinic_data.
    """
    logger.info("Manual sync endpoint /sync-now hit.")
    try:
        logger.info("Starting manual clinic data sync...")
        loop = asyncio.get_event_loop()
        clinic_data = await loop.run_in_executor(None, get_aggregated_clinic_data)
        request.app.state.clinic_data = clinic_data
        logger.info("Manual sync completed successfully.")
        return {
            "success": True,
            "message": "Clinic data sync completed successfully",
            "clinics_processed": len(clinic_data) if clinic_data else 0
        }
    except Exception as e:
        logger.error(f"Error during manual sync: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Manual sync failed: {str(e)}")