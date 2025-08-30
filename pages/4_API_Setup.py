import streamlit as st
import os
from services.api_manager import APIKeyManager
from google import genai

st.set_page_config(page_title="API Setup", page_icon="🔑")

def main():
    st.title("🔑 Gemini API Keys Setup")
    st.markdown("Configure your Google Gemini API keys for image generation")
    
    # Instructions
    st.markdown("""
    ### How to get Gemini API Keys:
    1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
    2. Sign in with your Google account
    3. Click "Create API Key"
    4. Copy the API key and paste it below
    5. Repeat for up to 10 different Google accounts for better rate limiting
    """)
    
    st.markdown("---")
    
    # Current status
    col1, col2, col3 = st.columns(3)
    with col1:
        total_keys = len(st.session_state.api_manager.api_keys) if st.session_state.api_manager.api_keys else 0
        st.metric("Total API Keys", total_keys)
    
    with col2:
        active_keys = st.session_state.api_manager.get_active_keys_count() if st.session_state.api_manager else 0
        st.metric("Active Keys", active_keys)
    
    with col3:
        if st.session_state.api_manager and hasattr(st.session_state.api_manager, 'usage_tracker'):
            total_requests = sum(st.session_state.api_manager.usage_tracker.values())
            st.metric("Total Requests", total_requests)
        else:
            st.metric("Total Requests", 0)
    
    st.markdown("---")
    
    # Add API Keys Section
    st.subheader("➕ Add New API Keys")
    
    # Method 1: Single key input
    st.markdown("**Method 1: Add Single Key**")
    single_key = st.text_input(
        "Enter API Key:",
        type="password",
        placeholder="AIzaSyD...",
        help="Your Gemini API key from Google AI Studio"
    )
    
    col1, col2 = st.columns([1, 2])
    with col1:
        if st.button("🔍 Test Key", disabled=not single_key):
            test_single_key(single_key)
    
    with col2:
        if st.button("➕ Add Key", disabled=not single_key):
            add_single_key(single_key)
    
    st.markdown("---")
    
    # Method 2: Multiple keys
    st.markdown("**Method 2: Add Multiple Keys**")
    multiple_keys = st.text_area(
        "Enter multiple API keys (one per line):",
        height=150,
        placeholder="AIzaSyD...\nAIzaSyE...\nAIzaSyF...",
        help="Enter up to 10 API keys, one per line"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🧪 Test All Keys", disabled=not multiple_keys):
            test_multiple_keys(multiple_keys)
    
    with col2:
        if st.button("💾 Add All Keys", disabled=not multiple_keys):
            add_multiple_keys(multiple_keys)
    
    st.markdown("---")
    
    # Management Section
    st.subheader("🛠️ Key Management")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📊 View Usage Stats"):
            show_usage_stats()
    
    with col2:
        if st.button("🔄 Reset Usage"):
            st.session_state.api_manager.reset_usage()
            st.success("Usage statistics reset!")
            st.rerun()
    
    with col3:
        if st.button("🗑️ Clear All Keys"):
            clear_all_keys()

def test_single_key(api_key: str):
    """Test a single API key"""
    try:
        with st.spinner("Testing API key..."):
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Say 'API key is working!' if you can read this."
            )
            
            if response and response.text:
                st.success("✅ API key is valid and working!")
                st.info(f"Response: {response.text}")
            else:
                st.error("❌ API key test failed - no response received")
                
    except Exception as e:
        st.error(f"❌ API key test failed: {str(e)}")

def add_single_key(api_key: str):
    """Add a single API key"""
    try:
        current_keys = st.session_state.api_manager.api_keys.copy() if st.session_state.api_manager.api_keys else []
        
        if api_key in current_keys:
            st.warning("⚠️ This API key is already added!")
            return
        
        if len(current_keys) >= 10:
            st.error("❌ Maximum 10 API keys allowed!")
            return
        
        current_keys.append(api_key)
        
        if st.session_state.api_manager.add_api_keys(current_keys):
            st.success("✅ API key added successfully!")
            st.rerun()
        else:
            st.error("❌ Failed to add API key!")
            
    except Exception as e:
        st.error(f"❌ Error adding API key: {str(e)}")

def test_multiple_keys(keys_text: str):
    """Test multiple API keys"""
    keys = [key.strip() for key in keys_text.split('\n') if key.strip()]
    
    if not keys:
        st.error("❌ No valid keys found!")
        return
    
    results = []
    progress = st.progress(0)
    status = st.empty()
    
    for i, key in enumerate(keys):
        status.text(f"Testing key {i+1}/{len(keys)}...")
        progress.progress((i+1)/len(keys))
        
        try:
            client = genai.Client(api_key=key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Test"
            )
            
            results.append({
                'key': key[:12] + "...",
                'status': '✅ Working' if response and response.text else '❌ Failed',
                'valid': bool(response and response.text)
            })
            
        except Exception as e:
            results.append({
                'key': key[:12] + "...",
                'status': f'❌ Error: {str(e)[:30]}...',
                'valid': False
            })
    
    progress.empty()
    status.empty()
    
    # Show results
    st.subheader("Test Results:")
    valid_count = sum(1 for r in results if r['valid'])
    st.metric("Valid Keys", f"{valid_count}/{len(results)}")
    
    for result in results:
        st.text(f"{result['key']}: {result['status']}")

def add_multiple_keys(keys_text: str):
    """Add multiple API keys"""
    keys = [key.strip() for key in keys_text.split('\n') if key.strip() and key.strip().startswith('AIza')]
    
    if not keys:
        st.error("❌ No valid API keys found!")
        return
    
    if len(keys) > 10:
        st.warning(f"⚠️ Only first 10 keys will be added (found {len(keys)})")
        keys = keys[:10]
    
    try:
        if st.session_state.api_manager.add_api_keys(keys):
            st.success(f"✅ Successfully added {len(keys)} API keys!")
            st.balloons()
            st.rerun()
        else:
            st.error("❌ Failed to add API keys!")
            
    except Exception as e:
        st.error(f"❌ Error adding API keys: {str(e)}")

def show_usage_stats():
    """Show detailed usage statistics"""
    if not st.session_state.api_manager:
        st.error("API manager not initialized")
        return
    
    stats = st.session_state.api_manager.get_usage_stats()
    
    st.subheader("📈 Usage Statistics")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Keys", stats['total_keys'])
    with col2:
        st.metric("Active Keys", stats['active_keys'])
    
    if stats['usage_per_key']:
        st.subheader("Per-Key Usage:")
        for key_hash, usage in stats['usage_per_key'].items():
            key_display = key_hash[:12] + "..." if len(key_hash) > 12 else key_hash
            st.metric(f"Key {key_display}", f"{usage} requests")
    else:
        st.info("No usage data available yet")

def clear_all_keys():
    """Clear all API keys with confirmation"""
    st.warning("⚠️ This will remove all API keys!")
    
    if st.button("🗑️ Confirm Delete All", type="secondary"):
        try:
            st.session_state.api_manager.add_api_keys([])  # Empty list
            st.success("✅ All API keys cleared!")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error clearing keys: {str(e)}")

if __name__ == "__main__":
    main()
