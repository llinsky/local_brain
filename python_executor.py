import json
import subprocess
import tempfile
import os
import sys
from pathlib import Path

def execute_python_code(code: str, timeout: int = 30) -> str:
    """Execute Python code in an isolated environment."""
    try:
        # Create a temporary file for the code
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        # Create a temporary directory for any file outputs
        with tempfile.TemporaryDirectory() as temp_dir:
            # Execute the code in the virtual environment if it exists
            venv_python = "test_env/bin/python" if os.path.exists("test_env/bin/python") else sys.executable
            
            # Run with restricted environment
            env = {
                "PYTHONPATH": "",
                "PATH": os.environ.get("PATH", ""),
                "TMPDIR": temp_dir,
                "HOME": temp_dir,
            }
            
            result = subprocess.run(
                [venv_python, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=temp_dir,
                env=env
            )
            
            # Clean up temp file
            os.unlink(temp_file)
            
            # Check for any files created in temp directory
            created_files = list(Path(temp_dir).glob("*"))
            file_outputs = {}
            
            for file_path in created_files:
                if file_path.is_file() and file_path.stat().st_size < 10000:  # Limit file size
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_outputs[file_path.name] = f.read()
                    except:
                        file_outputs[file_path.name] = "<binary or unreadable file>"
            
            return json.dumps({
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "execution_time": "completed",
                "created_files": file_outputs
            })
            
    except subprocess.TimeoutExpired:
        # Clean up temp file if it exists
        try:
            os.unlink(temp_file)
        except:
            pass
        return json.dumps({"error": f"Code execution timed out after {timeout} seconds"})
    except Exception as e:
        # Clean up temp file if it exists
        try:
            os.unlink(temp_file)
        except:
            pass
        return json.dumps({"error": f"Error executing Python code: {str(e)}"})

def install_package(package: str) -> str:
    """Install a Python package in the test environment."""
    try:
        # Use the virtual environment pip if available
        pip_command = "test_env/bin/pip" if os.path.exists("test_env/bin/pip") else "pip"
        
        result = subprocess.run(
            [pip_command, "install", package],
            capture_output=True,
            text=True,
            timeout=120  # 2 minutes for package installation
        )
        
        return json.dumps({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "package": package,
            "action": "install"
        })
        
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Package installation timed out after 2 minutes"})
    except Exception as e:
        return json.dumps({"error": f"Error installing package: {str(e)}"})

def list_installed_packages() -> str:
    """List installed packages in the environment."""
    try:
        # Use the virtual environment pip if available
        pip_command = "test_env/bin/pip" if os.path.exists("test_env/bin/pip") else "pip"
        
        result = subprocess.run(
            [pip_command, "list"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return json.dumps({
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "action": "list_packages"
        })
        
    except Exception as e:
        return json.dumps({"error": f"Error listing packages: {str(e)}"})

# AIDEV-NOTE: This provides a safe Python execution environment with timeouts and isolation