"""
Test the SmartFormFiller with candidate profiles
Run this to verify the human-in-loop system
"""

import yaml
from bot.application.smart_form_filler import SmartFormFiller

def load_candidates():
    """Load candidates from YAML"""
    with open('config/candidates.yaml', 'r') as f:
        data = yaml.safe_load(f)
    return data['candidates']

def test_profile_matching():
    """Test keyword matching with profile data"""
    candidates = load_candidates()
    candidate = candidates[0]  # First candidate
    
    print("=" * 70)
    print(f"Testing profile: {candidate['name']}")
    print("=" * 70)
    
    # Create a mock page object (we won't actually use it for this test)
    class MockPage:
        pass
    
    filler = SmartFormFiller(MockPage(), candidate)
    
    # Test keyword matching
    test_questions = [
        "What is your email address?",
        "How many years of Python experience do you have?",
        "Do you require visa sponsorship?",
        "Are you willing to relocate?",
        "What is your phone number?",
        "Phone country code",
    ]
    
    print("\nTesting keyword matching:")
    print("-" * 70)
    for question in test_questions:
        answer = filler._match_keywords(question.lower())
        print(f"Q: {question}")
        print(f"A: {answer or 'WOULD ASK HUMAN'}")
        print()
    
    print("=" * 70)
    print("✅ Profile matching test complete!")
    print("=" * 70)

if __name__ == "__main__":
    test_profile_matching()
