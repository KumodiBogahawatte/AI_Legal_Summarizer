"""
Setup Label Studio project for Legal NER annotation.

This script provides instructions and configuration for setting up
Label Studio with the appropriate labeling interface for legal NER.
"""

import json
from pathlib import Path

# Label Studio configuration template
LABEL_STUDIO_CONFIG = """
<View>
  <Header value="Legal Document NER Annotation"/>
  
  <Text name="text" value="$text"/>
  
  <Labels name="label" toName="text">
    <Label value="CASE_NAME" background="#FF6B6B" hotkey="1"/>
    <Label value="COURT" background="#4ECDC4" hotkey="2"/>
    <Label value="JUDGE" background="#45B7D1" hotkey="3"/>
    <Label value="STATUTE" background="#FFA07A" hotkey="4"/>
    <Label value="ARTICLE" background="#98D8C8" hotkey="5"/>
    <Label value="LEGAL_PRINCIPLE" background="#F7DC6F" hotkey="6"/>
    <Label value="DATE" background="#BB8FCE" hotkey="7"/>
    <Label value="CITATION" background="#85C1E2" hotkey="8"/>
  </Labels>
</View>
"""

# Entity descriptions for annotators
ENTITY_DESCRIPTIONS = {
    "CASE_NAME": {
        "description": "Names of legal cases (e.g., 'Silva v. Fernando', 'In re: Bandara')",
        "examples": [
            "Samantha Kumara vs. Manohari",
            "Silva v. Fernando",
            "Attorney General v. Perera",
            "In re: Application of Jayawardena"
        ],
        "tips": [
            "Include both party names connected by 'v.' or 'vs.'",
            "Include 'In re:', 'Ex parte' when present",
            "Don't include case numbers or citations"
        ]
    },
    "COURT": {
        "description": "Names of courts (e.g., 'Supreme Court', 'Court of Appeal')",
        "examples": [
            "Supreme Court of Sri Lanka",
            "Court of Appeal",
            "High Court of Colombo",
            "District Court of Kandy",
            "Magistrate's Court"
        ],
        "tips": [
            "Include full court names",
            "Include location if mentioned (e.g., 'High Court of Colombo')",
            "Abbreviations are acceptable: 'SC', 'CA', 'HC'"
        ]
    },
    "JUDGE": {
        "description": "Names of judges (e.g., 'Justice Dep P.C.J.', 'Chief Justice Silva')",
        "examples": [
            "Justice Dep P.C.J.",
            "Chief Justice Mohan Pieris",
            "Marsoof J.",
            "S.N. Silva, C.J.",
            "Justice Fernando"
        ],
        "tips": [
            "Include title (Justice, Chief Justice)",
            "Include full name or initials",
            "Annotate each judge separately when multiple mentioned"
        ]
    },
    "STATUTE": {
        "description": "Statutory references (e.g., 'Prevention of Terrorism Act', 'Penal Code')",
        "examples": [
            "Prevention of Terrorism Act No. 48 of 1979",
            "Penal Code",
            "Civil Procedure Code",
            "Maintenance Act, No. 37 of 1999",
            "Constitution"
        ],
        "tips": [
            "Include act numbers when present",
            "Include year if mentioned",
            "Short forms acceptable: 'Penal Code', 'CPC'"
        ]
    },
    "ARTICLE": {
        "description": "Constitutional or statutory articles/sections (e.g., 'Article 12', 'Section 3(a)')",
        "examples": [
            "Article 12(1)",
            "Article 13",
            "Section 3(a)",
            "Section 121(2)",
            "Article 154P(3)(b)"
        ],
        "tips": [
            "Include article/section number",
            "Include subsections in parentheses",
            "Don't include surrounding text"
        ]
    },
    "LEGAL_PRINCIPLE": {
        "description": "Legal doctrines and principles (e.g., 'natural justice', 'res judicata')",
        "examples": [
            "natural justice",
            "res judicata",
            "ultra vires",
            "habeas corpus",
            "reasonable doubt",
            "burden of proof",
            "stare decisis"
        ],
        "tips": [
            "Include Latin legal phrases",
            "Include common law principles",
            "Include procedural concepts"
        ]
    },
    "DATE": {
        "description": "Dates relevant to the case (e.g., '12th January 2020', '2020-01-12')",
        "examples": [
            "12th January 2020",
            "2020-01-12",
            "January 12, 2020",
            "15.03.2019",
            "March 2018"
        ],
        "tips": [
            "Include judgment dates, hearing dates",
            "Various formats acceptable",
            "Include year for context"
        ]
    },
    "CITATION": {
        "description": "Legal citations (e.g., '[2020] 1 SLR 345', 'NLR 234')",
        "examples": [
            "[2020] 1 SLR 345",
            "2015 BALR 123",
            "74 NLR 567",
            "[2006] 2 Sri L R. 57",
            "1994, 3 Sri LR 353"
        ],
        "tips": [
            "Include full citation format",
            "Include year, volume, page numbers",
            "SLR = Sri Lanka Reports, NLR = New Law Reports"
        ]
    }
}


