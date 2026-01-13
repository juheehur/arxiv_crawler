"""
Streamlit UI for ArXiv Paper Crawler and Summarizer
"""

import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime
import sys

# Import functions from existing modules
from test_crawler import (
    extract_paper_info,
    main_crawl_category,
    show_statistics,
    collect_arxiv_ids_from_category
)
from summarize_paper import summarize_paper
from process_all_papers import process_all_papers

# Page configuration
st.set_page_config(
    page_title="ArXiv Paper Crawler & Summarizer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .paper-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e0e0e0;
        margin-bottom: 1rem;
        background-color: #f9f9f9;
    }
    .success-message {
        color: #28a745;
        font-weight: bold;
    }
    .error-message {
        color: #dc3545;
        font-weight: bold;
    }
    .info-box {
        background-color: #e7f3ff;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'crawl_in_progress' not in st.session_state:
    st.session_state.crawl_in_progress = False
if 'summary_in_progress' not in st.session_state:
    st.session_state.summary_in_progress = False
if 'last_crawl_time' not in st.session_state:
    st.session_state.last_crawl_time = None
if 'last_summary_time' not in st.session_state:
    st.session_state.last_summary_time = None


def load_papers_csv(filepath='arxiv_papers.csv'):
    """Load papers from CSV file."""
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
            return df
        except Exception as e:
            st.error(f"Error loading CSV: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


def load_summaries_csv(filepath='papers_with_summary.csv'):
    """Load papers with summaries from CSV file."""
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath, encoding='utf-8')
            return df
        except Exception as e:
            st.error(f"Error loading summaries CSV: {e}")
            return pd.DataFrame()
    return pd.DataFrame()


def save_papers_to_csv(df, filepath='arxiv_papers.csv'):
    """Save papers to CSV file."""
    try:
        df.to_csv(filepath, index=False, encoding='utf-8')
        return True
    except Exception as e:
        st.error(f"Error saving CSV: {e}")
        return False


def main():
    # Header
    st.markdown('<div class="main-header">📚 ArXiv Paper Crawler & Summarizer</div>', unsafe_allow_html=True)
    
    # Sidebar navigation
    st.sidebar.title("메뉴")
    page = st.sidebar.radio(
        "페이지 선택",
        ["🏠 홈", "📥 논문 크롤링", "📋 논문 목록", "📝 요약 생성", "📊 통계"]
    )
    
    # Home page
    if page == "🏠 홈":
        st.header("홈")
        st.markdown("""
        <div class="info-box">
            <h3>환영합니다! 👋</h3>
            <p>이 애플리케이션은 ArXiv 논문을 크롤링하고 요약하는 도구입니다.</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📥 논문 크롤링")
            st.markdown("""
            - ArXiv 카테고리에서 논문 정보 수집
            - 단일 논문 URL로 크롤링
            - 중복 자동 감지
            """)
        
        with col2:
            st.subheader("📝 요약 생성")
            st.markdown("""
            - Gemini API를 사용한 논문 요약
            - 한 줄 요약, 쉬운 설명, 현실 적용, 한계점
            - 개별 또는 일괄 요약 생성
            """)
        
        # Show file status
        st.subheader("📁 파일 상태")
        col1, col2 = st.columns(2)
        
        with col1:
            if os.path.exists('arxiv_papers.csv'):
                df = load_papers_csv()
                st.success(f"✅ arxiv_papers.csv: {len(df)}개 논문")
            else:
                st.info("ℹ️ arxiv_papers.csv: 파일 없음")
        
        with col2:
            if os.path.exists('papers_with_summary.csv'):
                df = load_summaries_csv()
                st.success(f"✅ papers_with_summary.csv: {len(df)}개 논문")
            else:
                st.info("ℹ️ papers_with_summary.csv: 파일 없음")
    
    # Crawling page
    elif page == "📥 논문 크롤링":
        st.header("논문 크롤링")
        
        crawl_method = st.radio(
            "크롤링 방법 선택",
            ["카테고리에서 크롤링", "단일 논문 URL 크롤링"]
        )
        
        if crawl_method == "카테고리에서 크롤링":
            st.subheader("카테고리 크롤링")
            
            # Popular categories
            categories = {
                "AI (cs.AI)": "https://arxiv.org/list/cs.AI/recent",
                "Machine Learning (cs.LG)": "https://arxiv.org/list/cs.LG/recent",
                "Computer Vision (cs.CV)": "https://arxiv.org/list/cs.CV/recent",
                "NLP (cs.CL)": "https://arxiv.org/list/cs.CL/recent",
                "Robotics (cs.RO)": "https://arxiv.org/list/cs.RO/recent",
            }
            
            selected_category = st.selectbox(
                "카테고리 선택",
                list(categories.keys())
            )
            
            category_url = categories[selected_category]
            st.info(f"선택된 URL: {category_url}")
            
            # Custom URL option
            use_custom_url = st.checkbox("직접 URL 입력")
            if use_custom_url:
                category_url = st.text_input(
                    "ArXiv 카테고리 URL",
                    value=category_url,
                    help="예: https://arxiv.org/list/cs.AI/recent"
                )
            
            col1, col2 = st.columns(2)
            with col1:
                max_papers = st.number_input(
                    "최대 논문 수",
                    min_value=1,
                    max_value=100,
                    value=10,
                    help="크롤링할 최대 논문 수"
                )
            with col2:
                delay = st.number_input(
                    "요청 간 딜레이 (초)",
                    min_value=1,
                    max_value=60,
                    value=15,
                    help="각 요청 사이의 대기 시간 (초)"
                )
            
            if st.button("🚀 크롤링 시작", type="primary", disabled=st.session_state.crawl_in_progress):
                if not category_url:
                    st.error("URL을 입력해주세요.")
                else:
                    st.session_state.crawl_in_progress = True
                    
                    with st.spinner("크롤링 중... 잠시만 기다려주세요."):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            # Redirect stdout to capture print statements
                            import io
                            from contextlib import redirect_stdout
                            
                            f = io.StringIO()
                            with redirect_stdout(f):
                                df = main_crawl_category(
                                    category_url=category_url,
                                    output_csv='arxiv_papers.csv',
                                    delay=delay,
                                    max_papers=max_papers
                                )
                            
                            output = f.getvalue()
                            st.session_state.last_crawl_time = datetime.now()
                            
                            st.success(f"✅ 크롤링 완료! {len(df)}개 논문이 저장되었습니다.")
                            
                            # Show output in expander
                            with st.expander("크롤링 로그 보기"):
                                st.text(output)
                            
                        except Exception as e:
                            st.error(f"❌ 크롤링 중 오류 발생: {e}")
                        finally:
                            st.session_state.crawl_in_progress = False
                            progress_bar.empty()
                            status_text.empty()
        
        else:  # Single paper URL
            st.subheader("단일 논문 크롤링")
            
            paper_url = st.text_input(
                "ArXiv 논문 URL",
                placeholder="https://arxiv.org/abs/2301.00001",
                help="ArXiv 논문의 abs 페이지 URL을 입력하세요"
            )
            
            if st.button("🔍 논문 정보 추출", type="primary"):
                if not paper_url:
                    st.error("URL을 입력해주세요.")
                else:
                    with st.spinner("논문 정보를 추출하는 중..."):
                        try:
                            paper_info = extract_paper_info(paper_url)
                            
                            if 'error' in paper_info:
                                st.error(f"❌ 오류: {paper_info['error']}")
                            else:
                                st.success("✅ 논문 정보 추출 성공!")
                                
                                # Display paper info
                                st.subheader("📄 논문 정보")
                                col1, col2 = st.columns([2, 1])
                                
                                with col1:
                                    st.markdown(f"**제목:** {paper_info['title']}")
                                    st.markdown(f"**ArXiv ID:** {paper_info['arxiv_id']}")
                                    st.markdown(f"**카테고리:** {paper_info['categories']}")
                                    st.markdown(f"**제출일:** {paper_info['submitted_date']}")
                                
                                with col2:
                                    st.markdown(f"**저자 수:** {len(paper_info['authors'])}명")
                                    if paper_info['pdf_url']:
                                        st.markdown(f"[📥 PDF 다운로드]({paper_info['pdf_url']})")
                                
                                st.markdown("**저자:**")
                                for i, author in enumerate(paper_info['authors'], 1):
                                    st.markdown(f"{i}. {author}")
                                
                                st.markdown("**초록:**")
                                st.text_area("", paper_info['abstract'], height=150, disabled=True)
                                
                                # Save to CSV option
                                if st.button("💾 CSV에 저장"):
                                    # Load existing CSV
                                    df = load_papers_csv()
                                    
                                    # Check if paper already exists
                                    if not df.empty and 'arxiv_id' in df.columns:
                                        if paper_info['arxiv_id'] in df['arxiv_id'].values:
                                            st.warning("⚠️ 이 논문은 이미 CSV에 저장되어 있습니다.")
                                        else:
                                            # Add new paper
                                            authors_str = ', '.join(paper_info['authors'])
                                            new_row = pd.DataFrame([{
                                                'arxiv_id': paper_info['arxiv_id'],
                                                'title': paper_info['title'],
                                                'authors': authors_str,
                                                'abstract': paper_info['abstract'],
                                                'submitted_date': paper_info['submitted_date'],
                                                'categories': paper_info['categories'],
                                                'pdf_url': paper_info['pdf_url']
                                            }])
                                            df = pd.concat([df, new_row], ignore_index=True)
                                            if save_papers_to_csv(df):
                                                st.success("✅ CSV에 저장되었습니다!")
                                    else:
                                        # Create new DataFrame
                                        authors_str = ', '.join(paper_info['authors'])
                                        df = pd.DataFrame([{
                                            'arxiv_id': paper_info['arxiv_id'],
                                            'title': paper_info['title'],
                                            'authors': authors_str,
                                            'abstract': paper_info['abstract'],
                                            'submitted_date': paper_info['submitted_date'],
                                            'categories': paper_info['categories'],
                                            'pdf_url': paper_info['pdf_url']
                                        }])
                                        if save_papers_to_csv(df):
                                            st.success("✅ CSV에 저장되었습니다!")
                                
                        except Exception as e:
                            st.error(f"❌ 오류 발생: {e}")
    
    # Paper list page
    elif page == "📋 논문 목록":
        st.header("논문 목록")
        
        # Load papers
        df = load_papers_csv()
        
        if df.empty:
            st.info("ℹ️ 저장된 논문이 없습니다. 먼저 논문을 크롤링해주세요.")
        else:
            st.success(f"총 {len(df)}개의 논문이 있습니다.")
            
            # Search and filter
            col1, col2 = st.columns([3, 1])
            with col1:
                search_query = st.text_input("🔍 검색", placeholder="제목, 저자, 초록으로 검색...")
            with col2:
                show_summaries = st.checkbox("요약 포함 보기", value=False)
            
            # Filter DataFrame
            if search_query:
                mask = (
                    df['title'].astype(str).str.contains(search_query, case=False, na=False) |
                    df['authors'].astype(str).str.contains(search_query, case=False, na=False) |
                    df['abstract'].astype(str).str.contains(search_query, case=False, na=False)
                )
                filtered_df = df[mask]
            else:
                filtered_df = df
            
            st.info(f"검색 결과: {len(filtered_df)}개 논문")
            
            # Load summaries if requested
            if show_summaries:
                summary_df = load_summaries_csv()
                if not summary_df.empty:
                    # Merge with summaries
                    filtered_df = filtered_df.merge(
                        summary_df[['arxiv_id', 'summary_one_line', 'summary_easy', 'real_world', 'limitations']],
                        on='arxiv_id',
                        how='left'
                    )
            
            # Display papers
            for idx, row in filtered_df.iterrows():
                with st.expander(f"📄 {row['title']}"):
                    col1, col2 = st.columns([3, 1])
                    
                    with col1:
                        st.markdown(f"**ArXiv ID:** {row['arxiv_id']}")
                        st.markdown(f"**저자:** {row['authors']}")
                        st.markdown(f"**카테고리:** {row.get('categories', 'N/A')}")
                        st.markdown(f"**제출일:** {row.get('submitted_date', 'N/A')}")
                        
                        if pd.notna(row.get('pdf_url')):
                            st.markdown(f"[📥 PDF 다운로드]({row['pdf_url']})")
                    
                    with col2:
                        if show_summaries and pd.notna(row.get('summary_one_line')):
                            st.markdown("**한 줄 요약:**")
                            st.info(row['summary_one_line'])
                    
                    st.markdown("**초록:**")
                    st.text_area("", row['abstract'], height=100, disabled=True, key=f"abstract_{idx}")
                    
                    if show_summaries:
                        if pd.notna(row.get('summary_easy')):
                            st.markdown("**쉬운 설명:**")
                            st.info(row['summary_easy'])
                        
                        if pd.notna(row.get('real_world')):
                            st.markdown("**현실 적용:**")
                            st.success(row['real_world'])
                        
                        if pd.notna(row.get('limitations')):
                            st.markdown("**한계점:**")
                            st.warning(row['limitations'])
    
    # Summary generation page
    elif page == "📝 요약 생성":
        st.header("요약 생성")
        
        # Check for API key
        if not os.getenv('GEMINI_API_KEY'):
            st.error("❌ GEMINI_API_KEY가 설정되지 않았습니다. .env.local 파일을 확인해주세요.")
            st.stop()
        
        summary_method = st.radio(
            "요약 방법 선택",
            ["개별 논문 요약", "일괄 요약 생성"]
        )
        
        if summary_method == "개별 논문 요약":
            st.subheader("개별 논문 요약")
            
            # Load papers
            df = load_papers_csv()
            
            if df.empty:
                st.info("ℹ️ 저장된 논문이 없습니다. 먼저 논문을 크롤링해주세요.")
            else:
                # Paper selection
                paper_titles = df['title'].tolist()
                selected_idx = st.selectbox(
                    "논문 선택",
                    range(len(paper_titles)),
                    format_func=lambda x: f"{df.iloc[x]['arxiv_id']} - {paper_titles[x][:80]}..."
                )
                
                selected_paper = df.iloc[selected_idx]
                
                # Show paper info
                st.markdown("**선택된 논문:**")
                st.info(f"**{selected_paper['title']}**")
                st.text_area("초록", selected_paper['abstract'], height=150, disabled=True)
                
                if st.button("✨ 요약 생성", type="primary"):
                    with st.spinner("요약을 생성하는 중... (약 10-20초 소요)"):
                        try:
                            summary = summarize_paper(
                                selected_paper['title'],
                                selected_paper['abstract']
                            )
                            
                            st.success("✅ 요약 생성 완료!")
                            
                            # Display summary
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("**한 줄 요약 (20자 이내):**")
                                st.info(summary['summary_one_line'])
                                
                                st.markdown("**쉬운 설명:**")
                                st.info(summary['summary_easy'])
                            
                            with col2:
                                st.markdown("**현실 적용:**")
                                st.success(summary['real_world'])
                                
                                st.markdown("**한계점:**")
                                st.warning(summary['limitations'])
                            
                            # Save option
                            if st.button("💾 요약 저장"):
                                # Load or create summary CSV
                                summary_df = load_summaries_csv()
                                
                                # Check if paper already has summary
                                if not summary_df.empty and 'arxiv_id' in summary_df.columns:
                                    if selected_paper['arxiv_id'] in summary_df['arxiv_id'].values:
                                        # Update existing
                                        idx = summary_df[summary_df['arxiv_id'] == selected_paper['arxiv_id']].index[0]
                                        summary_df.at[idx, 'summary_one_line'] = summary['summary_one_line']
                                        summary_df.at[idx, 'summary_easy'] = summary['summary_easy']
                                        summary_df.at[idx, 'real_world'] = summary['real_world']
                                        summary_df.at[idx, 'limitations'] = summary['limitations']
                                    else:
                                        # Add new
                                        new_row = selected_paper.to_dict()
                                        new_row.update(summary)
                                        summary_df = pd.concat([summary_df, pd.DataFrame([new_row])], ignore_index=True)
                                else:
                                    # Create new DataFrame
                                    new_row = selected_paper.to_dict()
                                    new_row.update(summary)
                                    summary_df = pd.DataFrame([new_row])
                                
                                # Save
                                try:
                                    summary_df.to_csv('papers_with_summary.csv', index=False, encoding='utf-8-sig')
                                    st.success("✅ 요약이 저장되었습니다!")
                                except Exception as e:
                                    st.error(f"❌ 저장 중 오류: {e}")
                        
                        except Exception as e:
                            st.error(f"❌ 요약 생성 중 오류 발생: {e}")
        
        else:  # Batch summary
            st.subheader("일괄 요약 생성")
            
            # Load papers
            df = load_papers_csv()
            
            if df.empty:
                st.info("ℹ️ 저장된 논문이 없습니다. 먼저 논문을 크롤링해주세요.")
            else:
                # Check which papers already have summaries
                summary_df = load_summaries_csv()
                papers_with_summary = set()
                if not summary_df.empty and 'arxiv_id' in summary_df.columns:
                    papers_with_summary = set(summary_df['arxiv_id'].dropna().unique())
                
                papers_needing_summary = df[~df['arxiv_id'].isin(papers_with_summary)]
                
                st.info(f"총 {len(df)}개 논문 중 {len(papers_needing_summary)}개 논문에 요약이 필요합니다.")
                
                if len(papers_needing_summary) == 0:
                    st.success("✅ 모든 논문에 요약이 생성되어 있습니다!")
                else:
                    max_papers = st.number_input(
                        "처리할 최대 논문 수",
                        min_value=1,
                        max_value=len(papers_needing_summary),
                        value=min(5, len(papers_needing_summary)),
                        help="한 번에 처리할 논문 수를 선택하세요"
                    )
                    
                    if st.button("🚀 일괄 요약 시작", type="primary", disabled=st.session_state.summary_in_progress):
                        st.session_state.summary_in_progress = True
                        
                        papers_to_process = papers_needing_summary.head(max_papers)
                        
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        try:
                            # Load or create summary CSV
                            summary_df = load_summaries_csv()
                            if summary_df.empty:
                                summary_df = df.copy()
                                summary_df['summary_one_line'] = ''
                                summary_df['summary_easy'] = ''
                                summary_df['real_world'] = ''
                                summary_df['limitations'] = ''
                            
                            successful = 0
                            failed = 0
                            
                            for idx, (paper_idx, paper) in enumerate(papers_to_process.iterrows()):
                                status_text.text(f"처리 중: {paper['title'][:50]}... ({idx+1}/{len(papers_to_process)})")
                                progress_bar.progress((idx + 1) / len(papers_to_process))
                                
                                try:
                                    summary = summarize_paper(paper['title'], paper['abstract'])
                                    
                                    # Update or add summary
                                    if paper['arxiv_id'] in summary_df['arxiv_id'].values:
                                        summary_idx = summary_df[summary_df['arxiv_id'] == paper['arxiv_id']].index[0]
                                        summary_df.at[summary_idx, 'summary_one_line'] = summary['summary_one_line']
                                        summary_df.at[summary_idx, 'summary_easy'] = summary['summary_easy']
                                        summary_df.at[summary_idx, 'real_world'] = summary['real_world']
                                        summary_df.at[summary_idx, 'limitations'] = summary['limitations']
                                    else:
                                        new_row = paper.to_dict()
                                        new_row.update(summary)
                                        summary_df = pd.concat([summary_df, pd.DataFrame([new_row])], ignore_index=True)
                                    
                                    successful += 1
                                    
                                    # Rate limiting
                                    if idx < len(papers_to_process) - 1:
                                        time.sleep(2)
                                
                                except Exception as e:
                                    st.warning(f"⚠️ {paper['title'][:50]}... 처리 실패: {e}")
                                    failed += 1
                            
                            # Save results
                            summary_df.to_csv('papers_with_summary.csv', index=False, encoding='utf-8-sig')
                            st.session_state.last_summary_time = datetime.now()
                            
                            st.success(f"✅ 일괄 요약 완료! 성공: {successful}개, 실패: {failed}개")
                            
                        except Exception as e:
                            st.error(f"❌ 일괄 요약 중 오류 발생: {e}")
                        finally:
                            st.session_state.summary_in_progress = False
                            progress_bar.empty()
                            status_text.empty()
    
    # Statistics page
    elif page == "📊 통계":
        st.header("통계")
        
        # Load papers
        df = load_papers_csv()
        
        if df.empty:
            st.info("ℹ️ 저장된 논문이 없습니다. 먼저 논문을 크롤링해주세요.")
        else:
            # Filter out papers with errors
            valid_df = df[df['title'].notna()].copy()
            
            if valid_df.empty:
                st.warning("⚠️ 분석할 수 있는 유효한 논문이 없습니다.")
            else:
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("총 논문 수", len(valid_df))
                
                with col2:
                    # Average authors
                    author_counts = []
                    for authors_str in valid_df['authors'].dropna():
                        if authors_str:
                            authors_list = [a.strip() for a in str(authors_str).split(',') if a.strip()]
                            author_counts.append(len(authors_list))
                    
                    if author_counts:
                        avg_authors = sum(author_counts) / len(author_counts)
                        st.metric("평균 저자 수", f"{avg_authors:.1f}명")
                    else:
                        st.metric("평균 저자 수", "N/A")
                
                with col3:
                    # Categories count
                    if 'categories' in valid_df.columns:
                        category_count = valid_df['categories'].notna().sum()
                        st.metric("카테고리 정보", f"{category_count}개")
                    else:
                        st.metric("카테고리 정보", "N/A")
                
                # Summary statistics
                summary_df = load_summaries_csv()
                if not summary_df.empty:
                    st.subheader("요약 통계")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        papers_with_summary = summary_df['summary_one_line'].notna().sum()
                        st.metric("요약 생성된 논문", f"{papers_with_summary}개")
                    
                    with col2:
                        completion_rate = (papers_with_summary / len(valid_df)) * 100
                        st.metric("요약 완성도", f"{completion_rate:.1f}%")
                
                # Category distribution
                if 'categories' in valid_df.columns:
                    st.subheader("카테고리 분포")
                    category_counts = valid_df['categories'].value_counts().head(10)
                    st.bar_chart(category_counts)
                
                # Recent papers
                st.subheader("최근 논문 (최대 10개)")
                recent_papers = valid_df.head(10)[['arxiv_id', 'title', 'authors', 'submitted_date']]
                st.dataframe(recent_papers, use_container_width=True)


if __name__ == "__main__":
    main()
