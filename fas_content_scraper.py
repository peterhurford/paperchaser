#!/usr/bin/env python3
"""
FAS Publications Content Scraper

This script reads URLs from the fas_publications.csv file and extracts title and content
from each URL, then adds these as new columns to the CSV.
"""

import requests
from bs4 import BeautifulSoup
import time
import random
import csv
import os
import logging
import pandas as pd
from urllib.parse import urljoin

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FAS_Content_Scraper')

class FASContentScraper:
    """Scraper for extracting content from FAS publication pages."""
    
    def __init__(self, csv_file='fas_publications.csv', min_delay=3, max_delay=6):
        """
        Initialize the content scraper.
        
        Args:
            csv_file: Path to the CSV file containing publication URLs
            min_delay: Minimum delay between requests in seconds
            max_delay: Maximum delay between requests in seconds
        """
        self.csv_file = csv_file
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FAS Publication Content Parser - Research Tool - Contact example@example.com',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        
    def _random_delay(self):
        """Implement a random delay between requests to avoid overloading the server."""
        delay = random.uniform(self.min_delay, self.max_delay)
        logger.info(f"Waiting for {delay:.2f} seconds...")
        time.sleep(delay)
    
    def fetch_page(self, url):
        """
        Fetch a page with proper error handling and rate limiting.
        
        Args:
            url: The URL to fetch
            
        Returns:
            BeautifulSoup object of the page or None if fetch failed
        """
        logger.info(f"Fetching: {url}")
        try:
            self._random_delay()
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
    
    def extract_content(self, soup):
        """
        Extract title and content from a publication page.
        
        Args:
            soup: BeautifulSoup object of the page
            
        Returns:
            Tuple of (title, content) or (None, None) if extraction failed
        """
        if not soup:
            return None, None
        
        try:
            # Extract title - adjust selectors based on the actual page structure
            title_element = soup.find('h1')
            title = title_element.get_text().strip() if title_element else "No Title Found"
            
            # Clean the title - remove newlines, multiple spaces, etc.
            title = ' '.join(title.split())
            
            # Extract content - adjust selectors based on the actual page structure
            # Looking for the main content area which might be in a div with a specific class
            content_element = soup.find('article') or soup.find('div', class_='content') or soup.find('div', class_='post-content')
            
            if content_element:
                # Get all paragraphs and headings within the content
                content_parts = []
                for element in content_element.find_all(['p', 'h2', 'h3', 'h4', 'ul', 'ol']):
                    # Skip elements that appear to be navigation, metadata, etc.
                    if not any(cls in str(element.get('class', [])) for cls in ['navigation', 'meta', 'author', 'date']):
                        content_parts.append(element.get_text().strip())
                
                content = " ".join(content_parts)
            else:
                # Fallback: get all paragraphs on the page
                paragraphs = soup.find_all('p')
                content = " ".join(p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 50)
            
            # Clean up content - replace newlines, tabs, etc with spaces
            content = content.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
            # Remove multiple spaces
            while '  ' in content:
                content = content.replace('  ', ' ')
                
            return title, content
        
        except Exception as e:
            logger.error(f"Error extracting content: {e}")
            return None, None
    
    def process_publications(self, start_index=0, limit=None):
        """
        Process all publications in the CSV file and add title and content.
        
        Args:
            start_index: Index to start processing from (useful for resuming)
            limit: Maximum number of URLs to process (useful for testing)
        """
        try:
            # Read the CSV file into a pandas DataFrame
            df = pd.read_csv(self.csv_file)
            
            # Check if the required columns exist
            if 'Title' not in df.columns:
                df['Title'] = None
            if 'Content' not in df.columns:
                df['Content'] = None
            
            # Calculate end index based on limit if provided
            end_index = min(start_index + limit, len(df)) if limit else len(df)
            logger.info(f"Processing URLs from index {start_index} to {end_index-1} (total: {end_index-start_index})")
            
            # Process each row
            for index in range(start_index, end_index):
                row = df.iloc[index]
                url = row['URL']
                
                # Skip already processed URLs
                if pd.notna(row['Title']) and pd.notna(row['Content']):
                    logger.info(f"Skipping already processed URL [{index+1}/{end_index}]: {url}")
                    continue
                
                try:
                    # Fetch and extract content
                    soup = self.fetch_page(url)
                    title, content = self.extract_content(soup)
                    
                    # Update the DataFrame
                    if title and content:
                        df.at[index, 'Title'] = title
                        df.at[index, 'Content'] = content
                        logger.info(f"Successfully processed URL [{index+1}/{end_index}]: {url}")
                    else:
                        logger.warning(f"Failed to extract content from URL [{index+1}/{end_index}]: {url}")
                        
                    # Save after each successful extraction or every 5 publications
                    if index % 5 == 0 or index == end_index - 1:
                        # Save with proper CSV handling to avoid issues with newlines
                        df.to_csv(self.csv_file, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')
                        logger.info(f"Saved progress to {self.csv_file}")
                        
                except Exception as e:
                    logger.error(f"Error processing URL {url}: {e}")
                    # Continue with next URL instead of failing the entire process
                    continue
            
            # Final save
            df.to_csv(self.csv_file, index=False, quoting=csv.QUOTE_ALL, escapechar='\\')
            logger.info(f"Completed processing {end_index - start_index} URLs")
            
        except Exception as e:
            logger.error(f"Error processing publications: {e}")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Extract content from FAS publication URLs')
    parser.add_argument('--input', type=str, default='fas_publications.csv',
                        help='Input CSV file with URLs')
    parser.add_argument('--min-delay', type=float, default=3.0,
                        help='Minimum delay between requests in seconds')
    parser.add_argument('--max-delay', type=float, default=6.0,
                        help='Maximum delay between requests in seconds')
    parser.add_argument('--start', type=int, default=0,
                        help='Start processing from this index (for resuming)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Limit processing to this many URLs (for testing)')
    parser.add_argument('--batch', type=int, default=None,
                        help='Process URLs in batches of this size')
    args = parser.parse_args()
    
    # Create the content scraper
    scraper = FASContentScraper(
        csv_file=args.input,
        min_delay=args.min_delay, 
        max_delay=args.max_delay
    )
    
    # Process the publications
    if args.batch:
        # Read the CSV to determine total records
        df = pd.read_csv(args.input)
        total = len(df)
        
        start_index = args.start
        while start_index < total:
            end_index = min(start_index + args.batch, total)
            logger.info(f"Processing batch from {start_index} to {end_index-1} (batch size: {args.batch})")
            scraper.process_publications(start_index=start_index, limit=args.batch)
            start_index += args.batch
    else:
        # Process publications normally
        scraper.process_publications(start_index=args.start, limit=args.limit)

if __name__ == "__main__":
    main()