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
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MedicalAssistant:
    def __init__(self):
        # Initialize OpenAI client
        self.client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Initialize ElevenLabs client (optional)
        try:
            if os.getenv('ELEVENLABS_API_KEY'):
                self.elevenlabs_client = ElevenLabs(api_key=os.getenv('ELEVENLABS_API_KEY'))
                logger.info("ElevenLabs client initialized")
            else:
                self.elevenlabs_client = None
                logger.info("No ElevenLabs API key found, will use Google TTS")
        except Exception as e:
            logger.warning(f"Failed to initialize ElevenLabs client: {e}")
            self.elevenlabs_client = None
        
        # Initialize Pinecone with new API
        self.pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))
        
        # Initialize embeddings and vector store
        self.embeddings = OpenAIEmbeddings()
        self.index_name = os.getenv('PINECONE_INDEX_NAME', 'medical-assistant')
        
        try:
            # Check if index exists and connect to it
            if self.index_name in [index.name for index in self.pc.list_indexes()]:
                self.index = self.pc.Index(self.index_name)
                self.vectorstore = PineconeVectorStore(
                    index=self.index,
                    embedding=self.embeddings
                )
                logger.info(f"Connected to existing Pinecone index: {self.index_name}")
            else:
                logger.warning(f"Pinecone index '{self.index_name}' not found. Please run the upload script first.")
                self.vectorstore = None
        except Exception as e:
            logger.error(f"Failed to connect to Pinecone index: {e}")
            self.vectorstore = None
        
        # Conversation memory storage (in production, use proper session management)
        self.conversation_history = []
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            openai_api_key=os.getenv('OPENAI_API_KEY')
        )
        
        # Initialize RAG tool
        self.setup_rag_tool()
        
        # Initialize agent with RAG tool
        self.setup_agent()
    
    def setup_rag_tool(self):
        """Setup RAG tool for medical knowledge retrieval"""
        if not self.vectorstore:
            self.rag_tool = None
            return
        
        def search_medical_records(query):
            """Search medical records using RAG"""
            try:
                docs = self.vectorstore.similarity_search(query, k=3)
                return "\n\n".join([doc.page_content for doc in docs])
            except Exception as e:
                logger.error(f"Error searching medical records: {e}")
                return "Error searching medical records"
        
        self.rag_tool = Tool(
            name="medical_records_search",
            description="Search medical records and patient information. Use this tool to find patient details, medical conditions, medications, and other healthcare information.",
            func=search_medical_records
        )
    
    def setup_agent(self):
        """Setup the agent with RAG tool"""
        if not self.rag_tool:
            self.agent = None
            return
        
        # Custom prompt for medical assistant
        medical_prompt = PromptTemplate(
            input_variables=["input", "agent_scratchpad"],
            template="""You are a professional medical assistant. Provide direct, accurate medical information without conversational filler words or phrases.

Previous Conversation Context:
{conversation_history}

Current Question: {input}

Instructions:
- Be direct and professional
- Never use acknowledgment phrases, filler words, or conversational starters
- Never mention remembering previous conversations
- Provide clear, factual medical information only
- Reference previous conversation context when relevant but don't explicitly state it
- If information is unavailable, state this directly
- Answer only what is asked
- Use the medical_records_search tool to find relevant patient information
- Important - Do not hallucinate or make up information. Only use the information provided by the medical_records_search tool. Only Answer the question asked do not answer something which was not asked.

{agent_scratchpad}"""
        )
        
        # Initialize agent
        self.agent = initialize_agent(
            tools=[self.rag_tool],
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )
    
    def transcribe_audio(self, audio_file):
        """Convert audio to text using OpenAI Whisper"""
        try:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                audio_file.save(temp_file.name)
                
            # Transcribe using OpenAI Whisper
            with open(temp_file.name, "rb") as audio:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio
                )
            
            # Clean up temp file
            os.unlink(temp_file.name)
            
            return transcript.text
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None
    
    def text_to_speech(self, text):
        """Convert text to speech using ElevenLabs with gTTS fallback"""
        # Try ElevenLabs first
        try:
            logger.info("Trying ElevenLabs TTS...")
            # Use a professional, clear voice for medical context
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel - professional female voice
            
            # Generate speech with natural settings
            response = self.elevenlabs_client.text_to_speech.convert(
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
    
    def get_medical_response(self, question):
        """Get response from the medical knowledge base using agent with RAG tool"""
        if not self.agent:
            return "The medical knowledge base is not available. Please ensure the Pinecone index has been set up and contains patient data."
        
        try:
            # Format conversation history for context
            history_text = ""
            if self.conversation_history:
                history_text = "\n".join([
                    f"Q: {item['question']}\nA: {item['answer']}" 
                    for item in self.conversation_history[-3:]  # Keep last 3 exchanges
                ])
            
            # Get response from agent
            response = self.agent.run(question)
            answer = response if isinstance(response, str) else str(response)
            
            # Add to conversation history
            self.conversation_history.append({
                "question": question,
                "answer": answer
            })
            
            return answer
            
        except Exception as e:
            logger.error(f"Error getting medical response: {e}")
            return "I encountered an error while searching the medical records."
    
    def process_audio_query(self, audio_file):
        """Process audio query and return both text and audio response"""
        # Step 1: Transcribe audio to text
        transcribed_text = self.transcribe_audio(audio_file)
        if not transcribed_text:
            return None, None, "Failed to transcribe audio"
        
        logger.info(f"Transcribed text: {transcribed_text}")
        
        # Step 2: Get response from medical knowledge base
        medical_response = self.get_medical_response(transcribed_text)
        logger.info(f"Medical response: {medical_response}")
        
        # Step 3: Convert response to speech
        audio_response = self.text_to_speech(medical_response)
        if not audio_response:
            return transcribed_text, medical_response, "Failed to generate audio response"
        
        return transcribed_text, medical_response, audio_response
    
    def test_tts(self, text):
        """Test text-to-speech functionality"""
        return self.text_to_speech(text)
    
    def get_health_status(self):
        """Get health status of the assistant"""
        return {
            "pinecone_connected": self.vectorstore is not None,
            "rag_tool_ready": self.rag_tool is not None,
            "agent_ready": self.agent is not None,
            "available_indexes": [index.name for index in self.pc.list_indexes()] if self.pc else []
        } 