"""
Test script for multi-level summarization API endpoints.

Tests the new summarization endpoints:
- Executive summary
- Detailed summary
- Multi-level summary
- Plain language conversion
"""

import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/analysis"

def test_executive_summary(document_id=1):
    """Test executive summary endpoint."""
    print("\n" + "=" * 80)
    print("TESTING EXECUTIVE SUMMARY ENDPOINT")
    print("=" * 80)
    
    url = f"{BASE_URL}/summarize/executive/{document_id}"
    print(f"\nCalling: GET {url}")
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ SUCCESS")
        print(f"Document ID: {data.get('document_id')}")
        print(f"File Name: {data.get('file_name')}")
        print(f"Word Count: {data.get('word_count')}")
        print(f"Target Range: {data.get('target_range')}")
        print(f"\nSummary:")
        print("-" * 80)
        print(data.get('summary', '')[:500])
        if len(data.get('summary', '')) > 500:
            print(f"... (truncated, total {len(data.get('summary', ''))} chars)")
    else:
        print(f"\n❌ FAILED: {response.text}")


def test_detailed_summary(document_id=1):
    """Test detailed summary endpoint."""
    print("\n" + "=" * 80)
    print("TESTING DETAILED SUMMARY ENDPOINT")
    print("=" * 80)
    
    url = f"{BASE_URL}/summarize/detailed/{document_id}"
    print(f"\nCalling: GET {url}")
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ SUCCESS")
        print(f"Document ID: {data.get('document_id')}")
        print(f"File Name: {data.get('file_name')}")
        print(f"Word Count: {data.get('word_count')}")
        print(f"Target Range: {data.get('target_range')}")
        print(f"\nSummary (first 500 chars):")
        print("-" * 80)
        print(data.get('summary', '')[:500])
        if len(data.get('summary', '')) > 500:
            print(f"... (truncated, total {len(data.get('summary', ''))} chars)")
    else:
        print(f"\n❌ FAILED: {response.text}")


def test_multi_level_summary(document_id=1, include_plain=False):
    """Test multi-level summary endpoint."""
    print("\n" + "=" * 80)
    print("TESTING MULTI-LEVEL SUMMARY ENDPOINT")
    print("=" * 80)
    
    url = f"{BASE_URL}/summarize/multi-level/{document_id}?include_plain_language={str(include_plain).lower()}"
    print(f"\nCalling: GET {url}")
    
    response = requests.get(url)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ SUCCESS")
        print(f"Document ID: {data.get('document_id')}")
        print(f"File Name: {data.get('file_name')}")
        print(f"Structure Aware: {data.get('structure_aware')}")
        
        summaries = data.get('summaries', {})
        
        # Executive summary
        if 'executive' in summaries:
            exec_sum = summaries['executive']
            print(f"\n📋 EXECUTIVE SUMMARY:")
            print(f"   Word Count: {exec_sum.get('word_count')}")
            print(f"   Target: {exec_sum.get('target_range')}")
            print(f"   Preview: {exec_sum.get('summary', '')[:150]}...")
        
        # Detailed summary
        if 'detailed' in summaries:
            det_sum = summaries['detailed']
            print(f"\n📝 DETAILED SUMMARY:")
            print(f"   Word Count: {det_sum.get('word_count')}")
            print(f"   Target: {det_sum.get('target_range')}")
            print(f"   Sections: {len(det_sum.get('section_summaries', {}))}")
        
        # Section summaries
        if 'section_specific' in summaries:
            sec_sums = summaries['section_specific']
            print(f"\n📂 SECTION-SPECIFIC SUMMARIES:")
            for section, sec_data in sec_sums.items():
                print(f"   - {section}: {sec_data.get('word_count')} words")
        
        # Document stats
        if 'document_stats' in summaries:
            stats = summaries['document_stats']
            print(f"\n📊 DOCUMENT STATISTICS:")
            print(f"   Total Words: {stats.get('total_words')}")
            print(f"   Total Sentences: {stats.get('total_sentences')}")
            print(f"   Sections: {', '.join(stats.get('sections_available', []))}")
        
        # Plain language (if requested)
        if include_plain and 'plain_language' in summaries:
            plain = summaries['plain_language']
            print(f"\n🗣️ PLAIN LANGUAGE VERSIONS:")
            if 'executive' in plain:
                print(f"   Executive: {plain['executive'].get('terms_simplified')} terms simplified")
            if 'detailed' in plain:
                print(f"   Detailed: {plain['detailed'].get('terms_simplified')} terms simplified")
            if 'glossary' in plain:
                print(f"   Glossary: {len(plain.get('glossary', []))} terms")
    else:
        print(f"\n❌ FAILED: {response.text}")


def test_plain_language_conversion():
    """Test plain language conversion endpoint."""
    print("\n" + "=" * 80)
    print("TESTING PLAIN LANGUAGE CONVERSION ENDPOINT")
    print("=" * 80)
    
    url = f"{BASE_URL}/convert-to-plain-language"
    print(f"\nCalling: POST {url}")
    
    test_text = """
    The petitioner filed a writ of habeas corpus under Article 126, alleging 
    violation of fundamental rights. The respondent argued the detention was 
    de jure. The Court, acting per curiam, allowed the appeal and granted 
    locus standi to the appellant.
    """
    
    payload = {"text": test_text, "language": "en"}
    
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ SUCCESS")
        print(f"Replacements Made: {data.get('replacements_made')}")
        print(f"Simplification Rate: {data.get('simplification_rate', 0):.2%}")
        
        print(f"\n📄 ORIGINAL TEXT:")
        print("-" * 80)
        print(data.get('original_text', '').strip())
        
        print(f"\n🗣️ PLAIN LANGUAGE VERSION:")
        print("-" * 80)
        print(data.get('plain_text', '').strip())
        
        print(f"\n📚 GLOSSARY ({len(data.get('glossary', []))} terms):")
        print("-" * 80)
        for i, entry in enumerate(data.get('glossary', [])[:10], 1):
            print(f"   {i}. {entry['term']} → {entry['definition']}")
    else:
        print(f"\n❌ FAILED: {response.text}")


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("MULTI-LEVEL SUMMARIZATION API TEST SUITE")
    print("=" * 80)
    print("\nTesting endpoints with document_id=1")
    print("Make sure you have uploaded at least one document!")
    
    try:
        # Test individual endpoints
        test_executive_summary(document_id=1)
        test_detailed_summary(document_id=1)
        
        # Test multi-level (without plain language)
        test_multi_level_summary(document_id=1, include_plain=False)
        
        # Test multi-level (with plain language)
        print("\n\n" + "=" * 80)
        print("TESTING WITH PLAIN LANGUAGE ENABLED")
        print("=" * 80)
        test_multi_level_summary(document_id=1, include_plain=True)
        
        # Test plain language conversion
        test_plain_language_conversion()
        
        print("\n" + "=" * 80)
        print("✅ ALL TESTS COMPLETED")
        print("=" * 80)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to backend server")
        print("Make sure the backend is running at http://127.0.0.1:8000")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
