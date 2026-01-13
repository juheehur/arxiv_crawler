"""
Paper summarization using Gemini API.
Summarizes academic papers with structured output.
"""

import os
import json
from typing import Dict
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables
load_dotenv('.env.local')

# Configure Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env.local")

# Initialize client with API key
client = genai.Client(api_key=GEMINI_API_KEY)

# Use the cheapest model: gemini-2.5-flash-lite
MODEL_NAME = 'gemini-2.5-flash-lite'


def summarize_paper(title: str, abstract: str) -> Dict[str, str]:
    """
    Summarize a paper using Gemini API.
    
    Args:
        title: Paper title
        abstract: Paper abstract
        
    Returns:
        Dictionary with keys:
        - summary_one_line: One-line summary (within 20 characters)
        - summary_easy: Easy explanation (3-4 sentences, understandable by middle schoolers)
        - real_world: Real-world applications (2-3 lines, where it's used)
        - limitations: Limitations (1-2 lines)
    """
    
    # Create a very clear and structured prompt
    prompt = f"""You are a scientific paper summarizer. Analyze the following academic paper and provide a structured summary in JSON format. ALL OUTPUTS MUST BE IN KOREAN.

Paper Title: {title}

Abstract: {abstract}

Please provide a summary with the following structure. IMPORTANT: You must respond ONLY with valid JSON, no additional text before or after. ALL TEXT MUST BE IN KOREAN.

{{
    "summary_one_line": "한 줄 요약을 정확히 20자 이내로 작성하세요. 공백, 구두점, 한글 문자를 모두 포함하여 세세요. 20자를 초과하면 안 됩니다.",
    "summary_easy": "중학생도 이해할 수 있는 쉬운 설명을 정확히 3-4문장으로 작성하세요. 전문 용어를 피하고 간단한 언어를 사용하세요. 반드시 한국어로 작성하세요.",
    "real_world": "이 연구가 실제로 어디에, 어떻게 적용될 수 있는지 2-3줄로 설명하세요. 반드시 한국어로 작성하세요.",
    "limitations": "연구의 한계점이나 약점을 1-2줄로 설명하세요. 반드시 한국어로 작성하세요."
}}

CRITICAL REQUIREMENTS - READ CAREFULLY:
1. summary_one_line: 반드시 정확히 20자 이내여야 합니다. 공백, 구두점, 한글 문자를 모두 포함하여 세세요. 예시: "AI 모호성 감지" (9자) ✓, "3D 지시 명확성" (9자) ✓, "3D 지시 모호성 감지 시스템" (13자) ✓, "Detect 3D instruction ambiguity" (31자) ✗ 너무 김
2. summary_easy: 정확히 3-4개의 완전한 문장이어야 합니다. 더 많거나 적으면 안 됩니다. 반드시 한국어로 작성하세요.
3. real_world: 정확히 2-3줄이어야 합니다. 각 줄은 완전한 생각이어야 합니다. 반드시 한국어로 작성하세요.
4. limitations: 정확히 1-2줄이어야 합니다. 반드시 한국어로 작성하세요.
5. 모든 텍스트는 반드시 한국어로 작성해야 합니다.
6. 응답은 유효한 JSON만 제공하세요. 마크다운 형식, 코드 블록, 설명, 주석 없이
7. JSON의 모든 문자열에는 쌍따옴표를 사용하세요
8. 모든 특수 문자는 적절히 이스케이프 처리하세요
9. JSON 객체 앞이나 뒤에 텍스트를 포함하지 마세요

VERIFY: 응답하기 전에 summary_one_line의 문자 수를 세세요. 20자를 초과하면 즉시 줄이세요.

이제 JSON 응답을 제공하세요:"""

    try:
        # Generate response using the client
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,  # Lower temperature for more consistent output
                max_output_tokens=500,
            )
        )
        
        # Extract text from response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        elif response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate required keys
        required_keys = ['summary_one_line', 'summary_easy', 'real_world', 'limitations']
        for key in required_keys:
            if key not in result:
                raise ValueError(f"Missing required key: {key}")
        
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response text: {response_text}")
        raise
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        raise


if __name__ == "__main__":
    # Test with the first paper from arxiv_papers.csv
    import pandas as pd
    
    # Read CSV
    df = pd.read_csv('arxiv_papers.csv')
    
    # Get first paper
    first_paper = df.iloc[0]
    title = first_paper['title']
    abstract = first_paper['abstract']
    
    print("=" * 80)
    print("Testing summarize_paper with first paper:")
    print("=" * 80)
    print(f"\nTitle: {title}\n")
    print(f"Abstract: {abstract[:200]}...\n")
    print("=" * 80)
    print("\nGenerating summary...\n")
    
    # Generate summary
    summary = summarize_paper(title, abstract)
    
    # Display results
    print("=" * 80)
    print("SUMMARY RESULTS:")
    print("=" * 80)
    print(f"\n[한 줄 요약] ({len(summary['summary_one_line'])}자)")
    print(summary['summary_one_line'])
    print(f"\n[쉬운 설명]")
    print(summary['summary_easy'])
    print(f"\n[현실 적용]")
    print(summary['real_world'])
    print(f"\n[한계점]")
    print(summary['limitations'])
    print("\n" + "=" * 80)
    
    # Also print as JSON for verification
    print("\n[JSON 형식]")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
