#!/usr/bin/env python3
"""
GitHub Repository Scraper

This script fetches and outputs the code from a user's GitHub repositories.
It uses the GitHub API to authenticate, list repositories, retrieve files,
and output the content in plain text format.

Features:
- GitHub API authentication using personal access token
- Pagination support for API calls
- Retry logic for failed requests
- Progress logging
- Output repository contents to plain text files
"""

import os
import sys
import time
import logging
import argparse
import requests
from typing import List, Dict, Optional, Any
from pathlib import Path
import base64


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('github_scraper.log')
    ]
)
logger = logging.getLogger(__name__)


class GitHubScraper:
    """
    A scraper class to fetch and output code from GitHub repositories.
    """
    
    def __init__(self, token: str, max_retries: int = 3, retry_delay: int = 5):
        """
        Initialize the GitHub scraper.
        
        Args:
            token: GitHub personal access token for authentication
            max_retries: Maximum number of retry attempts for failed requests
            retry_delay: Delay in seconds between retry attempts
        """
        self.token = token
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.base_url = "https://api.github.com"
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'GitHub-Scraper/1.0'
        })
        logger.info("GitHub scraper initialized")
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[requests.Response]:
        """
        Make an HTTP request with retry logic.
        
        Args:
            url: The URL to request
            params: Optional query parameters
            
        Returns:
            Response object if successful, None otherwise
        """
        for attempt in range(self.max_retries):
            try:
                logger.debug(f"Making request to {url} (attempt {attempt + 1}/{self.max_retries})")
                response = self.session.get(url, params=params, timeout=30)
                
                # Check rate limiting
                if response.status_code == 403 and 'rate limit' in response.text.lower():
                    reset_time = int(response.headers.get('X-RateLimit-Reset', 0))
                    current_time = int(time.time())
                    wait_time = max(reset_time - current_time, 60)
                    logger.warning(f"Rate limit exceeded. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                
                if response.status_code == 200:
                    return response
                elif response.status_code == 404:
                    logger.error(f"Resource not found: {url}")
                    return None
                elif response.status_code == 401:
                    logger.error("Authentication failed. Please check your token.")
                    return None
                else:
                    logger.warning(f"Request failed with status code {response.status_code}")
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error: {e} (attempt {attempt + 1}/{self.max_retries})")
            
            if attempt < self.max_retries - 1:
                logger.info(f"Retrying in {self.retry_delay} seconds...")
                time.sleep(self.retry_delay)
        
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        return None
    
    def get_user_repositories(self, username: str) -> List[Dict[str, Any]]:
        """
        Get all repositories for a given user with pagination support.
        
        Args:
            username: GitHub username
            
        Returns:
            List of repository dictionaries
        """
        logger.info(f"Fetching repositories for user: {username}")
        repositories = []
        page = 1
        per_page = 100  # Maximum allowed by GitHub API
        
        while True:
            url = f"{self.base_url}/users/{username}/repos"
            params = {
                'page': page,
                'per_page': per_page,
                'sort': 'updated',
                'type': 'all'
            }
            
            response = self._make_request(url, params)
            if not response:
                break
            
            repos = response.json()
            if not repos:
                break
            
            repositories.extend(repos)
            logger.info(f"Fetched page {page}: {len(repos)} repositories")
            
            # Check if there are more pages
            if len(repos) < per_page:
                break
            
            page += 1
            time.sleep(1)  # Be nice to the API
        
        logger.info(f"Total repositories found: {len(repositories)}")
        return repositories
    
    def get_repository_tree(self, owner: str, repo: str, branch: str = 'main') -> Optional[List[Dict]]:
        """
        Get the file tree of a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (default: 'main')
            
        Returns:
            List of file objects or None if failed
        """
        logger.info(f"Fetching file tree for {owner}/{repo} (branch: {branch})")
        
        # First, get the default branch if 'main' doesn't exist
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = self._make_request(url)
        if response:
            repo_data = response.json()
            branch = repo_data.get('default_branch', branch)
        
        # Get the tree recursively
        url = f"{self.base_url}/repos/{owner}/{repo}/git/trees/{branch}"
        params = {'recursive': '1'}
        response = self._make_request(url, params)
        
        if not response:
            return None
        
        tree_data = response.json()
        files = tree_data.get('tree', [])
        logger.info(f"Found {len(files)} items in repository tree")
        return files
    
    def get_file_content(self, owner: str, repo: str, path: str) -> Optional[str]:
        """
        Get the content of a specific file.
        
        Args:
            owner: Repository owner
            repo: Repository name
            path: File path in the repository
            
        Returns:
            File content as string or None if failed
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/contents/{path}"
        response = self._make_request(url)
        
        if not response:
            return None
        
        try:
            data = response.json()
            if data.get('type') == 'file':
                content = data.get('content', '')
                if content:
                    # Decode base64 content
                    decoded_content = base64.b64decode(content).decode('utf-8', errors='ignore')
                    return decoded_content
        except Exception as e:
            logger.error(f"Error decoding file content: {e}")
        
        return None
    
    def scrape_repository(self, owner: str, repo: str, output_dir: str) -> bool:
        """
        Scrape all files from a repository and save to output directory.
        
        Args:
            owner: Repository owner
            repo: Repository name
            output_dir: Directory to save output files
            
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Scraping repository: {owner}/{repo}")
        
        # Create output directory
        repo_output_dir = Path(output_dir) / f"{owner}_{repo}"
        repo_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Get repository tree
        files = self.get_repository_tree(owner, repo)
        if not files:
            logger.error(f"Failed to get file tree for {owner}/{repo}")
            return False
        
        # Filter only code files (ignore binaries, images, etc.)
        code_extensions = {
            '.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.go', '.rs',
            '.rb', '.php', '.swift', '.kt', '.ts', '.tsx', '.jsx', '.vue',
            '.html', '.css', '.scss', '.sass', '.less', '.sql', '.sh',
            '.bash', '.yaml', '.yml', '.json', '.xml', '.md', '.txt',
            '.r', '.R', '.m', '.scala', '.pl', '.pm', '.lua'
        }
        
        code_files = [
            f for f in files 
            if f['type'] == 'blob' and any(f['path'].endswith(ext) for ext in code_extensions)
        ]
        
        logger.info(f"Found {len(code_files)} code files to scrape")
        
        # Create a combined output file
        combined_output = repo_output_dir / f"{repo}_combined.txt"
        successful_files = 0
        failed_files = 0
        
        with open(combined_output, 'w', encoding='utf-8') as outfile:
            outfile.write(f"Repository: {owner}/{repo}\n")
            outfile.write(f"{'=' * 80}\n\n")
            
            for idx, file_info in enumerate(code_files, 1):
                file_path = file_info['path']
                logger.info(f"[{idx}/{len(code_files)}] Fetching: {file_path}")
                
                content = self.get_file_content(owner, repo, file_path)
                
                if content:
                    outfile.write(f"\n{'=' * 80}\n")
                    outfile.write(f"File: {file_path}\n")
                    outfile.write(f"{'=' * 80}\n\n")
                    outfile.write(content)
                    outfile.write("\n\n")
                    successful_files += 1
                else:
                    logger.warning(f"Failed to fetch: {file_path}")
                    failed_files += 1
                
                # Add a small delay to avoid rate limiting
                time.sleep(0.5)
        
        logger.info(f"Repository scraping complete: {successful_files} files successful, {failed_files} failed")
        logger.info(f"Output saved to: {combined_output}")
        return True
    
    def scrape_user_repositories(self, username: str, output_dir: str = "output", 
                                 max_repos: Optional[int] = None) -> None:
        """
        Scrape all repositories for a user.
        
        Args:
            username: GitHub username
            output_dir: Directory to save output files
            max_repos: Maximum number of repositories to scrape (None for all)
        """
        logger.info(f"Starting scrape for user: {username}")
        
        # Get all repositories
        repositories = self.get_user_repositories(username)
        
        if not repositories:
            logger.error(f"No repositories found for user: {username}")
            return
        
        # Limit number of repositories if specified
        if max_repos:
            repositories = repositories[:max_repos]
            logger.info(f"Limited to {max_repos} repositories")
        
        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Scrape each repository
        successful = 0
        failed = 0
        
        for idx, repo in enumerate(repositories, 1):
            repo_name = repo['name']
            repo_owner = repo['owner']['login']
            
            logger.info(f"\n[{idx}/{len(repositories)}] Processing repository: {repo_owner}/{repo_name}")
            
            if self.scrape_repository(repo_owner, repo_name, output_dir):
                successful += 1
            else:
                failed += 1
            
            # Add delay between repositories
            time.sleep(2)
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Scraping complete!")
        logger.info(f"Total repositories: {len(repositories)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Output directory: {output_dir}")
        logger.info(f"{'=' * 80}")


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description='GitHub Repository Scraper - Fetch and output code from GitHub repositories'
    )
    parser.add_argument(
        'username',
        help='GitHub username to scrape repositories from'
    )
    parser.add_argument(
        '--token',
        help='GitHub personal access token (or set GITHUB_TOKEN environment variable)',
        default=os.environ.get('GITHUB_TOKEN')
    )
    parser.add_argument(
        '--output',
        default='output',
        help='Output directory for scraped files (default: output)'
    )
    parser.add_argument(
        '--max-repos',
        type=int,
        help='Maximum number of repositories to scrape (default: all)'
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help='Maximum number of retry attempts for failed requests (default: 3)'
    )
    parser.add_argument(
        '--retry-delay',
        type=int,
        default=5,
        help='Delay in seconds between retry attempts (default: 5)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Check for token
    if not args.token:
        logger.error("GitHub token is required. Provide via --token or GITHUB_TOKEN environment variable")
        sys.exit(1)
    
    # Create scraper instance
    scraper = GitHubScraper(
        token=args.token,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay
    )
    
    # Start scraping
    try:
        scraper.scrape_user_repositories(
            username=args.username,
            output_dir=args.output,
            max_repos=args.max_repos
        )
    except KeyboardInterrupt:
        logger.info("\nScraping interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
