#!/bin/bash

# Create base project directory
mkdir -p image-generator-streamlit
cd image-generator-streamlit || exit

# Create main app file
touch app.py

# Config directory and files
mkdir -p config
touch config/__init__.py
touch config/settings.py
touch config/api_keys.json
touch config/prompts.py

# Services directory and files
mkdir -p services
touch services/__init__.py
touch services/api_manager.py
touch services/gemini_client.py
touch services/image_processor.py
touch services/face_detector.py
touch services/generation_engine.py

# Utils directory and files
mkdir -p utils
touch utils/__init__.py
touch utils/image_utils.py
touch utils/storage.py
touch utils/validation.py

# Pages directory and files
mkdir -p pages
touch pages/1_Single_Person.py
touch pages/2_Couple_Generation.py
touch pages/3_Gallery.py
touch pages/4_API_Setup.py

# Storage structure
mkdir -p storage/uploads/single_person
mkdir -p storage/uploads/couples
mkdir -p storage/generated/single_person
mkdir -p storage/generated/couples
mkdir -p storage/temp

# Database directory and file
mkdir -p database
touch database/sessions.db

# Root-level project files
touch requirements.txt
touch .env.example
touch .gitignore
touch README.md
touch setup.py

echo "✅ Project structure created successfully!"
