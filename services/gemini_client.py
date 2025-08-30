import streamlit as st
from google import genai
from google.genai import types
import base64
import time
import os
import uuid
from typing import List, Dict, Optional
from pathlib import Path
from config.settings import GENERATED_DIR

class GeminiClient:
    def __init__(self, api_manager):
        self.api_manager = api_manager
        self.current_client = None
        self.current_api_key = None
    
    def _get_client(self):
        """Get or create a Gemini client with current API key"""
        api_key = self.api_manager.get_next_key()
        
        if not api_key:
            st.error("No available API keys. Please add API keys first.")
            return None
        
        # Create new client if key changed
        if api_key != self.current_api_key:
            try:
                # Set environment variable for the client
                os.environ['GEMINI_API_KEY'] = api_key
                self.current_client = genai.Client(api_key=api_key)
                self.current_api_key = api_key
            except Exception as e:
                st.error(f"Failed to create Gemini client: {e}")
                self.api_manager.mark_key_error(api_key)
                return None
        
        return self.current_client
    
    def generate_content_with_images(self, prompt: str, image_paths: List[str] = None) -> Optional[str]:
        """Generate content using Gemini with image inputs"""
        
        client = self._get_client()
        if not client:
            return None
        
        try:
            # Prepare content parts
            contents = [prompt]
            
            # Add images if provided
            if image_paths:
                for img_path in image_paths:
                    if os.path.exists(img_path):
                        # Read and encode image
                        with open(img_path, "rb") as img_file:
                            img_data = img_file.read()
                            contents.append({
                                "mime_type": "image/jpeg",
                                "data": img_data
                            })
            
            # Generate content with thinking disabled for faster response
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_budget=0),  # Disable thinking for speed
                    temperature=0.7,
                    top_p=0.8,
                    top_k=40,
                    max_output_tokens=2048,
                )
            )
            
            return response.text
            
        except Exception as e:
            st.error(f"Generation failed: {str(e)}")
            # Mark current key as having error
            if self.current_api_key:
                self.api_manager.mark_key_error(self.current_api_key)
                self.current_client = None
                self.current_api_key = None
            return None
    
    def generate_image_description_and_variations(self, base_prompt: str, style: str, 
                                                 reference_images: List[str], count: int = 4) -> List[Dict]:
        """Generate image descriptions that can be used for image generation"""
        
        from config.prompts import STYLE_PROMPTS, QUALITY_MODIFIERS, NEGATIVE_PROMPTS
        
        # Build enhanced prompt for generating image descriptions
        style_text = STYLE_PROMPTS.get(style, "")
        quality_text = ", ".join(QUALITY_MODIFIERS[:3])  # Use first 3 quality modifiers
        
        generation_prompt = f"""
        You are an expert image generation prompt creator. Based on the reference images provided and the requirements below, create {count} detailed image generation prompts that maintain facial consistency.

        Requirements:
        - Base description: {base_prompt}
        - Style: {style_text}
        - Quality: {quality_text}
        - Maintain the exact facial features, bone structure, and identity from the reference images
        - Each prompt should be unique but consistent with the person's identity
        - Include detailed descriptions of pose, lighting, composition, and setting
        - Each prompt should be suitable for AI image generation tools

        Please provide exactly {count} detailed prompts, numbered 1-{count}, each on a new line.
        Each prompt should be comprehensive and include:
        - Physical appearance details matching the reference
        - Pose and expression
        - Clothing/style elements
        - Setting/background
        - Lighting and mood
        - Camera angle and composition

        Format: Just the numbered prompts, nothing else.
        """
        
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("Analyzing reference images and generating prompts...")
            progress_bar.progress(0.3)
            
            # Generate prompts using Gemini
            response_text = self.generate_content_with_images(generation_prompt, reference_images)
            
            if response_text:
                progress_bar.progress(0.7)
                status_text.text("Processing generated prompts...")
                
                # Parse the generated prompts
                lines = [line.strip() for line in response_text.split('\n') if line.strip()]
                prompts = []
                
                for line in lines:
                    if line and (line[0].isdigit() or line.startswith('•') or line.startswith('-')):
                        # Clean up the prompt (remove numbering)
                        clean_prompt = line
                        for prefix in ['1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '•', '-']:
                            if clean_prompt.startswith(prefix):
                                clean_prompt = clean_prompt[len(prefix):].strip()
                                break
                        
                        if clean_prompt:
                            prompts.append(clean_prompt)
                
                # Create result objects
                for i, prompt in enumerate(prompts[:count]):
                    results.append({
                        'id': f"prompt_{uuid.uuid4().hex[:8]}",
                        'prompt': prompt,
                        'style': style,
                        'index': i + 1,
                        'status': 'generated'
                    })
                
                progress_bar.progress(1.0)
                status_text.text(f"Generated {len(results)} image prompts successfully!")
                
                # Clear progress indicators after a short delay
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()
                
            else:
                st.error("Failed to generate image prompts")
                
        except Exception as e:
            st.error(f"Error generating prompts: {str(e)}")
            progress_bar.empty()
            status_text.empty()
        
        return results
    
    def create_image_generation_summary(self, results: List[Dict], reference_paths: List[str]) -> Dict:
        """Create a summary of generated prompts for external image generation"""
        
        summary = {
            'total_prompts': len(results),
            'reference_images': len(reference_paths),
            'generation_date': time.strftime('%Y-%m-%d %H:%M:%S'),
            'prompts': []
        }
        
        for result in results:
            summary['prompts'].append({
                'index': result['index'],
                'prompt': result['prompt'],
                'style': result['style'],
                'recommended_settings': {
                    'steps': 30,
                    'cfg_scale': 7,
                    'sampler': 'DPM++ 2M Karras',
                    'size': '512x768'
                }
            })
        
        return summary
