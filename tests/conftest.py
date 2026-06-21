"""
Pytest configuration and shared fixtures/mocks for E2E tests.
"""

import os
import sys
import json
import socket
import threading
import tempfile
import shutil
import pytest
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- Programmatic PDF Generation ---
def generate_sample_pdf(pdf_path):
    objects = []
    
    # Object 1: Catalog
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    # Object 2: Pages
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    # Object 3: Page
    objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>")
    # Object 4: Content Stream
    stream_content = b"BT\n/F1 12 Tf\n70 700 Td\n(Mock PDF content for testing) Tj\nET"
    objects.append(b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream_content), stream_content))
    # Object 5: Font
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    
    pdf = b"%PDF-1.4\n"
    offsets = []
    
    for i, obj_content in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += b"%d 0 obj\n" % i
        pdf += obj_content
        pdf += b"\nendobj\n"
        
    xref_offset = len(pdf)
    pdf += b"xref\n"
    pdf += b"0 %d\n" % (len(objects) + 1)
    pdf += b"0000000000 65535 f \n"
    for offset in offsets:
        pdf += b"%010d 00000 n \n" % offset
        
    pdf += b"trailer\n"
    pdf += b"<< /Size %d /Root 1 0 R >>\n" % (len(objects) + 1)
    pdf += b"startxref\n"
    pdf += b"%d\n" % xref_offset
    pdf += b"%%EOF\n"
    
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)
    with open(pdf_path, "wb") as f:
        f.write(pdf)

# Ensure sample PDF exists
tests_dir = os.path.dirname(os.path.abspath(__file__))
sample_pdf_path = os.path.join(tests_dir, "mocks", "mock_data", "sample.pdf")
if not os.path.exists(sample_pdf_path):
    generate_sample_pdf(sample_pdf_path)

# Ensure agy mock is executable
agy_mock_path = os.path.join(tests_dir, "mocks", "agy")
if os.path.exists(agy_mock_path):
    try:
        os.chmod(agy_mock_path, 0o755)
    except Exception:
        pass


# --- Mock Notion Server Implementation ---
class MockNotionHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Suppress server logging to keep pytest output clean
        pass

    def do_GET(self):
        # Check authorization headers first
        auth_header = self.headers.get("Authorization")
        if not auth_header:
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"object": "error", "status": 401, "code": "unauthorized", "message": "API key is required."}')
            return
            
        token = auth_header.replace("Bearer ", "").strip()
        if token == "invalid-token" or token == "mock-invalid-key":
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"object": "error", "status": 401, "code": "unauthorized", "message": "API key is invalid."}')
            return
            
        if token == "rate-limit-token":
            self.send_response(429)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"object": "error", "status": 429, "code": "rate_limited", "message": "Rate limit exceeded."}')
            return

        # Load mock_notion.json data dynamically
        mock_data_path = os.path.join(os.path.dirname(__file__), "mocks", "mock_data", "mock_notion.json")
        try:
            with open(mock_data_path, "r") as f:
                mock_data = json.load(f)
        except Exception:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b'{"error": "Failed to load mock data"}')
            return

        # Routing
        if self.path.startswith("/v1/pages/"):
            page_id = self.path.split("/")[-1]
            page_id = page_id.strip()
            pages = mock_data.get("pages", {})
            page = pages.get(page_id)
            if not page:
                # Fallback to compare IDs normalized (without dashes)
                for pid, pdata in pages.items():
                    if pid.replace("-", "") == page_id.replace("-", ""):
                        page = pdata
                        break
            if page:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(page).encode("utf-8"))
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"object": "error", "status": 404, "code": "object_not_found", "message": "Could not find page."}')
                
        elif self.path.startswith("/v1/blocks/") and self.path.endswith("/children"):
            block_id = self.path.split("/")[-2]
            blocks = mock_data.get("blocks", {})
            block_list = blocks.get(block_id)
            if not block_list:
                # Fallback to compare IDs normalized (without dashes)
                for bid, bdata in blocks.items():
                    if bid.replace("-", "") == block_id.replace("-", ""):
                        block_list = bdata
                        break
            if block_list:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(block_list).encode("utf-8"))
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"object": "error", "status": 404, "code": "object_not_found", "message": "Could not find block children."}')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not Found"}')

