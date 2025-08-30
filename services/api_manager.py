# services/api_manager.py (Enhanced Version)
import json
import time
import random
from pathlib import Path
from typing import List, Dict, Optional
import streamlit as st

class APIKeyManager:
    def __init__(self, keys_file: str = "config/api_keys.json"):
        self.keys_file = Path(keys_file)
        self.api_keys = self._load_keys()
        self.settings = self._load_settings()
        self.usage_tracker = {}
        self.rate_limits = {}
        self.error_counts = {}
        self.current_index = 0
        
    def _load_keys(self) -> List[str]:
        """Load API keys from JSON file"""
        try:
            if self.keys_file.exists():
                with open(self.keys_file, 'r') as f:
                    data = json.load(f)
                    return data.get('keys', [])
        except Exception as e:
            st.error(f"Error loading API keys: {e}")
        return []
    
    def _load_settings(self) -> Dict:
        """Load settings from JSON file"""
        default_settings = {
            "rotation_strategy": "round_robin",
            "error_cooldown_minutes": 5,
            "rate_limit_cooldown_minutes": 1,
            "max_retries_per_key": 3
        }
        
        try:
            if self.keys_file.exists():
                with open(self.keys_file, 'r') as f:
                    data = json.load(f)
                    return data.get('settings', default_settings)
        except:
            pass
        return default_settings
    
    def get_next_key(self) -> Optional[str]:
        """Get next available API key with intelligent rotation"""
        if not self.api_keys:
            return None
        
        # Try all keys once
        attempts = 0
        start_index = self.current_index
        
        while attempts < len(self.api_keys):
            current_key = self.api_keys[self.current_index]
            
            if self._is_key_available(current_key):
                self._update_usage(current_key)
                return current_key
            
            # Move to next key
            self.current_index = (self.current_index + 1) % len(self.api_keys)
            attempts += 1
            
            # If we've gone full circle, break
            if self.current_index == start_index and attempts > 0:
                break
        
        return None  # All keys are unavailable
    
    def _is_key_available(self, key: str) -> bool:
        """Check if API key is available"""
        current_time = time.time()
        
        # Check rate limits
        if key in self.rate_limits:
            cooldown = self.settings['rate_limit_cooldown_minutes'] * 60
            if (current_time - self.rate_limits[key]) < cooldown:
                return False
        
        # Check error cooldowns
        if key in self.error_counts:
            error_cooldown = self.settings['error_cooldown_minutes'] * 60
            last_error_time = self.error_counts[key].get('last_error', 0)
            if (current_time - last_error_time) < error_cooldown:
                return False
        
        return True
    
    def get_usage_stats(self) -> Dict:
        """Get detailed usage statistics"""
        total_usage = sum(self.usage_tracker.values())
        available_keys = sum(1 for key in self.api_keys if self._is_key_available(key))
        
        return {
            'total_keys': len(self.api_keys),
            'active_keys': available_keys,
            'total_requests': total_usage,
            'usage_per_key': self.usage_tracker.copy(),
            'average_per_key': total_usage / len(self.api_keys) if self.api_keys else 0,
            'estimated_daily_capacity': len(self.api_keys) * 1500  # Free tier daily limit
        }
