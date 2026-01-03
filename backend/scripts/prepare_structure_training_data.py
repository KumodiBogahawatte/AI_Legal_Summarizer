"""
Prepare Training Data for Document Structure Classification
Converts annotated paragraphs into format suitable for BERT training

Input: Auto-annotated paragraphs with section labels
Output: Train/Dev/Test splits in JSON format for BERT fine-tuning
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Tuple
from collections import Counter
from datetime import datetime

# Set random seed for reproducibility
RANDOM_SEED = 42
random.seed(RANDOM_SEED)

# Train/Dev/Test split ratios
TRAIN_RATIO = 0.70
DEV_RATIO = 0.15
TEST_RATIO = 0.15

# Minimum confidence threshold for including annotations
MIN_CONFIDENCE = 1.0

# Label mapping
LABEL_MAP = {
    'FACTS': 0,
    'ISSUES': 1,
    'LEGAL_ANALYSIS': 2,
    'REASONING': 3,
    'JUDGMENT': 4,
    'ORDERS': 5,
}

# Reverse mapping
ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}


class TrainingDataPreparator:
    """Prepares training data for BERT-based document structure classifier"""
    
    def __init__(self, annotations_file: str, output_dir: str):
        self.annotations_file = Path(annotations_file)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.stats = {
            'total_paragraphs': 0,
            'filtered_paragraphs': 0,
            'train_size': 0,
            'dev_size': 0,
            'test_size': 0,
            'label_distribution': Counter(),
        }
    
    def load_annotations(self) -> List[Dict]:
        """Load annotated documents"""
        print(f"Loading annotations from: {self.annotations_file}")
        
        with open(self.annotations_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        annotations = data.get('annotations', [])
        print(f"Loaded {len(annotations)} annotated documents")
        
        return annotations
    
    def extract_training_examples(self, annotations: List[Dict]) -> List[Dict]:
        """Extract individual training examples from annotations"""
        examples = []
        
        for doc in annotations:
            doc_name = doc.get('file_name', 'unknown')
            
            for para in doc.get('annotations', []):
                section = para.get('section')
                confidence = para.get('confidence', 0)
                text = para.get('text', '').strip()
                
                # Filter criteria
                if section == 'UNLABELED':
                    continue
                
                if confidence < MIN_CONFIDENCE:
                    continue
                
                if len(text) < 20:  # Too short
                    continue
                
                if section not in LABEL_MAP:
                    continue
                
                # Create training example
                example = {
                    'text': text,
                    'label': section,
                    'label_id': LABEL_MAP[section],
                    'confidence': confidence,
                    'source_document': doc_name,
                    'paragraph_id': para.get('paragraph_id', -1),
                }
                
                examples.append(example)
                self.stats['label_distribution'][section] += 1
        
        self.stats['total_paragraphs'] = len(examples)
        
        print(f"Extracted {len(examples)} training examples")
        return examples
    
    def balance_dataset(self, examples: List[Dict], max_per_class: int = None) -> List[Dict]:
        """Balance dataset by downsampling majority classes"""
        if max_per_class is None:
            # Find median class size
            class_counts = Counter(ex['label'] for ex in examples)
            max_per_class = sorted(class_counts.values())[len(class_counts) // 2]
        
        print(f"\nBalancing dataset (max {max_per_class} examples per class)...")
        
        # Group by label
        by_label = {}
        for ex in examples:
            label = ex['label']
            if label not in by_label:
                by_label[label] = []
            by_label[label].append(ex)
        
        # Sample from each class
        balanced = []
        for label, label_examples in by_label.items():
            if len(label_examples) <= max_per_class:
                balanced.extend(label_examples)
                print(f"  {label}: Kept all {len(label_examples)} examples")
            else:
                # Sort by confidence and take top max_per_class
                sorted_examples = sorted(label_examples, key=lambda x: x['confidence'], reverse=True)
                sampled = sorted_examples[:max_per_class]
                balanced.extend(sampled)
                print(f"  {label}: Downsampled from {len(label_examples)} to {max_per_class}")
        
        random.shuffle(balanced)
        return balanced
    
    def split_dataset(self, examples: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """Split dataset into train/dev/test sets"""
        # Shuffle
        random.shuffle(examples)
        
        total = len(examples)
        train_size = int(total * TRAIN_RATIO)
        dev_size = int(total * DEV_RATIO)
        
        train = examples[:train_size]
        dev = examples[train_size:train_size + dev_size]
        test = examples[train_size + dev_size:]
        
        self.stats['train_size'] = len(train)
        self.stats['dev_size'] = len(dev)
        self.stats['test_size'] = len(test)
        
        print(f"\nDataset split:")
        print(f"  Train: {len(train)} examples ({len(train)/total*100:.1f}%)")
        print(f"  Dev:   {len(dev)} examples ({len(dev)/total*100:.1f}%)")
        print(f"  Test:  {len(test)} examples ({len(test)/total*100:.1f}%)")
        
        return train, dev, test
    
    def save_splits(self, train: List[Dict], dev: List[Dict], test: List[Dict]):
        """Save train/dev/test splits to files"""
        # Save individual splits
        splits = {
            'train': train,
            'dev': dev,
            'test': test,
        }
        
        for split_name, split_data in splits.items():
            output_file = self.output_dir / f'{split_name}.json'
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(split_data, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Saved {split_name} split: {output_file} ({len(split_data)} examples)")
        
        # Save combined training data with metadata
        combined_file = self.output_dir / 'training_data.json'
        combined_data = {
            'metadata': {
                'creation_date': datetime.now().isoformat(),
                'description': 'Training data for document structure classification',
                'total_examples': len(train) + len(dev) + len(test),
                'train_size': len(train),
                'dev_size': len(dev),
                'test_size': len(test),
                'num_labels': len(LABEL_MAP),
                'label_map': LABEL_MAP,
                'id_to_label': ID_TO_LABEL,
                'random_seed': RANDOM_SEED,
            },
            'statistics': self.stats,
            'splits': {
                'train': train,
                'dev': dev,
                'test': test,
            },
        }
        
        with open(combined_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Saved combined training data: {combined_file}")
    
    def print_statistics(self):
        """Print dataset statistics"""
        print("\n" + "="*70)
        print("TRAINING DATA STATISTICS")
        print("="*70)
        print(f"Total examples: {self.stats['total_paragraphs']}")
        print(f"Train: {self.stats['train_size']}")
        print(f"Dev: {self.stats['dev_size']}")
        print(f"Test: {self.stats['test_size']}")
        print(f"\nLabel Distribution:")
        print("-"*70)
        
        for label in sorted(LABEL_MAP.keys(), key=lambda x: LABEL_MAP[x]):
            count = self.stats['label_distribution'][label]
            percentage = (count / self.stats['total_paragraphs'] * 100) if self.stats['total_paragraphs'] > 0 else 0
            print(f"  {LABEL_MAP[label]} - {label:20s}: {count:5d} ({percentage:5.2f}%)")
        
        print("="*70)
    
    def process(self, balance: bool = False, max_per_class: int = None):
        """Main processing pipeline"""
        # Load annotations
        annotations = self.load_annotations()
        
        # Extract examples
        examples = self.extract_training_examples(annotations)
        
        if len(examples) == 0:
            print("❌ No training examples found!")
            return
        
        # Balance if requested
        if balance:
            examples = self.balance_dataset(examples, max_per_class)
        
        # Split dataset
        train, dev, test = self.split_dataset(examples)
        
        # Save splits
        self.save_splits(train, dev, test)
        
        # Print statistics
        self.print_statistics()


def main():
    """Main execution function"""
    annotations_file = r'e:\ai-legal-summarizer\data\training_data\document_structure_annotations\document_structure_annotations.json'
    output_dir = r'e:\ai-legal-summarizer\data\training_data\document_structure_training'
    
    print("="*70)
    print("PREPARING TRAINING DATA FOR DOCUMENT STRUCTURE CLASSIFICATION")
    print("="*70)
    print(f"Input: {annotations_file}")
    print(f"Output: {output_dir}")
    print("="*70)
    print()
    
    preparator = TrainingDataPreparator(annotations_file, output_dir)
    
    # Process with balancing
    preparator.process(balance=True, max_per_class=1000)
    
    print("\n✅ Training data preparation complete!")
    print(f"📁 Training files saved in: {output_dir}")
    print("\nReady for BERT model training!")


if __name__ == '__main__':
    main()
