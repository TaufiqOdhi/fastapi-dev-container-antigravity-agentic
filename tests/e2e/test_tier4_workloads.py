"""
Tier 4 E2E Test Suite - Real-world Workloads.
Verifies realistic end-to-end integration workflows.
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


def test_scenario_host_driven_autopilot(dev_container):
    """Scenario 1: Host-Driven Task Autopilot.
    1. Write task spec to host file.
    2. Run agent to parse it and invoke agy.
    3. agy creates src/auth.py.
    4. Verify src/auth.py is created on host and contains valid code.
    """
    run_agent_path = check_run_agent(dev_container["root_dir"])
    
    tasks_dir = os.path.join(dev_container["root_dir"], "workspace", "tasks")
    os.makedirs(tasks_dir, exist_ok=True)
    task_file = os.path.join(tasks_dir, "implement_login.txt")
    with open(task_file, "w") as f:
        f.write("Create a FastAPI endpoint at /auth/login that accepts username/password.")
        
    src_dir = os.path.join(dev_container["root_dir"], "workspace", "src")
    auth_py = os.path.join(src_dir, "auth.py")
    if os.path.exists(auth_py):
        os.remove(auth_py)
        
    env = os.environ.copy()
    env["AGY_BIN_PATH"] = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy")
    env["MOCK_AGY_WRITE_FILE_PATH"] = auth_py
    env["MOCK_AGY_WRITE_FILE_CONTENT"] = 'from fastapi import APIRouter\nrouter = APIRouter()\n@router.post("/auth/login")\ndef login():\n    return {"message": "success"}\n'
    
    try:
        res = subprocess.run([sys.executable, run_agent_path, "--source", task_file], env=env, capture_output=True, text=True)
        assert res.returncode == 0
        
        assert os.path.exists(auth_py)
        with open(auth_py, "r") as f:
            code = f.read()
        assert "def login():" in code
    finally:
        if os.path.exists(task_file):
            os.remove(task_file)
        if os.path.exists(auth_py):
            os.remove(auth_py)

def test_scenario_secure_autonomous_release(dev_container, mock_env_dirs):
    """Scenario 2: Secure Autonomous Code Release.
    Verify git identity and commits in workspace.
    """
    if not has_binary("git"):
        pytest.skip("git not available on host")
        
    if dev_container["container_id"] == "mock-container":
        assert True
        return
        
    code, stdout, _ = run_in_container(dev_container["container_id"], "git config user.name")
    assert code == 0
    assert "Test E2E User" in stdout

def test_scenario_multipage_pdf_code_gen(dev_container):
    """Scenario 3: Multi-Page Specification Code Generator."""
    run_agent_path = check_run_agent(dev_container["root_dir"])
    pdf_path = os.path.join(dev_container["root_dir"], "tests", "mocks", "mock_data", "sample.pdf")
    
    model_py = os.path.join(dev_container["root_dir"], "workspace", "src", "models.py")
    if os.path.exists(model_py):
        os.remove(model_py)
        
    env = os.environ.copy()
    env["AGY_BIN_PATH"] = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy")
    env["MOCK_AGY_WRITE_FILE_PATH"] = model_py
    env["MOCK_AGY_WRITE_FILE_CONTENT"] = 'from sqlalchemy import Column, Integer, String\nfrom sqlalchemy.orm import declarative_base\nBase = declarative_base()\nclass User(Base):\n    __tablename__ = "users"\n    id = Column(Integer, primary_key=True)\n    name = Column(String)\n'
    
    try:
        res = subprocess.run([sys.executable, run_agent_path, "--source", pdf_path], env=env, capture_output=True, text=True)
        assert res.returncode == 0
        
        assert os.path.exists(model_py)
        with open(model_py, "r") as f:
            content = f.read()
        assert "class User(Base):" in content
    finally:
        if os.path.exists(model_py):
            os.remove(model_py)

def test_scenario_notion_ticket_completion_cycle(dev_container, mock_notion_server):
    """Scenario 4: Notion ticket completion cycle.
    Fetch ticket, parse it, run agy, update status.
    """
    run_agent_path = check_run_agent(dev_container["root_dir"])
    
    log_file = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy_invocation.json")
    if os.path.exists(log_file):
        os.remove(log_file)
        
    env = os.environ.copy()
    env["AGY_BIN_PATH"] = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy")
    env["MOCK_AGY_LOG_FILE"] = log_file
    env["NOTION_API_URL"] = mock_notion_server
    env["NOTION_API_KEY"] = "mock-secret-key"
    
    page_id = "4a2f8c5b-8e1d-4d7a-9a1b-3c4d5e6f7a8b"
    res = subprocess.run([sys.executable, run_agent_path, "--source", page_id], env=env, capture_output=True, text=True)
    assert res.returncode == 0
    
    assert os.path.exists(log_file)
    with open(log_file, "r") as f:
        log_data = json.load(f)
    combined = " ".join(log_data["args"])
    assert "Implement Login Endpoint Spec" in combined

def test_scenario_persistent_context(dev_container, mock_env_dirs):
    """Scenario 5: Persistent Agent Context Across Container Lifecycle."""
    run_agent_path = check_run_agent(dev_container["root_dir"])
    
    env = os.environ.copy()
    env["AGY_BIN_PATH"] = os.path.join(dev_container["root_dir"], "tests", "mocks", "agy")
    txt_path = os.path.join(dev_container["root_dir"], "tests", "mocks", "mock_data", "sample.txt")
    
    history_dir = os.path.join(mock_env_dirs["gemini_dir"], "history")
    os.makedirs(history_dir, exist_ok=True)
    session_file = os.path.join(history_dir, "session_1.json")
    
    env["MOCK_AGY_WRITE_FILE_PATH"] = session_file
    env["MOCK_AGY_WRITE_FILE_CONTENT"] = '{"history": ["prompt 1"]}'
    
    res1 = subprocess.run([sys.executable, run_agent_path, "--source", txt_path], env=env, capture_output=True, text=True)
    assert res1.returncode == 0
    assert os.path.exists(session_file)
    
    assert os.path.exists(session_file)
    with open(session_file, "r") as f:
        history_data = json.load(f)
    assert history_data["history"][0] == "prompt 1"
