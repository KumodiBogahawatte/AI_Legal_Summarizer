"""
Train Document Structure Classification Model
Fine-tunes BERT for classifying legal document sections

Sections: FACTS, ISSUES, LEGAL_ANALYSIS, REASONING, JUDGMENT, ORDERS
"""

import json
import torch
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List
from collections import Counter

from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    Trainer,
    TrainingArguments,
    EvalPrediction,
)
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
from torch.utils.data import Dataset

# Training configuration
MODEL_NAME = 'bert-base-uncased'  # Can switch to legal-bert if available
MAX_LENGTH = 256
BATCH_SIZE = 16
LEARNING_RATE = 2e-5
NUM_EPOCHS = 3  # Reduced from 5 for faster training
WARMUP_STEPS = 500
WEIGHT_DECAY = 0.01

# Label mapping
LABEL_MAP = {
    'FACTS': 0,
    'ISSUES': 1,
    'LEGAL_ANALYSIS': 2,
    'REASONING': 3,
    'JUDGMENT': 4,
    'ORDERS': 5,
}

ID_TO_LABEL = {v: k for k, v in LABEL_MAP.items()}
NUM_LABELS = len(LABEL_MAP)


class DocumentStructureDataset(Dataset):
    """PyTorch Dataset for document structure classification"""
    
    def __init__(self, data: List[Dict], tokenizer, max_length: int = MAX_LENGTH):
        self.data = data
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        text = item['text']
        label = item['label_id']
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt',
        )
        
        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(label, dtype=torch.long),
        }


