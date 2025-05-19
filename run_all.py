import subprocess
import os
import signal
import sys

# Get the absolute path of the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths to the run scripts
backend_script_path = os.path.join(script_dir, "backend", "run.sh")
frontend_script_path = os.path.join(script_dir, "frontend", "run.sh")

# Function to execute a script
def run_script(script_path, name):
    print(f"Starting {name} from {script_path}...")
    # Ensure the script is executable
    subprocess.run(["chmod", "+x", script_path], check=True)
    # Run the script in a new terminal window if possible, or as a background process
    # For macOS, using 'open -a Terminal' is a common way to open a new terminal
    # For Linux, 'gnome-terminal --' or 'xterm -e' might be used
    # For Windows, 'start cmd /k'
    # As a fallback, run as a subprocess without a new terminal window
    try:
        if sys.platform == "darwin": # macOS
            process = subprocess.Popen(["open", "-a", "Terminal", script_path], cwd=os.path.dirname(script_path))
        elif sys.platform.startswith("linux"): # Linux
            # Try gnome-terminal, then xterm as fallbacks
            try:
                process = subprocess.Popen(["gnome-terminal", "--", script_path], cwd=os.path.dirname(script_path))
            except FileNotFoundError:
                try:
                    process = subprocess.Popen(["xterm", "-e", script_path], cwd=os.path.dirname(script_path))
                except FileNotFoundError:
                    print(f"Could not find gnome-terminal or xterm. Running {name} in the background.")
                    process = subprocess.Popen([script_path], cwd=os.path.dirname(script_path), preexec_fn=os.setsid if sys.platform != "win32" else None)
        elif sys.platform == "win32": # Windows
            process = subprocess.Popen(["start", "cmd", "/k", script_path], shell=True, cwd=os.path.dirname(script_path))
        else: # Fallback for other OS
            print(f"Unsupported OS for opening new terminal. Running {name} in the background.")
            process = subprocess.Popen([script_path], cwd=os.path.dirname(script_path), preexec_fn=os.setsid if sys.platform != "win32" else None)
        print(f"{name} started with PID: {process.pid if hasattr(process, 'pid') else 'N/A (likely new terminal)'}")
        return process
    except Exception as e:
        print(f"Failed to start {name}: {e}")
        return None

processes = []

def cleanup_processes(signum, frame):
    print("\nShutting down all processes...")
    for p_info in processes:
        name = p_info["name"]
        process = p_info["process"]
        if process and hasattr(process, 'pid') and process.poll() is None: # Check if process is running
            print(f"Terminating {name} (PID: {process.pid})...")
            if sys.platform == "win32":
                subprocess.run(["taskkill", "/PID", str(process.pid), "/F", "/T"], check=False)
            else:
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM) # Send SIGTERM to the process group
                except ProcessLookupError:
                    print(f"{name} (PID: {process.pid}) already terminated.")
                except Exception as e:
                    print(f"Error terminating {name} (PID: {process.pid}): {e}. Attempting SIGKILL.")
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except Exception as e_kill:
                         print(f"Error sending SIGKILL to {name} (PID: {process.pid}): {e_kill}")
        elif process and not hasattr(process, 'pid'):
             print(f"{name} was likely started in a separate terminal. Please close it manually.")
    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, cleanup_processes) # Ctrl+C
signal.signal(signal.SIGTERM, cleanup_processes) # Termination signal

if __name__ == "__main__":
    backend_process = run_script(backend_script_path, "Backend")
    if backend_process:
        processes.append({"name": "Backend", "process": backend_process})

    frontend_process = run_script(frontend_script_path, "Frontend")
    if frontend_process:
        processes.append({"name": "Frontend", "process": frontend_process})

    print("\nBoth frontend and backend processes have been initiated.")
    print("Backend typically runs at: http://localhost:8000")
    print("Frontend typically runs at: http://localhost:5173 (or http://localhost:3000 if Vite default)")
    print("Press Ctrl+C to shut down all processes.")

    # Keep the main script alive to allow signal handling
    # This loop is primarily for non-new-terminal subprocesses to be managed
    try:
        while True:
            all_terminated = True
            for p_info in processes:
                process = p_info["process"]
                # Only monitor processes that were not opened in a new terminal window
                # and have a PID and are still running.
                if process and hasattr(process, 'pid') and process.poll() is None:
                    all_terminated = False
                    break
            if all_terminated and any(hasattr(p_info["process"], 'pid') for p_info in processes):
                print("All managed child processes have terminated.")
                break
            signal.pause() # Wait for a signal
    except KeyboardInterrupt:
        # cleanup_processes will be called by the signal handler
        pass
    finally:
        # Ensure cleanup is called if loop exits for other reasons
        if any(p_info["process"] and hasattr(p_info["process"], 'pid') and p_info["process"].poll() is None for p_info in processes):
            cleanup_processes(None, None)