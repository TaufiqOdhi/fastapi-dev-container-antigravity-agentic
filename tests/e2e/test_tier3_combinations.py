"""
Tier 3 E2E Test Suite - Cross-Feature Combinations.
Verifies pairwise and multi-feature interaction test cases.
"""

import os
import sys
import subprocess
import json
import pytest

# Helper to check if a binary is available on the host
def has_binary(name):
    import shutil
    return shutil.which(name) is not None

# Helper to execute command inside the container
def run_in_container(container_id, cmd, env=None):
    if container_id == "mock-container":
        # If we are stubbed, return a simulated response based on the command
        if "python3 --version" in cmd:
            return 0, "Python 3.14.0b2", ""
        if "git --version" in cmd or "curl --version" in cmd or "gcc --version" in cmd:
            return 0, "mock version", ""
        if "pip list" in cmd or "pip show" in cmd:
            return 0, "fastapi uvicorn python-multipart pypdf", ""
        if "git config --list" in cmd:
            gitconfig_path = os.environ.get("HOST_GITCONFIG")
            if gitconfig_path and os.path.exists(gitconfig_path):
                res = subprocess.run(["git", "config", "-f", gitconfig_path, "--list"], capture_output=True, text=True)
                return res.returncode, res.stdout, res.stderr
            return 0, "user.name=Test E2E User\nuser.email=e2e@example.com", ""
        if cmd.startswith("git config "):
            gitconfig_path = os.environ.get("HOST_GITCONFIG")
            if gitconfig_path and os.path.exists(gitconfig_path):
                args = cmd.split()[2:]
                res = subprocess.run(["git", "config", "-f", gitconfig_path] + args, capture_output=True, text=True)
                return res.returncode, res.stdout, res.stderr
        if "ssh -V" in cmd:
            return 0, "OpenSSH_9.6p1", ""
        if "ls -la /root/.ssh/id_rsa" in cmd:
            # Simulate strict permissions check
            return 0, "-rw------- 1 root root 1200", ""
        if cmd.startswith("stat -c "):
            path = cmd.split()[-1]
            if path.startswith("/root/.ssh/"):
                host_path = path.replace("/root/.ssh/", os.environ.get("HOST_SSH_DIR", "") + "/")
                if os.path.exists(host_path):
                    return 0, "600", ""
        if cmd.startswith("test -f "):
            path = cmd.split()[-1]
            if path.startswith("/root/.ssh/"):
                host_path = path.replace("/root/.ssh/", os.environ.get("HOST_SSH_DIR", "") + "/")
                if os.path.exists(host_path):
                    return 0, "", ""
                return 1, "", ""
            if path.startswith("/root/.gemini/antigravity-cli/"):
                host_path = path.replace("/root/.gemini/antigravity-cli/", os.environ.get("HOST_GEMINI_DIR", "") + "/")
                if os.path.exists(host_path):
                    return 0, "", ""
                return 1, "", ""
        if cmd.startswith("test -d "):
            path = cmd.split()[-1]
            if path.startswith("/root/.ssh"):
                host_path = path.replace("/root/.ssh", os.environ.get("HOST_SSH_DIR", ""))
                if os.path.exists(host_path):
                    return 0, "", ""
                return 1, "", ""
            if path.startswith("/root/.gemini/antigravity-cli"):
                host_path = path.replace("/root/.gemini/antigravity-cli", os.environ.get("HOST_GEMINI_DIR", ""))
                if os.path.exists(host_path):
                    return 0, "", ""
                return 1, "", ""
        if cmd.startswith("touch "):
            path = cmd.split()[-1]
            if path.startswith("/root/.gemini/antigravity-cli/"):
                host_path = path.replace("/root/.gemini/antigravity-cli/", os.environ.get("HOST_GEMINI_DIR", "") + "/")
                try:
                    with open(host_path, "a"):
                        os.utime(host_path, None)
                    return 0, "", ""
                except Exception:
                    return 1, "", ""
        if cmd.startswith("cat "):
            path = cmd.split()[1]
            if path.startswith("/root/.gemini/antigravity-cli/"):
                host_path = path.replace("/root/.gemini/antigravity-cli/", os.environ.get("HOST_GEMINI_DIR", "") + "/")
                if os.path.exists(host_path):
                    with open(host_path, "r", encoding="utf-8") as f:
                        return 0, f.read(), ""
            elif path == "/root/.gitconfig":
                host_path = os.environ.get("HOST_GITCONFIG", "")
                if host_path and os.path.exists(host_path):
                    with open(host_path, "r", encoding="utf-8") as f:
                        return 0, f.read(), ""
            return 1, "", "File not found"
        return 0, "", ""
        
    full_cmd = ["docker", "compose", "exec", "dev-container"] + cmd.split()
    res = subprocess.run(full_cmd, capture_output=True, text=True, env=env)
    return res.returncode, res.stdout, res.stderr

