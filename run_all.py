import subprocess
import os
import signal
import sys

# Get the absolute path of the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths to the run scripts
backend_script_path = os.path.join(script_dir, "backend", "run.sh")
frontend_script_path = os.path.join(script_dir, "frontend", "run.sh")

# Function to kill any process running on port 8123
def kill_port_8123():
    try:
        print("Checking for any existing processes on port 8123...")
        # Get process IDs using port 8123
        result = subprocess.run(
            ["lsof", "-ti:8123"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print(f"Found processes on port 8123: {pids}")
            
            # Kill the processes
            for pid in pids:
                if pid.strip():
                    try:
                        subprocess.run(["kill", "-9", pid.strip()], check=True)
                        print(f"Killed process {pid.strip()}")
                    except subprocess.CalledProcessError as e:
                        print(f"Failed to kill process {pid.strip()}: {e}")
        else:
            print("No processes found on port 8123")
    except FileNotFoundError:
        print("lsof command not found - skipping port cleanup")
    except Exception as e:
        print(f"Error during port cleanup: {e}")

# Function to execute a script
def run_script(script_path, name):
    print(f"Starting {name} from {script_path} (output will be in this terminal)...")
    # Ensure the script is executable
    subprocess.run(["chmod", "+x", script_path], check=True)
    try:
        # Run the script as a direct child process.
        # Its output (stdout/stderr) will be inherited by this script's terminal.
        process = subprocess.Popen(
            [script_path],
            cwd=os.path.dirname(script_path),
            # preexec_fn is used on POSIX to make the child its own process group leader.
            # This allows os.killpg to terminate the entire group later.
            preexec_fn=os.setsid if sys.platform != "win32" else None
        )
        print(f"{name} started with PID: {process.pid}")
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
        # All processes should now have a PID and be directly managed.
        if process and process.poll() is None: # Check if process is running
            print(f"Terminating {name} (PID: {process.pid})...")
            if sys.platform == "win32":
                # For Windows, Popen creates a new process group by default if shell=False (which it is here).
                # Terminating the parent should be enough, but taskkill /T attempts to kill child processes.
                subprocess.run(["taskkill", "/PID", str(process.pid), "/F", "/T"], check=False)
            else:
                try:
                    # os.setsid in Popen made the child a new session leader and process group leader.
                    # os.killpg will send the signal to all processes in that group.
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                except ProcessLookupError:
                    print(f"{name} (PID: {process.pid}) already terminated.")
                except Exception as e:
                    print(f"Error terminating {name} (PID: {process.pid}) with SIGTERM: {e}. Attempting SIGKILL.")
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except Exception as e_kill:
                         print(f"Error sending SIGKILL to {name} (PID: {process.pid}): {e_kill}")
        elif process and process.poll() is not None:
            print(f"{name} (PID: {process.pid}) had already terminated with code {process.poll()}.")

    sys.exit(0)

# Register signal handlers for graceful shutdown
signal.signal(signal.SIGINT, cleanup_processes) # Ctrl+C
signal.signal(signal.SIGTERM, cleanup_processes) # Termination signal

if __name__ == "__main__":
    # Kill any existing processes on port 8123 before starting
    kill_port_8123()
    
    backend_process = run_script(backend_script_path, "Backend")
    if backend_process:
        processes.append({"name": "Backend", "process": backend_process})

    frontend_process = run_script(frontend_script_path, "Frontend")
    if frontend_process:
        processes.append({"name": "Frontend", "process": frontend_process})

    print("\nBoth frontend and backend processes have been initiated.")
    print("Backend typically runs at: http://localhost:8123") # Updated port
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