class DocumentStructureTrainer:
    """Trainer for document structure classification model"""
    
    def __init__(self, data_dir: str, output_dir: str):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        print(f"Using device: {self.device}")
        
        # Initialize tokenizer and model
        print(f"\nLoading tokenizer and model: {MODEL_NAME}")
        self.tokenizer = BertTokenizer.from_pretrained(MODEL_NAME)
        self.model = BertForSequenceClassification.from_pretrained(
            MODEL_NAME,
            num_labels=NUM_LABELS,
        )
        
        self.model.to(self.device)
    
    def load_data(self) -> tuple:
        """Load train/dev/test datasets"""
        print(f"\nLoading training data from: {self.data_dir}")
        
        # Load splits
        with open(self.data_dir / 'train.json', 'r', encoding='utf-8') as f:
            train_data = json.load(f)
        
        with open(self.data_dir / 'dev.json', 'r', encoding='utf-8') as f:
            dev_data = json.load(f)
        
        with open(self.data_dir / 'test.json', 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        
        print(f"Train: {len(train_data)} examples")
        print(f"Dev: {len(dev_data)} examples")
        print(f"Test: {len(test_data)} examples")
        
        # Create datasets
        train_dataset = DocumentStructureDataset(train_data, self.tokenizer)
        dev_dataset = DocumentStructureDataset(dev_data, self.tokenizer)
        test_dataset = DocumentStructureDataset(test_data, self.tokenizer)
        
        return train_dataset, dev_dataset, test_dataset
    
    def compute_metrics(self, pred: EvalPrediction) -> Dict:
        """Compute evaluation metrics"""
        labels = pred.label_ids
        preds = pred.predictions.argmax(-1)
        
        # Calculate metrics
        accuracy = accuracy_score(labels, preds)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, preds, average='weighted', zero_division=0
        )
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
        }
    
    def train(self):
        """Train the model"""
        print("\n" + "="*70)
        print("TRAINING DOCUMENT STRUCTURE CLASSIFICATION MODEL")
        print("="*70)
        
        # Load data
        train_dataset, dev_dataset, test_dataset = self.load_data()
        
        # Check for existing checkpoint to resume from
        checkpoint_dir = None
        checkpoints = list(self.output_dir.glob('checkpoint-*'))
        if checkpoints:
            # Get the latest checkpoint
            checkpoint_dir = max(checkpoints, key=lambda p: int(p.name.split('-')[1]))
            print(f"\n✅ Found checkpoint: {checkpoint_dir.name}")
            print(f"   Resuming training from this checkpoint...")
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=str(self.output_dir),
            num_train_epochs=NUM_EPOCHS,
            per_device_train_batch_size=BATCH_SIZE,
            per_device_eval_batch_size=BATCH_SIZE,
            learning_rate=LEARNING_RATE,
            weight_decay=WEIGHT_DECAY,
            warmup_steps=WARMUP_STEPS,
            logging_dir=str(self.output_dir / 'logs'),
            logging_steps=50,
            eval_strategy='epoch',
            save_strategy='epoch',
            load_best_model_at_end=True,
            metric_for_best_model='f1',
            greater_is_better=True,
            save_total_limit=2,
            report_to='none',
            resume_from_checkpoint=str(checkpoint_dir) if checkpoint_dir else None,
        )
        
        # Create trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=dev_dataset,
            compute_metrics=self.compute_metrics,
        )
        
        # Train
        print(f"\n{'='*70}")
        print(f"Starting training for {NUM_EPOCHS} epochs...")
        print(f"{'='*70}\n")
        
        train_result = trainer.train()
        
        # Save model
        model_path = self.output_dir / 'final_model'
        trainer.save_model(str(model_path))
        self.tokenizer.save_pretrained(str(model_path))
        
        print(f"\n✅ Model saved to: {model_path}")
        
        # Evaluate on test set
        print(f"\n{'='*70}")
        print("EVALUATING ON TEST SET")
        print(f"{'='*70}\n")
        
        test_results = trainer.evaluate(test_dataset)
        
        # Get predictions for detailed metrics
        predictions = trainer.predict(test_dataset)
        preds = predictions.predictions.argmax(-1)
        labels = predictions.label_ids
        
        # Classification report
        print("\nDetailed Classification Report:")
        print("-"*70)
        report = classification_report(
            labels,
            preds,
            target_names=[ID_TO_LABEL[i] for i in range(NUM_LABELS)],
            digits=4,
        )
        print(report)
        
        # Save results
        results = {
            'training_args': {
                'model_name': MODEL_NAME,
                'max_length': MAX_LENGTH,
                'batch_size': BATCH_SIZE,
                'learning_rate': LEARNING_RATE,
                'num_epochs': NUM_EPOCHS,
                'warmup_steps': WARMUP_STEPS,
                'weight_decay': WEIGHT_DECAY,
            },
            'training_results': {
                'train_loss': float(train_result.training_loss),
                'train_runtime': train_result.metrics['train_runtime'],
                'train_samples_per_second': train_result.metrics['train_samples_per_second'],
            },
            'test_results': {
                'accuracy': float(test_results['eval_accuracy']),
                'precision': float(test_results['eval_precision']),
                'recall': float(test_results['eval_recall']),
                'f1': float(test_results['eval_f1']),
            },
            'classification_report': report,
            'timestamp': datetime.now().isoformat(),
        }
        
        results_file = self.output_dir / 'training_results.json'
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"\n✅ Results saved to: {results_file}")
        
        # Print summary
        self.print_summary(results)
        
        return results
    
    def print_summary(self, results: Dict):
        """Print training summary"""
        print("\n" + "="*70)
        print("TRAINING SUMMARY")
        print("="*70)
        print(f"Model: {MODEL_NAME}")
        print(f"Device: {self.device}")
        print(f"\nTraining Metrics:")
        print(f"  Training Loss: {results['training_results']['train_loss']:.4f}")
        print(f"  Training Time: {results['training_results']['train_runtime']:.2f}s")
        
        print(f"\nTest Set Performance:")
        print(f"  Accuracy:  {results['test_results']['accuracy']:.4f} ({results['test_results']['accuracy']*100:.2f}%)")
        print(f"  Precision: {results['test_results']['precision']:.4f}")
        print(f"  Recall:    {results['test_results']['recall']:.4f}")
        print(f"  F1 Score:  {results['test_results']['f1']:.4f}")
        
        print("="*70)


def main():
    """Main execution function"""
    data_dir = r'e:\ai-legal-summarizer\data\training_data\document_structure_training'
    output_dir = r'e:\ai-legal-summarizer\backend\models\document_classifier'
    
    print("="*70)
    print("DOCUMENT STRUCTURE CLASSIFICATION - MODEL TRAINING")
    print("="*70)
    print(f"Training data: {data_dir}")
    print(f"Output directory: {output_dir}")
    print(f"Model: {MODEL_NAME}")
    print(f"Max sequence length: {MAX_LENGTH}")
    print(f"Batch size: {BATCH_SIZE}")
    print(f"Learning rate: {LEARNING_RATE}")
    print(f"Epochs: {NUM_EPOCHS}")
    print("="*70)
    
    # Check if transformers is installed
    try:
        import transformers
        print(f"\n✅ Transformers version: {transformers.__version__}")
    except ImportError:
        print("\n❌ Error: transformers library not installed")
        print("Install with: pip install transformers torch scikit-learn")
        return
    
    # Create trainer and train
    trainer = DocumentStructureTrainer(data_dir, output_dir)
    results = trainer.train()
    
    print("\n✅ Training complete!")
    print(f"📁 Model saved in: {output_dir}")
    print(f"🎯 Test F1 Score: {results['test_results']['f1']:.4f}")


if __name__ == '__main__':
    main()
