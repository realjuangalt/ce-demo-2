# GitHub Explorer

## Overview

GitHub Explorer is a web application designed to visualize and explore the directory structure of GitHub repositories through an interactive sunburst graph. It integrates a chatbot powered by a large language model (LLM) to provide contextual assistance based on the user’s navigation within the repository. The project aims to enhance the developer experience by offering a visual and conversational tool for repository exploration.

## Design Goals

The primary design goals of GitHub Explorer are:

- **Visual Exploration**: Provide an intuitive, interactive visualization of a GitHub repository’s directory structure using a sunburst graph, allowing users to drill down into directories and view files.
- **Contextual Assistance**: Integrate a chatbot that leverages an LLM (Llama 3.3 70B via Venice AI) to answer questions about the repository, with context based on the user’s current exploration path.
- **Performance Optimization**: Ensure fast loading of large repositories by optimizing the scraping process and providing visual feedback (e.g., loading messages) during data fetching.
- **User-Friendly Interface**: Create a clean, cypherpunk-inspired aesthetic with a dark theme, orange accents, and readable text formatting, while maximizing screen space for the graph and chat.
- **Extensibility**: Design the architecture to support future features, such as file content viewing, API integrations, and multi-user support.

## Technical Specification

### Front-End
- **HTML/CSS/JavaScript**: The front-end is a single-page application built with vanilla HTML, CSS, and JavaScript.
- **Visualization**: Uses D3.js (v7) to render an interactive sunburst graph for repository structure visualization.
- **Markdown Rendering**: Integrates `marked.js` (v4.0.12) to parse and render LLM responses as Markdown, improving readability with formatted lists, bold/italic text, and more.
- **Layout**: Utilizes CSS flexbox for a responsive layout:
  - Top section: Input field and buttons for loading repositories.
  - Main section: Sunburst graph (left, 75% width) and chat sidebar (right, 25% width, max 400px).
  - Bottom spacing: Added padding to prevent content from bleeding into the screen edge.
- **Styling**: Dark theme with orange accents (`#f7931a` for text/buttons, `#ff9900` for donate button), using `'Courier New', monospace` font for a tech aesthetic.

### Back-End
- **Server**: A Python HTTP server (`http.server` and `socketserver`) running on `localhost:8000`.
- **Scraping**: Fetches repository structure using the GitHub API (`GET /repos/:owner/:repo/contents/:path`), with authentication via a GitHub API key stored in `.env`.
- **Cancellation**: Implements a cancellation mechanism to stop ongoing scraping tasks when a new repository is loaded, using a global `scraping_cancelled` flag.
- **LLM Integration**: Uses the Venice AI API (`llama-3.3-70b` model) for the chatbot, with the API key stored in `.env`. The user’s current exploration path metadata is appended to the LLM prompt for context-aware responses.
- **State Management**: Stores repository structures and user exploration paths in global variables (`repo_structures`, `current_path`, `current_repo_url`), with plans for session-based handling in the future.

### Endpoints
- **`/scrape-repo` (POST)**: Scrapes the folder structure of a specified GitHub repository URL and returns it in JSON format.
- **`/chat` (POST)**: Sends a user message to the LLM, including the current exploration metadata, and returns the LLM’s response.
- **`/update-path` (POST)**: Updates the server-side record of the user’s current exploration path.
- **`/cancel-scrape` (POST)**: Cancels an ongoing scraping task to allow a new scrape to start immediately.

### Data Schema
- **Repository Structure**: Stored as a JSON object with a nested structure:
  ```json
  {
    "files": [
      {
        "name": "dir_name",
        "type": "directory",
        "quality": 50,
        "children": [...]
      },
      {
        "name": "file_name",
        "type": "file",
        "quality": 50
      }
    ],
    "path": ["root"]
  }
  ```
- **Quality Scores**: Currently mocked based on directory depth (e.g., `50 + depth * 10`).

## Current Features
- **Interactive Sunburst Graph**: Visualize repository structure with a large, clickable sunburst graph (600x600px).
- **Chatbot with Context**: Ask questions about the repository, with the LLM receiving the user’s current location (e.g., directory contents) as part of the prompt.
- **Markdown Rendering**: LLM responses are rendered as Markdown, with formatted lists, bold/italic text, and proper spacing.
- **Loading Feedback**: Displays a "Loading repository..." message during scraping.
- **Cancellation**: Cancels ongoing scraping tasks when a new repository is loaded.
- **Responsive Layout**: Optimized screen space with a top input section, a large graph area, and a tall chat sidebar, with bottom spacing to prevent content bleeding.

## Future Goals and Features
- **File Content Fetching**: Fetch file contents on demand when a user clicks a file, displaying them in `#code-view`, to balance performance and functionality.
- **Session Handling**: Implement session management to support multiple users, replacing global variables with session-based storage (e.g., using a dictionary keyed by session IDs).
- **Performance Optimization**: Use the GitHub API’s Trees endpoint (`GET /repos/:owner/:repo/git/trees/:tree_sha?recursive=1`) to fetch the entire repository structure in one request, further reducing load times for large repositories.
- **Enhanced Visualization**: Add tooltips or labels to the sunburst graph to display additional metadata (e.g., file size, last commit date) on hover.
- **Advanced Chat Features**: Allow the LLM to suggest actions (e.g., "Would you like to view the contents of `server.py`?") and handle more complex queries (e.g., code analysis).
- **Authentication and Security**: Add user authentication for private repository access and secure the Venice AI API key handling.
- **Export Functionality**: Allow users to export the repository structure as a JSON file or visualize it in other formats (e.g., tree view).
- **Visual Customization**: Provide options to customize the graph’s appearance (e.g., color schemes, graph size) and save user preferences.

## Setup Instructions
1. **Clone the Repository**:
   ```
   git clone <repository-url>
   cd <repository-directory>
   ```
2. **Set Up a Virtual Environment** (optional but recommended):
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install Dependencies**:
   ```
   pip3 install requests python-dotenv
   ```
4. **Create a `.env` File**:
   ```
   GITHUB_API_KEY=your_github_api_key
   VENICE_API_KEY=your_venice_api_key
   ```
   - Obtain a GitHub API key from GitHub (Settings > Developer settings > Personal access tokens, with `repo` scope).
   - Obtain a Venice AI API key from the Venice AI platform.
5. **Run the Server**:
   ```
   python3 server.py
   ```
6. **Access the App**:
   - Open `http://localhost:8000` in your browser.
   - Enter a public GitHub repository URL (e.g., `https://github.com/bitcoin/bitcoin`) and click "Load" to visualize the structure.
   - Use the chat to ask questions about the repository.

## Contributing
Contributions are welcome! Please fork the repository, create a new branch, and submit a pull request with your changes. Ensure your code follows the project’s style guidelines and includes appropriate documentation.

## License
This project is licensed under the MIT License. See the `LICENSE` file for details.

## Acknowledgments
- Built with inspiration from tools like Niston and Grok, aiming to combine repository visualization with conversational AI.
- Thanks to the open-source community for libraries like D3.js and marked.js, and to Venice AI for their LLM API.