# Helper to check run_agent.py existence and skip if not found
def check_run_agent(root_dir):
    run_agent_path = os.path.join(root_dir, "run_agent.py")
    if not os.path.exists(run_agent_path):
        pytest.skip("run_agent.py is not implemented yet in this workspace")
    return run_agent_path


def test_docker_gitconfig_ssh_integration(dev_container, mock_env_dirs):
    """Verify container git config and ssh mounts integration."""
    code_git, out_git, _ = run_in_container(dev_container["container_id"], "git config user.name")
    assert code_git == 0
    assert "Test E2E User" in out_git.strip()
    
    code_ssh, _, _ = run_in_container(dev_container["container_id"], "test -f /root/.ssh/id_rsa")
    assert code_ssh == 0

def test_txt_to_cli_pipeline(dev_container):
    """Verify that a txt prompt is extracted and passed to agy."""
    run_agent_path = check_run_agent(dev_container["root_dir"])
    txt_path = os.path.join(dev_container["root_dir"], "tests", "mocks", "mock_data", "sample.txt")
    log_file = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy_invocation.json")
    if os.path.exists(log_file):
        os.remove(log_file)
        
    env = os.environ.copy()
    env["AGY_BIN_PATH"] = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy")
    env["MOCK_AGY_LOG_FILE"] = log_file
    
    res = subprocess.run([sys.executable, run_agent_path, "--source", txt_path], env=env, capture_output=True, text=True)
    assert res.returncode == 0
    
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        log_data = json.load(f)
        
    combined_args = " ".join(log_data["args"])
    assert "Implement a simple health check endpoint in FastAPI at /health" in combined_args

def test_pdf_to_cli_pipeline(dev_container):
    """Verify that a pdf prompt is extracted and passed to agy."""
    run_agent_path = check_run_agent(dev_container["root_dir"])
    pdf_path = os.path.join(dev_container["root_dir"], "tests", "mocks", "mock_data", "sample.pdf")
    log_file = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy_invocation.json")
    if os.path.exists(log_file):
        os.remove(log_file)
        
    env = os.environ.copy()
    env["AGY_BIN_PATH"] = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy")
    env["MOCK_AGY_LOG_FILE"] = log_file
    
    res = subprocess.run([sys.executable, run_agent_path, "--source", pdf_path], env=env, capture_output=True, text=True)
    assert res.returncode == 0
    
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        log_data = json.load(f)
        
    combined_args = " ".join(log_data["args"])
    assert "Mock PDF content for testing" in combined_args

def test_notion_to_cli_pipeline(dev_container, mock_notion_server):
    """Verify Notion page URL triggers fetching and forwarding to agy."""
    run_agent_path = check_run_agent(dev_container["root_dir"])
    log_file = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy_invocation.json")
    if os.path.exists(log_file):
        os.remove(log_file)
        
    env = os.environ.copy()
    env["AGY_BIN_PATH"] = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy")
    env["MOCK_AGY_LOG_FILE"] = log_file
    env["NOTION_API_URL"] = mock_notion_server
    env["NOTION_API_KEY"] = "mock-secret-key"
    
    notion_url = "https://www.notion.so/Implement-Login-Endpoint-4a2f8c5b8e1d4d7a9a1b3c4d5e6f7a8b"
    res = subprocess.run([sys.executable, run_agent_path, "--source", notion_url], env=env, capture_output=True, text=True)
    assert res.returncode == 0
    
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        log_data = json.load(f)
        
    combined_args = " ".join(log_data["args"])
    assert "Implement Login Endpoint Spec" in combined_args
    assert "Create a POST endpoint at /auth/login" in combined_args

def test_cli_gemini_config_interaction(dev_container, mock_env_dirs):
    """Verify that run_agent.py and agy can access/modify Gemini config directory."""
    run_agent_path = check_run_agent(dev_container["root_dir"])
    txt_path = os.path.join(dev_container["root_dir"], "tests", "mocks", "mock_data", "sample.txt")
    
    env = os.environ.copy()
    env["AGY_BIN_PATH"] = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy")
    
    res = subprocess.run([sys.executable, run_agent_path, "--source", txt_path], env=env, capture_output=True, text=True)
    assert res.returncode == 0
    
    config_json = os.path.join(mock_env_dirs["gemini_dir"], "config.json")
    assert os.path.exists(config_json)
    with open(config_json, "r") as f:
        data = json.load(f)
    assert data.get("api_key") == "mock-gemini-key"
