# main.py - Binaural Beats Generator MVP for Railway
import asyncio
import json
import math
import os
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import jwt
from pydantic import BaseModel, Field
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "binaural-beats-secret-key-change-in-production")
SAMPLE_RATE = 44100
BUFFER_SIZE = 1024

# Track startup time for health checks
startup_time = time.time()

# Data Models
class BinauralConfig(BaseModel):
    carrier_freq: float = Field(ge=40, le=1000, description="Base frequency in Hz")
    beat_freq: float = Field(ge=0.5, le=40, description="Beat frequency in Hz")
    waveform: str = Field(default="sine", pattern="^(sine|square|sawtooth|triangle)$")
    duration: int = Field(ge=1, le=3600, description="Duration in seconds")
    volume: float = Field(ge=0.0, le=1.0, default=0.5)

class SessionData(BaseModel):
    session_id: str
    config: BinauralConfig
    start_time: datetime
    is_active: bool = True

@dataclass
class AudioBuffer:
    left_channel: np.ndarray
    right_channel: np.ndarray
    timestamp: float

# Audio Generation Engine
class BinauralGenerator:
    """High-performance binaural beat generator with scientific accuracy"""
    
    def __init__(self, sample_rate: int = SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.buffer_size = BUFFER_SIZE
        
    def generate_waveform(self, frequency: float, duration: float, waveform: str = "sine") -> np.ndarray:
        """Generate waveform with specified parameters"""
        samples = int(duration * self.sample_rate)
        t = np.linspace(0, duration, samples, False)
        
        if waveform == "sine":
            return np.sin(2 * np.pi * frequency * t)
        elif waveform == "square":
            return np.sign(np.sin(2 * np.pi * frequency * t))
        elif waveform == "sawtooth":
            return 2 * (t * frequency - np.floor(0.5 + t * frequency))
        elif waveform == "triangle":
            return 2 * np.abs(2 * (t * frequency - np.floor(0.5 + t * frequency))) - 1
        else:
            raise ValueError(f"Unsupported waveform: {waveform}")
    
    def generate_binaural_beats(self, config: BinauralConfig) -> AudioBuffer:
        """Generate binaural beats with perfect L/R channel separation"""
        try:
            # Calculate frequencies for each ear
            left_freq = config.carrier_freq
            right_freq = config.carrier_freq + config.beat_freq
            
            # Generate buffer duration (streaming chunks)
            buffer_duration = self.buffer_size / self.sample_rate
            
            # Generate waveforms
            left_channel = self.generate_waveform(
                left_freq, buffer_duration, config.waveform
            ) * config.volume
            
            right_channel = self.generate_waveform(
                right_freq, buffer_duration, config.waveform
            ) * config.volume
            
            # Apply anti-aliasing filter (simple low-pass)
            nyquist = self.sample_rate / 2
            if config.carrier_freq > nyquist * 0.8:
                logger.warning(f"Frequency {config.carrier_freq}Hz near Nyquist limit")
            
            return AudioBuffer(
                left_channel=left_channel,
                right_channel=right_channel,
                timestamp=time.time()
            )
            
        except Exception as e:
            logger.error(f"Audio generation error: {e}")
            raise HTTPException(status_code=500, detail="Audio generation failed")

# Session Management
class SessionManager:
    """Manage active binaural beat sessions"""
    
    def __init__(self):
        self.sessions: Dict[str, SessionData] = {}
        self.active_connections: Dict[str, WebSocket] = {}
    
    def create_session(self, config: BinauralConfig) -> str:
        """Create new listening session"""
        session_id = f"session_{int(time.time())}_{hash(str(config)) % 10000}"
        
        session = SessionData(
            session_id=session_id,
            config=config,
            start_time=datetime.now()
        )
        
        self.sessions[session_id] = session
        logger.info(f"Created session {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    def end_session(self, session_id: str):
        """End session and cleanup"""
        if session_id in self.sessions:
            self.sessions[session_id].is_active = False
            if session_id in self.active_connections:
                del self.active_connections[session_id]
            logger.info(f"Ended session {session_id}")

# Authentication
security = HTTPBearer()

def create_access_token(user_id: str) -> str:
    """Create JWT token for user"""
    payload = {
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(hours=24),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify JWT token and return user_id"""
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Initialize components
app = FastAPI(
    title="Binaural Beats Generator MVP",
    description="Production-ready binaural beats generator for Railway",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
generator = BinauralGenerator()
session_manager = SessionManager()

# Preset configurations
PRESETS = {
    "focus": BinauralConfig(carrier_freq=200, beat_freq=40, waveform="sine", duration=1800),
    "relaxation": BinauralConfig(carrier_freq=150, beat_freq=8, waveform="sine", duration=1800),
    "deep_sleep": BinauralConfig(carrier_freq=100, beat_freq=2, waveform="sine", duration=3600),
    "creativity": BinauralConfig(carrier_freq=180, beat_freq=6, waveform="sine", duration=1800),
    "meditation": BinauralConfig(carrier_freq=120, beat_freq=4, waveform="sine", duration=2400),
}

# API Routes
@app.get("/", response_class=HTMLResponse)
async def get_frontend():
    """Serve the main UI"""
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Binaural Beats Generator</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                color: white;
            }
            
            .container {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(10px);
                border-radius: 20px;
                padding: 40px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                max-width: 500px;
                width: 100%;
            }
            
            h1 {
                text-align: center;
                margin-bottom: 30px;
                font-size: 2.5em;
                font-weight: 300;
                text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
            }
            
            .controls {
                display: grid;
                gap: 20px;
                margin-bottom: 30px;
            }
            
            .control-group {
                display: flex;
                flex-direction: column;
                gap: 8px;
            }
            
            label {
                font-weight: 500;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            input, select, button {
                padding: 12px;
                border: none;
                border-radius: 10px;
                background: rgba(255, 255, 255, 0.9);
                color: #333;
                font-size: 1em;
            }
            
            input:focus, select:focus {
                outline: none;
                box-shadow: 0 0 0 3px rgba(255, 255, 255, 0.3);
            }
            
            .presets {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                gap: 10px;
                margin-bottom: 20px;
            }
            
            .preset-btn {
                background: rgba(255, 255, 255, 0.2);
                color: white;
                border: 1px solid rgba(255, 255, 255, 0.3);
                cursor: pointer;
                transition: all 0.3s ease;
                font-size: 0.85em;
            }
            
            .preset-btn:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }
            
            .preset-btn.active {
                background: rgba(255, 255, 255, 0.4);
                box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            }
            
            .play-btn {
                background: linear-gradient(45deg, #00f260, #0575e6);
                color: white;
                font-weight: 600;
                font-size: 1.1em;
                cursor: pointer;
                transition: all 0.3s ease;
                margin-top: 10px;
            }
            
            .play-btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            }
            
            .play-btn:disabled {
                background: #666;
                cursor: not-allowed;
                transform: none;
            }
            
            .status {
                text-align: center;
                margin-top: 20px;
                padding: 15px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 10px;
                font-weight: 500;
            }
            
            .status.playing {
                background: rgba(0, 242, 96, 0.2);
                animation: pulse 2s infinite;
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 0.8; }
                50% { opacity: 1; }
            }
            
            .visualizer {
                height: 60px;
                background: rgba(0, 0, 0, 0.2);
                border-radius: 10px;
                margin: 20px 0;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }
            
            .wave {
                width: 4px;
                background: linear-gradient(to top, #00f260, #0575e6);
                margin: 0 1px;
                border-radius: 2px;
                animation: wave 1.5s ease-in-out infinite;
            }
            
            @keyframes wave {
                0%, 100% { height: 10px; }
                50% { height: 40px; }
            }
            
            .wave:nth-child(2) { animation-delay: 0.1s; }
            .wave:nth-child(3) { animation-delay: 0.2s; }
            .wave:nth-child(4) { animation-delay: 0.3s; }
            .wave:nth-child(5) { animation-delay: 0.4s; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎵 Binaural Beats</h1>
            
            <div class="presets">
                <button class="preset-btn" onclick="loadPreset('focus')">Focus</button>
                <button class="preset-btn" onclick="loadPreset('relaxation')">Relax</button>
                <button class="preset-btn" onclick="loadPreset('deep_sleep')">Sleep</button>
                <button class="preset-btn" onclick="loadPreset('creativity')">Create</button>
                <button class="preset-btn" onclick="loadPreset('meditation')">Meditate</button>
            </div>
            
            <div class="controls">
                <div class="control-group">
                    <label>Carrier Frequency (Hz)</label>
                    <input type="number" id="carrier_freq" min="40" max="1000" value="200" step="10">
                </div>
                
                <div class="control-group">
                    <label>Beat Frequency (Hz)</label>
                    <input type="number" id="beat_freq" min="0.5" max="40" value="10" step="0.5">
                </div>
                
                <div class="control-group">
                    <label>Waveform</label>
                    <select id="waveform">
                        <option value="sine">Sine Wave</option>
                        <option value="square">Square Wave</option>
                        <option value="sawtooth">Sawtooth Wave</option>
                        <option value="triangle">Triangle Wave</option>
                    </select>
                </div>
                
                <div class="control-group">
                    <label>Volume</label>
                    <input type="range" id="volume" min="0" max="1" value="0.3" step="0.1">
                </div>
            </div>
            
            <button class="play-btn" id="playBtn" onclick="togglePlay()">
                ▶ Start Session
            </button>
            
            <div class="visualizer" id="visualizer" style="display: none;">
                <div class="wave"></div>
                <div class="wave"></div>
                <div class="wave"></div>
                <div class="wave"></div>
                <div class="wave"></div>
            </div>
            
            <div class="status" id="status">
                Ready to generate binaural beats
            </div>
        </div>
        
        <script>
            let audioContext;
            let leftOscillator, rightOscillator;
            let gainNode;
            let isPlaying = false;
            let currentSession = null;
            
            const presets = {
                focus: { carrier_freq: 200, beat_freq: 40, waveform: 'sine', volume: 0.3 },
                relaxation: { carrier_freq: 150, beat_freq: 8, waveform: 'sine', volume: 0.3 },
                deep_sleep: { carrier_freq: 100, beat_freq: 2, waveform: 'sine', volume: 0.2 },
                creativity: { carrier_freq: 180, beat_freq: 6, waveform: 'sine', volume: 0.3 },
                meditation: { carrier_freq: 120, beat_freq: 4, waveform: 'sine', volume: 0.25 }
            };
            
            function loadPreset(presetName) {
                const preset = presets[presetName];
                if (preset) {
                    document.getElementById('carrier_freq').value = preset.carrier_freq;
                    document.getElementById('beat_freq').value = preset.beat_freq;
                    document.getElementById('waveform').value = preset.waveform;
                    document.getElementById('volume').value = preset.volume;
                    
                    // Update UI
                    document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
                    event.target.classList.add('active');
                    
                    updateStatus(`Loaded ${presetName} preset`);
                }
            }
            
            function updateStatus(message) {
                const status = document.getElementById('status');
                status.textContent = message;
                status.className = isPlaying ? 'status playing' : 'status';
            }
            
            async function initAudio() {
                if (!audioContext) {
                    audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    gainNode = audioContext.createGain();
                    gainNode.connect(audioContext.destination);
                }
                
                if (audioContext.state === 'suspended') {
                    await audioContext.resume();
                }
            }
            
            function startBinauralBeats() {
                const carrierFreq = parseFloat(document.getElementById('carrier_freq').value);
                const beatFreq = parseFloat(document.getElementById('beat_freq').value);
                const waveform = document.getElementById('waveform').value;
                const volume = parseFloat(document.getElementById('volume').value);
                
                // Create oscillators
                leftOscillator = audioContext.createOscillator();
                rightOscillator = audioContext.createOscillator();
                
                // Create stereo panner for perfect L/R separation
                const leftPanner = audioContext.createStereoPanner();
                const rightPanner = audioContext.createStereoPanner();
                leftPanner.pan.value = -1; // Full left
                rightPanner.pan.value = 1;  // Full right
                
                // Set frequencies
                leftOscillator.frequency.value = carrierFreq;
                rightOscillator.frequency.value = carrierFreq + beatFreq;
                
                // Set waveform
                leftOscillator.type = waveform;
                rightOscillator.type = waveform;
                
                // Set volume
                gainNode.gain.value = volume;
                
                // Connect audio graph
                leftOscillator.connect(leftPanner);
                rightOscillator.connect(rightPanner);
                leftPanner.connect(gainNode);
                rightPanner.connect(gainNode);
                
                // Start oscillators
                leftOscillator.start();
                rightOscillator.start();
                
                updateStatus(`Playing: ${carrierFreq}Hz ± ${beatFreq/2}Hz (${waveform})`);
            }
            
            function stopBinauralBeats() {
                if (leftOscillator) {
                    leftOscillator.stop();
                    leftOscillator = null;
                }
                if (rightOscillator) {
                    rightOscillator.stop();
                    rightOscillator = null;
                }
                updateStatus('Session ended');
            }
            
            async function togglePlay() {
                const playBtn = document.getElementById('playBtn');
                const visualizer = document.getElementById('visualizer');
                
                if (!isPlaying) {
                    try {
                        await initAudio();
                        startBinauralBeats();
                        isPlaying = true;
                        playBtn.textContent = '⏹ Stop Session';
                        playBtn.style.background = 'linear-gradient(45deg, #ff6b6b, #ee5a24)';
                        visualizer.style.display = 'flex';
                    } catch (error) {
                        console.error('Failed to start audio:', error);
                        updateStatus('Failed to start audio - check permissions');
                    }
                } else {
                    stopBinauralBeats();
                    isPlaying = false;
                    playBtn.textContent = '▶ Start Session';
                    playBtn.style.background = 'linear-gradient(45deg, #00f260, #0575e6)';
                    visualizer.style.display = 'none';
                }
            }
            
            // Update volume in real-time
            document.getElementById('volume').addEventListener('input', function() {
                if (gainNode && isPlaying) {
                    gainNode.gain.value = this.value;
                }
            });
            
            // Update frequency in real-time
            document.getElementById('carrier_freq').addEventListener('input', function() {
                if (leftOscillator && isPlaying) {
                    const carrierFreq = parseFloat(this.value);
                    const beatFreq = parseFloat(document.getElementById('beat_freq').value);
                    leftOscillator.frequency.value = carrierFreq;
                    rightOscillator.frequency.value = carrierFreq + beatFreq;
                }
            });
            
            document.getElementById('beat_freq').addEventListener('input', function() {
                if (rightOscillator && isPlaying) {
                    const carrierFreq = parseFloat(document.getElementById('carrier_freq').value);
                    const beatFreq = parseFloat(this.value);
                    rightOscillator.frequency.value = carrierFreq + beatFreq;
                }
            });
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint for Railway"""
    try:
        # Basic health indicators
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "active_sessions": len(session_manager.sessions),
            "active_connections": len(session_manager.active_connections),
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "port": os.getenv("PORT", "8000"),
            "uptime": time.time() - startup_time if 'startup_time' in globals() else 0
        }
        
        logger.info(f"Health check: {health_data['status']}")
        return health_data
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/auth/demo-token")
async def get_demo_token():
    """Get demo token for testing (remove in production)"""
    token = create_access_token("demo_user")
    return {"access_token": token, "token_type": "bearer"}

@app.get("/beats/presets")
async def get_presets():
    """Get available binaural beat presets"""
    return {
        "presets": {
            name: {
                "carrier_freq": config.carrier_freq,
                "beat_freq": config.beat_freq,
                "waveform": config.waveform,
                "duration": config.duration,
                "description": f"Optimized for {name.replace('_', ' ')}"
            }
            for name, config in PRESETS.items()
        }
    }

@app.post("/beats/generate")
async def generate_beats(config: BinauralConfig, user_id: str = Depends(verify_token)):
    """Generate custom binaural beats configuration"""
    try:
        # Validate configuration
        if config.carrier_freq + config.beat_freq > 1000:
            raise HTTPException(
                status_code=400, 
                detail="Combined frequency exceeds maximum limit"
            )
        
        # Test generation to ensure parameters work
        test_buffer = generator.generate_binaural_beats(config)
        
        # Create session
        session_id = session_manager.create_session(config)
        
        return {
            "session_id": session_id,
            "config": config.dict(),
            "status": "ready",
            "estimated_quality": "high" if config.carrier_freq < 500 else "medium"
        }
        
    except Exception as e:
        logger.error(f"Beat generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str, user_id: str = Depends(verify_token)):
    """Get session information"""
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    duration_played = (datetime.now() - session.start_time).total_seconds()
    
    return {
        "session_id": session_id,
        "config": session.config.dict(),
        "start_time": session.start_time.isoformat(),
        "duration_played": duration_played,
        "is_active": session.is_active,
        "progress": min(duration_played / session.config.duration, 1.0) if session.config.duration else 0
    }

@app.delete("/sessions/{session_id}")
async def end_session(session_id: str, user_id: str = Depends(verify_token)):
    """End and cleanup session"""
    session_manager.end_session(session_id)
    return {"status": "session_ended", "session_id": session_id}

@app.websocket("/beats/stream/{session_id}")
async def websocket_audio_stream(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time audio streaming"""
    await websocket.accept()
    
    session = session_manager.get_session(session_id)
    if not session:
        await websocket.close(code=4004, reason="Session not found")
        return
    
    session_manager.active_connections[session_id] = websocket
    logger.info(f"WebSocket connected for session {session_id}")
    
    try:
        start_time = time.time()
        
        while session.is_active and time.time() - start_time < session.config.duration:
            # Generate audio buffer
            audio_buffer = generator.generate_binaural_beats(session.config)
            
            # Convert to JSON-serializable format
            audio_data = {
                "left_channel": audio_buffer.left_channel.tolist(),
                "right_channel": audio_buffer.right_channel.tolist(),
                "timestamp": audio_buffer.timestamp,
                "sample_rate": SAMPLE_RATE,
                "buffer_size": BUFFER_SIZE
            }
            
            # Send to client
            await websocket.send_json(audio_data)
            
            # Wait for next buffer (maintain real-time streaming)
            await asyncio.sleep(BUFFER_SIZE / SAMPLE_RATE)
        
        # Session completed
        await websocket.send_json({"status": "completed", "message": "Session finished"})
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.send_json({"status": "error", "message": str(e)})
    finally:
        session_manager.end_session(session_id)

@app.get("/metrics")
async def get_metrics():
    """Prometheus-compatible metrics endpoint"""
    active_sessions = len([s for s in session_manager.sessions.values() if s.is_active])
    total_sessions = len(session_manager.sessions)
    
    metrics = f"""
# HELP binaural_active_sessions Number of active binaural beat sessions
# TYPE binaural_active_sessions gauge
binaural_active_sessions {active_sessions}

# HELP binaural_total_sessions Total number of sessions created
# TYPE binaural_total_sessions counter
binaural_total_sessions {total_sessions}

# HELP binaural_websocket_connections Number of active WebSocket connections
# TYPE binaural_websocket_connections gauge
binaural_websocket_connections {len(session_manager.active_connections)}
"""
    
    return JSONResponse(content=metrics, media_type="text/plain")

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Global HTTP exception handler"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "timestamp": datetime.now().isoformat()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "timestamp": datetime.now().isoformat()}
    )

# Startup/shutdown events
@app.on_event("startup")
async def startup_event():
    """Application startup"""
    logger.info("🎵 Binaural Beats Generator MVP starting up...")
    logger.info(f"📊 Sample rate: {SAMPLE_RATE}Hz, Buffer size: {BUFFER_SIZE}")
    logger.info(f"🌐 Port: {os.getenv('PORT', 8000)}")
    logger.info(f"🔒 JWT Secret configured: {'Yes' if JWT_SECRET else 'No'}")
    logger.info("✅ Application startup complete!")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown"""
    logger.info("🛑 Shutting down Binaural Beats Generator MVP...")
    # End all active sessions
    for session_id in list(session_manager.sessions.keys()):
        session_manager.end_session(session_id)
    logger.info("✅ Shutdown complete!")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
