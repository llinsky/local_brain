import os
import json
from pathlib import Path
from typing import List

# AIDEV-NOTE: Define allowed directories for file operations to prevent security issues
ALLOWED_DIRS = [
    "/tmp",
    "/var/tmp", 
    os.path.expanduser("~/Downloads"),
    os.path.expanduser("~/dev/llm_client"),
    os.getcwd(),  # Current working directory
]

def is_path_allowed(filepath: str) -> bool:
    """Check if a file path is within allowed directories."""
    try:
        abs_path = os.path.abspath(filepath)
        return any(abs_path.startswith(os.path.abspath(allowed_dir)) for allowed_dir in ALLOWED_DIRS)
    except Exception:
        return False

def read_file(filepath: str) -> str:
    """Read a file from an allowed directory."""
    if not is_path_allowed(filepath):
        return json.dumps({"error": f"Access denied: {filepath} is not in an allowed directory"})
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return json.dumps({"content": content, "filepath": filepath})
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {filepath}"})
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {filepath}"})
    except Exception as e:
        return json.dumps({"error": f"Error reading file: {str(e)}"})

def write_file(filepath: str, content: str) -> str:
    """Write content to a file in an allowed directory."""
    if not is_path_allowed(filepath):
        return json.dumps({"error": f"Access denied: {filepath} is not in an allowed directory"})
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return json.dumps({"success": True, "filepath": filepath, "bytes_written": len(content.encode('utf-8'))})
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {filepath}"})
    except Exception as e:
        return json.dumps({"error": f"Error writing file: {str(e)}"})

def append_file(filepath: str, content: str) -> str:
    """Append content to a file in an allowed directory."""
    if not is_path_allowed(filepath):
        return json.dumps({"error": f"Access denied: {filepath} is not in an allowed directory"})
    
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(content)
        return json.dumps({"success": True, "filepath": filepath, "bytes_appended": len(content.encode('utf-8'))})
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {filepath}"})
    except Exception as e:
        return json.dumps({"error": f"Error appending to file: {str(e)}"})

def delete_file(filepath: str) -> str:
    """Delete a file from an allowed directory."""
    if not is_path_allowed(filepath):
        return json.dumps({"error": f"Access denied: {filepath} is not in an allowed directory"})
    
    try:
        os.remove(filepath)
        return json.dumps({"success": True, "filepath": filepath, "action": "deleted"})
    except FileNotFoundError:
        return json.dumps({"error": f"File not found: {filepath}"})
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {filepath}"})
    except Exception as e:
        return json.dumps({"error": f"Error deleting file: {str(e)}"})

def list_directory(dirpath: str) -> str:
    """List contents of a directory in an allowed location."""
    if not is_path_allowed(dirpath):
        return json.dumps({"error": f"Access denied: {dirpath} is not in an allowed directory"})
    
    try:
        if not os.path.isdir(dirpath):
            return json.dumps({"error": f"Not a directory: {dirpath}"})
        
        items = []
        for item in os.listdir(dirpath):
            item_path = os.path.join(dirpath, item)
            item_info = {
                "name": item,
                "type": "directory" if os.path.isdir(item_path) else "file",
                "size": os.path.getsize(item_path) if os.path.isfile(item_path) else None
            }
            items.append(item_info)
        
        return json.dumps({"directory": dirpath, "items": items})
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {dirpath}"})
    except Exception as e:
        return json.dumps({"error": f"Error listing directory: {str(e)}"})

def create_directory(dirpath: str) -> str:
    """Create a directory in an allowed location."""
    if not is_path_allowed(dirpath):
        return json.dumps({"error": f"Access denied: {dirpath} is not in an allowed directory"})
    
    try:
        os.makedirs(dirpath, exist_ok=True)
        return json.dumps({"success": True, "directory": dirpath, "action": "created"})
    except PermissionError:
        return json.dumps({"error": f"Permission denied: {dirpath}"})
    except Exception as e:
        return json.dumps({"error": f"Error creating directory: {str(e)}"})