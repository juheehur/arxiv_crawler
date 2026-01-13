import requests
from bs4 import BeautifulSoup
import re
import json
import time
import logging
import os
from datetime import datetime
from requests.exceptions import RequestException, Timeout, ConnectionError
import pandas as pd
from collections import Counter

# Set User-Agent header
headers = {
    'User-Agent': 'Educational Crawler (contact: emily.hur.juhee@gmail.com)'
}

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log'),
        logging.StreamHandler()
    ]
)


def extract_paper_info(url):
    """
    Extract all paper information from arxiv.org page.
    
    Args:
        url: ArXiv paper URL (e.g., https://arxiv.org/abs/2301.00001)
    
    Returns:
        dict: Dictionary containing paper information
    """
    # Extract arxiv_id from URL
    arxiv_id_match = re.search(r'abs/(\d{4}\.\d{4,5})', url)
    if not arxiv_id_match:
        return {'error': 'Invalid ArXiv URL format', 'url': url}
    
    arxiv_id = arxiv_id_match.group(1)
    
    try:
        # Make HTTP request with timeout
        response = requests.get(url, headers=headers, timeout=30)
        
        # Handle HTTP errors
        if response.status_code == 404:
            return {'error': 'Paper not found (404)', 'arxiv_id': arxiv_id, 'url': url}
        elif response.status_code == 500:
            return {'error': 'Server error (500)', 'arxiv_id': arxiv_id, 'url': url}
        elif response.status_code != 200:
            return {'error': f'HTTP {response.status_code}', 'arxiv_id': arxiv_id, 'url': url}
        
        # Parse HTML with BeautifulSoup
        try:
            soup = BeautifulSoup(response.content, 'lxml')
        except Exception as e:
            return {'error': f'Parsing error: {str(e)}', 'arxiv_id': arxiv_id, 'url': url}
        
        # Extract title
        title_tag = soup.find('h1', class_='title')
        title = title_tag.get_text(strip=True) if title_tag else None
        if title and title.startswith('Title:'):
            title = title.replace('Title:', '').strip()
        
        # Extract authors
        authors_div = soup.find('div', class_='authors')
        authors = []
        if authors_div:
            author_tags = authors_div.find_all('a')
            authors = [author.get_text(strip=True) for author in author_tags]
        
        # Extract abstract
        abstract_tag = soup.find('blockquote', class_='abstract')
        abstract = None
        if abstract_tag:
            abstract_text = abstract_tag.get_text(strip=True)
            # Remove "Abstract:" prefix if present
            if abstract_text.startswith('Abstract:'):
                abstract_text = abstract_text.replace('Abstract:', '').strip()
            abstract = abstract_text
        
        # Extract submitted date
        dateline_div = soup.find('div', class_='dateline')
        submitted_date = None
        if dateline_div:
            submitted_date = dateline_div.get_text(strip=True)
        
        # Extract categories (primary subject)
        category_tag = soup.find('span', class_='primary-subject')
        categories = None
        if category_tag:
            categories = category_tag.get_text(strip=True)
        
        # Generate PDF URL
        pdf_url = f'https://arxiv.org/pdf/{arxiv_id}.pdf'
        
        # Return dictionary
        return {
            'arxiv_id': arxiv_id,
            'title': title,
            'authors': authors,
            'abstract': abstract,
            'submitted_date': submitted_date,
            'categories': categories,
            'pdf_url': pdf_url
        }
    
    except Timeout:
        return {'error': 'Request timeout', 'arxiv_id': arxiv_id, 'url': url}
    except ConnectionError:
        return {'error': 'Connection error', 'arxiv_id': arxiv_id, 'url': url}
    except RequestException as e:
        return {'error': f'Network error: {str(e)}', 'arxiv_id': arxiv_id, 'url': url}
    except Exception as e:
        return {'error': f'Unexpected error: {str(e)}', 'arxiv_id': arxiv_id, 'url': url}


def print_paper_info(paper_info):
    """
    Pretty print paper information.
    
    Args:
        paper_info: Dictionary containing paper information
    """
    if 'error' in paper_info:
        print(f"Error: {paper_info['error']}")
        return
    
    print("=" * 80)
    print("ARXIV PAPER INFORMATION")
    print("=" * 80)
    print(f"\nArXiv ID: {paper_info['arxiv_id']}")
    print(f"Title: {paper_info['title']}")
    print(f"\nAuthors:")
    for i, author in enumerate(paper_info['authors'], 1):
        print(f"  {i}. {author}")
    print(f"\nCategories: {paper_info['categories']}")
    print(f"Submitted Date: {paper_info['submitted_date']}")
    print(f"\nAbstract:")
    if paper_info['abstract']:
        # Wrap abstract text for better readability
        abstract_lines = paper_info['abstract'].split('. ')
        for line in abstract_lines:
            print(f"  {line.strip()}")
    print(f"\nPDF URL: {paper_info['pdf_url']}")
    print("=" * 80)


