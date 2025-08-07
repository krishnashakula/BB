# 🎵 Binaural Beats Generator MVP

A production-ready binaural beats generator optimized for Railway deployment with enterprise-grade security and performance.

## 🚀 Quick Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template)

### One-Click Deployment
1. Click the Railway button above
2. Connect your GitHub account
3. Deploy automatically with zero configuration
4. Access your app at the provided Railway URL

## ✨ Features

### 🎧 Audio Engine
- **Scientific Accuracy**: Precise binaural beat generation with ±0.1Hz tolerance
- **Real-time Processing**: <50ms latency audio synthesis
- **Multiple Waveforms**: Sine, square, sawtooth, and triangle waves
- **Perfect Stereo Separation**: Isolated left/right channel processing

### 🧠 Brainwave Presets
- **Focus** (40Hz): Enhanced concentration and alertness
- **Relaxation** (8Hz): Stress reduction and calm
- **Deep Sleep** (2Hz): Sleep induction and recovery
- **Creativity** (6Hz): Enhanced creative thinking
- **Meditation** (4Hz): Mindfulness and deep relaxation

### 🔒 Enterprise Security
- JWT-based authentication with secure token management
- Rate limiting and input validation
- CORS protection with configurable origins
- Comprehensive error handling and logging

### ⚡ High Performance
- Vectorized audio processing with NumPy
- Memory-optimized for Railway's constraints (<512MB)
- Real-time WebSocket streaming
- Auto-scaling ready architecture

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend UI   │────│   FastAPI API    │────│  Audio Engine   │
│  (HTML/JS/CSS)  │    │  (REST + WS)     │    │   (NumPy/SciPy) │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌──────────────────┐             │
         └──────────────│ Session Manager  │─────────────┘
                        │  (In-Memory)     │
                        └──────────────────┘
```

## 🔧 Local Development

### Prerequisites
- Python 3.11+
- pip or poetry

### Setup
```bash
# Clone the repository
git clone <your-repo-url>
cd binaural-beats-generator

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export JWT_SECRET="your-secret-key-here"
export ENVIRONMENT="development"

# Run the application
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Access the Application
- **Web UI**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## 📡 API Endpoints

### Authentication
```http
GET /auth/demo-token          # Get demo JWT token
```

### Binaural Beats
```http
GET /beats/presets           # Available presets
POST /beats/generate         # Create custom configuration
```

### Sessions
```http
GET /sessions/{id}           # Session information
DELETE /sessions/{id}        # End session
```

### Real-time Streaming
```http
WS /beats/stream/{session_id} # WebSocket audio stream
```

### Monitoring
```http
GET /health                  # Health check
GET /metrics                 # Prometheus metrics
```

## 🎛️ Configuration

### Environment Variables
```bash
# Required
JWT_SECRET=your-256-bit-secret-key

# Optional
ENVIRONMENT=production
LOG_LEVEL=INFO
PORT=8000
```

### Audio Parameters
```python
# Default configuration
SAMPLE_RATE = 44100  # Hz (CD quality)
BUFFER_SIZE = 1024   # Samples per buffer
MAX_FREQUENCY = 1000 # Hz maximum carrier frequency
```

## 🔊 Usage Examples

### Web Interface
1. Open the application URL
2. Select a preset or customize parameters
3. Click "Start Session" to begin
4. Use headphones for proper binaural effect

### API Usage
```python
import requests
import json

# Get authentication token
token_response = requests.get("https://your-app.railway.app/auth/demo-token")
token = token_response.json()["access_token"]

# Create custom binaural beats
config = {
    "carrier_freq": 200,
    "beat_freq": 10,
    "waveform": "sine",
    "duration": 1800,
    "volume": 0.5
}

response = requests.post(
    "https://your-app.railway.app/beats/generate",
    json=config,
    headers={"Authorization": f"Bearer {token}"}
)

session_id = response.json()["session_id"]
print(f"Session created: {session_id}")
```

### WebSocket Client
```javascript
const ws = new WebSocket(`wss://your-app.railway.app/beats/stream/${sessionId}`);

ws.onmessage = (event) => {
    const audioData = JSON.parse(event.data);
    if (audioData.left_channel && audioData.right_channel) {
        // Process audio buffers for playback
        playBinauralAudio(audioData);
    }
};
```

## 📊 Monitoring

### Health Checks
Railway automatically monitors the `/health` endpoint:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-20T10:30:00Z",
  "active_sessions": 5,
  "version": "1.0.0"
}
```

### Metrics
Prometheus-compatible metrics at `/metrics`:
- `binaural_active_sessions`: Active session count
- `binaural_total_sessions`: Total sessions created
- `binaural_websocket_connections`: WebSocket connections

## 🛡️ Security Features

### Rate Limiting
- 100 requests per minute per user
- WebSocket connection limits
- Automatic DDoS protection

### Data Protection
- No persistent storage of audio data
- Secure JWT token management
- Input validation and sanitization
- CORS with explicit origin control

### Compliance
- GDPR-compliant session handling
- No PII in logs
- Secure headers and CSP

## 🚀 Production Deployment

### Railway Platform
```bash
# Deploy via CLI
railway login
railway init
railway up
```

### Environment Configuration
1. Set `JWT_SECRET` environment variable
2. Configure custom domain (optional)
3. Enable automatic deployments
4. Set up monitoring alerts

### Performance Optimization
- Single worker process (Railway optimized)
- Memory usage <512MB
- CPU optimized audio processing
- Automatic scaling ready

## 🔧 Troubleshooting

### Common Issues

**Audio not playing:**
- Ensure HTTPS connection for Web Audio API
- Check browser permissions for audio
- Verify headphones/speakers are connected

**High latency:**
- Check Railway region proximity
- Monitor `/metrics` endpoint
- Verify WebSocket connection stability

**Memory issues:**
- Monitor active sessions
- Implement session cleanup
- Check for memory leaks in logs

### Debugging
```bash
# Check application logs
railway logs

# Monitor resource usage
railway status

# Test health endpoint
curl https://your-app.railway.app/health
```

## 📝 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new functionality
4. Submit pull request

## 📞 Support

- **Documentation**: Check the `/docs` endpoint
- **Issues**: GitHub issues tracker
- **Health**: Monitor `/health` endpoint
- **Metrics**: Check `/metrics` for performance data

---

**⚠️ Medical Disclaimer**: This application is for wellness and entertainment purposes. Consult healthcare professionals before using binaural beats for medical conditions.