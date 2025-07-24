# Voice-Enabled Medical RAG Assistant MVP

A minimal full-stack voice conversational app for doctors to query basic patient information using speech.

## 🏗️ Architecture

- **Frontend**: React app with voice recording capabilities
- **Backend**: Flask API with speech-to-text, RAG, and text-to-speech
- **Speech-to-Text**: OpenAI Whisper API
- **Vector Database**: Pinecone for patient information storage
- **Text-to-Speech**: ElevenLabs (high-quality, natural voices)
- **LLM**: OpenAI GPT-3.5-turbo via LangChain

## 📁 Project Structure

```
voice-med-assistant-mvp/
├── backend/
│   ├── app.py                 # Flask application
│   ├── requirements.txt       # Python dependencies
│   ├── env.example           # Environment variables template
│   └── data/
│       └── sample_patients.json  # Sample patient data
├── frontend/
│   ├── src/
│   │   ├── App.js            # Main React component
│   │   ├── App.css           # Application styles
│   │   ├── index.js          # React entry point
│   │   └── index.css         # Global styles
│   ├── public/
│   │   └── index.html        # HTML template
│   └── package.json          # Node.js dependencies
├── scripts/
│   └── upload_patients.py    # Script to upload data to Pinecone
└── README.md
```

## 🚀 Quick Start

### Prerequisites

1. **Node.js** (v16 or higher)
2. **Python** (3.9 or higher) with **pipenv** installed
3. **OpenAI API Key** (for Whisper and GPT-3.5)
4. **ElevenLabs API Key** (for high-quality TTS - free tier: 10k chars/month)
5. **Pinecone Account** (free tier available)

> **Note**: If you don't have pipenv installed, run: `pip install pipenv`

### Step 1: Get API Keys

1. **OpenAI**: Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. **ElevenLabs**: Get your API key from [ElevenLabs](https://elevenlabs.io/app/speech-synthesis)
   - Sign up for free (10k characters/month)
   - Go to Profile & API Key to get your key
3. **Pinecone**: 
   - Sign up at [Pinecone.io](https://www.pinecone.io/)
   - Create a new project
   - Note your API key (no environment needed for serverless)

### Step 2: Setup Environment and Backend

```bash
cd voice-med-assistant-mvp

# Run the interactive setup script
python setup_env.py

# This will ask for your API keys and create the .env file automatically
# Alternatively, you can manually create backend/.env from backend/env.example

# Navigate to backend and set up Python environment
cd backend

# Create pipenv environment and install dependencies
pipenv install

# The script will automatically install all required packages
```

### Step 3: Upload Patient Data to Pinecone

```bash
cd ../scripts

# Run the upload script (will use the pipenv environment automatically)
pipenv run python upload_patients.py
```

This will:
- Create a Pinecone serverless index (free tier compatible)
- Upload 5 sample patient records
- Test the retrieval functionality

### Step 4: Start Backend Server

```bash
cd ../backend

# Start Flask server in pipenv environment
pipenv run python app.py
```

The backend will be available at `http://localhost:5000`

### Step 5: Frontend Setup

```bash
# Open a new terminal
cd voice-med-assistant-mvp/frontend

# Install dependencies
npm install

# Start React development server
npm start
```

The frontend will be available at `http://localhost:3000`

## 🎯 Usage

1. **Open** `http://localhost:3000` in your browser
2. **Click** "Start Conversation" to begin
3. **Speak naturally** - the system automatically detects when you stop talking
4. **Listen** to the AI's high-quality voice response
5. **Continue talking** - the conversation flows naturally back and forth
6. **Click** "End Conversation" when finished

### 🎤 Voice Features:
- **Automatic silence detection** - no need to click buttons repeatedly
- **Continuous conversation flow** - just like talking to a real assistant
- **High-quality ElevenLabs TTS** - natural, professional voice
- **Real-time status indicators** - shows listening, thinking, speaking states
- **Conversation history** - tracks your entire session

### Example Queries

- "Tell me about John Doe"
- "Who has diabetes?"
- "Which patients are on blood pressure medication?"
- "Show me information about Sarah Smith"
- "What medications is Michael Johnson taking?"

## 🔧 API Endpoints

### Backend Endpoints

- `GET /api/health` - Health check
- `POST /api/ask` - Main voice query endpoint
- `POST /api/test-tts` - Test text-to-speech

## 🎛️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `ELEVENLABS_API_KEY` | ElevenLabs API key | `your-key-here` |
| `PINECONE_API_KEY` | Pinecone API key | `your-key-here` |
| `PINECONE_INDEX_NAME` | Pinecone index name | `medical-assistant` |

## 🩺 Sample Patient Data

The system includes 5 sample patients:

1. **John Doe** (45) - Hypertension
2. **Sarah Smith** (32) - Type 2 Diabetes, Obesity
3. **Michael Johnson** (67) - Heart failure, COPD, A-fib
4. **Emily Chen** (28) - Asthma, Anxiety
5. **Robert Williams** (55) - Chronic kidney disease, Gout

## 🛠️ Development

### Adding New Patients

1. Add patient data to `backend/data/sample_patients.json`
2. Run the upload script: `pipenv run python scripts/upload_patients.py`

### Backend Development

```bash
cd backend
pipenv run python app.py
```

### Frontend Development

```bash
cd frontend
npm start
```

## 🔍 Troubleshooting

### Common Issues

1. **Microphone not working**
   - Ensure browser has microphone permissions
   - Use HTTPS in production (required for microphone access)

2. **Backend connection errors**
   - Check if Flask server is running on port 5000
   - Verify API keys in `.env` file

3. **Pinecone errors**
   - Verify Pinecone API key and environment
   - Ensure index exists or run upload script

4. **Audio playback issues**
   - Check browser audio permissions
   - Ensure speakers/headphones are connected

### Debug Mode

Set `FLASK_DEBUG=True` in your `.env` file for detailed error logs.

## 📝 Notes

- **Continuous Conversation**: Natural voice flow with automatic silence detection
- **High-Quality TTS**: ElevenLabs provides professional, natural-sounding voices
- **Real-time Feedback**: Visual indicators for listening, thinking, and speaking states
- **Voice Activity Detection**: Automatically detects when you stop speaking (2-second silence threshold)
- No authentication implemented (add for production)
- Uses browser's MediaRecorder API (WebM format)
- Supports modern browsers with microphone access
- Uses pipenv for Python dependency management [[memory:3365572]]
- Compatible with newer Pinecone serverless (free tier) and LangChain 0.3.x APIs

## 🔄 Next Steps

For production deployment:

1. Add user authentication
2. Implement HTTPS/SSL
3. Add patient data encryption
4. Improve error handling
5. Add conversation history
6. Implement role-based access control
7. Add audit logging

## 📄 License

This project is for educational/demo purposes. Ensure compliance with HIPAA and other medical data regulations before using with real patient data. # Ai-Medical-Assistant
