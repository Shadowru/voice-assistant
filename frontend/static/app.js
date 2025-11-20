// frontend/static/app.js
class VoiceAssistant {
    constructor() {
        this.websocket = null;
        this.audioContext = null;
        this.mediaStream = null;
        this.processor = null;
        this.isRecording = false;
        this.startTime = null;
        
        this.initElements();
        this.attachEventListeners();
    }
    
    initElements() {
        this.startBtn = document.getElementById('startBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.status = document.getElementById('status');
        this.messages = document.getElementById('messages');
        this.latency = document.getElementById('latency');
        this.audioLevel = document.querySelector('.audio-level-bar');
    }
    
    attachEventListeners() {
        this.startBtn.addEventListener('click', () => this.start());
        this.stopBtn.addEventListener('click', () => this.stop());
    }
    
    async start() {
        try {
            await this.connectWebSocket();
            await this.startRecording();
            
            this.startBtn.disabled = true;
            this.stopBtn.disabled = false;
            this.updateStatus('recording', 'Recording...');
            
        } catch (error) {
            console.error('Start error:', error);
            this.addMessage('system', `Error: ${error.message}`);
        }
    }
    
    stop() {
        this.stopRecording();
        this.disconnectWebSocket();
        
        this.startBtn.disabled = false;
        this.stopBtn.disabled = true;
        this.updateStatus('disconnected', 'Disconnected');
    }
    
    async connectWebSocket() {
        return new Promise((resolve, reject) => {
            // Автоматическое определение протокола (ws или wss)
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/voice`;
            
            console.log('Connecting to:', wsUrl);
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('WebSocket connected');
                this.updateStatus('connected', 'Connected');
                resolve();
            };
            
            this.websocket.onmessage = async (event) => {
                if (typeof event.data === 'string') {
                    const data = JSON.parse(event.data);
                    this.handleTextMessage(data);
                } else {
                    await this.handleAudioMessage(event.data);
                }
            };
            
            this.websocket.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };
            
            this.websocket.onclose = () => {
                console.log('WebSocket closed');
                this.updateStatus('disconnected', 'Disconnected');
            };
        });
    }
    
    disconnectWebSocket() {
        if (this.websocket) {
            this.websocket.close();
            this.websocket = null;
        }
    }
    
    async startRecording() {
        try {
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    channelCount: 1,
                    sampleRate: 16000,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            this.audioContext = new AudioContext({ sampleRate: 16000 });
            const source = this.audioContext.createMediaStreamSource(this.mediaStream);
            
            // Анализатор для визуализации уровня
            const analyser = this.audioContext.createAnalyser();
            source.connect(analyser);
            this.visualizeAudioLevel(analyser);
            
            // Процессор для отправки данных
            this.processor = this.audioContext.createScriptProcessor(4096, 1, 1);
            source.connect(this.processor);
            this.processor.connect(this.audioContext.destination);
            
            this.processor.onaudioprocess = (e) => {
                if (!this.isRecording) return;
                
                const inputData = e.inputBuffer.getChannelData(0);
                const int16Data = this.float32ToInt16(inputData);
                
                if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                    this.websocket.send(int16Data.buffer);
                }
            };
            
            this.isRecording = true;
            this.startTime = Date.now();
            
        } catch (error) {
            console.error('Recording error:', error);
            throw error;
        }
    }
    
    stopRecording() {
        this.isRecording = false;
        
        if (this.processor) {
            this.processor.disconnect();
            this.processor = null;
        }
        
        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach(track => track.stop());
            this.mediaStream = null;
        }
        
        if (this.audioContext) {
            this.audioContext.close();
            this.audioContext = null;
        }
    }
    
    handleTextMessage(data) {
        if (data.type === 'transcript') {
            this.addMessage('user', data.content);
        } else if (data.type === 'response') {
            this.addMessage('assistant', data.content);
            
            // Обновление latency
            if (this.startTime) {
                const latency = ((Date.now() - this.startTime) / 1000).toFixed(2);
                this.latency.textContent = `${latency}s`;
                this.startTime = null;
            }
        }
    }
    
    async handleAudioMessage(audioBlob) {
        try {
            const arrayBuffer = await audioBlob.arrayBuffer();
            const audioBuffer = await this.audioContext.decodeAudioData(arrayBuffer);
            
            const source = this.audioContext.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(this.audioContext.destination);
            source.start();
            
        } catch (error) {
            console.error('Audio playback error:', error);
        }
    }
    
    addMessage(type, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const icon = type === 'user' ? '👤' : type === 'assistant' ? '🤖' : 'ℹ️';
        messageDiv.innerHTML = `
            <span class="message-icon">${icon}</span>
            <p>${content}</p>
        `;
        
        this.messages.appendChild(messageDiv);
        this.messages.scrollTop = this.messages.scrollHeight;
    }
    
    updateStatus(state, text) {
        this.status.className = `status ${state}`;
        this.status.textContent = text;
    }
    
    visualizeAudioLevel(analyser) {
        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        
        const update = () => {
            if (!this.isRecording) return;
            
            analyser.getByteFrequencyData(dataArray);
            const average = dataArray.reduce((a, b) => a + b) / dataArray.length;
            const percentage = (average / 255) * 100;
            
            this.audioLevel.style.width = `${percentage}%`;
            
            requestAnimationFrame(update);
        };
        
        update();
    }
    
    float32ToInt16(float32Array) {
        const int16Array = new Int16Array(float32Array.length);
        for (let i = 0; i < float32Array.length; i++) {
            const s = Math.max(-1, Math.min(1, float32Array[i]));
            int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        return int16Array;
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    new VoiceAssistant();
});