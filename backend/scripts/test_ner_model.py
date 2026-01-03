"""
Test the trained Legal NER model.
"""

import spacy
from pathlib import Path
from termcolor import colored

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODEL_DIR = PROJECT_ROOT / "backend" / "models" / "legal_ner"

# Test texts
TEST_TEXTS = [
    """
    In the case of Silva vs. Fernando decided by the Supreme Court on 15.03.2006,
    Justice S.N. Silva held that Section 175(1) of the Civil Procedure Code requires
    filing witness lists 15 days before trial. The Court cited precedent from 
    [2005] 2 SRI L.R. 123 establishing the burden of proof principle.
    """,
    
    """
    The Court of Appeal in Perera and Another vs. Bank of Ceylon (CA 450/2003) 
    examined Article 138 of the Constitution and the Maintenance Act No. 37 of 1999.
    Hon. Andrew Somawansa, J. delivered the judgment on 21.02.2005.
    """,
    
    """
    The High Court considered the Evidence Ordinance and fundamental rights under
    Article 154P(3)(b). The learned District Judge applied the doctrine of 
    res judicata as per the ruling in DC Colombo 17090/L.
    """
]


def load_model(model_path: Path):
    """Load trained spaCy model."""
    if not model_path.exists():
        print(f"❌ Model not found at {model_path}")
        print("   Run: python scripts/train_ner_auto.py first")
        return None
    
    return spacy.load(model_path)


def visualize_entities(doc):
    """Display entities with colors."""
    colors = {
        "CASE_NAME": "red",
        "COURT": "cyan",
        "JUDGE": "blue",
        "STATUTE": "magenta",
        "ARTICLE": "green",
        "LEGAL_PRINCIPLE": "yellow",
        "DATE": "light_magenta",
        "CITATION": "light_cyan"
    }
    
    # Sort entities by start position
    entities = sorted(doc.ents, key=lambda e: e.start_char)
    
    last_end = 0
    result = []
    
    for ent in entities:
        # Add text before entity
        result.append(doc.text[last_end:ent.start_char])
        
        # Add colored entity
        color = colors.get(ent.label_, "white")
        entity_text = colored(ent.text, color, attrs=['bold'])
        label_text = colored(f"[{ent.label_}]", color)
        result.append(f"{entity_text} {label_text}")
        
        last_end = ent.end_char
    
    # Add remaining text
    result.append(doc.text[last_end:])
    
    return "".join(result)


def test_model(nlp):
    """Test model on sample texts."""
    print("=" * 70)
    print("Testing Legal NER Model")
    print("=" * 70)
    print()
    
    for i, text in enumerate(TEST_TEXTS, 1):
        print(f"\n{'=' * 70}")
        print(f"Test Case {i}")
        print('=' * 70)
        
        doc = nlp(text.strip())
        
        print("\n📝 Text:")
        print(visualize_entities(doc))
        
        print("\n\n🏷️  Entities found:")
        if doc.ents:
            for ent in doc.ents:
                print(f"   • {ent.text:30} → {ent.label_:20}")
        else:
            print("   (No entities found)")
        
        print()
    
    print("=" * 70)


def main():
    """Main execution function."""
    print("\n🔍 Loading trained model...")
    nlp = load_model(MODEL_DIR)
    
    if nlp is None:
        return
    
    print(f"✅ Model loaded from {MODEL_DIR}")
    print(f"📊 Entity types: {', '.join(nlp.get_pipe('ner').labels)}")
    
    # Test model
    test_model(nlp)
    
    print("\n✅ Testing complete!")
    print("\n💡 To use this model in your application:")
    print("   nlp = spacy.load('backend/models/legal_ner')")
    print("   doc = nlp(text)")
    print("   entities = [(ent.text, ent.label_) for ent in doc.ents]")


if __name__ == "__main__":
    main()
