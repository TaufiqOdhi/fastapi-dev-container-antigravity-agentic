#!/usr/bin/env python3
"""
run_agent.py — Agentic Runner for Antigravity CLI

Accepts an instruction source (text file, PDF, or Notion page URL/ID),
extracts the text content, and invokes the Antigravity CLI (agy) with
the extracted prompt to run tasks autonomously.

Usage:
    python run_agent.py --source <path_or_url_or_notion_id>

Environment Variables:
    AGY_BIN_PATH      - Path to the agy binary (default: "agy" on PATH)
    NOTION_API_KEY    - Notion integration token for API access
    NOTION_API_URL    - Base URL for the Notion API (default: https://api.notion.com)
    MOCK_AGY_LOG_FILE - (Testing) Log file path for mock agy invocations
    MOCK_AGY_*        - (Testing) Various mock agy environment variables
"""

import argparse
import os
import re
import subprocess
import sys
import json
import urllib.request
import urllib.error


# ---------------------------------------------------------------------------
# Source detection
# ---------------------------------------------------------------------------

def detect_source_type(source: str) -> str:
    """Detect whether the source is a text file, PDF, Notion URL, or Notion ID."""
    # Notion URL pattern
    if source.startswith("https://") and "notion.so" in source:
        return "notion_url"

    # UUID pattern (with or without dashes) — treat as Notion page ID
    uuid_pattern = r"^[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}$"
    if re.match(uuid_pattern, source):
        return "notion_id"

    # File-based detection
    if source.lower().endswith(".pdf"):
        return "pdf"

    if source.lower().endswith(".txt"):
        return "txt"

    # Fallback: try to read as text file if it exists
    if os.path.isfile(source):
        return "txt"

    print(f"Error: Cannot determine source type for: {source}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Text file extraction
# ---------------------------------------------------------------------------

def extract_from_txt(filepath: str) -> str:
    """Read and return the stripped text content of a .txt file."""
    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except UnicodeDecodeError:
        print(f"Error: File {filepath} is not a valid UTF-8 text file.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

    return content.strip()


# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_from_pdf(filepath: str) -> str:
    """Extract text from a PDF using pypdf."""
    if not os.path.isfile(filepath):
        print(f"Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)

    try:
        from pypdf import PdfReader
    except ImportError:
        print("Error: pypdf is required for PDF parsing. Install with: pip install pypdf", file=sys.stderr)
        sys.exit(1)

    reader = PdfReader(filepath)
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)

    return "\n".join(pages_text).strip()


# ---------------------------------------------------------------------------
# Notion extraction
# ---------------------------------------------------------------------------

def extract_page_id_from_url(url: str) -> str:
    """Extract the 32-character hex page ID from a Notion URL."""
    # Notion URLs end with a 32-char hex ID (no dashes)
    match = re.search(r"([0-9a-fA-F]{32})$", url.split("?")[0])
    if match:
        raw = match.group(1)
        # Format as UUID with dashes
        return f"{raw[:8]}-{raw[8:12]}-{raw[12:16]}-{raw[16:20]}-{raw[20:]}"

    # Try with dashes already present
    match = re.search(
        r"([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
        url,
    )
    if match:
        return match.group(1)

    print(f"Error: Could not extract page ID from Notion URL: {url}", file=sys.stderr)
    sys.exit(1)


def notion_api_request(endpoint: str, api_url: str, api_key: str) -> dict:
    """Make an authenticated GET request to the Notion API."""
    url = f"{api_url}{endpoint}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }

    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Error: Notion API returned {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: Failed to connect to Notion API: {e.reason}", file=sys.stderr)
        sys.exit(1)


def extract_rich_text(rich_text_list: list) -> str:
    """Extract plain text from a Notion rich_text array."""
    parts = []
    for item in rich_text_list:
        parts.append(item.get("plain_text", ""))
    return "".join(parts)


def extract_block_text(block: dict) -> str:
    """Extract text content from a single Notion block."""
    block_type = block.get("type", "")
    block_data = block.get(block_type, {})

    if not isinstance(block_data, dict):
        return ""

    rich_text = block_data.get("rich_text", [])
    text = extract_rich_text(rich_text)

    # Add formatting based on block type
    if block_type == "heading_1":
        return f"# {text}"
    elif block_type == "heading_2":
        return f"## {text}"
    elif block_type == "heading_3":
        return f"### {text}"
    elif block_type == "bulleted_list_item":
        return f"- {text}"
    elif block_type == "numbered_list_item":
        return f"1. {text}"
    elif block_type == "to_do":
        checked = block_data.get("checked", False)
        marker = "[x]" if checked else "[ ]"
        return f"- {marker} {text}"
    elif block_type == "code":
        language = block_data.get("language", "")
        return f"```{language}\n{text}\n```"
    elif block_type == "quote":
        return f"> {text}"
    elif block_type == "divider":
        return "---"
    else:
        return text


def extract_from_notion(page_id: str) -> str:
    """Fetch a Notion page's title and block content, returning combined text."""
    api_url = os.environ.get("NOTION_API_URL", "https://api.notion.com")
    api_key = os.environ.get("NOTION_API_KEY", "")

    if not api_key:
        print("Error: NOTION_API_KEY environment variable is required for Notion sources.", file=sys.stderr)
        sys.exit(1)

    # Fetch page metadata for the title
    page_data = notion_api_request(f"/v1/pages/{page_id}", api_url, api_key)

    # Extract title from page properties
    title = ""
    properties = page_data.get("properties", {})
    for prop in properties.values():
        if prop.get("type") == "title":
            title_items = prop.get("title", [])
            title = extract_rich_text(title_items)
            break

    # Fetch block children for content
    blocks_data = notion_api_request(f"/v1/blocks/{page_id}/children", api_url, api_key)
    results = blocks_data.get("results", [])

    text_parts = []
    if title:
        text_parts.append(f"# {title}")
        text_parts.append("")

    for block in results:
        block_text = extract_block_text(block)
        if block_text:
            text_parts.append(block_text)

    return "\n".join(text_parts).strip()


# ---------------------------------------------------------------------------
# CLI invocation
# ---------------------------------------------------------------------------

def invoke_agy(prompt: str) -> int:
    """Invoke the Antigravity CLI with the extracted prompt text."""
    agy_bin = os.environ.get("AGY_BIN_PATH", "agy")

    # If the prompt is too large to be passed as a single command-line argument
    # (Linux has a limit of 128KB per argument), we pass it via stdin instead.
    if len(prompt.encode('utf-8', errors='replace')) > 120000:
        cmd = [agy_bin]
        stdin_data = prompt
    else:
        cmd = [agy_bin, prompt]
        stdin_data = None

    try:
        result = subprocess.run(
            cmd,
            input=stdin_data,
            capture_output=True,
            text=True,
            env=os.environ.copy(),
        )

        # Pass through stdout
        if result.stdout:
            sys.stdout.write(result.stdout)
            sys.stdout.flush()

        # Pass through stderr
        if result.stderr:
            sys.stderr.write(result.stderr)
            sys.stderr.flush()

        return result.returncode

    except FileNotFoundError:
        print(f"Error: Antigravity CLI not found at '{agy_bin}'. "
              "Ensure it is installed and AGY_BIN_PATH is set correctly.", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error invoking Antigravity CLI: {e}", file=sys.stderr)
        return 1


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Agentic Runner — Extract prompts from sources and invoke Antigravity CLI"
    )
    parser.add_argument(
        "--source",
        required=True,
        help="Path to a .txt or .pdf file, a Notion page URL, or a Notion page UUID",
    )
    args = parser.parse_args()

    source = args.source
    source_type = detect_source_type(source)

    # Extract prompt text based on source type
    if source_type == "txt":
        prompt = extract_from_txt(source)
    elif source_type == "pdf":
        prompt = extract_from_pdf(source)
    elif source_type == "notion_url":
        page_id = extract_page_id_from_url(source)
        prompt = extract_from_notion(page_id)
    elif source_type == "notion_id":
        prompt = extract_from_notion(source)
    else:
        print(f"Error: Unsupported source type: {source_type}", file=sys.stderr)
        sys.exit(1)

    if not prompt:
        print("Error: No text content could be extracted from the source.", file=sys.stderr)
        sys.exit(1)

    print(f"[run_agent] Extracted prompt ({len(prompt)} chars) from {source_type} source.", file=sys.stderr)
    print(f"[run_agent] Invoking Antigravity CLI...", file=sys.stderr)

    exit_code = invoke_agy(prompt)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
