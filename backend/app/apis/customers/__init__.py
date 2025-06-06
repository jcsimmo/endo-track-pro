from fastapi import APIRouter

router = APIRouter()

@router.get("")
async def list_customers():
    """
    Stub endpoint to prevent 404 errors from old frontend code.
    Returns empty list since we're now using aggregated clinic data.
    """
    return {"customers": []}

@router.options("")
async def options_customers():
    """
    Handle OPTIONS requests for CORS preflight
    """
    return {}