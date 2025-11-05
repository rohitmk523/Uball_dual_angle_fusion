#!/usr/bin/env python3
"""
YOLOv11 Custom Training Pipeline for Basketball Detection

This script handles the complete training pipeline for basketball and hoop detection
using YOLOv11 models with the custom dataset.

Usage:
    python custom_training.py --action setup
    python custom_training.py --action train
    python custom_training.py --action evaluate --model_path runs/detect/train/weights/best.pt
"""

import argparse
import os
import yaml
from pathlib import Path
import torch
from ultralytics import YOLO
import shutil

class BasketballTrainer:
    def __init__(self, dataset_yaml='basketball_dataset/data.yaml'):
        """Initialize the basketball trainer"""
        self.dataset_yaml = dataset_yaml
        self.project_root = Path.cwd()
        self.runs_dir = self.project_root / 'runs'
        
    def setup_training_environment(self):
        """Setup the training environment and verify dataset"""
        print("Setting up training environment...")
        
        # Check if dataset exists
        dataset_path = Path(self.dataset_yaml)
        if not dataset_path.exists():
            print(f"❌ Dataset configuration not found: {dataset_path}")
            print("Please run: python download_dataset.py")
            return False
            
        # Verify dataset structure
        with open(dataset_path, 'r') as f:
            dataset_config = yaml.safe_load(f)
            
        required_keys = ['train', 'val', 'nc', 'names']
        for key in required_keys:
            if key not in dataset_config:
                print(f"❌ Missing key in dataset config: {key}")
                return False
                
        print(f"✓ Dataset configuration verified")
        print(f"✓ Classes: {dataset_config['nc']} - {dataset_config['names']}")
        
        # Check for images and labels
        for split in ['train', 'val']:
            if split in dataset_config:
                # Handle both absolute and relative paths
                dataset_base = Path(dataset_config.get('path', dataset_path.parent))
                split_path = dataset_base / dataset_config[split]
                
                # The split path should point to images directory, labels should be sibling
                if split_path.name == 'images':
                    images_dir = split_path
                    labels_dir = split_path.parent / 'labels'
                else:
                    # If path doesn't end in images, assume it's the parent
                    images_dir = split_path / 'images' if not split_path.name == 'images' else split_path
                    labels_dir = split_path.parent / 'labels' if split_path.name == 'images' else split_path / 'labels'
                
                if images_dir.exists() and labels_dir.exists():
                    image_count = len(list(images_dir.glob('*.jpg')) + list(images_dir.glob('*.png')))
                    label_count = len(list(labels_dir.glob('*.txt')))
                    print(f"✓ {split}: {image_count} images, {label_count} labels")
                else:
                    print(f"❌ Missing directories for {split} split")
                    print(f"   Expected images: {images_dir}")
                    print(f"   Expected labels: {labels_dir}")
                    return False
        
        # Create runs directory
        self.runs_dir.mkdir(exist_ok=True)
        print(f"✓ Training environment ready")
        return True
        
    def train_model(self, model_size='n', epochs=100, batch_size=16, imgsz=640, device='auto'):
        """Train YOLOv11 model on basketball dataset"""
        
        if not self.setup_training_environment():
            return None
            
        # Auto-detect best device for Mac users
        if device == 'auto':
            if torch.backends.mps.is_available():
                device = 'mps'
                print("🚀 Using MacBook GPU (MPS) acceleration")
            elif torch.cuda.is_available():
                device = 'cuda'
                print("🚀 Using CUDA GPU acceleration")
            else:
                device = 'cpu'
                print("ℹ️ Using CPU")
        else:
            print(f"🔧 Using specified device: {device}")
            
        print(f"\nStarting YOLOv11{model_size} training...")
        print(f"Epochs: {epochs}, Batch size: {batch_size}, Image size: {imgsz}, Device: {device}")
        
        # Initialize model
        model_name = f'yolo11{model_size}.pt'
        model = YOLO(model_name)
        
        # Training parameters
        train_params = {
            'data': self.dataset_yaml,
            'epochs': epochs,
            'batch': batch_size,
            'imgsz': imgsz,
            'device': device,
            'project': 'runs/detect',
            'name': f'basketball_yolo11{model_size}',
            'save': True,
            'save_period': 10,
            'cache': True,
            'mixup': 0.1,
            'copy_paste': 0.1,
            'degrees': 15.0,
            'translate': 0.1,
            'scale': 0.5,
            'shear': 2.0,
            'perspective': 0.0,
            'flipud': 0.0,
            'fliplr': 0.5,
            'mosaic': 1.0,
            'hsv_h': 0.015,
            'hsv_s': 0.7,
            'hsv_v': 0.4,
        }
        
        try:
            # Start training
            results = model.train(**train_params)
            
            print("✓ Training completed successfully!")
            print(f"✓ Best model saved to: runs/detect/basketball_yolo11{model_size}/weights/best.pt")
            print(f"✓ Last model saved to: runs/detect/basketball_yolo11{model_size}/weights/last.pt")
            
            return results
            
        except Exception as e:
            print(f"❌ Training failed: {e}")
            return None
            
    def validate_model(self, model_path=None, dataset_yaml=None):
        """Validate trained model performance"""
        
        if model_path is None:
            # Find the latest training run
            detect_runs = list(Path('runs/detect').glob('basketball_yolo11*'))
            if not detect_runs:
                print("❌ No training runs found")
                return None
            latest_run = max(detect_runs, key=os.path.getctime)
            model_path = latest_run / 'weights' / 'best.pt'
            
        if dataset_yaml is None:
            dataset_yaml = self.dataset_yaml
            
        if not Path(model_path).exists():
            print(f"❌ Model not found: {model_path}")
            return None
            
        print(f"Validating model: {model_path}")
        
        # Load model and validate
        model = YOLO(model_path)
        results = model.val(data=dataset_yaml)
        
        print("✓ Validation completed")
        print(f"mAP50: {results.box.map50:.3f}")
        print(f"mAP50-95: {results.box.map:.3f}")
        
        return results
        
    def export_model(self, model_path, format='onnx'):
        """Export model to different formats"""
        
        if not Path(model_path).exists():
            print(f"❌ Model not found: {model_path}")
            return None
            
        print(f"Exporting model to {format} format...")
        
        model = YOLO(model_path)
        exported_model = model.export(format=format)
        
        print(f"✓ Model exported: {exported_model}")
        return exported_model

