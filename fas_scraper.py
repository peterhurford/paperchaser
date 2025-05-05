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
        file_exists = os.path.isfile(self.output_file)
        
        with open(self.output_file, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            if not file_exists:
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
            # Match only publication URLs - FIXED REGEX
            if re.match(r'https://fas\.org/publication/[^/]+/?$', href):
                if href not in urls:
                    urls.append(href)
        
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
            
        # Look for pagination links - might be 'Next' or a number
        pagination_elements = soup.find_all('a', class_=lambda x: x and ('pagination' in x or 'next' in x.lower()))
        
        for element in pagination_elements:
            text = element.get_text().lower()
            if 'next' in text or '»' in text:
                return urljoin(self.base_url, element['href'])
        
        # Alternative approach: look for page numbers and find the highest one
        page_links = soup.find_all('a', href=lambda href: href and 'page' in href)
        highest_page = 0
        next_page_url = None
        
        for link in page_links:
            match = re.search(r'/page/(\d+)/?', link['href'])
            if match:
                page_num = int(match.group(1))
                if page_num > highest_page:
                    highest_page = page_num
                    next_page_url = link['href']
        
        if highest_page > 0:
            # Check if we're already on this page
            current_page_match = re.search(r'/page/(\d+)/?', self.base_url)
            current_page = int(current_page_match.group(1)) if current_page_match else 1
            
            if highest_page > current_page:
                return urljoin(self.base_url, next_page_url)
        
        return None
    
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
        
        while current_url:
            max_page_str = f"/{max_pages}" if max_pages else ""
            self.logger.info(f"Processing page {page_num}{max_page_str}")
            soup = self.fetch_page(current_url)
            
            if not soup:
                self.logger.error(f"Failed to fetch page {page_num}{max_page_str}, stopping")
                break
                
            # Extract publications from this page
            page_publications = self.extract_publications_from_page(soup)
            
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
