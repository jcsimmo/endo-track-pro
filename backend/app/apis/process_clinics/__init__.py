from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
import json
import os
import sys
from io import StringIO

import process_clinics

router = APIRouter()

# In-memory task status tracking similar to zoho_data
tasks_status = {}

class ProcessClinicsResponse(BaseModel):
    task_id: str
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: Optional[int] = None
    error: Optional[str] = None
    output: Optional[str] = None
    json_key: Optional[str] = None


@router.get("/process-clinics", response_model=ProcessClinicsResponse)
def run_process_clinics(background_tasks: BackgroundTasks):
    """Run the process_clinics.main() function in a background task."""
    task_id = f"process_clinics_{int(time.time())}"
    background_tasks.add_task(_execute_process_clinics, task_id)
    return ProcessClinicsResponse(task_id=task_id, message="Clinic processing started")


def _execute_process_clinics(task_id: str):
    tasks_status[task_id] = {
        "status": "running",
        "progress": 0,
        "output": "",
        "json_key": None,
    }

    original_stdout = sys.stdout
    captured_output = StringIO()
    sys.stdout = captured_output

    try:
        process_clinics.main()
        output = captured_output.getvalue()
        aggregated_path = os.path.join(process_clinics.BASE_OUTPUT_DIR, "all_clinics_aggregated_csa_data.json")
        tasks_status[task_id] = {
            "status": "completed",
            "progress": 100,
            "output": output,
            "json_key": aggregated_path,
        }
    except Exception as e:
        import traceback
        error_msg = f"Error running process_clinics: {e}\n{traceback.format_exc()}"
        tasks_status[task_id] = {
            "status": "failed",
            "progress": 0,
            "output": captured_output.getvalue(),
            "error": error_msg,
        }
    finally:
        sys.stdout = original_stdout


@router.get("/task-status/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    """Return status information for a background task."""
    if task_id not in tasks_status:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    data = tasks_status[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        status=data.get("status", "unknown"),
        progress=data.get("progress"),
        error=data.get("error"),
        output=data.get("output"),
        json_key=data.get("json_key"),
    )


@router.get("/clinic-data/{json_key}")
def get_clinic_data(json_key: str):
    """Return aggregated clinic data from disk."""
    safe_name = os.path.basename(json_key)
    file_path = os.path.join(process_clinics.BASE_OUTPUT_DIR, safe_name)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"File {safe_name} not found")
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read {safe_name}: {e}")
