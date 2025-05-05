# PaperChaser

A collection of tools for academic research publication scraping and analysis.

## FAS Publications Scraper

This tool scrapes the Federation of American Scientists (FAS) publications archive at [https://fas.org/publications-archive/](https://fas.org/publications-archive/) and saves publication URLs to a CSV file. The CSV is updated incrementally after each page is processed, providing resilience against network interruptions.

### About the FAS Archive

The FAS publications archive contains research papers, reports, and articles on national security, nuclear weapons policy, government secrecy, and related topics. The archive spans multiple pages with hundreds of publications.

### Requirements

- Python 3.6+
- Required packages: `requests`, `beautifulsoup4`, `pandas`

Install dependencies:

```bash
pip install requests beautifulsoup4 pandas
```

## Scripts

The project includes two main scripts:

1. `fas_url_scraper.py`: Scrapes publication URLs from the FAS archive
2. `fas_content_scraper.py`: Extracts titles and content from the publication URLs

### URL Scraper Usage

Basic usage:

```bash
python3 fas_url_scraper.py
```

This will:
1. Start scraping the FAS publications archive
2. Process up to 53 pages (configurable with `--max-pages`)
3. Add random delays between requests (2-5 seconds by default)
4. Save results to `fas_publications.csv` as each page is processed

### Content Scraper Usage

After running the URL scraper, use the content scraper to fetch titles and content:

```bash
python3 fas_content_scraper.py
```

This will:
1. Read URLs from `fas_publications.csv`
2. Visit each publication page and extract title and content
3. Add these as new columns to the CSV
4. Save progress regularly to handle interruptions

For polite scraping with longer delays between requests:

```bash
python3 fas_content_scraper.py --min-delay 5 --max-delay 10
```

This introduces a random delay of 5-10 seconds between requests, reducing server load.

#### Working with Large Datasets

The content scraper has two key parameters for working with large datasets:

- `--start`: The 0-based index position in the CSV to start processing from
- `--batch`: The number of URLs to process in a single run

##### Row-Based Processing

The `--start` parameter refers to the row index in the CSV file (0-based, excluding header row). This can be confusing, so here's a clear explanation:

- The CSV has a header row (row 1 in the file)
- Data begins at row 2 in the file
- Index 0 refers to the first data row (row 2 in the file)
- Index 79 refers to the 80th data row (row 81 in the file)

For example, if you have processed the first 29 rows (URLs) and want to continue from row 30:

```bash
python3 fas_content_scraper.py --start 29
```

This will start processing from the 30th URL in your CSV (index 29, which is row 31 in the file including the header) and continue until the end.

##### Batch Processing

To limit the number of URLs processed in a single run (useful for very large datasets), use the `--batch` parameter:

```bash
python3 fas_content_scraper.py --batch 20
```

This will process 20 URLs at a time, saving progress after each batch. 

##### Combining Parameters

You can combine multiple parameters to customize the scraping process:

```bash
python3 fas_content_scraper.py --start 30 --batch 50 --min-delay 4 --max-delay 8
```

This:
- Processes 50 URLs starting from index 30 (rows 31-80 in the CSV)
- Introduces a random delay of 4-8 seconds between requests
- Saves progress after completing the batch

### CSV Output Format

The initial CSV from the URL scraper contains:
- `URL`: The URL of the publication
- `Page`: The page number where the URL was found

After running the content scraper, it adds:
- `Title`: The title of the publication
- `Content`: The full text content of the publication

### Command Line Options

#### URL Scraper Options
- `--min-delay`: Minimum delay between requests in seconds (default: 2.0)
- `--max-delay`: Maximum delay between requests in seconds (default: 5.0)
- `--output`: Output CSV file name (default: 'fas_publications.csv')
- `--max-pages`: Maximum number of pages to scrape (default: 53)

#### Content Scraper Options
- `--input`: Input CSV file with URLs (default: 'fas_publications.csv')
- `--min-delay`: Minimum delay between requests in seconds (default: 3.0)
- `--max-delay`: Maximum delay between requests in seconds (default: 6.0)
- `--start`: Start processing from this row index in the CSV (0-based, default: 0)
- `--limit`: Limit processing to this many URLs (for testing) (default: None)
- `--batch`: Process URLs in batches of this size (default: None)

### Examples

#### URL Scraper Examples

Scrape with longer delays (more polite scraping):

```bash
python3 fas_url_scraper.py --min-delay 5 --max-delay 10
```

Scrape only the first 10 pages to a custom file:

```bash
python3 fas_url_scraper.py --output fas_first10.csv --max-pages 10
```

#### Content Scraper Examples

Extract content for a small batch of URLs:

```bash
python3 fas_content_scraper.py --input fas_first10.csv --limit 5
```

Process a large dataset in batches of 20 starting from the beginning:

```bash
python3 fas_content_scraper.py --batch 20
```

Resume content extraction from the 100th row (index 99):

```bash
python3 fas_content_scraper.py --start 99
```

Process URLs 200-299 (100 URLs starting at index 199):

```bash
python3 fas_content_scraper.py --start 199 --batch 100
```

Process URLs with longer delays between requests:

```bash
python3 fas_content_scraper.py --min-delay 5 --max-delay 12
```

Full example with all common parameters:

```bash
python3 fas_content_scraper.py --start 50 --batch 25 --min-delay 4 --max-delay 8 --input fas_publications.csv
```

### Notes

- Both scripts include polite scraping practices with random delays
- User-Agent identification is included in requests
- All publication URLs are deduplicated in the final collection
- The content scraper handles newlines and special characters properly for CSV
- CSVs are updated regularly after each batch, so interruptions won't lose much progress
- The full archive has 446 pages, but default is limited to 53 pages

### Troubleshooting

#### Missing Dependencies

If you see a `ModuleNotFoundError`, ensure all dependencies are installed:

```bash
pip install requests beautifulsoup4 pandas
```

#### Unprocessed URLs

If specific URLs aren't being processed by the content scraper (such as line 81, URL "https://fas.org/publication/creating-a-national-exposome-project/"), try running:

```bash
python3 fas_content_scraper.py --start X --limit 1
```

where X is the 0-based index of the problematic URL (e.g., 79 for row 81 in the file, since row 1 is the header and indexing starts at 0).

If a URL consistently fails to process, it may have a different HTML structure than what the content scraper is configured to handle. You can manually process these rare cases by:

1. Running the content scraper with debugging enabled:
   ```bash
   python3 -m pdb fas_content_scraper.py --start X --limit 1
   ```

2. Or examining the page structure with a manual request:
   ```bash
   curl https://problematic-url | less
   ```

3. Then update the selectors in the `extract_content` method if needed.
