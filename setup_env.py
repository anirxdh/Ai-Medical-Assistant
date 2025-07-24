#!/usr/bin/env python3
"""
Setup script to configure environment variables for the Medical Voice Assistant
"""

import os
from pathlib import Path

def main():
    """Main setup function"""
    print("🏥 Medical Voice Assistant - Environment Setup")
    print("=" * 50)
    
    backend_dir = Path(__file__).parent / "backend"
    env_file = backend_dir / ".env"
    env_example = backend_dir / "env.example"
    
    # Check if .env already exists
    if env_file.exists():
        overwrite = input("\n.env file already exists. Overwrite? (y/N): ").lower().strip()
        if overwrite != 'y':
            print("Setup cancelled.")
            return
    
    print("\nPlease provide your API keys:")
    print("You can get these from:")
    print("- OpenAI: https://platform.openai.com/api-keys")
    print("- ElevenLabs: https://elevenlabs.io/app/speech-synthesis (free tier: 10k chars/month)")
    print("- Pinecone: https://app.pinecone.io/ (sign up for free)")
    print()
    
    # Get API keys from user
    openai_key = input("OpenAI API Key: ").strip()
    elevenlabs_key = input("ElevenLabs API Key: ").strip()
    pinecone_key = input("Pinecone API Key: ").strip()
    
    # Optional: Index name
    index_name = input("Pinecone Index Name (default: medical-assistant): ").strip()
    if not index_name:
        index_name = "medical-assistant"
    
    # Create .env file content
    env_content = f"""# OpenAI API Configuration
OPENAI_API_KEY={openai_key}

# ElevenLabs API Configuration (for high-quality TTS)
ELEVENLABS_API_KEY={elevenlabs_key}

# Pinecone Configuration
PINECONE_API_KEY={pinecone_key}
PINECONE_INDEX_NAME={index_name}

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
"""
    
    # Write .env file
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"\n✅ Environment file created at: {env_file}")
    print("\nNext steps:")
    print("1. Run the data upload script:")
    print("   cd scripts && python upload_patients.py")
    print("\n2. Start the backend server:")
    print("   cd backend && pipenv run python app.py")
    print("\n3. In another terminal, start the frontend:")
    print("   cd frontend && npm start")
    print("\n4. Open http://localhost:3000 in your browser")

if __name__ == "__main__":
    main() 