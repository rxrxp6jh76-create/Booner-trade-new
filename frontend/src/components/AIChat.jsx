import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';

const API = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8001';

const AIChat = ({ aiProvider, aiModel, onClose }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);
  const [isOpen, setIsOpen] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [recognition, setRecognition] = useState(null);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Welcome message
    setMessages([{
      role: 'assistant',
      content: `👋 Hallo! Ich bin deine Trading-KI (${aiProvider === 'ollama' ? 'Ollama' : 'GPT-5'}). Frag mich alles über deine Trades, Marktdaten oder Trading-Strategien!`,
      timestamp: new Date()
    }]);
    
    // Initialize Web Speech API
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      console.log('✅ Web Speech API verfügbar');
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();
      
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = false;
      recognitionInstance.lang = 'de-DE'; // German
      recognitionInstance.maxAlternatives = 1;
      
      console.log('✅ Speech Recognition konfiguriert:', {
        continuous: recognitionInstance.continuous,
        lang: recognitionInstance.lang,
        interimResults: recognitionInstance.interimResults
      });
      
      recognitionInstance.onresult = (event) => {
        try {
          const transcript = event.results[0][0].transcript;
          console.log('✅ Erkannt:', transcript);
          setInput(transcript);
          setIsListening(false);
        } catch (error) {
          console.error('Fehler beim Verarbeiten der Spracherkennung:', error);
          setIsListening(false);
        }
      };
      
      recognitionInstance.onerror = (event) => {
        console.error('❌ Speech recognition error:', event.error);
        setIsListening(false);
        
        if (event.error === 'not-allowed') {
          alert('⚠️ Mikrofon-Zugriff verweigert!\n\nBitte erlauben Sie den Mikrofon-Zugriff in Ihren Browser-Einstellungen.');
        } else if (event.error === 'no-speech') {
          console.log('Keine Sprache erkannt');
        } else if (event.error === 'network') {
          alert('⚠️ Netzwerkfehler bei der Spracherkennung. Prüfen Sie Ihre Internetverbindung.');
        } else {
          alert(`⚠️ Spracherkennungs-Fehler: ${event.error}`);
        }
      };
      
      recognitionInstance.onstart = () => {
        console.log('🎤 Spracherkennung läuft...');
      };
      
      recognitionInstance.onend = () => {
        console.log('⏹️ Spracherkennung beendet');
        setIsListening(false);
      };
      
      setRecognition(recognitionInstance);
      console.log('✅ Speech Recognition Instance erstellt');
    } else {
      console.warn('❌ Web Speech API NICHT verfügbar in diesem Browser!');
      console.log('Browser:', navigator.userAgent);
    }
  }, [aiProvider]);

  // Voice recognition handlers (Web Speech API)
  const startListening = () => {
    console.log('🎤 startListening aufgerufen');
    console.log('Recognition Object:', recognition);
    console.log('isListening:', isListening);
    
    if (!recognition) {
      alert('❌ Spracherkennung ist nicht verfügbar!\n\nBitte nutzen Sie Chrome oder Safari.\n\nAktueller Browser: ' + navigator.userAgent);
      return;
    }
    
    if (isListening) {
      console.log('⚠️ Recognition läuft bereits');
      return;
    }
    
    try {
      console.log('🎤 Starte recognition.start()...');
      recognition.start();
      setIsListening(true);
      console.log('✅ Web Speech Recognition gestartet');
    } catch (error) {
      console.error('❌ Fehler beim Starten der Spracherkennung:', error);
      console.error('Error Name:', error.name);
      console.error('Error Message:', error.message);
      
      if (error.name === 'InvalidStateError') {
        alert('⚠️ Spracherkennung läuft bereits oder wurde nicht richtig gestoppt.\n\nBitte laden Sie die Seite neu.');
      } else {
        alert('❌ Spracherkennung konnte nicht gestartet werden.\n\nFehler: ' + error.message + '\n\nBitte erlauben Sie Mikrofon-Zugriff in den Browser-Einstellungen.');
      }
    }
  };

  const stopListening = () => {
    if (recognition && isListening) {
      try {
        recognition.stop();
        setIsListening(false);
        console.log('⏹️ Web Speech Recognition gestoppt');
      } catch (error) {
        console.error('Fehler beim Stoppen:', error);
        setIsListening(false);
      }
    }
  };

  // Whisper recording handlers (Local Mac)
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(chunks, { type: 'audio/webm' });
        await transcribeWithWhisper(audioBlob);
        
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      setAudioChunks([]);
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Mikrofon-Zugriff verweigert');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
    }
  };

  const transcribeWithWhisper = async (audioBlob) => {
    try {
      const formData = new FormData();
      formData.append('file', audioBlob, 'audio.webm');

      const response = await axios.post(`${API}/api/whisper/transcribe`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        },
        timeout: 30000
      });

      if (response.data && response.data.success) {
        setInput(response.data.text);
      } else {
        alert('Whisper Transkription fehlgeschlagen');
      }
    } catch (error) {
      console.error('Whisper transcription error:', error);
      alert('Whisper ist nicht verfügbar. Installieren Sie: pip install openai-whisper');
    }
  };

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      console.log('Sending AI chat message:', input, 'Provider:', aiProvider);
      
      const response = await axios.post(`${API}/api/ai-chat`, null, {
        params: {
          message: input,
          session_id: sessionId,
          ai_provider: aiProvider || 'openai',
          model: aiModel || 'gpt-5'
        },
        timeout: 180000 // 3 minutes timeout for bulk operations (28 trades)
      });

      console.log('AI Chat response:', response.data);

      if (response.data && response.data.success) {
        const aiMessage = {
          role: 'assistant',
          content: response.data.response || 'Keine Antwort erhalten.',
          timestamp: new Date()
        };
        setMessages(prev => [...prev, aiMessage]);
      } else {
        throw new Error(response.data.response || 'Keine gültige Antwort');
      }
    } catch (error) {
      console.error('AI Chat error:', error);
      const errorMsg = error.response?.data?.response 
        || error.message 
        || 'Konnte keine Antwort von der KI erhalten.';
      
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `❌ Fehler: ${errorMsg}`,
        timestamp: new Date()
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Chat Toggle Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed bottom-4 right-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white p-4 rounded-full shadow-lg hover:shadow-xl transition-all z-50"
          title="KI-Chat öffnen"
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
          </svg>
        </button>
      )}

      {/* Chat Window */}
      {isOpen && (
        <div className="fixed bottom-4 right-4 w-96 h-[600px] bg-slate-800 rounded-lg shadow-2xl flex flex-col z-50 border border-slate-700">
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-4 rounded-t-lg flex justify-between items-center">
            <div>
              <h3 className="text-white font-bold">🤖 Trading KI</h3>
              <p className="text-xs text-blue-100">
                {aiProvider === 'ollama' ? '📍 Ollama (Lokal)' : '☁️ GPT-5 (Cloud)'}
              </p>
            </div>
            <button
              onClick={() => setIsOpen(false)}
              className="text-white hover:bg-white/20 p-1 rounded"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[80%] p-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-slate-700 text-slate-100'
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  <p className="text-xs opacity-60 mt-1">
                    {msg.timestamp.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-slate-700 p-3 rounded-lg">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                    <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                    <div className="w-2 h-2 bg-pink-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="p-4 border-t border-slate-700">
            {/* Status Indicator */}
            {(isListening || isRecording) && (
              <div className="mb-2 p-2 bg-red-900/30 border border-red-500/50 rounded text-center">
                <span className="text-red-400 text-sm font-semibold animate-pulse">
                  {isListening ? '🎤 Browser hört zu...' : '🎙️ Aufnahme läuft...'}
                </span>
              </div>
            )}
            
            {/* Debug Info - nur wenn recognition nicht verfügbar */}
            {!recognition && (
              <div className="mb-2 p-2 bg-yellow-900/30 border border-yellow-500/50 rounded text-center">
                <span className="text-yellow-400 text-xs">
                  ⚠️ Spracherkennung nicht verfügbar. Nutzen Sie Chrome oder Safari.
                  <br/>
                  <button 
                    onClick={() => window.location.reload()} 
                    className="mt-1 text-blue-400 underline"
                  >
                    Seite neu laden
                  </button>
                </span>
              </div>
            )}
            
            <div className="flex space-x-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                placeholder="Frage die KI... oder nutze Mikrofon 🎤"
                className="flex-1 bg-slate-700 text-white px-4 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={loading}
              />
              
              {/* Button Container with Labels */}
              <div className="flex items-center gap-2">
                {/* Web Speech Button (Browser) */}
                {recognition && (
                  <div className="flex flex-col items-center">
                    <button
                      onClick={isListening ? stopListening : startListening}
                      disabled={loading || isRecording}
                      className={`${
                        isListening 
                          ? 'bg-red-600 hover:bg-red-700 animate-pulse' 
                          : 'bg-purple-600 hover:bg-purple-700'
                      } text-white p-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed relative group`}
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                      {/* Tooltip */}
                      <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                        {isListening ? 'Stoppen' : 'Browser Spracheingabe'}
                      </div>
                    </button>
                    <span className="text-[10px] text-slate-400 mt-1">Browser</span>
                  </div>
                )}
                
                {/* Whisper Button (Local Mac) */}
                <div className="flex flex-col items-center">
                  <button
                    onClick={isRecording ? stopRecording : startRecording}
                    disabled={loading || isListening}
                    className={`${
                      isRecording 
                        ? 'bg-red-600 hover:bg-red-700 animate-pulse' 
                        : 'bg-orange-600 hover:bg-orange-700'
                    } text-white p-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed relative group`}
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                    </svg>
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                      {isRecording ? 'Stoppen & Senden' : 'Whisper (Offline)'}
                    </div>
                  </button>
                  <span className="text-[10px] text-slate-400 mt-1">Whisper</span>
                </div>
                
                {/* Send Button */}
                <div className="flex flex-col items-center">
                  <button
                    onClick={sendMessage}
                    disabled={loading || !input.trim()}
                    className="bg-blue-600 hover:bg-blue-700 text-white p-3 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed relative group"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    {/* Tooltip */}
                    <div className="absolute bottom-full mb-2 left-1/2 transform -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
                      Nachricht senden
                    </div>
                  </button>
                  <span className="text-[10px] text-slate-400 mt-1">Senden</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AIChat;
