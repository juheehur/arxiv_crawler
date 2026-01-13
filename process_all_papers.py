"""
Process all papers in CSV file and add summaries using Gemini API.
"""

import pandas as pd
import time
import sys
from summarize_paper import summarize_paper

def process_all_papers(input_file: str = 'arxiv_papers.csv', output_file: str = 'papers_with_summary.csv'):
    """
    Process all papers in CSV file and add summaries.
    
    Args:
        input_file: Input CSV file path (default: 'arxiv_papers.csv')
        output_file: Output CSV file path (default: 'papers_with_summary.csv')
    """
    
    # Read CSV file
    print(f"Reading {input_file}...")
    try:
        df = pd.read_csv(input_file)
    except FileNotFoundError:
        print(f"Error: {input_file} not found!")
        sys.exit(1)
    
    total_papers = len(df)
    print(f"Found {total_papers} papers to process.\n")
    
    # Initialize new columns
    df['summary_one_line'] = ''
    df['summary_easy'] = ''
    df['real_world'] = ''
    df['limitations'] = ''
    
    # Process each paper
    for idx, row in df.iterrows():
        paper_num = idx + 1
        title = row['title']
        abstract = row['abstract']
        
        print(f"[{paper_num}/{total_papers}] Processing: {title[:60]}...")
        
        try:
            # Generate summary
            summary = summarize_paper(title, abstract)
            
            # Add summary to dataframe
            df.at[idx, 'summary_one_line'] = summary['summary_one_line']
            df.at[idx, 'summary_easy'] = summary['summary_easy']
            df.at[idx, 'real_world'] = summary['real_world']
            df.at[idx, 'limitations'] = summary['limitations']
            
            print(f"  ✓ Summary generated successfully")
            
        except Exception as e:
            print(f"  ✗ Error processing paper: {e}")
            print(f"  Continuing with next paper...")
            # Leave empty values for failed papers
            continue
        
        # Wait 2 seconds before next API call (rate limiting)
        if paper_num < total_papers:
            print(f"  Waiting 2 seconds before next request...\n")
            time.sleep(2)
        else:
            print()
    
    # Save to output file
    print(f"\nSaving results to {output_file}...")
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"✓ Successfully saved {total_papers} papers with summaries to {output_file}")
    
    # Print summary statistics
    successful = df['summary_one_line'].str.len() > 0
    print(f"\nSummary Statistics:")
    print(f"  Total papers: {total_papers}")
    print(f"  Successfully processed: {successful.sum()}")
    print(f"  Failed: {(~successful).sum()}")


if __name__ == "__main__":
    # Check if custom input file is provided
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'arxiv_papers.csv'
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'papers_with_summary.csv'
    
    print("=" * 80)
    print("Paper Summarization Batch Processor")
    print("=" * 80)
    print()
    
    process_all_papers(input_file, output_file)
    
    print("\n" + "=" * 80)
    print("Processing complete!")
    print("=" * 80)
