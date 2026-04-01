"""
Model Management Service - Handles ML model versioning and management
"""

import os
import json
import joblib
import shutil
from datetime import datetime
import pandas as pd
import numpy as np
from pathlib import Path

class ModelManagementService:
    """
    Service for managing ML models
    Handles model versioning, performance tracking, and model updates
    """
    
    def __init__(self, model_dir='ml_model/saved_models', versions_dir='ml_model/model_versions'):
        """
        Initialize model management service
        
        Args:
            model_dir: directory for current models
            versions_dir: directory for versioned models
        """
        self.model_dir = Path(model_dir)
        self.versions_dir = Path(versions_dir)
        
        # Create directories if they don't exist
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.versions_dir.mkdir(parents=True, exist_ok=True)
    
    def list_models(self):
        """
        List all available models
        
        Returns:
            dict with model information
        """
        models = []
        
        # List current models
        for file in self.model_dir.glob('*.pkl'):
            if file.name != 'scaler.pkl':
                model_info = self._get_model_info(file)
                models.append(model_info)
        
        return {
            'success': True,
            'models': models,
            'count': len(models)
        }
    
    def _get_model_info(self, model_path):
        """Get information about a model file"""
        stats = model_path.stat()
        
        info = {
            'name': model_path.name,
            'path': str(model_path),
            'size_kb': round(stats.st_size / 1024, 2),
            'modified': datetime.fromtimestamp(stats.st_mtime).isoformat()
        }
        
        # Try to load metadata
        metadata_path = model_path.parent / 'model_metadata.json'
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                all_metadata = json.load(f)
                model_key = model_path.stem
                if model_key in all_metadata:
                    info['metadata'] = all_metadata[model_key]
        
        return info
    
    def list_versions(self):
        """
        List all model versions
        
        Returns:
            dict with version information
        """
        versions = []
        
        for version_dir in self.versions_dir.iterdir():
            if version_dir.is_dir():
                version_info = self._get_version_info(version_dir)
                versions.append(version_info)
        
        # Sort by version (newest first)
        versions.sort(key=lambda x: x['version'], reverse=True)
        
        return {
            'success': True,
            'versions': versions,
            'count': len(versions)
        }
    
    def _get_version_info(self, version_dir):
        """Get information about a model version"""
        info = {
            'version': version_dir.name,
            'path': str(version_dir),
            'created': datetime.fromtimestamp(version_dir.stat().st_ctime).isoformat()
        }
        
        # Load metadata if exists
        metadata_path = version_dir / 'metadata.json'
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                info['metadata'] = json.load(f)
        
        return info
    
    def save_model_version(self, model, scaler, feature_names, version_name, metrics=None, notes=''):
        """
        Save a new model version
        
        Args:
            model: trained model object
            scaler: fitted scaler object
            feature_names: list of feature names
            version_name: version identifier (e.g., 'v2.0.0')
            metrics: performance metrics dict
            notes: version notes
        
        Returns:
            dict with save result
        """
        version_dir = self.versions_dir / version_name
        version_dir.mkdir(exist_ok=True)
        
        # Save model and scaler
        joblib.dump(model, version_dir / 'model.pkl')
        joblib.dump(scaler, version_dir / 'scaler.pkl')
        
        # Save feature names
        with open(version_dir / 'feature_names.json', 'w') as f:
            json.dump(feature_names, f)
        
        # Save metadata
        metadata = {
            'version': version_name,
            'save_date': datetime.now().isoformat(),
            'model_type': type(model).__name__,
            'metrics': metrics or {},
            'notes': notes,
            'features': feature_names
        }
        
        with open(version_dir / 'metadata.json', 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Update current model (optional - copy to saved_models)
        self._update_current_model(model, scaler, feature_names, version_name, metrics)
        
        return {
            'success': True,
            'version': version_name,
            'path': str(version_dir),
            'message': f'Model version {version_name} saved successfully'
        }
    
    def _update_current_model(self, model, scaler, feature_names, version_name, metrics):
        """Update the current model (copy to saved_models)"""
        # Save model
        joblib.dump(model, self.model_dir / 'logistic_regression.pkl')
        
        # Save scaler
        joblib.dump(scaler, self.model_dir / 'scaler.pkl')
        
        # Save feature names
        with open(self.model_dir / 'feature_names.json', 'w') as f:
            json.dump(feature_names, f)
        
        # Update metadata
        metadata_path = self.model_dir / 'model_metadata.json'
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                all_metadata = json.load(f)
        else:
            all_metadata = {}
        
        all_metadata['current_version'] = version_name
        all_metadata[version_name] = {
            'save_date': datetime.now().isoformat(),
            'metrics': metrics,
            'notes': f'Current model updated to {version_name}'
        }
        
        with open(metadata_path, 'w') as f:
            json.dump(all_metadata, f, indent=2)
        
        # Record best model
        with open(self.model_dir / 'best_model.txt', 'w') as f:
            f.write('logistic_regression')
    
    def load_version(self, version_name):
        """
        Load a specific model version
        
        Args:
            version_name: version identifier
        
        Returns:
            dict with loaded model and metadata
        """
        version_dir = self.versions_dir / version_name
        
        if not version_dir.exists():
            return {'success': False, 'error': f'Version {version_name} not found'}
        
        try:
            model = joblib.load(version_dir / 'model.pkl')
            scaler = joblib.load(version_dir / 'scaler.pkl')
            
            with open(version_dir / 'feature_names.json', 'r') as f:
                feature_names = json.load(f)
            
            metadata = {}
            metadata_path = version_dir / 'metadata.json'
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            
            return {
                'success': True,
                'version': version_name,
                'model': model,
                'scaler': scaler,
                'feature_names': feature_names,
                'metadata': metadata
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def compare_versions(self, version_names=None):
        """
        Compare performance of different versions
        
        Args:
            version_names: list of versions to compare (None = all)
        
        Returns:
            DataFrame with comparison
        """
        versions = []
        
        if version_names:
            # Load specified versions
            for vname in version_names:
                result = self.load_version(vname)
                if result['success']:
                    versions.append(result)
        else:
            # Load all versions
            for version_dir in self.versions_dir.iterdir():
                if version_dir.is_dir():
                    result = self.load_version(version_dir.name)
                    if result['success']:
                        versions.append(result)
        
        # Create comparison dataframe
        comparison = []
        for v in versions:
            metadata = v.get('metadata', {})
            metrics = metadata.get('metrics', {})
            
            comparison.append({
                'version': v['version'],
                'model_type': metadata.get('model_type', 'Unknown'),
                'save_date': metadata.get('save_date', '')[:10],
                'accuracy': metrics.get('accuracy', 0),
                'precision': metrics.get('precision', 0),
                'recall': metrics.get('recall', 0),
                'f1': metrics.get('f1', 0),
                'roc_auc': metrics.get('roc_auc', 0)
            })
        
        # Sort by version
        comparison.sort(key=lambda x: x['version'], reverse=True)
        
        return {
            'success': True,
            'comparison': comparison,
            'count': len(comparison)
        }
    
    def delete_version(self, version_name):
        """
        Delete a model version
        
        Args:
            version_name: version to delete
        
        Returns:
            dict with deletion result
        """
        version_dir = self.versions_dir / version_name
        
        if not version_dir.exists():
            return {'success': False, 'error': f'Version {version_name} not found'}
        
        # Don't delete if it's the current version
        metadata_path = self.model_dir / 'model_metadata.json'
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            if metadata.get('current_version') == version_name:
                return {
                    'success': False, 
                    'error': f'Cannot delete current version {version_name}'
                }
        
        # Delete directory
        shutil.rmtree(version_dir)
        
        return {
            'success': True,
            'message': f'Version {version_name} deleted successfully'
        }
    
    def get_performance_history(self):
        """
        Get model performance history
        
        Returns:
            dict with performance trends
        """
        versions = self.list_versions()
        
        history = []
        for v in versions.get('versions', []):
            metadata = v.get('metadata', {})
            metrics = metadata.get('metrics', {})
            
            if metrics:
                history.append({
                    'version': v['version'],
                    'date': v.get('created', '')[:10],
                    'accuracy': metrics.get('accuracy', 0),
                    'precision': metrics.get('precision', 0),
                    'recall': metrics.get('recall', 0),
                    'f1': metrics.get('f1', 0)
                })
        
        return {
            'success': True,
            'history': history,
            'count': len(history)
        }
    
    def rollback_to_version(self, version_name):
        """
        Rollback to a previous version (make it current)
        
        Args:
            version_name: version to rollback to
        
        Returns:
            dict with rollback result
        """
        # Load the version
        result = self.load_version(version_name)
        
        if not result['success']:
            return result
        
        # Update current model
        self._update_current_model(
            result['model'],
            result['scaler'],
            result['feature_names'],
            version_name,
            result.get('metadata', {}).get('metrics', {})
        )
        
        return {
            'success': True,
            'message': f'Rolled back to version {version_name}',
            'version': result['metadata']
        }