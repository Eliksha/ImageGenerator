import json
import time
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
        
        # Debug: Print loaded keys
        st.write(f"🔍 DEBUG: Loaded {len(self.api_keys)} API keys")
        if self.api_keys:
            for i, key in enumerate(self.api_keys):
                st.write(f"🔑 Key {i+1}: {key[:10]}...")

    def _load_keys(self) -> List[str]:
        """Load API keys from JSON file"""
        try:
            if self.keys_file.exists():
                with open(self.keys_file, 'r') as f:
                    data = json.load(f)
                    keys = data.get('keys', [])
                    print(f"DEBUG: Loaded {len(keys)} keys from {self.keys_file}")
                    return keys
            else:
                print(f"DEBUG: File {self.keys_file} does not exist!")
                st.error(f"❌ Config file not found: {self.keys_file}")
        except Exception as e:
            st.error(f"Error loading API keys: {e}")
            print(f"DEBUG: Error loading keys: {e}")
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
        except Exception:
            pass
        return default_settings

    def add_api_keys(self, keys: List[str]) -> bool:
        """Save API keys to JSON file and update API keys list"""
        try:
            keys = keys[:10]  # limit to max 10 keys
            data = {"keys": keys, "settings": self.settings}
            self.keys_file.parent.mkdir(parents=True, exist_ok=True)  # Create directories
            self.keys_file.write_text(json.dumps(data, indent=2))
            self.api_keys = keys
            self.reset_usage()
            print(f"DEBUG: Saved {len(keys)} keys to {self.keys_file}")
            return True
        except Exception as e:
            st.error(f"Failed to save API keys: {e}")
            return False

    def get_next_key(self) -> Optional[str]:
        """Get next available API key by rotating through keys"""
        if not self.api_keys:
            print("DEBUG: No API keys available!")
            return None

        attempts = 0
        total_keys = len(self.api_keys)
        
        while attempts < total_keys:
            key = self.api_keys[self.current_index]
            print(f"DEBUG: Checking key {self.current_index}: {key[:10]}...")
            
            if self._is_key_available(key):
                self._update_usage(key)
                print(f"DEBUG: Using key: {key[:10]}...")
                return key
            
            print(f"DEBUG: Key {key[:10]}... not available, trying next")
            self.current_index = (self.current_index + 1) % total_keys
            attempts += 1

        print("DEBUG: All keys exhausted!")
        return None
    
    def _is_key_available(self, key: str) -> bool:
        """Check if API key is available with conservative cooldowns"""
        now = time.time()
        
        # Increased cooldowns for free tier
        rate_limit_cd = self.settings.get('rate_limit_cooldown_minutes', 5) * 60  # 5 min default
        error_cd = self.settings.get('error_cooldown_minutes', 15) * 60  # 15 min default
        
        last_used = self.rate_limits.get(key, 0)
        if now - last_used < rate_limit_cd:
            remaining = int(rate_limit_cd - (now - last_used))
            print(f"DEBUG: Key {key[:10]}... on cooldown for {remaining}s more")
            return False

        last_err = self.error_counts.get(key, {}).get('last_error', 0)
        if now - last_err < error_cd:
            remaining = int(error_cd - (now - last_err))
            print(f"DEBUG: Key {key[:10]}... on error cooldown for {remaining}s more")
            return False

        return True

    def _update_usage(self, key: str):
        self.usage_tracker[key] = self.usage_tracker.get(key, 0) + 1
        self.rate_limits[key] = time.time()
        print(f"DEBUG: Updated usage for key {key[:10]}... (total: {self.usage_tracker[key]})")

    def mark_key_error(self, key: str):
        self.error_counts[key] = {'last_error': time.time()}
        print(f"DEBUG: Marked key {key[:10]}... as error")

    def get_active_keys_count(self) -> int:
        return sum(1 for key in self.api_keys if self._is_key_available(key))

    def get_usage_stats(self) -> Dict:
        total_requests = sum(self.usage_tracker.values())
        active_keys = self.get_active_keys_count()
        total_keys = len(self.api_keys)
        return {
            'total_keys': total_keys,
            'active_keys': active_keys,
            'total_requests': total_requests,
            'usage_per_key': self.usage_tracker.copy(),
            'average_per_key': total_requests / total_keys if total_keys else 0,
            'estimated_daily_capacity': total_keys * 50  # Conservative estimate for free tier
        }

    def reset_usage(self):
        self.usage_tracker.clear()
        self.rate_limits.clear()
        self.error_counts.clear()
        self.current_index = 0
        print("DEBUG: Reset all usage tracking")