def collect_arxiv_ids_from_category(category_url):
    """
    Collect arXiv IDs from a category listing page.
    
    Args:
        category_url: ArXiv category listing URL (e.g., https://arxiv.org/list/cs.AI/recent)
    
    Returns:
        list: List of arXiv IDs (strings)
    """
    arxiv_ids = []
    
    try:
        logging.info(f"Fetching category page: {category_url}")
        response = requests.get(category_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            logging.error(f"Failed to fetch category page: HTTP {response.status_code}")
            return []
        
        # Parse HTML with BeautifulSoup
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Find all dt tags
        dt_tags = soup.find_all('dt')
        
        logging.info(f"Found {len(dt_tags)} dt tags")
        
        # Extract arXiv IDs from dt tags
        # Pattern: "arXiv:2301.00001" or "arXiv:2301.00001v1"
        pattern = r'arxiv:(\d{4}\.\d{4,5}(?:v\d+)?)'
        
        for dt in dt_tags:
            text = dt.get_text()
            # Search for arXiv ID pattern (case-insensitive)
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Remove version suffix if present (e.g., "2301.00001v1" -> "2301.00001")
                arxiv_id = match.split('v')[0]
                if arxiv_id not in arxiv_ids:
                    arxiv_ids.append(arxiv_id)
        
        logging.info(f"Collected {len(arxiv_ids)} unique arXiv IDs")
        return arxiv_ids
    
    except Timeout:
        logging.error("Request timeout while fetching category page")
        return []
    except ConnectionError:
        logging.error("Connection error while fetching category page")
        return []
    except RequestException as e:
        logging.error(f"Network error: {str(e)}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error: {str(e)}")
        return []


def crawl_multiple_papers(urls, delay=15):
    """
    Crawl multiple ArXiv papers with safe rate limiting and error handling.
    
    Args:
        urls: List of ArXiv paper URLs
        delay: Delay in seconds between requests (default: 15)
    
    Returns:
        list: List of dictionaries containing paper information
    """
    results = []
    total = len(urls)
    
    logging.info(f"Starting crawl of {total} papers with {delay}s delay between requests")
    
    for idx, url in enumerate(urls, 1):
        # Calculate remaining time
        remaining_papers = total - idx
        estimated_time_remaining = remaining_papers * delay
        
        print(f"\n[{idx}/{total}] Processing: {url}")
        print(f"Estimated time remaining: {estimated_time_remaining // 60:.0f}m {estimated_time_remaining % 60:.0f}s")
        
        # Log the crawl attempt
        logging.info(f"[{idx}/{total}] Crawling: {url}")
        
        # Extract paper info
        paper_info = extract_paper_info(url)
        
        # Check for errors
        if 'error' in paper_info:
            error_msg = f"Error for {paper_info.get('arxiv_id', 'unknown')}: {paper_info['error']}"
            print(f"  ❌ {error_msg}")
            logging.error(error_msg)
            results.append(paper_info)
        else:
            print(f"  ✅ Successfully extracted: {paper_info.get('title', 'N/A')[:50]}...")
            logging.info(f"Successfully crawled: {paper_info.get('arxiv_id')} - {paper_info.get('title', 'N/A')[:50]}")
            results.append(paper_info)
        
        # Wait before next request (except for the last one)
        if idx < total:
            print(f"  Waiting {delay} seconds before next request...")
            time.sleep(delay)
    
    # Summary
    successful = sum(1 for r in results if 'error' not in r)
    failed = total - successful
    
    print(f"\n{'='*80}")
    print(f"CRAWL SUMMARY")
    print(f"{'='*80}")
    print(f"Total papers: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"{'='*80}")
    
    logging.info(f"Crawl completed: {successful}/{total} successful, {failed} failed")
    
    return results


def main_crawl_category(category_url, output_csv='arxiv_papers.csv', delay=15, max_papers=None):
    """
    Main function to collect arXiv IDs from a category and crawl all papers.
    Supports duplicate detection by checking existing CSV file.
    
    Args:
        category_url: ArXiv category listing URL (e.g., https://arxiv.org/list/cs.AI/recent)
        output_csv: Output CSV filename (default: 'arxiv_papers.csv')
        delay: Delay in seconds between requests (default: 15)
        max_papers: Maximum number of papers to crawl (None for all)
    
    Returns:
        pd.DataFrame: DataFrame containing all paper information
    """
    print("=" * 80)
    print("ARXIV CATEGORY CRAWLER")
    print("=" * 80)
    
    # Step 0: Check for existing CSV file and load existing arxiv_ids
    existing_df = pd.DataFrame()
    existing_arxiv_ids = set()
    
    if os.path.exists(output_csv):
        try:
            print(f"\n[Step 0] Reading existing CSV file: {output_csv}")
            existing_df = pd.read_csv(output_csv, encoding='utf-8')
            if 'arxiv_id' in existing_df.columns:
                existing_arxiv_ids = set(existing_df['arxiv_id'].astype(str).dropna().unique())
                print(f"✅ Found {len(existing_arxiv_ids)} existing papers in {output_csv}")
            else:
                print(f"⚠️  CSV file exists but 'arxiv_id' column not found. Starting fresh.")
                existing_df = pd.DataFrame()
                existing_arxiv_ids = set()
        except Exception as e:
            print(f"⚠️  Error reading existing CSV: {str(e)}. Starting fresh.")
            logging.warning(f"Error reading existing CSV: {str(e)}")
            existing_df = pd.DataFrame()
            existing_arxiv_ids = set()
    else:
        print(f"\n[Step 0] No existing CSV file found. Starting fresh.")
    
    # Step 1: Collect arXiv IDs
    print(f"\n[Step 1] Collecting arXiv IDs from: {category_url}")
    arxiv_ids = collect_arxiv_ids_from_category(category_url)
    
    if not arxiv_ids:
        print("❌ No arXiv IDs found. Exiting.")
        return existing_df if not existing_df.empty else pd.DataFrame()
    
    print(f"✅ Collected {len(arxiv_ids)} arXiv IDs")
    
    # Limit number of papers if specified
    if max_papers and max_papers < len(arxiv_ids):
        arxiv_ids = arxiv_ids[:max_papers]
        print(f"📝 Limiting to first {max_papers} papers")
    
    # Step 2: Filter out existing papers
    print(f"\n[Step 2] Checking for duplicates...")
    new_arxiv_ids = [aid for aid in arxiv_ids if aid not in existing_arxiv_ids]
    skipped_count = len(arxiv_ids) - len(new_arxiv_ids)
    
    if skipped_count > 0:
        print(f"⏭️  {len(arxiv_ids)}개 중 {skipped_count}개는 이미 있어서 건너뜀")
        logging.info(f"Skipping {skipped_count} duplicate papers out of {len(arxiv_ids)}")
    
    if not new_arxiv_ids:
        print("✅ 모든 논문이 이미 저장되어 있습니다. 새로운 크롤링이 필요하지 않습니다.")
        logging.info("All papers already exist in CSV. No new crawling needed.")
        return existing_df
    
    print(f"🆕 {len(new_arxiv_ids)}개의 새로운 논문을 크롤링합니다.")
    
    # Step 3: Convert new IDs to URLs
    print(f"\n[Step 3] Converting new IDs to URLs...")
    urls = [f'https://arxiv.org/abs/{arxiv_id}' for arxiv_id in new_arxiv_ids]
    
    # Step 4: Crawl new papers
    print(f"\n[Step 4] Crawling {len(urls)} new papers...")
    results = crawl_multiple_papers(urls, delay=delay)
    
    # Step 5: Convert to DataFrame
    print(f"\n[Step 5] Converting results to DataFrame...")
    
    # Prepare data for DataFrame
    df_data = []
    for result in results:
        if 'error' not in result:
            # Convert authors list to string
            authors_str = ', '.join(result.get('authors', []))
            
            df_data.append({
                'arxiv_id': result.get('arxiv_id'),
                'title': result.get('title'),
                'authors': authors_str,
                'abstract': result.get('abstract'),
                'submitted_date': result.get('submitted_date'),
                'categories': result.get('categories'),
                'pdf_url': result.get('pdf_url')
            })
        else:
            # Include failed papers with error info
            df_data.append({
                'arxiv_id': result.get('arxiv_id', 'unknown'),
                'title': None,
                'authors': None,
                'abstract': None,
                'submitted_date': None,
                'categories': None,
                'pdf_url': None,
                'error': result.get('error')
            })
    
    new_df = pd.DataFrame(df_data)
    
    # Step 6: Combine existing and new data
    print(f"\n[Step 6] Combining existing and new data...")
    if not existing_df.empty:
        # Ensure both DataFrames have the same columns
        all_columns = set(existing_df.columns) | set(new_df.columns)
        for col in all_columns:
            if col not in existing_df.columns:
                existing_df[col] = None
            if col not in new_df.columns:
                new_df[col] = None
        
        # Combine DataFrames
        df = pd.concat([existing_df, new_df], ignore_index=True)
        print(f"✅ Combined: {len(existing_df)} existing + {len(new_df)} new = {len(df)} total")
    else:
        df = new_df
        print(f"✅ New data: {len(df)} papers")
    
    # Step 7: Save to CSV
    print(f"\n[Step 7] Saving to CSV: {output_csv}")
    df.to_csv(output_csv, index=False, encoding='utf-8')
    print(f"✅ Saved {len(df)} papers to {output_csv}")
    
    # Print summary
    successful = len(new_df[new_df['title'].notna()]) if not new_df.empty else 0
    failed = len(new_df) - successful if not new_df.empty else 0
    
    print(f"\n{'='*80}")
    print("FINAL SUMMARY")
    print(f"{'='*80}")
    print(f"Total papers in CSV: {len(df)}")
    print(f"  - Existing: {len(existing_arxiv_ids)}")
    print(f"  - Newly crawled: {len(new_df)}")
    print(f"    * Successful: {successful}")
    print(f"    * Failed: {failed}")
    print(f"  - Skipped (duplicates): {skipped_count}")
    print(f"Output file: {output_csv}")
    print(f"{'='*80}")
    
    logging.info(f"Main crawl completed: {successful}/{len(new_df)} new papers successful, {skipped_count} skipped, {len(df)} total in CSV")
    
    return df


def show_statistics(df):
    """
    Display statistics about the crawled papers.
    
    Args:
        df: DataFrame containing paper information
    """
    if df.empty:
        print("No data to analyze.")
        return
    
    # Filter out papers with errors
    valid_df = df[df['title'].notna()].copy()
    
    if valid_df.empty:
        print("No valid papers to analyze.")
        return
    
    print("\n" + "=" * 80)
    print("STATISTICS")
    print("=" * 80)
    
    # 1. 총 논문 수
    total_papers = len(valid_df)
    print(f"\n📊 총 논문 수: {total_papers}개")
    
    # 2. 저자 수 평균
    author_counts = []
    for authors_str in valid_df['authors'].dropna():
        if authors_str:
            # Count authors by splitting on comma
            authors_list = [a.strip() for a in str(authors_str).split(',') if a.strip()]
            author_counts.append(len(authors_list))
    
    if author_counts:
        avg_authors = sum(author_counts) / len(author_counts)
        print(f"👥 저자 수 평균: {avg_authors:.2f}명")
        print(f"   (최소: {min(author_counts)}명, 최대: {max(author_counts)}명)")
    else:
        print("👥 저자 수 평균: 데이터 없음")
    
    # 3. 가장 많이 나온 키워드
    # Extract keywords from titles and abstracts
    all_text = []
    for _, row in valid_df.iterrows():
        text_parts = []
        if pd.notna(row.get('title')):
            text_parts.append(str(row['title']).lower())
        if pd.notna(row.get('abstract')):
            text_parts.append(str(row['abstract']).lower())
        all_text.extend(text_parts)
    
    if all_text:
        # Combine all text
        combined_text = ' '.join(all_text)
        
        # Extract words (alphanumeric, at least 3 characters)
        words = re.findall(r'\b[a-z]{3,}\b', combined_text)
        
        # Common stop words to exclude
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'its', 'may', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use', 'this', 'that', 'with', 'from', 'have', 'been', 'more', 'than', 'their', 'would', 'there', 'these', 'other', 'which', 'could', 'should', 'about', 'after', 'before', 'during', 'while', 'where', 'when', 'what', 'will', 'into', 'onto', 'upon', 'over', 'under', 'through', 'between', 'among', 'within', 'without', 'throughout', 'toward', 'towards', 'against', 'during', 'within', 'without', 'throughout'
        }
        
        # Filter out stop words and short words
        meaningful_words = [w for w in words if w not in stop_words and len(w) > 3]
        
        # Count word frequencies
        word_counts = Counter(meaningful_words)
        
        # Get top 10 keywords
        top_keywords = word_counts.most_common(10)
        
        if top_keywords:
            print(f"\n🔑 가장 많이 나온 키워드 (상위 10개):")
            for i, (word, count) in enumerate(top_keywords, 1):
                print(f"   {i}. {word}: {count}회")
        else:
            print("\n🔑 키워드 추출 실패")
    else:
        print("\n🔑 키워드 추출 실패 (제목/초록 데이터 없음)")
    
    print("=" * 80)


# Test the function
if __name__ == "__main__":
    # Main crawl function test
    category_url = 'https://arxiv.org/list/cs.AI/recent'
    
    # Crawl 10 latest papers from cs.AI category
    print("🚀 cs.AI 카테고리의 최신 논문 10개를 크롤링합니다...\n")
    df = main_crawl_category(
        category_url=category_url,
        output_csv='arxiv_papers.csv',
        delay=15,
        max_papers=10  # Crawl 10 papers
    )
    
    # Show statistics
    if not df.empty:
        show_statistics(df)
        print("\n✅ 크롤링 완료! 결과는 arxiv_papers.csv에 저장되었습니다.")
        print("📋 상세 로그는 crawler.log를 확인하세요.")
