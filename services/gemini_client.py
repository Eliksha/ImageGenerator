import streamlit as st
from google import genai
from google.genai import types
import time
import os
import uuid
import mimetypes
from typing import List, Dict, Optional
from pathlib import Path
from PIL import Image
from io import BytesIO
from config.settings import GENERATED_DIR
from services.api_manager import APIKeyManager

# Initialize APIKeyManager once per session if missing
if 'api_manager' not in st.session_state:
    st.session_state.api_manager = APIKeyManager()

class GeminiClient:
    def __init__(self, api_manager):
        self.api_manager = api_manager
        self.current_client = None
        self.current_api_key = None
        self.locked_api_key = None

    def _get_client_locked(self) -> Optional[genai.Client]:
        """Get client using locked API key to ensure consistency"""
        if self.locked_api_key:
            api_key = self.locked_api_key
            st.info(f"🔒 Using locked API key: {api_key[:10]}...")
        else:
            api_key = self.api_manager.get_next_key()
            if not api_key:
                st.error("🚨 **No available API keys.** All keys are on cooldown.")
                return None
            
            self.locked_api_key = api_key
            st.success(f"🔒 **Locked API key for session:** {api_key[:10]}...")
        
        if self.current_api_key != api_key:
            try:
                os.environ["GEMINI_API_KEY"] = api_key
                self.current_client = genai.Client(api_key=api_key)
                self.current_api_key = api_key
            except Exception as e:
                st.error(f"❌ Failed to create Gemini client: {e}")
                self.api_manager.mark_key_error(api_key)
                self.locked_api_key = None
                return None
        
        return self.current_client

    def unlock_session_key(self):
        """Unlock the session key to allow rotation"""
        self.locked_api_key = None
        st.info("🔓 Unlocked API key - rotation enabled")

    def _upload_images_with_locked_key(self, image_paths: List[str]) -> List[object]:
        """Upload images using locked API key"""
        client = self._get_client_locked()
        if not client:
            return []
        
        uploaded_files = []
        st.info(f"📤 **Uploading {len(image_paths)} reference images...**")
        
        for i, img_path in enumerate(image_paths):
            if not Path(img_path).exists():
                st.warning(f"🚫 File not found: {img_path}")
                continue
            
            file_size = Path(img_path).stat().st_size / (1024 * 1024)
            if file_size > 20:
                st.warning(f"⚠️ File too large ({file_size:.1f}MB): {Path(img_path).name}")
                continue
            
            st.info(f"⏳ Uploading {i+1}/{len(image_paths)}: {Path(img_path).name}")
            
            try:
                uploaded_file = client.files.upload(file=img_path)
                uploaded_files.append(uploaded_file)
                st.success(f"✅ Uploaded: {Path(img_path).name}")
                
                if i < len(image_paths) - 1:
                    time.sleep(1)
                    
            except Exception as e:
                st.error(f"❌ Upload failed: {str(e)}")
                if "429" in str(e):
                    self.api_manager.mark_key_error(self.locked_api_key)
                    self.unlock_session_key()
                    return []
        
        return uploaded_files

    def generate_image_with_prompt(self, prompt: str, reference_images: List[str] = None, 
                                  output_dir: str = "storage/generated/single_person") -> Dict:
        """Generate both image prompts AND actual images using Nano Banana"""
        
        st.info(f"🍌 **Nano Banana Image Generation Starting...**")
        st.info(f"📝 Prompt: {prompt[:100]}...")
        
        client = self._get_client_locked()
        if not client:
            return {"success": False, "error": "No API client available"}

        # Prepare contents for generation
        contents = [prompt]
        
        # Add reference images if provided
        if reference_images:
            limited_images = reference_images[:1]  # Conservative for quota
            st.info(f"📸 Using {len(limited_images)} reference image(s)")
            
            uploaded_files = self._upload_images_with_locked_key(limited_images)
            if uploaded_files:
                contents.extend(uploaded_files)
                st.success(f"✅ Ready with {len(contents)} content items")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            st.info("🚀 **Generating image with Nano Banana...**")
            
            # Use Nano Banana model for image generation
            response = client.models.generate_content(
                model="gemini-2.5-flash-image-preview",  # Nano Banana for image generation
                contents=contents,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0),
                    response_modalities=["TEXT", "IMAGE"],  # Request both text and image
                    temperature=0.7,
                    max_output_tokens=400,
                    top_p=0.8,
                    top_k=30,
                )
            )
            
            # Process response to extract text and images
            generated_text = ""
            saved_images = []
            
            if response and response.candidates:
                st.success("✅ **Generation successful!**")
                
                for candidate_idx, candidate in enumerate(response.candidates):
                    for part_idx, part in enumerate(candidate.content.parts):
                        
                        # Extract generated text
                        if part.text:
                            generated_text += part.text + "\n"
                            st.success(f"📝 **Generated description:** {part.text[:200]}...")
                        
                        # Extract and save generated images
                        if hasattr(part, 'inline_data') and part.inline_data:
                            try:
                                # Get image data
                                image_data = part.inline_data.data
                                
                                # Create PIL Image
                                image = Image.open(BytesIO(image_data))
                                
                                # Generate unique filename
                                timestamp = int(time.time())
                                filename = f"generated_image_{timestamp}_{part_idx}.png"
                                filepath = os.path.join(output_dir, filename)
                                
                                # Save image
                                image.save(filepath)
                                saved_images.append(filepath)
                                
                                st.success(f"🖼️ **Image saved:** {filename}")
                                st.image(image, caption=f"Generated Image {part_idx + 1}", width=300)
                                
                            except Exception as img_error:
                                st.error(f"❌ Error saving image {part_idx}: {str(img_error)}")
                
                # Also save the text description
                if generated_text.strip():
                    timestamp = int(time.time())
                    text_filename = f"generated_description_{timestamp}.txt"
                    text_filepath = os.path.join(output_dir, text_filename)
                    
                    with open(text_filepath, 'w', encoding='utf-8') as f:
                        f.write(f"Original Prompt: {prompt}\n\n")
                        f.write(f"Generated Description:\n{generated_text}")
                    
                    st.success(f"📄 **Description saved:** {text_filename}")
                
                return {
                    "success": True,
                    "generated_text": generated_text.strip(),
                    "saved_images": saved_images,
                    "output_dir": output_dir
                }
            
            else:
                st.error("❌ No response candidates received")
                return {"success": False, "error": "Empty response"}
                
        except Exception as e:
            error_msg = str(e)
            st.error(f"❌ **Image generation failed:** {error_msg}")
            
            if "429" in error_msg:
                st.error("🔥 **Quota exhausted!**")
                st.info("💡 **Solutions:**")
                st.info("• Wait 24 hours for quota reset")
                st.info("• Enable billing on Google Cloud")
                st.info("• Try with fewer reference images")
                
                self.api_manager.mark_key_error(self.locked_api_key)
                self.unlock_session_key()
            
            return {"success": False, "error": error_msg}

    def generate_image_description_and_variations(self, base_prompt: str, style: str,
                                                 reference_images: List[str], count: int = 4) -> List[Dict]:
        """Generate detailed prompts AND actual images"""
        
        from config.prompts import STYLE_PROMPTS, QUALITY_MODIFIERS

        # Conservative settings for free tier
        count = 1  # Generate 1 detailed prompt + 1 actual image
        st.warning(f"🍌 **Nano Banana Mode:** Generating {count} prompt + actual image")

        style_text = STYLE_PROMPTS.get(style, "")
        quality_text = QUALITY_MODIFIERS[0] if QUALITY_MODIFIERS else ""

        # Create detailed image generation prompt
        image_generation_prompt = f"""{base_prompt}. {style_text}. {quality_text}. 
Professional photography, high quality, detailed, photorealistic."""

        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            status_text.text("🍌 Generating with Nano Banana...")
            progress_bar.progress(0.3)

            # Generate actual image using Nano Banana
            generation_result = self.generate_image_with_prompt(
                prompt=image_generation_prompt,
                reference_images=reference_images[:1],  # Use 1 reference image
                output_dir=f"{GENERATED_DIR}/single_person"
            )

            progress_bar.progress(0.7)

            if generation_result["success"]:
                # Create result with both prompt and generated images
                results.append({
                    'id': f"nano_banana_{uuid.uuid4().hex[:8]}",
                    'prompt': image_generation_prompt,
                    'generated_text': generation_result.get("generated_text", ""),
                    'saved_images': generation_result.get("saved_images", []),
                    'style': style,
                    'index': 1,
                    'status': 'generated',
                    'model': 'nano-banana-image-generator'
                })

                progress_bar.progress(1.0)
                status_text.text("🎉 Nano Banana generation complete!")
                
                # Show success with image count
                image_count = len(generation_result.get("saved_images", []))
                st.success(f"🍌 **SUCCESS!** Generated {image_count} image(s) and detailed description!")
                
                # Show generated images
                for img_path in generation_result.get("saved_images", []):
                    if os.path.exists(img_path):
                        st.image(img_path, caption=f"Generated: {Path(img_path).name}", width=400)

                time.sleep(2)
                progress_bar.empty()
                status_text.empty()
                
                # Unlock session key
                self.unlock_session_key()

            else:
                st.error(f"❌ Image generation failed: {generation_result.get('error', 'Unknown error')}")
                progress_bar.empty()
                status_text.empty()

        except Exception as e:
            st.error(f"❌ Error in Nano Banana generation: {str(e)}")
            progress_bar.empty()
            status_text.empty()

        return results

    def create_image_generation_summary(self, results: List[Dict], reference_paths: List[str]) -> Dict:
        """Create summary including generated images info"""
        summary = {
            'total_prompts': len(results),
            'total_images': sum(len(r.get('saved_images', [])) for r in results),
            'reference_images': len(reference_paths),
            'generation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'model_used': 'nano-banana-image-generator',
            'output_location': f"{GENERATED_DIR}/single_person",
            'prompts': []
        }

        for result in results:
            summary['prompts'].append({
                'index': result['index'],
                'prompt': result['prompt'],
                'generated_text': result.get('generated_text', ''),
                'generated_images': result.get('saved_images', []),
                'style': result['style'],
                'model': 'nano-banana'
            })

        return summary