def save_label_studio_config():
    """Save Label Studio XML configuration."""
    output_dir = Path(__file__).parent.parent.parent / "data" / "training_data" / "ner_annotations"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = output_dir / "label_studio_config.xml"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(LABEL_STUDIO_CONFIG.strip())
    
    print(f"✅ Label Studio config saved to: {config_file}")
    return config_file


def save_annotation_guide():
    """Save annotation guidelines as JSON."""
    output_dir = Path(__file__).parent.parent.parent / "data" / "training_data" / "ner_annotations"
    
    guide_file = output_dir / "annotation_guide.json"
    with open(guide_file, 'w', encoding='utf-8') as f:
        json.dump(ENTITY_DESCRIPTIONS, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Annotation guide saved to: {guide_file}")
    return guide_file


def print_setup_instructions():
    """Print setup instructions for Label Studio."""
    print("\n" + "=" * 70)
    print("LABEL STUDIO SETUP INSTRUCTIONS")
    print("=" * 70)
    print()
    
    print("📦 STEP 1: Install Label Studio")
    print("-" * 70)
    print("Run in terminal:")
    print("  pip install label-studio")
    print()
    
    print("🚀 STEP 2: Start Label Studio")
    print("-" * 70)
    print("Run in terminal:")
    print("  label-studio start")
    print()
    print("This will:")
    print("  - Start the Label Studio server")
    print("  - Open your browser at http://localhost:8080")
    print("  - Create an admin account on first run")
    print()
    
    print("🎨 STEP 3: Create New Project")
    print("-" * 70)
    print("In the Label Studio interface:")
    print("  1. Click 'Create Project'")
    print("  2. Name: 'Legal NER - Sri Lankan Cases'")
    print("  3. Go to 'Labeling Setup' tab")
    print("  4. Click 'Code' view")
    print("  5. Copy the config from: label_studio_config.xml")
    print("  6. Save the project")
    print()
    
    print("📥 STEP 4: Import Annotation Batches")
    print("-" * 70)
    print("  1. Click 'Import' button")
    print("  2. Select JSON format")
    print("  3. Upload batch files from:")
    print("     data/training_data/ner_annotations/annotation_batches/")
    print("  4. Start with batch_001.json (50 texts)")
    print()
    
    print("✏️  STEP 5: Start Annotating!")
    print("-" * 70)
    print("Keyboard shortcuts:")
    print("  1 = CASE_NAME")
    print("  2 = COURT")
    print("  3 = JUDGE")
    print("  4 = STATUTE")
    print("  5 = ARTICLE")
    print("  6 = LEGAL_PRINCIPLE")
    print("  7 = DATE")
    print("  8 = CITATION")
    print()
    print("Annotation tips:")
    print("  - Select text with mouse, press hotkey to label")
    print("  - Click Submit to save and move to next")
    print("  - Use Skip if text has no entities")
    print("  - Review annotation_guide.json for detailed guidelines")
    print()
    
    print("📊 STEP 6: Export Annotations")
    print("-" * 70)
    print("After annotating a batch:")
    print("  1. Click 'Export' button")
    print("  2. Select 'JSON' format")
    print("  3. Save to: data/training_data/ner_annotations/completed/")
    print("  4. Run: python scripts/convert_label_studio_to_spacy.py")
    print()
    
    print("🎯 ANNOTATION TARGETS")
    print("-" * 70)
    print("  Minimum for training: 1,000 annotated texts")
    print("  Current progress: 10/1,000 (1%)")
    print("  Recommended daily goal: 50 texts (1 batch)")
    print("  Estimated time: 20 days @ 50 texts/day")
    print()
    
    print("💡 TIPS FOR EFFICIENT ANNOTATION")
    print("-" * 70)
    print("  - Focus on quality over speed")
    print("  - Take breaks every 50-100 annotations")
    print("  - Maintain consistency across batches")
    print("  - Use annotation_guide.json as reference")
    print("  - Mark uncertain cases for review")
    print()
    
    print("=" * 70)
    print()


def main():
    """Main setup function."""
    print("=" * 70)
    print("Setting up Label Studio for Legal NER Annotation")
    print("=" * 70)
    print()
    
    # Save configuration files
    config_file = save_label_studio_config()
    guide_file = save_annotation_guide()
    
    print()
    print(f"📁 Configuration files created:")
    print(f"   - {config_file.name}")
    print(f"   - {guide_file.name}")
    
    # Print setup instructions
    print_setup_instructions()


if __name__ == "__main__":
    main()
