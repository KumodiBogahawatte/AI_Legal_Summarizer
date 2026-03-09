import os
import sys
import logging

# Add the current directory to sys.path to allow imports from app
sys.path.append(os.getcwd())

# Mock environment variables if needed
# os.environ["OPENAI_API_KEY"] = "your-key"

from app.services.llm_generation_service import get_llm_service

def test_service():
    logging.basicConfig(level=logging.INFO)
    print("Testing LLMGenerationService initialization...")
    try:
        service = get_llm_service()
        print(f"Service mode: {service.get_mode()}")
        
        print("\nTesting generate_full_analysis signature...")
        # We use empty/small data just to check for crashes and source
        result = service.generate_full_analysis(1, "Test text", {"court": "SC"})
        print(f"Result source: {result.get('_source')}")
        
        print("\nTesting generate_case_brief signature...")
        brief = service.generate_case_brief(1, "Test text", {"court": "SC"})
        print(f"Brief keys: {list(brief.keys()) if isinstance(brief, dict) else 'Not a dict'}")
        
        print("\n✅ Service tests passed basic checks.")
    except Exception as e:
        print(f"\n❌ Service test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_service()
