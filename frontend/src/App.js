import React, { useState, useRef, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const App = () => {
  const [isConversationActive, setIsConversationActive] = useState(false);
  const [hasUserInteracted, setHasUserInteracted] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isThinking, setIsThinking] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const [response, setResponse] = useState('Click the button below to start your medical conversation');
  const [conversationHistory, setConversationHistory] = useState([]);
  const [error, setError] = useState('');
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [silenceTimer, setSilenceTimer] = useState(null);
  
  const audioChunks = useRef([]);
  const responseAudioRef = useRef(null);
  const audioContext = useRef(null);
  const analyser = useRef(null);
  const microphone = useRef(null);
  const dataArray = useRef(null);
  const animationFrame = useRef(null);
  
  const thinkingPhrases = [
    "Processing...",
    "Searching records...", 
    "Analyzing...",
    "Looking up data...",
    "Checking records..."
  ];

  const SILENCE_THRESHOLD = 25; // Adjust based on your microphone
  const SILENCE_DURATION = 1000; // 1 second of silence before stopping

  useEffect(() => {
    checkBackendHealth();
    
    // Set up periodic check to ensure conversation continues
    const conversationCheckInterval = setInterval(() => {
      ensureContinuousListening();
    }, 3000); // Check every 3 seconds
    
    return () => {
      if (animationFrame.current) {
        cancelAnimationFrame(animationFrame.current);
      }
      if (silenceTimer) {
        clearTimeout(silenceTimer);
      }
      clearInterval(conversationCheckInterval);
    };
  }, [isConversationActive, isListening, isProcessing, isSpeaking]);

  const checkBackendHealth = async () => {
    try {
      await axios.get('/api/health');
      console.log('Backend is running');
    } catch (error) {
      setError('Backend server is not running. Please start the Flask backend.');
    }
  };

  const detectSilence = useCallback(() => {
    if (!analyser.current || !isListening || !dataArray.current) {
      console.log('detectSilence: Missing required components', {
        analyser: !!analyser.current,
        isListening,
        dataArray: !!dataArray.current
      });
      return;
    }
    
    analyser.current.getByteFrequencyData(dataArray.current);
    
    // Calculate average volume
    let sum = 0;
    for (let i = 0; i < dataArray.current.length; i++) {
      sum += dataArray.current[i];
    }
    const average = sum / dataArray.current.length;
    
    console.log('Audio level:', average); // Debug logging
    
    if (average < SILENCE_THRESHOLD) {
      // Silence detected
      if (!silenceTimer) {
        console.log('Silence detected, starting timer');
        const timer = setTimeout(() => {
          console.log('Silence timeout reached, stopping listening');
          if (isListening && mediaRecorder && mediaRecorder.state === 'recording') {
            console.log('Stopping recording due to silence');
            stopListening();
          }
        }, SILENCE_DURATION);
        setSilenceTimer(timer);
      }
    } else {
      // Sound detected, clear silence timer
      if (silenceTimer) {
        console.log('Sound detected, clearing silence timer');
        clearTimeout(silenceTimer);
        setSilenceTimer(null);
      }
    }
    
    if (isListening) {
      animationFrame.current = requestAnimationFrame(detectSilence);
    }
  }, [isListening, mediaRecorder, silenceTimer]);

  const startConversation = async () => {
    try {
      setError('');
      setConversationHistory([]);
      setIsConversationActive(true);
      
      // Generate and play welcome message
      const welcomeText = "Hello! I'm your medical assistant. How can I help you today?";
      setResponse(welcomeText);
      
      // Convert welcome to speech and play it
      const audioResponse = await textToSpeechLocally(welcomeText);
      if (audioResponse && responseAudioRef.current) {
        setIsSpeaking(true);
        const audioUrl = URL.createObjectURL(audioResponse);
        responseAudioRef.current.src = audioUrl;
        responseAudioRef.current.play();
      } else {
        // If TTS fails, just start listening
        setTimeout(() => {
          startListening();
        }, 2000);
      }
      
    } catch (error) {
      console.error('Error starting conversation:', error);
      setError('Error starting conversation. Please check microphone permissions.');
    }
  };

  const textToSpeechLocally = async (text) => {
    try {
      const response = await axios.post('/api/test-tts', { text }, {
        responseType: 'blob',
        timeout: 10000
      });
      return response.data;
    } catch (error) {
      console.error('Error with local TTS:', error);
      return null;
    }
  };

  const startConversationWithGreeting = async () => {
    try {
      setIsConversationActive(true);
      setResponse('🎤 Starting conversation...');
      
      // Generate greeting message
      const greetingText = "Hello! I'm your medical assistant. I can help you find patient information. What would you like to know?";
      
      // Add greeting to conversation history immediately
      setConversationHistory(prev => [...prev, 
        { type: 'assistant', content: greetingText, timestamp: new Date() }
      ]);
      
      // Convert greeting to speech
      const response = await axios.post('/api/test-tts', { text: greetingText }, {
        responseType: 'blob',
        timeout: 10000
      });
      
      if (response.data && responseAudioRef.current) {
        setIsSpeaking(true);
        setResponse('🔊 Greeting you...');
        const audioUrl = URL.createObjectURL(response.data);
        responseAudioRef.current.src = audioUrl;
        responseAudioRef.current.play();
        // The onAudioEnded handler will automatically start listening after greeting finishes
      } else {
        // If TTS fails, just start listening
        setTimeout(() => {
          setResponse('🎧 Listening...');
          startListening();
        }, 2000);
      }
      
    } catch (error) {
      console.error('Error starting conversation:', error);
      // Fallback to just start listening
      setTimeout(() => {
        setResponse('🎧 Listening...');
        startListening();
      }, 2000);
    }
  };

  const handleStartConversation = async () => {
    setHasUserInteracted(true);
    
    // Small delay to let the UI update
    setTimeout(() => {
      startConversationWithGreeting();
    }, 300);
  };

  const stopConversation = () => {
    setIsConversationActive(false);
    setIsListening(false);
    setIsProcessing(false);
    setIsSpeaking(false);
    
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    
    if (silenceTimer) {
      clearTimeout(silenceTimer);
      setSilenceTimer(null);
    }
    
    if (animationFrame.current) {
      cancelAnimationFrame(animationFrame.current);
    }
    
    // Stop any playing audio
    if (responseAudioRef.current) {
      responseAudioRef.current.pause();
      responseAudioRef.current.currentTime = 0;
    }
    
    setResponse("Conversation paused. Click below to continue.");
  };

  const continueConversation = async () => {
    try {
      setIsConversationActive(true);
      setResponse('🎧 Listening...');
      
      // Start listening immediately without any greeting
      startListening();
      
    } catch (error) {
      console.error('Error continuing conversation:', error);
      // Fallback to just start listening
      setTimeout(() => {
        setResponse('🎧 Listening...');
        startListening();
      }, 1000);
    }
  };

  const startListening = async () => {
    console.log('startListening called', { isConversationActive, isProcessing, isListening });
    if (!isConversationActive || isProcessing || isListening) {
      console.log('startListening: Early return due to state', { isConversationActive, isProcessing, isListening });
      return;
    }
    
    try {
      console.log('Starting to listen...');
      setResponse('Listening... speak now');
      
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 44100,
          autoGainControl: false
        } 
      });
      
      // Set up audio analysis for silence detection
      if (!audioContext.current || audioContext.current.state === 'closed') {
        audioContext.current = new (window.AudioContext || window.webkitAudioContext)();
      }
      
      if (audioContext.current.state === 'suspended') {
        await audioContext.current.resume();
      }
      
      analyser.current = audioContext.current.createAnalyser();
      microphone.current = audioContext.current.createMediaStreamSource(stream);
      
      analyser.current.fftSize = 512;
      analyser.current.smoothingTimeConstant = 0.3;
      dataArray.current = new Uint8Array(analyser.current.frequencyBinCount);
      microphone.current.connect(analyser.current);
      
      const recorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });
      
      audioChunks.current = [];
      
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.current.push(event.data);
        }
      };
      
      recorder.onstop = () => {
        console.log('Recording stopped');
        stream.getTracks().forEach(track => track.stop());
        if (audioContext.current && audioContext.current.state !== 'closed') {
          audioContext.current.close();
        }
        sendAudioToBackend();
      };
      
      recorder.start(100); // Collect data every 100ms
      setMediaRecorder(recorder);
      setIsListening(true);
      
      // Start silence detection after a brief delay
      setTimeout(() => {
        if (isListening) {
          detectSilence();
        }
      }, 500);
      
    } catch (error) {
      console.error('Error starting recording:', error);
      setError('Error accessing microphone. Please allow microphone access and refresh the page.');
    }
  };

  const stopListening = () => {
    console.log('stopListening called', { 
      mediaRecorder: !!mediaRecorder, 
      state: mediaRecorder?.state,
      isListening 
    });
    
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      console.log('Stopping media recorder');
      mediaRecorder.stop();
      setIsListening(false);
      
      if (silenceTimer) {
        console.log('Clearing silence timer');
        clearTimeout(silenceTimer);
        setSilenceTimer(null);
      }
      
      if (animationFrame.current) {
        console.log('Cancelling animation frame');
        cancelAnimationFrame(animationFrame.current);
      }
    } else {
      console.log('stopListening: No active media recorder to stop');
    }
  };

  const sendAudioToBackend = async () => {
    console.log('sendAudioToBackend called', { 
      audioChunksLength: audioChunks.current.length,
      isConversationActive 
    });
    
    if (audioChunks.current.length === 0) {
      console.log('No audio recorded, restarting listening...');
      if (isConversationActive) {
        setTimeout(() => {
          setResponse('No audio detected. Please speak louder.');
          setTimeout(startListening, 2000);
        }, 1000);
      }
      return;
    }

    setIsProcessing(true);
    setIsThinking(true);
    setResponse('Processing your request...');
    
    // Start thinking phrase cycle
    let thinkingIndex = 0;
    const thinkingInterval = setInterval(() => {
      setResponse(thinkingPhrases[thinkingIndex]);
      thinkingIndex = (thinkingIndex + 1) % thinkingPhrases.length;
    }, 2000);

    try {
      const audioBlob = new Blob(audioChunks.current, { type: 'audio/webm' });
      console.log('Audio blob size:', audioBlob.size);
      
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      console.log('Sending audio to backend...');
      
      // Get both transcription and response in one call
      const response = await axios.post('/api/ask', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        responseType: 'json',
        timeout: 30000
      });

      clearInterval(thinkingInterval);
      setIsThinking(false);
      
      // Extract the response data
      const { transcribed_text, medical_response } = response.data;
      
      // Add user message to conversation history with transcribed text
      setConversationHistory(prev => [...prev, 
        { type: 'user', content: transcribed_text, timestamp: new Date() }
      ]);
      
      // Add assistant response to conversation history with actual medical response
      setConversationHistory(prev => [...prev, 
        { type: 'assistant', content: medical_response, timestamp: new Date() }
      ]);
      
      // Convert medical response to speech
      const audioResponse = await textToSpeechLocally(medical_response);
      if (audioResponse && responseAudioRef.current) {
        console.log('Playing audio response');
        setIsSpeaking(true);
        setResponse('Speaking...');
        const audioUrl = URL.createObjectURL(audioResponse);
        responseAudioRef.current.src = audioUrl;
        responseAudioRef.current.play();
      } else {
        console.log('No audio response, continuing conversation');
        // If no audio, just continue listening
        setTimeout(() => {
          onAudioEnded();
        }, 1000);
      }
      
    } catch (error) {
      clearInterval(thinkingInterval);
      setIsThinking(false);
      console.error('Error sending audio:', error);
      
      let errorMessage = 'Unknown error occurred';
      if (error.response) {
        errorMessage = `Server error: ${error.response.status} - ${error.response.statusText}`;
      } else if (error.request) {
        errorMessage = 'No response from server. Is the backend running on port 5001?';
      } else {
        errorMessage = `Error: ${error.message}`;
      }
      
      setError(errorMessage);
      
      // Continue conversation even on error
      if (isConversationActive) {
        setTimeout(() => {
          setResponse('I encountered an error. Please try speaking again.');
          setTimeout(startListening, 3000);
        }, 2000);
      }
    } finally {
      setIsProcessing(false);
    }
  };

  const onAudioEnded = () => {
    console.log('onAudioEnded called', { isConversationActive, isSpeaking });
    setIsSpeaking(false);
    
    // Always continue listening if conversation is active
    if (isConversationActive) {
      console.log('Conversation is active, restarting listening');
      setResponse('🎧 Listening...');
      // Automatically restart listening after AI finishes speaking
      setTimeout(() => {
        console.log('Timeout reached, calling startListening');
        startListening();
      }, 800);
    } else {
      console.log('Conversation is not active, stopping');
      setResponse('Conversation stopped.');
    }
  };

  // Add a backup mechanism to ensure conversation continues
  const ensureContinuousListening = () => {
    console.log('ensureContinuousListening called', { 
      isConversationActive, 
      isListening, 
      isProcessing, 
      isSpeaking 
    });
    
    if (isConversationActive && !isListening && !isProcessing && !isSpeaking) {
      console.log('Detected conversation should be listening but is not - restarting');
      setResponse('🎧 Listening...');
      setTimeout(() => {
        startListening();
      }, 500);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Board Walk Health - Medical Voice Assistant</h1>
        <p>Continuous voice conversation with medical AI</p>
      </header>

      <main className="App-main">
        <div className="conversation-section">
          
          {/* Conversation Control */}
          <div className="conversation-control">
            {!hasUserInteracted ? (
              <button onClick={handleStartConversation} className="start-conversation-btn">
                🎤 Start Medical Assistant
              </button>
            ) : !isConversationActive ? (
              <button onClick={continueConversation} className="start-conversation-btn">
                🔄 Continue Conversation
              </button>
            ) : (
              <div>
                <button onClick={stopConversation} className="stop-conversation-btn">
                  ⏸️ Pause Conversation
                </button>
                {isListening && (
                  <button onClick={stopListening} className="stop-listening-btn" style={{marginLeft: '10px', backgroundColor: '#ff4444'}}>
                    🛑 Stop Listening (Debug)
                  </button>
                )}
                {isConversationActive && !isListening && !isProcessing && (
                  <button onClick={startListening} className="force-listen-btn" style={{marginLeft: '10px', backgroundColor: '#44ff44'}}>
                    🎧 Force Listen (Debug)
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Status Display */}
          <div className={`status-display ${isListening ? 'listening' : ''} ${isProcessing ? 'processing' : ''} ${isSpeaking ? 'speaking' : ''}`}>
            {isListening && (
              <div className="listening-indicator">
                <div className="pulse-ring"></div>
                <div className="pulse-ring"></div>
                <div className="pulse-ring"></div>
                <span>🎧 Listening...</span>
              </div>
            )}
            
            {isProcessing && !isListening && (
              <div className="processing-indicator">
                <div className="spinner"></div>
                <span> Thinking...</span>
              </div>
            )}
            
            {isSpeaking && (
              <div className="speaking-indicator">
                <div className="audio-wave"></div>
                <span> Speaking...</span>
              </div>
            )}
          </div>

          {/* Current Response */}
          {response && (
            <div className={`current-response ${isThinking ? 'thinking' : ''}`}>
              <p>{response}</p>
            </div>
          )}

          {/* Conversation History */}
          {conversationHistory.length > 0 && (
            <div className="conversation-history">
              <h3>Conversation History</h3>
              <div className="history-messages">
                {conversationHistory.map((message, index) => (
                  <div key={index} className={`message ${message.type}`}>
                    <span className="message-type">
                      {message.type === 'user' ? '🗣️ You:' : '🤖 Assistant:'}
                    </span>
                    <span className="message-content">{message.content}</span>
                    <span className="message-time">
                      {message.timestamp.toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {error && (
            <div className="error">
              <h3>Error:</h3>
              <p>{error}</p>
            </div>
          )}
        </div>

        <div className="instructions">
          <h3>How to use:</h3>
          <ul>
            <li>Click "🎤 Start Medical Assistant" to begin</li>
            <li>The AI will greet you first, then you can respond naturally</li>
            <li>Speak when you see "🎧 Listening..." - it detects when you stop talking (1-second pause)</li>
            <li>The conversation flows continuously with memory of all previous exchanges</li>
            <li>Ask about patients like: "Tell me about John Doe" or "Who has diabetes?"</li>
            <li>Click "⏸️ Pause" to stop temporarily - use "🔄 Continue" to resume with full memory</li>
          </ul>
        </div>

        <div className="patient-details">
          <h3>Available Patient Records</h3>
          <div className="patient-grid">
            <div className="patient-card">
              <div className="patient-name">John Doe (45, Male)</div>
              <div className="patient-info">
                <div className="patient-condition">Hypertension</div>
                <p><strong>Last Visit:</strong> July 10, 2024</p>
                <p><strong>Medications:</strong> Amlodipine 5mg, Lisinopril 10mg</p>
                <p><strong>BP:</strong> 140/90 mmHg | <strong>Cholesterol:</strong> 220 mg/dL</p>
                <p><strong>Allergies:</strong> Penicillin</p>
              </div>
            </div>

            <div className="patient-card">
              <div className="patient-name">Sarah Smith (32, Female)</div>
              <div className="patient-info">
                <div className="patient-condition">Type 2 Diabetes</div>
                <div className="patient-condition">Obesity</div>
                <p><strong>Last Visit:</strong> August 15, 2024</p>
                <p><strong>Medications:</strong> Metformin 1000mg, Insulin glargine</p>
                <p><strong>HbA1c:</strong> 7.2% | <strong>Weight:</strong> 180 lbs (Goal: 150 lbs)</p>
                <p><strong>Complications:</strong> Early diabetic retinopathy</p>
              </div>
            </div>

            <div className="patient-card">
              <div className="patient-name">Michael Johnson (67, Male)</div>
              <div className="patient-info">
                <div className="patient-condition">Heart Failure</div>
                <div className="patient-condition">Atrial Fibrillation</div>
                <div className="patient-condition">COPD</div>
                <p><strong>Last Visit:</strong> September 2, 2024</p>
                <p><strong>Medications:</strong> Carvedilol, Furosemide, Warfarin</p>
                <p><strong>EF:</strong> 35% | <strong>O2 Sat:</strong> 92% on room air</p>
                <p><strong>INR:</strong> 2.4 (Target: 2-3)</p>
              </div>
            </div>

            <div className="patient-card">
              <div className="patient-name">Emily Chen (28, Female)</div>
              <div className="patient-info">
                <div className="patient-condition">Asthma</div>
                <div className="patient-condition">Anxiety</div>
                <p><strong>Last Visit:</strong> June 20, 2024</p>
                <p><strong>Medications:</strong> Fluticasone/Salmeterol, Sertraline 50mg</p>
                <p><strong>Control:</strong> Good asthma control, stable peak flow</p>
                <p><strong>Allergies:</strong> Environmental (pollen, dust mites)</p>
              </div>
            </div>

            <div className="patient-card">
              <div className="patient-name">Robert Williams (55, Male)</div>
              <div className="patient-info">
                <div className="patient-condition">Chronic Kidney Disease</div>
                <div className="patient-condition">Hypertension</div>
                <div className="patient-condition">Gout</div>
                <p><strong>Last Visit:</strong> August 30, 2024</p>
                <p><strong>Medications:</strong> Losartan 100mg, Allopurinol 300mg</p>
                <p><strong>Creatinine:</strong> 1.8 mg/dL | <strong>eGFR:</strong> 42 mL/min/1.73m²</p>
                <p><strong>Uric Acid:</strong> 6.2 mg/dL</p>
              </div>
            </div>
          </div>
        </div>

        {/* Hidden audio element for playing responses */}
        <audio 
          ref={responseAudioRef} 
          controls={false} 
          onEnded={onAudioEnded}
        />
      </main>
    </div>
  );
};

export default App; 