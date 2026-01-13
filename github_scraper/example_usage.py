#!/usr/bin/env python3
"""
Example usage of the GitHub scraper

This example demonstrates basic usage of the github_scraper module.
"""

import os
from github_scraper import GitHubScraper

def main():
    # Get token from environment variable
    token = os.environ.get('GITHUB_TOKEN')
    
    if not token:
        print("Error: Please set GITHUB_TOKEN environment variable")
        print("Example: export GITHUB_TOKEN='your_token_here'")
        return
    
    # Create scraper instance
    scraper = GitHubScraper(
        token=token,
        max_retries=3,
        retry_delay=5
    )
    
    # Example 1: Get repositories for a user
    username = "octocat"  # Replace with actual username
    print(f"Fetching repositories for user: {username}")
    
    repos = scraper.get_user_repositories(username)
    print(f"\nFound {len(repos)} repositories:")
    
    for repo in repos[:5]:  # Show first 5
        print(f"  - {repo['name']} ({repo['language']}) - {repo['stargazers_count']} stars")
    
    # Example 2: Scrape a specific repository
    if repos:
        first_repo = repos[0]
        owner = first_repo['owner']['login']
        repo_name = first_repo['name']
        
        print(f"\nScraping repository: {owner}/{repo_name}")
        scraper.scrape_repository(owner, repo_name, "example_output")
        print("Done! Check the 'example_output' directory")

if __name__ == "__main__":
    main()