def main():
    parser = argparse.ArgumentParser(description='Basketball Detection Training Pipeline')
    parser.add_argument('--action', type=str, required=True,
                       choices=['setup', 'train', 'validate', 'export'],
                       help='Action to perform')
    parser.add_argument('--model_size', type=str, default='n',
                       choices=['n', 's', 'm', 'l', 'x'],
                       help='YOLOv11 model size (n=nano, s=small, m=medium, l=large, x=xlarge)')
    parser.add_argument('--epochs', type=int, default=100,
                       help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=16,
                       help='Batch size for training')
    parser.add_argument('--imgsz', type=int, default=640,
                       help='Input image size')
    parser.add_argument('--dataset_yaml', type=str, default='basketball_dataset/data.yaml',
                       help='Path to dataset YAML configuration')
    parser.add_argument('--model_path', type=str,
                       help='Path to model for validation/export')
    parser.add_argument('--export_format', type=str, default='onnx',
                       help='Export format (onnx, torchscript, etc.)')
    parser.add_argument('--device', type=str, default='auto',
                       help='Training device (cpu, cuda, mps, auto) - auto detects best available')
    
    args = parser.parse_args()
    
    # Initialize trainer
    trainer = BasketballTrainer(args.dataset_yaml)
    
    if args.action == 'setup':
        print("="*60)
        print("SETTING UP TRAINING ENVIRONMENT")
        print("="*60)
        success = trainer.setup_training_environment()
        if success:
            print("\n🏀 Training environment ready!")
            print("Next step: python custom_training.py --action train")
        else:
            print("\n❌ Setup failed. Please check the errors above.")
            
    elif args.action == 'train':
        print("="*60)
        print("STARTING YOLOV11 TRAINING")
        print("="*60)
        results = trainer.train_model(
            model_size=args.model_size,
            epochs=args.epochs,
            batch_size=args.batch_size,
            imgsz=args.imgsz,
            device=args.device
        )
        if results:
            print("\n🏀 Training completed successfully!")
            print("Next step: python custom_training.py --action validate")
        else:
            print("\n❌ Training failed. Please check the errors above.")
            
    elif args.action == 'validate':
        print("="*60)
        print("VALIDATING MODEL PERFORMANCE")
        print("="*60)
        results = trainer.validate_model(args.model_path, args.dataset_yaml)
        if results:
            print("\n🏀 Validation completed!")
        else:
            print("\n❌ Validation failed.")
            
    elif args.action == 'export':
        if not args.model_path:
            print("❌ --model_path required for export")
            return
        print("="*60)
        print("EXPORTING MODEL")
        print("="*60)
        exported = trainer.export_model(args.model_path, args.export_format)
        if exported:
            print(f"\n🏀 Model exported successfully!")
        else:
            print("\n❌ Export failed.")

if __name__ == "__main__":
    main()