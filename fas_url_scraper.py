#!/usr/bin/env python3
"""
FAS Publications Archive Scraper

This script scrapes the Federation of American Scientists (FAS) publications archive
at https://fas.org/publications-archive/ and extracts all publication URLs.
It includes proper rate limiting to avoid overloading the FAS website server.
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import re
import argparse
from urllib.parse import urljoin
import logging
import csv
import os


class FASPublicationScraper:
    """A scraper for FAS publications with rate limiting and pagination handling."""
    
    def __init__(self, base_url="https://fas.org/publications-archive/", 
                 min_delay=2, max_delay=5, output_file='fas_publications.csv'):
        """
        Initialize the scraper with configurable rate limiting.
        
        Args:
            base_url: The base URL for the FAS publications archive
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
            output_file: Path to the CSV output file
        """
        self.base_url = base_url
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.output_file = output_file
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FAS Publication Parser - Research Tool - Contact example@example.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger('FAS_Scraper')
        
        # Storage for all publication URLs
        self.publication_urls = []
        
        # Initialize CSV file with headers
        self._initialize_csv()
    
    def _initialize_csv(self):
        """Initialize the CSV file with headers if it doesn't exist."""
        # Always start with a fresh file to ensure headers are included
        with open(self.output_file, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['URL', 'Page'])
            self.logger.info(f"Initialized CSV file: {self.output_file}")
    
    def _append_to_csv(self, urls, page_num):
        """
        Append URLs to the CSV file with page number.
        
        Args:
            urls: List of URLs to append
            page_num: The page number these URLs were found on
        """
        with open(self.output_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            for url in urls:
                writer.writerow([url, page_num])
                
        # Create progress message with max_pages if available
        max_page_str = ""
        if hasattr(self, 'max_pages') and self.max_pages:
            max_page_str = f"/{self.max_pages}"
            
        self.logger.info(f"Added {len(urls)} URLs from page {page_num}{max_page_str} to {self.output_file}")
    
    def _random_delay(self):
        """Implement a random delay between requests to avoid overloading the server."""
        delay = random.uniform(self.min_delay, self.max_delay)
        self.logger.info(f"Waiting for {delay:.2f} seconds...")
        time.sleep(delay)
    
    def fetch_page(self, url):
        """
        Fetch a page with proper error handling and rate limiting.
        
        Args:
            url: The URL to fetch
            
        Returns:
            BeautifulSoup object of the page or None if fetch failed
        """
        self.logger.info(f"Fetching: {url}")
        try:
            self._random_delay()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_publications_from_page(self, soup):
        """
        Extract publication URLs from a page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            List of publication URLs found on the page
        """
        urls = []
        
        if not soup:
            return urls
            
        # Based on the observed structure of the FAS publications archive page
        for link in soup.find_all('a', href=True):
            href = link['href']
            full_url = href if href.startswith('http') else urljoin(self.base_url, href)
            
            # Pattern to ignore
            excluded_patterns = [
                'https://fas.org/publications/',
                'https://fas.org/publications-archive/'
            ]
            
            # Check if the URL contains /publication/ (singular) and doesn't match any excluded patterns
            if 'https://fas.org/publication/' in full_url:
                # Make sure it's not a match for any excluded patterns
                if not any(full_url.startswith(pattern) for pattern in excluded_patterns):
                    if full_url not in urls:
                        urls.append(full_url)
        
        self.logger.info(f"Found {len(urls)} publication URLs on page")
        return urls
    
    def find_next_page_link(self, soup):
        """
        Find the link to the next page of publications.
        
        Args:
            soup: BeautifulSoup object of the current page
            
        Returns:
            URL of the next page or None if not found
        """
        if not soup:
            return None
            
        # Debug current page content
        self.logger.info(f"Looking for pagination elements on current page")
            
        # First look specifically for the next page link
        # Look broadly for any elements that might be pagination controls
        pagination_wrappers = soup.find_all(['div', 'nav', 'ul'], class_=lambda x: x and any(
            term in str(x).lower() for term in ['pagination', 'pager', 'nav', 'page-numbers']
        ))
        
        for wrapper in pagination_wrappers:
            # Within these wrappers, look for links that might be "next page"
            next_links = wrapper.find_all('a', 
                string=lambda x: x and any(term in str(x).lower() for term in ['next', 'more', '»', '>', '→']),
                href=True
            )
            
            if next_links:
                next_url = urljoin(self.base_url, next_links[0]['href'])
                self.logger.info(f"Found next page link: {next_url}")
                return next_url
                
            # If no explicit next link, look for numbered page links
            page_links = wrapper.find_all('a', href=lambda href: href and ('page' in href or re.search(r'[?&]p=\d+', href)))
            
            if page_links:
                current_page = self._get_current_page_number()
                next_page = current_page + 1
                
                # Look for a link to the next page number
                for link in page_links:
                    page_match = re.search(r'/page/(\d+)|[?&]p=(\d+)', link['href'])
                    if page_match:
                        page_num = int(page_match.group(1) or page_match.group(2))
                        if page_num == next_page:
                            next_url = urljoin(self.base_url, link['href'])
                            self.logger.info(f"Found link to page {next_page}: {next_url}")
                            return next_url
        
        # If we couldn't find a next link, try to construct one
        current_page = self._get_current_page_number()
        next_page = current_page + 1
        
        # Try different URL patterns for next page
        possible_next_urls = [
            f"{self.base_url.rstrip('/')}/page/{next_page}/",
            f"{self.base_url}?paged={next_page}",
            f"{self.base_url}?page={next_page}",
            f"{self.base_url}?p={next_page}"
        ]
        
        self.logger.info(f"Trying constructed URLs for page {next_page}")
        return possible_next_urls[0]  # Return the first pattern (can be adjusted based on website)
    
    def _get_current_page_number(self):
        """Extract the current page number from the base URL or default to 1."""
        # Try different patterns for page number in URL
        patterns = [
            r'/page/(\d+)/?',
            r'[?&]p=(\d+)',
            r'[?&]page=(\d+)',
            r'[?&]paged=(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, self.base_url)
            if match:
                return int(match.group(1))
                
        return 1  # Default to page 1
    
    def scrape_all_publications(self, max_pages=None):
        """
        Scrape publications from the FAS publications archive.
        
        Args:
            max_pages: Maximum number of pages to scrape (None for all pages)
            
        Returns:
            List of all publication URLs found
        """
        # Store max_pages in the instance for access by other methods
        self.max_pages = max_pages
        
        current_url = self.base_url
        page_num = 1
        consecutive_empty_pages = 0
        max_empty_pages = 3  # Stop after 3 consecutive pages with no publications
        
        while current_url:
            max_page_str = f"/{max_pages}" if max_pages else ""
            self.logger.info(f"Processing page {page_num}{max_page_str}: {current_url}")
            soup = self.fetch_page(current_url)
            
            if not soup:
                self.logger.error(f"Failed to fetch page {page_num}{max_page_str}, stopping")
                break
                
            # Check if the page seems to be a valid publications page
            # Look for indicators like titles, section headings, etc.
            page_titles = soup.find_all(['h1', 'h2'], string=lambda s: s and 'publication' in s.lower())
            if not page_titles:
                self.logger.warning(f"Page {page_num} doesn't appear to have publication headings")
            
            # Extract publications from this page
            page_publications = self.extract_publications_from_page(soup)
            
            # Track consecutive empty pages
            if not page_publications:
                consecutive_empty_pages += 1
                self.logger.warning(f"Page {page_num} had no publications. Empty pages so far: {consecutive_empty_pages}/{max_empty_pages}")
                
                if consecutive_empty_pages >= max_empty_pages:
                    self.logger.warning(f"Reached {consecutive_empty_pages} consecutive pages with no publications, stopping")
                    break
            else:
                consecutive_empty_pages = 0  # Reset counter when we find publications
            
            # Add these URLs to our master list
            self.publication_urls.extend(page_publications)
            
            # Update the CSV file after each page is processed
            self._append_to_csv(page_publications, page_num)
            
            # Check if we've reached the maximum number of pages
            if max_pages and page_num >= max_pages:
                self.logger.info(f"Reached maximum number of pages ({page_num}/{max_pages}), stopping")
                break
                
            # Check if there's a next page
            next_page_url = self.find_next_page_link(soup)
            
            # If we didn't find a next page link, try adding /page/X to the base URL
            if not next_page_url and page_num == 1:
                next_page_url = f"{self.base_url.rstrip('/')}/page/2/"
                self.logger.info(f"Defaulting to standard page 2 URL: {next_page_url}")
                
            if next_page_url == current_url:
                self.logger.info("Next page URL is the same as current, stopping")
                break
                
            if not next_page_url:
                self.logger.info("No next page found, finished scraping")
                break
                
            current_url = next_page_url
            page_num += 1
        
        # Remove duplicates while preserving order
        self.publication_urls = list(dict.fromkeys(self.publication_urls))
        self.logger.info(f"Scraping complete. Found {len(self.publication_urls)} unique publication URLs")
        return self.publication_urls
    
    def save_to_file(self, filename='fas_publications.txt'):
        """
        Save the scraped publication URLs to a file.
        
        Args:
            filename: The name of the file to save the URLs to
        """
        with open(filename, 'w') as f:
            for url in self.publication_urls:
                f.write(f"{url}\n")
        self.logger.info(f"Saved {len(self.publication_urls)} URLs to {filename}")


def main():
    parser = argparse.ArgumentParser(description='Scrape publications from the FAS archive')
    parser.add_argument('--min-delay', type=float, default=2.0,
                        help='Minimum delay between requests in seconds')
    parser.add_argument('--max-delay', type=float, default=5.0,
                        help='Maximum delay between requests in seconds')
    parser.add_argument('--output', type=str, default='fas_publications.csv',
                        help='Output CSV file name')
    parser.add_argument('--max-pages', type=int, default=53,
                        help='Maximum number of pages to scrape (default: 53)')
    args = parser.parse_args()
    
    # Create the scraper with the output file
    scraper = FASPublicationScraper(
        min_delay=args.min_delay, 
        max_delay=args.max_delay,
        output_file=args.output
    )
    
    # Scrape publications (CSV file is updated after each page)
    scraper.scrape_all_publications(max_pages=args.max_pages)
    
    # Note: We don't need to save_to_file since we're writing to CSV during scraping


if __name__ == "__main__":
    main()
