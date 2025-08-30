import streamlit as st
import os
import json
from pathlib import Path
from services.gemini_client import GeminiClient
from config.prompts import STYLE_PROMPTS
from utils.image_utils import validate_image, resize_image
from utils.storage import save_uploaded_file
import streamlit as st
from services.api_manager import APIKeyManager

# Initialize APIKeyManager once per session if missing
if 'api_manager' not in st.session_state:
    st.session_state.api_manager = APIKeyManager()


st.set_page_config(page_title="Single Person Generator", page_icon="👤")

def main():
    st.title("👤 Single Person Image Generator")
    st.markdown("Generate detailed prompts for AI image creation with facial consistency")
    st.markdown("---")
    
    # Check if API keys are configured
    if not st.session_state.api_manager.api_keys:
        st.error("⚠️ No API keys configured. Please set up your Gemini API keys first.")
        if st.button("🔑 Setup API Keys"):
            st.switch_page("pages/4_API_Setup.py")
        return
    
    # Initialize services
    if 'gemini_client' not in st.session_state:
        st.session_state.gemini_client = GeminiClient(st.session_state.api_manager)
    
    # Main layout
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📷 Upload Images")
        
        # Main reference image
        st.subheader("Main Reference Image")
        main_image = st.file_uploader(
            "Upload main reference image (clear face visible)",
            type=['jpg', 'jpeg', 'png', 'webp'],
            key="main_image",
            help="This should be your best quality reference photo"
        )
        
        if main_image:
            st.image(main_image, caption="Main Reference", width=200)
        
        # Additional reference images
        st.subheader("Additional Reference Images")
        st.caption("Upload 3-5 additional images for better facial consistency")
        additional_images = st.file_uploader(
            "Upload additional reference images",
            type=['jpg', 'jpeg', 'png', 'webp'],
            accept_multiple_files=True,
            key="additional_images"
        )
        
        if additional_images:
            if len(additional_images) > 5:
                st.warning("Using first 5 additional images.")
                additional_images = additional_images[:5]
            
            # Display additional images
            cols = st.columns(min(len(additional_images), 3))
            for idx, img in enumerate(additional_images):
                with cols[idx % 3]:
                    st.image(img, caption=f"Ref {idx+1}", width=120)
    
    with col2:
        st.header("⚙️ Generation Settings")
        
        # Style selection
        st.subheader("Choose Style")
        selected_style = st.selectbox(
            "Select generation style:",
            options=list(STYLE_PROMPTS.keys()),
            format_func=lambda x: x.replace('_', ' ').title(),
            key="style_select"
        )
        
        # Display style description
        if selected_style:
            st.info(f"**Style:** {STYLE_PROMPTS[selected_style]}")
        
        # Custom prompt
        st.subheader("Custom Description")
        custom_prompt = st.text_area(
            "Describe the desired scene/pose:",
            placeholder="E.g., sitting in a coffee shop, wearing elegant dress, natural lighting...",
            key="custom_prompt",
            height=80
        )
        
        # Generation count
        image_count = st.slider(
            "Number of prompts to generate:",
            min_value=1,
            max_value=6,
            value=4,
            key="image_count",
            help="Each prompt can be used to generate images with external tools"
        )
        
        # Advanced settings
        with st.expander("⚙️ Advanced Settings"):
            include_negative = st.checkbox("Include negative prompts", value=True)
            detailed_description = st.checkbox("Extra detailed descriptions", value=True)
            st.caption("These settings affect prompt complexity and detail level")
        
        st.markdown("---")
        
        # Generate button
        generate_btn = st.button(
            "🎨 Generate Image Prompts",
            type="primary",
            use_container_width=True,
            disabled=not (main_image and len(additional_images) >= 1),
            help="Generate detailed prompts for AI image generation tools"
        )
        
        if generate_btn:
            if not main_image:
                st.error("Please upload a main reference image!")
            elif len(additional_images) < 1:
                st.error("Please upload at least 1 additional reference image!")
            else:
                generate_single_person_prompts()

