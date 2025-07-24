from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import openai
import os
import tempfile
import io
from elevenlabs import ElevenLabs, VoiceSettings
from gtts import gTTS
from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize ElevenLabs client (optional)
try:
    if os.getenv('ELEVENLABS_API_KEY'):
        elevenlabs_client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
        logger.info("ElevenLabs client initialized")
    else:
        elevenlabs_client = None
        logger.info("No ElevenLabs API key found, will use Google TTS")
except Exception as e:
    logger.warning(f"Failed to initialize ElevenLabs client: {e}")
    elevenlabs_client = None

# Initialize Pinecone with new API
pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

# Initialize embeddings and vector store
embeddings = OpenAIEmbeddings()
index_name = os.getenv('PINECONE_INDEX_NAME', 'medical-assistant')

try:
    # Check if index exists and connect to it
    if index_name in [index.name for index in pc.list_indexes()]:
        index = pc.Index(index_name)
        vectorstore = PineconeVectorStore(
            index=index,
            embedding=embeddings
        )
        logger.info(f"Connected to existing Pinecone index: {index_name}")
    else:
        logger.warning(f"Pinecone index '{index_name}' not found. Please run the upload script first.")
        vectorstore = None
except Exception as e:
    logger.error(f"Failed to connect to Pinecone index: {e}")
    vectorstore = None

# Conversation memory storage (in production, use proper session management)
conversation_history = []

# Initialize LLM and QA chain
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    openai_api_key=os.getenv('OPENAI_API_KEY')
)

# Custom prompt for medical assistant - direct and professional
medical_prompt = PromptTemplate(
    input_variables=["context", "question", "conversation_history"],
    template="""You are a professional medical assistant. Provide direct, accurate medical information without conversational filler words or phrases.

Patient Information:
{context}

Previous Conversation:
{conversation_history}

Current Question: {question}

Instructions:
- Be direct and professional
- Never use acknowledgment phrases, filler words, or conversational starters
- Provide clear, factual medical information only
- Reference previous conversation context when relevant
- If information is unavailable, state this directly
- Answer only what is asked

Response:"""
)

# Initialize QA chain
if vectorstore:
    # Use a simpler approach without RetrievalQA to handle custom prompt with conversation history
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    qa_chain = retriever
else:
    qa_chain = None

def transcribe_audio(audio_file):
    """Convert audio to text using OpenAI Whisper"""
    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            audio_file.save(temp_file.name)
            
        # Transcribe using OpenAI Whisper
        with open(temp_file.name, "rb") as audio:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio
            )
        
        # Clean up temp file
        os.unlink(temp_file.name)
        
        return transcript.text
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return None

def text_to_speech(text):
    """Convert text to speech using ElevenLabs with gTTS fallback"""
    # Try ElevenLabs first
    try:
        logger.info("Trying ElevenLabs TTS...")
        # Use a professional, clear voice for medical context
        voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel - professional female voice
        
        # Generate speech with natural settings
        response = elevenlabs_client.text_to_speech.convert(
            voice_id=voice_id,
            optimize_streaming_latency="0",
            output_format="mp3_22050_32",
            text=text,
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.8,
                style=0.2,
                use_speaker_boost=True,
            ),
        )
        
        # Create audio buffer
        audio_buffer = io.BytesIO()
        for chunk in response:
            audio_buffer.write(chunk)
        audio_buffer.seek(0)
        
        logger.info("ElevenLabs TTS successful")
        return audio_buffer
        
    except Exception as e:
        logger.warning(f"ElevenLabs TTS failed: {e}")
        logger.info("Falling back to Google TTS...")
        
        # Fallback to Google TTS
        try:
            tts = gTTS(text=text, lang='en', slow=False)
            audio_buffer = io.BytesIO()
            tts.write_to_fp(audio_buffer)
            audio_buffer.seek(0)
            
            logger.info("Google TTS successful")
            return audio_buffer
            
        except Exception as gtt_error:
            logger.error(f"Both ElevenLabs and Google TTS failed: {gtt_error}")
            return None

def get_medical_response(question):
    """Get response from the medical knowledge base with conversation memory"""
    if not qa_chain:
        return "The medical knowledge base is not available. Please ensure the Pinecone index has been set up and contains patient data."
    
    try:
        # Format conversation history for context
        history_text = ""
        if conversation_history:
            history_text = "\n".join([
                f"Q: {item['question']}\nA: {item['answer']}" 
                for item in conversation_history[-3:]  # Keep last 3 exchanges
            ])
        
        # Retrieve relevant documents
        docs = qa_chain.get_relevant_documents(question)
        context = "\n\n".join([doc.page_content for doc in docs])
        
        # Format the prompt with all required variables
        formatted_prompt = medical_prompt.format(
            context=context,
            question=question,
            conversation_history=history_text
        )
        
        # Get response from LLM
        response = llm.invoke(formatted_prompt)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Add to conversation history
        conversation_history.append({
            "question": question,
            "answer": answer
        })
        
        return answer
        
    except Exception as e:
        logger.error(f"Error getting medical response: {e}")
        return "I encountered an error while searching the medical records."

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "pinecone_connected": vectorstore is not None,
        "qa_chain_ready": qa_chain is not None,
        "available_indexes": [index.name for index in pc.list_indexes()] if pc else []
    })

@app.route('/api/ask', methods=['POST'])
def ask_medical_question():
    """Main endpoint for voice medical queries"""
    try:
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "No audio file selected"}), 400
        
        logger.info("Received audio file for processing")
        
        # Step 1: Transcribe audio to text
        transcribed_text = transcribe_audio(audio_file)
        if not transcribed_text:
            return jsonify({"error": "Failed to transcribe audio"}), 500
        
        logger.info(f"Transcribed text: {transcribed_text}")
        
        # Step 2: Get response from medical knowledge base
        medical_response = get_medical_response(transcribed_text)
        logger.info(f"Medical response: {medical_response}")
        
        # Step 3: Convert response to speech
        audio_response = text_to_speech(medical_response)
        if not audio_response:
            return jsonify({"error": "Failed to generate audio response"}), 500
        
        # Step 4: Return audio file
        return send_file(
            audio_response,
            mimetype='audio/mpeg',
            as_attachment=True,
            download_name='response.mp3'
        )
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/api/test-tts', methods=['POST'])
def test_tts():
    """Test endpoint for text-to-speech"""
    data = request.get_json()
    text = data.get('text', 'Hello, this is a test of the text-to-speech system.')
    
    audio_response = text_to_speech(text)
    if not audio_response:
        return jsonify({"error": "Failed to generate audio"}), 500
    
    return send_file(
        audio_response,
        mimetype='audio/mpeg',
        as_attachment=True,
        download_name='test.mp3'
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001) 