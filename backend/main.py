import os
import pathlib
import json
import dotenv
from fastapi import FastAPI, APIRouter, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager # Added for lifespan
import asyncio # Added for running synchronous code in async context
import traceback # Added for detailed exception logging

# Assuming process_clinics.py is in the same directory or accessible via PYTHONPATH
from process_clinics import get_aggregated_clinic_data, load_data_from_disk # Import the new function

print("DEBUG: backend/main.py top-level imports complete.")

dotenv.load_dotenv()
print("DEBUG: dotenv.load_dotenv() called.")

from databutton_app.mw.auth_mw import AuthConfig, get_authorized_user
print("DEBUG: AuthConfig and get_authorized_user imported.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("DEBUG: Entering lifespan context manager.")
    print("Attempting to load clinic data from disk on startup...")
    try:
        loop = asyncio.get_event_loop()
        # Run the synchronous load_data_from_disk in an executor
        disk_data = await loop.run_in_executor(None, load_data_from_disk)
        if disk_data:
            app.state.clinic_data = disk_data
            print("Successfully loaded clinic data from disk into app.state.")
        else:
            app.state.clinic_data = {}
            print("Failed to load complete data from disk (or no data found). Initializing empty. Use 'Sync Now' to fetch.")
    except Exception as e:
        print(f"CRITICAL ERROR during startup disk load: {e}")
        traceback.print_exc()
        app.state.clinic_data = {} # Ensure it's initialized empty on any error
        print("Error during disk load. Initializing empty. Use 'Sync Now' to fetch.")
    
    print(f"LIFESPAN_DEBUG: Before yield, app.state.clinic_data keys: {list(app.state.clinic_data.keys()) if app.state.clinic_data else 'Empty or None'}")
    print(f"LIFESPAN_DEBUG: Before yield, id(app): {id(app)}, id(app.state): {id(app.state)}")
    print("Server startup sequence complete.")
    yield
    print("DEBUG: Exiting lifespan context manager (after yield).")
    # Clean up resources if any on shutdown (not needed for this case)
    print("Shutting down application.") # Existing print


def get_router_config() -> dict:
    try:
        # Note: This file is not available to the agent
        cfg = json.loads(open("routers.json").read())
    except:
        return False
    return cfg


def is_auth_disabled(router_config: dict, name: str) -> bool:
    """Return True if authentication is disabled for the given router."""
    try:
        return router_config["routers"][name]["disableAuth"]
    except Exception:
        # Default to requiring auth when configuration is missing
        return False


def import_api_routers() -> APIRouter:
    """Create top level router including all user defined endpoints."""
    routes = APIRouter(prefix="/routes")

    router_config = get_router_config()

    src_path = pathlib.Path(__file__).parent

    # Import API routers from "src/app/apis/*/__init__.py"
    apis_path = src_path / "app" / "apis"

    api_names = [
        p.relative_to(apis_path).parent.as_posix()
        for p in apis_path.glob("*/__init__.py")
    ]

    api_module_prefix = "app.apis."

    for name in api_names:
        print(f"Importing API: {name}")
        try:
            api_module = __import__(api_module_prefix + name, fromlist=[name])
            api_router = getattr(api_module, "router", None)
            if isinstance(api_router, APIRouter):
                routes.include_router(
                    api_router,
                    prefix=f"/{name}",  # Remove trailing slash from prefix
                    dependencies=(
                        []
                        if is_auth_disabled(router_config, name)
                        else [Depends(get_authorized_user)]
                    ),
                )
        except Exception as e:
            print(e)
            continue

    print(routes.routes)

    return routes


def get_firebase_config() -> dict | None:
    extensions = os.environ.get("DATABUTTON_EXTENSIONS", "[]")
    extensions = json.loads(extensions)

    for ext in extensions:
        if ext["name"] == "firebase-auth":
            return ext["config"]["firebaseConfig"]

    return None


def create_app() -> FastAPI:
    print("DEBUG: create_app() called.")
    """Create the app. This is called by uvicorn with the factory option to construct the app object."""
    app = FastAPI(lifespan=lifespan) # Added lifespan manager
    print("DEBUG: FastAPI app instance created with lifespan manager.")
    app.include_router(import_api_routers())
    print("DEBUG: API routers included.")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5100",  # Base port
            "http://localhost:5101",
            "http://localhost:5102",
            "http://localhost:5103",
            "http://localhost:5104",
            "http://localhost:5174",  # Your current frontend port
            # Add other common development ports if needed, or the original 5173 if still used
            # "http://localhost:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    print("DEBUG: CORS middleware added.")

    for route in app.routes:
        if hasattr(route, "methods"):
            for method in route.methods:
                print(f"{method} {route.path}")

    firebase_config = get_firebase_config()

    if firebase_config is None:
        print("No firebase config found")
        app.state.auth_config = None
    else:
        print("Firebase config found")
        auth_config = {
            "jwks_url": "https://www.googleapis.com/service_accounts/v1/jwk/securetoken@system.gserviceaccount.com",
            "audience": firebase_config["projectId"],
            "header": "authorization",
        }

        app.state.auth_config = AuthConfig(**auth_config)
    print("DEBUG: Firebase auth config processed.")
    print("DEBUG: create_app() finished.")
    return app

print("DEBUG: backend/main.py script is being executed/imported (before create_app call).")
app = create_app()
print("DEBUG: backend/main.py: app instance created via create_app().")