def generate_single_person_prompts():
    """Generate detailed prompts for single person images"""
    
    try:
        # Save uploaded files
        main_path = save_uploaded_file(st.session_state.main_image, "single_person", "main")
        additional_paths = []
        
        for idx, img in enumerate(st.session_state.additional_images):
            path = save_uploaded_file(img, "single_person", f"additional_{idx}")
            additional_paths.append(path)
        
        # Prepare reference images list
        reference_images = [main_path] + additional_paths
        
        # Build generation prompt
        base_prompt = "Professional portrait of the person shown in the reference images"
        if st.session_state.custom_prompt:
            base_prompt += f", {st.session_state.custom_prompt}"
        
        # Generate prompts
        results = st.session_state.gemini_client.generate_image_description_and_variations(
            base_prompt=base_prompt,
            style=st.session_state.style_select,
            reference_images=reference_images,
            count=st.session_state.image_count
        )
        
        # Display results
        if results:
            st.success(f"✅ Successfully generated {len(results)} detailed image prompts!")
            
            # Store in session state
            st.session_state.generated_prompts = results
            st.session_state.reference_images = reference_images
            
            # Display generated prompts
            st.markdown("---")
            st.subheader("🎉 Generated Image Prompts")
            st.caption("Copy these prompts to use with AI image generation tools like DALL-E, Midjourney, Stable Diffusion, etc.")
            
            for idx, result in enumerate(results):
                with st.expander(f"📝 Prompt {result['index']} - {result['style'].title().replace('_', ' ')}", expanded=True):
                    st.text_area(
                        f"Prompt {result['index']}:",
                        value=result['prompt'],
                        height=120,
                        key=f"prompt_{idx}",
                        help="Click to select all text, then copy"
                    )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.caption(f"Style: {result['style'].replace('_', ' ').title()}")
                    with col2:
                        # Copy button (visual only, user needs to manually copy)
                        if st.button(f"📋 Copy Prompt {result['index']}", key=f"copy_{idx}"):
                            st.info("Select the text above and copy it (Ctrl+C / Cmd+C)")
            
            # Export options
            st.markdown("---")
            st.subheader("📥 Export Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # Export as JSON
                summary = st.session_state.gemini_client.create_image_generation_summary(results, reference_images)
                json_data = json.dumps(summary, indent=2)
                
                st.download_button(
                    "📄 Download as JSON",
                    json_data,
                    file_name=f"image_prompts_{st.session_state.style_select}_{len(results)}.json",
                    mime="application/json",
                    use_container_width=True
                )
            
            with col2:
                # Export as text file
                text_content = f"Image Generation Prompts - {st.session_state.style_select.title()}\n"
                text_content += f"Generated: {results[0].get('generation_date', 'N/A')}\n"
                text_content += "="*50 + "\n\n"
                
                for result in results:
                    text_content += f"PROMPT {result['index']}:\n"
                    text_content += f"{result['prompt']}\n\n"
                    text_content += "-"*30 + "\n\n"
                
                st.download_button(
                    "📝 Download as Text",
                    text_content,
                    file_name=f"image_prompts_{st.session_state.style_select}_{len(results)}.txt",
                    mime="text/plain",
                    use_container_width=True
                )
            
            # Instructions
            st.markdown("---")
            st.info("""
            **How to use these prompts:**
            1. Copy any prompt above
            2. Use it with AI image generators like:
               - DALL-E 3 (OpenAI)
               - Midjourney
               - Stable Diffusion
               - Leonardo AI
               - Adobe Firefly
            3. Upload your reference images to the tool if it supports them
            4. Generate your images!
            """)
            
        else:
            st.error("❌ Failed to generate prompts. Please try again or check your API keys.")
            
    except Exception as e:
        st.error(f"❌ Error during generation: {str(e)}")
        st.exception(e)  # For debugging

if __name__ == "__main__":
    main()
