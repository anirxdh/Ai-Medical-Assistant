from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import logging
from agent import MedicalAssistant

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize the medical assistant
medical_assistant = MedicalAssistant()

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    health_status = medical_assistant.get_health_status()
    return jsonify({
        "status": "healthy",
        **health_status
    })

@app.route('/api/transcribe', methods=['POST'])
def transcribe_audio():
    """Endpoint to transcribe audio to text"""
    try:
        # Check if audio file is present
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file provided"}), 400
        
        audio_file = request.files['audio']
        if audio_file.filename == '':
            return jsonify({"error": "No audio file selected"}), 400
        
        logger.info("Received audio file for transcription")
        
        # Transcribe audio to text
        transcribed_text = medical_assistant.transcribe_audio(audio_file)
        
        if not transcribed_text:
            return jsonify({"error": "Failed to transcribe audio"}), 500
        
        return jsonify({
            "transcribed_text": transcribed_text
        })
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return jsonify({"error": "Internal server error"}), 500

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
        
        # Process the audio query using the medical assistant
        transcribed_text, medical_response, audio_response = medical_assistant.process_audio_query(audio_file)
        
        if not transcribed_text:
            return jsonify({"error": "Failed to transcribe audio"}), 500
        
        if not medical_response:
            return jsonify({"error": "Failed to get medical response"}), 500
        
        if not audio_response:
            return jsonify({"error": "Failed to generate audio response"}), 500
        
        # Return both text and audio response
        return jsonify({
            "transcribed_text": transcribed_text,
            "medical_response": medical_response
        })
        
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        return jsonify({"error": "Internal server error"}), 500



@app.route('/api/test-tts', methods=['POST'])
def test_tts():
    """Test endpoint for text-to-speech"""
    data = request.get_json()
    text = data.get('text', 'Hello, this is a test of the text-to-speech system.')
    
    audio_response = medical_assistant.test_tts(text)
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