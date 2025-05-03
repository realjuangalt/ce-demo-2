import http.server
import socketserver
import json
import os
import logging
from urllib.parse import parse_qs
import requests
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env
load_dotenv()
VENICE_API_KEY = os.getenv("VENICE_API_KEY")
GITHUB_API_KEY = os.getenv("GITHUB_API_KEY")

PORT = 8000

# Base GitHub API URL
BASE_URL = "https://api.github.com"

# Headers for GitHub API authentication
github_headers = {
    "Authorization": f"Bearer {GITHUB_API_KEY}",
    "Accept": "application/vnd.github+json"
}

# Global variables for repository structure, user exploration path, and cancellation
repo_structures = {}  # Dictionary to store repo structures, keyed by repo URL
current_path = ["root"]  # Current exploration path, starting at root
current_repo_url = None  # Track the current repo URL being explored
scraping_cancelled = False  # Flag to cancel ongoing scraping

def fetch_repo_contents(owner, repo, path="", depth=0):
    """
    Recursively fetch the folder structure of a GitHub repository (without file contents).
    Args:
        owner (str): Repository owner (e.g., "bitcoin")
        repo (str): Repository name (e.g., "bitcoin")
        path (str): Path within the repository (default is root "")
        depth (int): Depth for recursion (default 0)
    Returns:
        list: List of items (files and directories) in schema format
    """
    if scraping_cancelled:
        logger.info(f"Scraping cancelled for {owner}/{repo} at path: {path}")
        return []

    url = f"{BASE_URL}/repos/{owner}/{repo}/contents/{path}"
    items = []
    
    try:
        logger.info(f"Fetching GitHub contents from: {url}")
        response = requests.get(url, headers=github_headers)
        response.raise_for_status()
        contents = response.json()
        logger.info(f"Received {len(contents)} items at path: {path}")

        for item in contents:
            if scraping_cancelled:
                logger.info(f"Scraping cancelled for {owner}/{repo} at path: {path}/{item['name']}")
                return items
            if item["type"] == "dir":
                children = fetch_repo_contents(owner, repo, item["path"], depth + 1)
                items.append({
                    "name": item["name"],
                    "type": "directory",
                    "quality": 50 + depth * 10,
                    "children": children
                })
            else:
                items.append({
                    "name": item["name"],
                    "type": "file",
                    "quality": 50 + depth * 10
                })
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response:
            logger.error(f"Error fetching contents at {path}: {e.response.status_code} - {e.response.text}")
            if e.response.status_code == 404:
                raise Exception(f"Repository {owner}/{repo} not found")
            elif e.response.status_code == 401:
                raise Exception("Invalid GitHub API key")
            elif e.response.status_code == 403:
                raise Exception("GitHub API rate limit exceeded")
        logger.error(f"Error fetching contents at {path}: {e}")
        raise Exception(f"Failed to fetch contents: {str(e)}")
    
    return items

def scrape_repo_structure(repo_url):
    """
    Scrape the folder structure of a GitHub repository and return it in schema format.
    Args:
        repo_url (str): URL of the repository (e.g., "https://github.com/bitcoin/bitcoin")
    Returns:
        dict: Repository structure in schema format
    """
    global repo_structures, current_repo_url, current_path
    parts = repo_url.split("/")
    owner = parts[-2]
    repo = parts[-1]

    logger.info(f"Scraping folder structure for {owner}/{repo}...")
    files = fetch_repo_contents(owner, repo)
    
    repo_structures[repo_url] = {
        "files": files,
        "path": ["root"]
    }
    current_repo_url = repo_url
    current_path = ["root"]
    
    return repo_structures[repo_url]

def get_current_metadata():
    """
    Get the metadata of the user's current exploration location.
    Returns:
        dict: Metadata of the current location (e.g., directory or file details)
    """
    if not current_repo_url or current_repo_url not in repo_structures:
        return {"location": "No repository loaded"}

    repo_data = repo_structures[current_repo_url]
    current = repo_data["files"]
    path = current_path[1:]

    for name in path:
        found = False
        for item in current:
            if item["name"] == name:
                if item["type"] == "directory":
                    current = item["children"]
                found = True
                break
        if not found:
            return {"location": "Path not found", "path": current_path}

    if len(path) == 0:
        return {
            "location": "root",
            "contents": [item["name"] for item in current],
            "path": current_path
        }
    else:
        last_name = path[-1]
        for item in current:
            if item["name"] == last_name:
                if item["type"] == "directory":
                    return {
                        "location": f"Directory: {last_name}",
                        "contents": [child["name"] for child in item["children"]],
                        "path": current_path
                    }
                else:
                    return {
                        "location": f"File: {last_name}",
                        "path": current_path
                    }
        return {"location": "Path not found", "path": current_path}

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/chat":
            logger.info("Received chat request")
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = parse_qs(post_data)
            message = data.get('message', [''])[0]
            logger.info(f"Chat message: {message}")

            metadata = get_current_metadata()
            prompt = f"User is exploring a GitHub repository. Current location: {json.dumps(metadata)}\nUser message: {message}"

            url = "https://api.venice.ai/api/v1/chat/completions"
            payload = {
                "frequency_penalty": 0,
                "n": 1,
                "presence_penalty": 0,
                "temperature": 0.15,
                "top_p": 0.9,
                "venice_parameters": {"include_venice_system_prompt": True},
                "parallel_tool_calls": True,
                "model": "llama-3.3-70b",
                "messages": [{"role": "user", "content": prompt}]
            }
            headers = {
                "Authorization": f"Bearer {VENICE_API_KEY}",
                "Content-Type": "application/json"
            }

            try:
                response = requests.post(url, json=payload, headers=headers)
                response.raise_for_status()
                bot_message = response.json()['choices'][0]['message']['content']
                logger.info(f"Chat response: {bot_message}")
            except Exception as e:
                bot_message = f"Error: {str(e)}"
                logger.error(f"Chat API error: {str(e)}")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps({"message": bot_message}).encode('utf-8'))
            self.wfile.flush()

        elif self.path == "/scrape-repo":
            logger.info("Received scrape-repo request")
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = parse_qs(post_data)
            repo_url = data.get('repo_url', [''])[0]
            logger.info(f"Scraping repo: {repo_url}")

            scraping_cancelled = False  # Reset cancellation flag

            try:
                repo_structure = scrape_repo_structure(repo_url)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.end_headers()
                self.wfile.write(json.dumps(repo_structure).encode('utf-8'))
                self.wfile.flush()
            except Exception as e:
                logger.error(f"Error scraping repo: {e}")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
                self.wfile.flush()

        elif self.path == "/update-path":
            logger.info("Received update-path request")
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = parse_qs(post_data)
            path = json.loads(data.get('path', ['[]'])[0])
            logger.info(f"Updating exploration path to: {path}")

            global current_path
            current_path = path

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            self.wfile.flush()

        elif self.path == "/cancel-scrape":
            logger.info("Received cancel-scrape request")
            scraping_cancelled = True
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "cancelled"}).encode('utf-8'))
            self.wfile.flush()

        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/":
            self.path = "/index.html"
        logger.info(f"Serving static file: {self.path}")
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

# Set up and start the server
Handler = CustomHandler
with socketserver.TCPServer(("", PORT), Handler) as httpd:
    logger.info(f"Serving at http://localhost:{PORT}")
    httpd.serve_forever()