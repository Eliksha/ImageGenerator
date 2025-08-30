import streamlit as st
import os
from pathlib import Path
from services.api_manager import APIKeyManager
from config.settings import UPLOAD_DIR, GENERATED_DIR
import time

# Page configuration
st.set_page_config(
    page_title="AI Image Generator",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'api_manager' not in st.session_state:
    st.session_state.api_manager = APIKeyManager()

if 'generated_images' not in st.session_state:
    st.session_state.generated_images = []

def main():
    st.title("🎨 AI Image Generator with Gemini")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("📊 Dashboard")
        
        # API Status
        st.subheader("API Status")
        if st.session_state.api_manager:
            active_keys = st.session_state.api_manager.get_active_keys_count()
            st.metric("Active API Keys", active_keys, f"/{st.session_state.api_manager.total_keys}")
            
        st.markdown("---")
        
        # Quick Stats
        st.subheader("Quick Stats")
        total_generated = len(st.session_state.generated_images)
        st.metric("Images Generated", total_generated)
        
        # API Usage Reset
        if st.button("🔄 Reset API Usage"):
            st.session_state.api_manager.reset_usage()
            st.success("API usage reset!")
            st.experimental_rerun()
    
    # Main content
    st.markdown("""
    ### Welcome to AI Image Generator! 
    
    Choose your generation mode:
    """)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👤 Single Person", use_container_width=True):
            st.switch_page("pages/1_Single_Person.py")
    
    with col2:
        if st.button("💑 Couple", use_container_width=True):
            st.switch_page("pages/2_Couple_Generation.py")
    
    with col3:
        if st.button("🖼️ Gallery", use_container_width=True):
            st.switch_page("pages/3_Gallery.py")
    
    # Recent generations
    if st.session_state.generated_images:
        st.markdown("### 🔥 Recent Generations")
        cols = st.columns(4)
        for idx, img_path in enumerate(st.session_state.generated_images[-4:]):
            with cols[idx]:
                if os.path.exists(img_path):
                    st.image(img_path, caption=f"Generated {idx+1}")

if __name__ == "__main__":
    main()
