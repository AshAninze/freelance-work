# GitHub Repository Scraper

A Python tool that fetches and outputs the code from a user's GitHub repositories. This tool uses the GitHub API to authenticate, list repositories, retrieve each repository's files, and output the content in plain text format.

## Features

- **GitHub API Authentication**: Secure authentication using GitHub personal access tokens
- **Pagination Support**: Automatically handles pagination for API calls to fetch all repositories
- **Retry Logic**: Built-in retry mechanism for failed requests with configurable attempts and delays
- **Progress Logging**: Comprehensive logging to track scraping progress and errors
- **Rate Limit Handling**: Automatically detects and handles GitHub API rate limits
- **File Filtering**: Intelligently filters and scrapes only code files (ignores binaries, images, etc.)
- **Combined Output**: Saves all repository code in a single, organized text file per repository

## Prerequisites

- Python 3.6 or higher
- GitHub personal access token

## Installation

1. Clone the repository or download the `github_scraper` folder

2. Navigate to the `github_scraper` directory:
   ```bash
   cd github_scraper
   ```

3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Getting a GitHub Personal Access Token

1. Go to GitHub.com and log in to your account
2. Click on your profile picture (top right) → **Settings**
3. Scroll down and click **Developer settings** (bottom of left sidebar)
4. Click **Personal access tokens** → **Tokens (classic)**
5. Click **Generate new token** → **Generate new token (classic)**
6. Give your token a descriptive name (e.g., "GitHub Scraper")
7. Select the following scopes:
   - `repo` (Full control of private repositories)
   - `public_repo` (Access public repositories)
8. Click **Generate token**
9. **Important**: Copy the token immediately - you won't be able to see it again!

## Usage

### Basic Usage

Scrape all repositories from a user:

```bash
python github_scraper.py USERNAME --token YOUR_GITHUB_TOKEN
```

### Python Module Usage

You can also import and use the scraper as a Python module:

```python
from github_scraper import GitHubScraper

# Create scraper instance
scraper = GitHubScraper(token='your_token_here')

# Scrape all repos for a user
scraper.scrape_user_repositories('username', output_dir='output')
```

See `example_usage.py` for a complete example.

### Using Environment Variable

You can set your GitHub token as an environment variable to avoid typing it each time:

**Linux/Mac:**
```bash
export GITHUB_TOKEN="your_github_token_here"
python github_scraper.py USERNAME
```

**Windows (Command Prompt):**
```cmd
set GITHUB_TOKEN=your_github_token_here
python github_scraper.py USERNAME
```

**Windows (PowerShell):**
```powershell
$env:GITHUB_TOKEN="your_github_token_here"
python github_scraper.py USERNAME
```

### Advanced Options

```bash
python github_scraper.py USERNAME [OPTIONS]
```

**Options:**

- `--token TOKEN`: GitHub personal access token (required if GITHUB_TOKEN env var not set)
- `--output DIR`: Output directory for scraped files (default: `output`)
- `--max-repos N`: Maximum number of repositories to scrape (default: all)
- `--max-retries N`: Maximum retry attempts for failed requests (default: 3)
- `--retry-delay N`: Delay in seconds between retry attempts (default: 5)
- `--debug`: Enable debug logging for detailed information

### Examples

**Scrape first 5 repositories:**
```bash
python github_scraper.py octocat --token YOUR_TOKEN --max-repos 5
```

**Custom output directory:**
```bash
python github_scraper.py octocat --token YOUR_TOKEN --output my_repos
```

**Enable debug logging:**
```bash
python github_scraper.py octocat --token YOUR_TOKEN --debug
```

**Scrape with custom retry settings:**
```bash
python github_scraper.py octocat --token YOUR_TOKEN --max-retries 5 --retry-delay 10
```

## Output

The scraper creates the following structure:

```
output/
├── username_repo1/
│   └── repo1_combined.txt
├── username_repo2/
│   └── repo2_combined.txt
└── ...
```

Each `*_combined.txt` file contains:
- Repository information header
- All code files from the repository
- Each file is clearly separated with headers showing the file path
- Only text-based code files are included (filters out binaries, images, etc.)

## Logging

The tool creates a `github_scraper.log` file in the current directory with detailed logs of the scraping process. This includes:
- API requests and responses
- Retry attempts
- Rate limit information
- File processing status
- Errors and warnings

## Supported File Extensions

The scraper automatically identifies and scrapes files with these extensions:

**Programming Languages:**
- Python (`.py`)
- JavaScript (`.js`, `.jsx`, `.ts`, `.tsx`)
- Java (`.java`)
- C/C++ (`.c`, `.cpp`, `.h`)
- C# (`.cs`)
- Go (`.go`)
- Rust (`.rs`)
- Ruby (`.rb`)
- PHP (`.php`)
- Swift (`.swift`)
- Kotlin (`.kt`)
- And many more...

**Web & Config Files:**
- HTML (`.html`)
- CSS (`.css`, `.scss`, `.sass`, `.less`)
- JSON (`.json`)
- YAML (`.yaml`, `.yml`)
- XML (`.xml`)
- Markdown (`.md`)
- Shell scripts (`.sh`, `.bash`)

## Error Handling

The scraper includes comprehensive error handling:

1. **Authentication Errors**: Validates token and provides clear error messages
2. **Rate Limiting**: Automatically waits when rate limits are reached
3. **Network Errors**: Retries failed requests with exponential backoff
4. **File Errors**: Gracefully handles files that cannot be decoded
5. **Missing Resources**: Handles repositories or files that no longer exist

## Rate Limits

GitHub API has rate limits:
- **Authenticated requests**: 5,000 requests per hour
- **Unauthenticated requests**: 60 requests per hour (not supported by this tool)

The scraper automatically:
- Monitors rate limit headers
- Waits when limits are reached
- Adds small delays between requests to avoid hitting limits

## Troubleshooting

### "Authentication failed" error
- Verify your token is correct
- Ensure your token has the required scopes (`repo` or `public_repo`)
- Check that the token hasn't expired

### "Rate limit exceeded" error
- The scraper will automatically wait, but if you hit limits frequently:
  - Reduce the number of repositories with `--max-repos`
  - Increase delays between requests (this is automatic)
  - Wait for your rate limit to reset (resets every hour)

### Files not being scraped
- Check that they have supported file extensions
- Verify the files exist in the repository
- Look at the log file for specific error messages

### Connection timeouts
- Check your internet connection
- Increase retry attempts with `--max-retries`
- Increase retry delay with `--retry-delay`

## Security Notes

- **Never commit your GitHub token to version control**
- Store tokens securely using environment variables or secret management tools
- Tokens should be treated like passwords
- You can revoke tokens anytime from GitHub settings
- Use tokens with minimum required permissions

## License

This tool is provided as-is for educational and personal use.

## Contributing

Feel free to submit issues or pull requests for improvements.

## Disclaimer

This tool makes requests to the GitHub API. Please:
- Respect GitHub's Terms of Service
- Use reasonable rate limiting
- Only scrape repositories you have permission to access
- Be mindful of private repositories and sensitive data
