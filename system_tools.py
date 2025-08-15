import os
import json
import subprocess
from file_tools import is_path_allowed, ALLOWED_DIRS

def safe_command_in_allowed_dir(command: list, cwd: str = None) -> str:
    """Execute a command safely within allowed directories."""
    try:
        if cwd and not is_path_allowed(cwd):
            return json.dumps({"error": f"Access denied: {cwd} is not in an allowed directory"})
        
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            timeout=30,
            cwd=cwd or os.getcwd()
        )
        
        return json.dumps({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "command": " ".join(command)
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Command timed out after 30 seconds"})
    except Exception as e:
        return json.dumps({"error": f"Error executing command: {str(e)}"})

def grep_files(pattern: str, directory: str = None, recursive: bool = False, case_insensitive: bool = False) -> str:
    """Search for patterns in files using grep."""
    if directory is None:
        directory = os.getcwd()
    
    if not is_path_allowed(directory):
        return json.dumps({"error": f"Access denied: {directory} is not in an allowed directory"})
    
    command = ["grep"]
    
    if case_insensitive:
        command.append("-i")
    
    if recursive:
        command.append("-r")
    
    command.extend(["-n", pattern])
    
    if recursive:
        command.append(directory)
    else:
        # Search in files in the directory
        try:
            files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
            command.extend([os.path.join(directory, f) for f in files[:50]])  # Limit to 50 files
        except Exception as e:
            return json.dumps({"error": f"Error listing directory: {str(e)}"})
    
    return safe_command_in_allowed_dir(command, cwd=directory)

def find_files(name_pattern: str = None, directory: str = None, file_type: str = None) -> str:
    """Find files using the find command."""
    if directory is None:
        directory = os.getcwd()
    
    if not is_path_allowed(directory):
        return json.dumps({"error": f"Access denied: {directory} is not in an allowed directory"})
    
    command = ["find", directory]
    
    if name_pattern:
        command.extend(["-name", name_pattern])
    
    if file_type:
        if file_type == "file":
            command.extend(["-type", "f"])
        elif file_type == "directory":
            command.extend(["-type", "d"])
    
    # Limit results
    command.extend(["-print", "|", "head", "-100"])
    
    return safe_command_in_allowed_dir(["sh", "-c", " ".join(command)], cwd=directory)

def head_file(filepath: str, lines: int = 10) -> str:
    """Show the first N lines of a file."""
    if not is_path_allowed(filepath):
        return json.dumps({"error": f"Access denied: {filepath} is not in an allowed directory"})
    
    command = ["head", f"-{lines}", filepath]
    return safe_command_in_allowed_dir(command)

def tail_file(filepath: str, lines: int = 10) -> str:
    """Show the last N lines of a file."""
    if not is_path_allowed(filepath):
        return json.dumps({"error": f"Access denied: {filepath} is not in an allowed directory"})
    
    command = ["tail", f"-{lines}", filepath]
    return safe_command_in_allowed_dir(command)

def cat_file(filepath: str) -> str:
    """Display the contents of a file."""
    if not is_path_allowed(filepath):
        return json.dumps({"error": f"Access denied: {filepath} is not in an allowed directory"})
    
    command = ["cat", filepath]
    return safe_command_in_allowed_dir(command)

def wc_file(filepath: str) -> str:
    """Count lines, words, and characters in a file."""
    if not is_path_allowed(filepath):
        return json.dumps({"error": f"Access denied: {filepath} is not in an allowed directory"})
    
    command = ["wc", filepath]
    return safe_command_in_allowed_dir(command)