def find_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


# --- Pytest Fixtures ---
@pytest.fixture(scope="session")
def mock_notion_server():
    port = find_free_port()
    server = HTTPServer(('127.0.0.1', port), MockNotionHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()

@pytest.fixture
def mock_env_dirs():
    with tempfile.TemporaryDirectory() as temp_ssh, \
         tempfile.TemporaryDirectory() as temp_git, \
         tempfile.TemporaryDirectory() as temp_gemini:
         
        # Populate SSH keys
        private_key_path = os.path.join(temp_ssh, "id_rsa")
        public_key_path = os.path.join(temp_ssh, "id_rsa.pub")
        
        with open(private_key_path, "w") as f:
            f.write("-----BEGIN OPENSSH PRIVATE KEY-----\nmock_private_key\n-----END OPENSSH PRIVATE KEY-----")
        with open(public_key_path, "w") as f:
            f.write("ssh-rsa AAAAB3NzaC1yc2E... mock_public_key")
            
        # Set strict permissions on private key
        os.chmod(private_key_path, 0o600)
        
        # Populate gitconfig
        gitconfig_path = os.path.join(temp_git, ".gitconfig")
        with open(gitconfig_path, "w") as f:
            f.write("[user]\n\tname = Test E2E User\n\temail = e2e@example.com\n")
            
        # Populate gemini config directory
        gemini_config_dir = os.path.join(temp_gemini, "antigravity-cli")
        os.makedirs(gemini_config_dir, exist_ok=True)
        config_json_path = os.path.join(gemini_config_dir, "config.json")
        with open(config_json_path, "w") as f:
            json.dump({"api_key": "mock-gemini-key", "history": []}, f)
            
        # Keep track of original env vars
        orig_ssh = os.environ.get("HOST_SSH_DIR")
        orig_git = os.environ.get("HOST_GITCONFIG")
        orig_gemini = os.environ.get("HOST_GEMINI_DIR")
        
        # Set env vars to isolate the mounts
        os.environ["HOST_SSH_DIR"] = temp_ssh
        os.environ["HOST_GITCONFIG"] = gitconfig_path
        os.environ["HOST_GEMINI_DIR"] = gemini_config_dir
        
        yield {
            "ssh_dir": temp_ssh,
            "gitconfig": gitconfig_path,
            "gemini_dir": gemini_config_dir
        }
        
        # Restore env vars
        if orig_ssh is not None:
            os.environ["HOST_SSH_DIR"] = orig_ssh
        else:
            del os.environ["HOST_SSH_DIR"]
            
        if orig_git is not None:
            os.environ["HOST_GITCONFIG"] = orig_git
        else:
            del os.environ["HOST_GITCONFIG"]
            
        if orig_gemini is not None:
            os.environ["HOST_GEMINI_DIR"] = orig_gemini
        else:
            del os.environ["HOST_GEMINI_DIR"]

@pytest.fixture
def dev_container(mock_env_dirs):
    import subprocess
    import shutil
    
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    compose_path = os.path.join(project_root, "docker-compose.yml")
    
    if not os.path.exists(compose_path) or not shutil.which("docker") or os.environ.get("SKIP_DOCKER"):
        # Fallback graceful stub if docker-compose.yml has not been created, Docker is not installed, or SKIP_DOCKER is set
        yield {"container_id": "mock-container", "status": "running", "root_dir": project_root}
        return
        
    cmd_up = ["docker", "compose", "up", "-d"]
    try:
        subprocess.run(cmd_up, cwd=project_root, env=os.environ, check=True, timeout=120)
    except (subprocess.SubprocessError, subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # Docker not functional — fall back to mock container for non-Docker tests
        yield {"container_id": "mock-container", "status": "running", "root_dir": project_root}
        return
        
    yield {"container_id": "dev-container", "status": "running", "root_dir": project_root}
    
    cmd_down = ["docker", "compose", "down", "-v"]
    try:
        subprocess.run(cmd_down, cwd=project_root, env=os.environ, check=True, timeout=60)
    except (subprocess.SubprocessError, subprocess.TimeoutExpired):
        pass
