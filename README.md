# PaperChaser

A collection of tools for academic research publication scraping and analysis.

## FAS Publications Scraper

This tool scrapes the Federation of American Scientists (FAS) publications archive at [https://fas.org/publications-archive/](https://fas.org/publications-archive/) and saves publication URLs to a CSV file. The CSV is updated incrementally after each page is processed, providing resilience against network interruptions.

### About the FAS Archive

The FAS publications archive contains research papers, reports, and articles on national security, nuclear weapons policy, government secrecy, and related topics. The archive spans multiple pages with hundreds of publications.

### Requirements

- Python 3.6+
- Required packages: `requests`, `beautifulsoup4`

Install dependencies:

```bash
pip install requests beautifulsoup4
```

### Usage

Basic usage:

```bash
python3 fas_scraper.py
```

This will:
1. Start scraping the FAS publications archive
2. Process up to 53 pages (configurable with `--max-pages`)
3. Add random delays between requests (2-5 seconds by default)
4. Save results to `fas_publications.csv` as each page is processed

### CSV Output Format

The CSV file contains:
- `URL`: The URL of the publication
- `Page`: The page number where the URL was found

The CSV file is continuously updated after each page is processed, so you can safely interrupt the script at any time without losing progress.

### Command Line Options

- `--min-delay`: Minimum delay between requests in seconds (default: 2.0)
- `--max-delay`: Maximum delay between requests in seconds (default: 5.0)
- `--output`: Output CSV file name (default: 'fas_publications.csv')
- `--max-pages`: Maximum number of pages to scrape (default: 53)

### Examples

Scrape with longer delays (more polite scraping):

```bash
python3 fas_scraper.py --min-delay 5 --max-delay 10
```

Scrape only the first 10 pages to a custom file:

```bash
python3 fas_scraper.py --output fas_first10.csv --max-pages 10
```

Resume a previous scrape (will append to existing CSV):

```bash
python3 fas_scraper.py --output my_existing_data.csv
```

### Notes

- The script includes polite scraping practices with random delays
- User-Agent identification is included in requests
- All publication URLs are deduplicated in the final collection
- CSV is updated after each page, so interruptions won't lose progress
- The full archive has 446 pages, but default is limited to 53 pages
