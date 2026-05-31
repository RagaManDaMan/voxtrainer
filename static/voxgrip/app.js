// VoxGrip App Logic

let mediaRecorder;
let audioChunks = [];
let recordTimer;
let startTime;
let audioContext;
let analyser;
let bufferLength;
let dataArray;
let animationFrameId;
let isRecording = false;

// Trend chart state
let trendCanvas, trendCtx;
let historySessions = [];
let currentTrendMetric = 'dryness';

// UI elements
const recordBtn = document.getElementById("record-btn");
const timerDisplay = document.getElementById("timer-count");
const statusDisplay = document.getElementById("recording-status");
const apiStatus = document.getElementById("api-status");
const warningBanner = document.getElementById("api-key-warning");
const chatHistory = document.getElementById("agent-chat-history");
const analysisSpinner = document.getElementById("analysis-spinner");

// Exercise Instructions Mapping
const EXERCISE_INSTRUCTIONS = {
    lip_trill: {
        title: "The Trill Sustainer",
        desc: "Close lips loosely and blow air through them to make a motorboat sound, or roll your tongue ('r'). Keep pitch stable or slide up and down."
    },
    vowel_migration: {
        title: "Vowel Migration",
        desc: "Start singing on /i/ or /u/ in your high register. As you climb higher, gradually widen your throat and shade the vowel towards /ɪ/ ('bit') or /ʊ/ ('book') to release jaw tension."
    },
    voiced_fricative: {
        title: "Voiced Fricative Support",
        desc: "Produce a sustained 'v-v-v' or 'z-z-z' sound. Maintain a steady teeth-to-lip or teeth-to-tongue constriction to build abdominal back-pressure."
    },
    vocal_fry: {
        title: "Vocal Fry Onset",
        desc: "Relax your throat and make a lazy, low-pitched creaking sound. Let the bubbles of air float up without force to massage and realign the vocal fold margins."
    },
    messa_di_voce: {
        title: "Messa di Voce",
        desc: "Sing a single held note. Start extremely quiet (pianissimo), swell to your maximum comfortable volume (forte), and fade back to silence (pianissimo) without breaking pitch."
    },
    free_singing: {
        title: "Free Phonation Stability",
        desc: "Sing any custom scales, arpeggios, glissandi, or free musical phrases. The engine will evaluate your overall vocal stability, jitter, and shimmer indexes."
    }
};

function updateExerciseTooltip() {
    const selected = document.getElementById("exercise-type").value;
    const info = EXERCISE_INSTRUCTIONS[selected] || EXERCISE_INSTRUCTIONS.free_singing;
    
    document.getElementById("tooltip-title").textContent = info.title;
    document.getElementById("tooltip-desc").textContent = info.desc;
}

// Initialize on page load
window.addEventListener("DOMContentLoaded", () => {
    checkAPIStatus();
    initCanvases();
    loadHistory();
    loadSettings();
    loadProfile();
    updateExerciseTooltip();
});

// Check backend status & key
async function checkAPIStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        
        const indicator = apiStatus.querySelector(".status-indicator");
        const text = apiStatus.querySelector(".status-text");
        
        if (data.api_key_configured) {
            indicator.className = "status-indicator success";
            text.textContent = "Agent Active";
            warningBanner.classList.add("hidden");
        } else {
            indicator.className = "status-indicator error";
            text.textContent = "Key Missing";
            warningBanner.classList.remove("hidden");
        }
    } catch (e) {
        console.error("Backend offline", e);
        const indicator = apiStatus.querySelector(".status-indicator");
        const text = apiStatus.querySelector(".status-text");
        indicator.className = "status-indicator error";
        text.textContent = "Offline";
    }
}

// Tab navigation switching
function switchTab(tab) {
    document.querySelectorAll(".tab-btn").forEach(btn => btn.classList.remove("active"));
    document.querySelectorAll(".tab-section").forEach(sec => sec.classList.remove("active"));
    
    document.getElementById(`tab-${tab}`).classList.add("active");
    document.getElementById(`${tab}-section`).classList.add("active");
    
    if (tab === "history") {
        loadHistory();
    }
}

// --- Canvas Initializations ---
let vowelCanvas, vowelCtx;
let stabilityCanvas, stabilityCtx;
let waveCanvas, waveCtx;

function initCanvases() {
    vowelCanvas = document.getElementById("vowel-canvas");
    vowelCtx = vowelCanvas.getContext("2d");
    
    stabilityCanvas = document.getElementById("stability-canvas");
    stabilityCtx = stabilityCanvas.getContext("2d");
    
    waveCanvas = document.getElementById("waveform-canvas");
    waveCtx = waveCanvas.getContext("2d");
    
    trendCanvas = document.getElementById("trend-canvas");
    trendCtx = trendCanvas.getContext("2d");
    
    resizeCanvases();
    window.addEventListener("resize", resizeCanvases);
    
    // Draw initial static backgrounds
    drawVowelBackground([], []);
    drawStabilityBackground([], []);
    drawWaveformBackground();
}

function resizeCanvases() {
    // Read container sizes
    const vRect = vowelCanvas.parentElement.getBoundingClientRect();
    vowelCanvas.width = vRect.width;
    vowelCanvas.height = vRect.height;
    
    const sRect = stabilityCanvas.parentElement.getBoundingClientRect();
    stabilityCanvas.width = sRect.width;
    stabilityCanvas.height = sRect.height;
    
    const wRect = waveCanvas.parentElement.getBoundingClientRect();
    waveCanvas.width = wRect.width;
    waveCanvas.height = wRect.height;
    
    const tRect = trendCanvas.parentElement.getBoundingClientRect();
    trendCanvas.width = tRect.width;
    trendCanvas.height = tRect.height;
    
    if (historySessions && historySessions.length > 0) {
        drawLongitudinalChart(historySessions, currentTrendMetric);
    }
}

// --- Micro-Waveform Visualizer for Recording ---
function drawWaveformBackground() {
    waveCtx.fillStyle = "rgba(0, 0, 0, 0.1)";
    waveCtx.fillRect(0, 0, waveCanvas.width, waveCanvas.height);
    
    waveCtx.lineWidth = 2;
    waveCtx.strokeStyle = "rgba(0, 240, 255, 0.2)";
    waveCtx.beginPath();
    waveCtx.moveTo(0, waveCanvas.height / 2);
    waveCtx.lineTo(waveCanvas.width, waveCanvas.height / 2);
    waveCtx.stroke();
}

function visualizeLiveWave() {
    if (!isRecording) return;
    
    animationFrameId = requestAnimationFrame(visualizeLiveWave);
    analyser.getByteTimeDomainData(dataArray);
    
    waveCtx.fillStyle = "#0c101b";
    waveCtx.fillRect(0, 0, waveCanvas.width, waveCanvas.height);
    
    waveCtx.lineWidth = 2;
    waveCtx.strokeStyle = "#00f0ff";
    waveCtx.shadowBlur = 4;
    waveCtx.shadowColor = "#00f0ff";
    waveCtx.beginPath();
    
    const sliceWidth = waveCanvas.width * 1.0 / bufferLength;
    let x = 0;
    
    for (let i = 0; i < bufferLength; i++) {
        const v = dataArray[i] / 128.0;
        const y = v * waveCanvas.height / 2;
        
        if (i === 0) {
            waveCtx.moveTo(x, y);
        } else {
            waveCtx.lineTo(x, y);
        }
        
        x += sliceWidth;
    }
    
    waveCtx.lineTo(waveCanvas.width, waveCanvas.height / 2);
    waveCtx.stroke();
    waveCtx.shadowBlur = 0; // Reset
}

// --- Microphone Recording Code ---
async function toggleRecording() {
    if (isRecording) {
        stopRecording();
    } else {
        await startRecording();
    }
}

async function startRecording() {
    audioChunks = [];
    isRecording = true;
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Setup visualizer
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const source = audioContext.createMediaStreamSource(stream);
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;
        bufferLength = analyser.frequencyBinCount;
        dataArray = new Uint8Array(bufferLength);
        source.connect(analyser);
        
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = e => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };
        
        mediaRecorder.onstop = async () => {
            stream.getTracks().forEach(track => track.stop());
            if (audioContext) audioContext.close();
            
            const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
            uploadAudio(audioBlob);
        };
        
        mediaRecorder.start();
        
        recordBtn.className = "record-btn recording";
        statusDisplay.textContent = "Recording...";
        statusDisplay.style.color = "var(--accent-cyan)";
        
        startTime = Date.now();
        recordTimer = setInterval(updateTimer, 500);
        visualizeLiveWave();
        
    } catch (e) {
        console.error("Failed to access mic:", e);
        alert("Microphone access denied or not supported.");
        isRecording = false;
    }
}

function stopRecording() {
    isRecording = false;
    if (mediaRecorder && mediaRecorder.state !== "inactive") {
        mediaRecorder.stop();
    }
    
    clearInterval(recordTimer);
    cancelAnimationFrame(animationFrameId);
    
    recordBtn.className = "record-btn idle";
    statusDisplay.textContent = "Analyzing...";
    statusDisplay.style.color = "var(--accent-yellow)";
    
    drawWaveformBackground();
}

function updateTimer() {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const m = String(Math.floor(elapsed / 60)).padStart(2, "0");
    const s = String(elapsed % 60).padStart(2, "0");
    timerDisplay.textContent = `${m}:${s}`;
    
    // Automatically stop after 15 seconds to prevent memory overflow
    if (elapsed >= 15) {
        stopRecording();
    }
}

// --- Upload & Analysis API Call ---
async function uploadAudio(blob) {
    analysisSpinner.classList.remove("hidden");
    
    const exerciseType = document.getElementById("exercise-type").value;
    const enableFeedback = document.getElementById("enable-feedback").checked;
    const formData = new FormData();
    formData.append("file", blob, "record.wav");
    formData.append("exercise_type", exerciseType);
    formData.append("include_feedback", enableFeedback);
    
    try {
        const response = await fetch("/api/analyze", {
            method: "POST",
            body: formData
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Analysis failed.");
        }
        
        const data = await response.json();
        
        // Update metric display
        updateMetrics(data.summary);
        
        // Draw visualizer metrics
        drawVowelBackground(data.time_series.f1, data.time_series.f2);
        drawStabilityBackground(data.time_series.time_stamps, data.time_series.f0, data.time_series.back_pressure);
        
        // Add chat feedback
        addAgentBubble(data.feedback);
        
    } catch (e) {
        console.error(e);
        addAgentBubble(`### ⚠️ Error analyzing vocal segment\n\n${e.message}\n\nPlease check your .env configuration and try recording again.`);
    } finally {
        analysisSpinner.classList.add("hidden");
        statusDisplay.textContent = "Idle";
        statusDisplay.style.color = "var(--text-secondary)";
    }
}

// Handle file upload selection
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        uploadAudio(file);
    }
}

// --- Update Page Summary Cards ---
function updateMetrics(summary) {
    // Numeric metrics
    document.getElementById("val-backpressure").textContent = Math.round(summary.back_pressure_index);
    document.getElementById("val-jitter").textContent = summary.jitter_percentage.toFixed(2);
    document.getElementById("val-shimmer").textContent = summary.shimmer_percentage.toFixed(2);
    document.getElementById("val-dryness").textContent = Math.round(summary.dryness_friction_index);
    
    // Progress Bars
    document.getElementById("bar-backpressure").style.width = `${summary.back_pressure_index}%`;
    document.getElementById("bar-jitter").style.width = `${Math.min(100, summary.jitter_percentage * 50)}%`;
    document.getElementById("bar-shimmer").style.width = `${Math.min(100, summary.shimmer_percentage * 20)}%`;
    document.getElementById("bar-dryness").style.width = `${summary.dryness_friction_index}%`;
    
    // Alert colors
    toggleAlertState("card-jitter", summary.jitter_percentage > 1.0);
    toggleAlertState("card-shimmer", summary.shimmer_percentage > 3.0);
    toggleAlertState("card-backpressure", summary.back_pressure_index < 60);
    
    // Summary Hints updates
    document.getElementById("hint-backpressure").textContent = summary.back_pressure_index > 65 ? "Excellent cushion!" : "Increase lip support";
    document.getElementById("hint-jitter").textContent = summary.jitter_percentage < 1.0 ? "Stable mucosal wave" : "Caution: Sticky wave / Friction!";
    document.getElementById("hint-shimmer").textContent = summary.shimmer_percentage < 3.0 ? "Steady air support" : "Warning: Airflow fluctuation";
}

function toggleAlertState(cardId, isWarning) {
    const card = document.getElementById(cardId);
    if (isWarning) {
        card.classList.add("warning-state");
    } else {
        card.classList.remove("warning-state");
    }
}

// --- AI Chat Console Updates ---
function addAgentBubble(markdown) {
    const bubble = document.createElement("div");
    bubble.className = "chat-bubble agent";
    
    const content = document.createElement("div");
    content.className = "bubble-content";
    content.innerHTML = parseMarkdown(markdown);
    
    const time = document.createElement("span");
    time.className = "bubble-time";
    time.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    
    bubble.appendChild(content);
    bubble.appendChild(time);
    chatHistory.appendChild(bubble);
    
    // Auto-scroll
    chatHistory.scrollTop = chatHistory.scrollHeight;
}

// Mini Markdown compiler
function parseMarkdown(text) {
    if (!text) return "";
    let html = text;
    // Remove headers, format bold and code blocks
    html = html.replace(/### (.*)/g, '<h3>$1</h3>');
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`(.*?)`/g, '<code>$1</code>');
    
    // Lists parse
    const lines = html.split('\n');
    let inList = false;
    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        if (line.startsWith("- ") || line.startsWith("* ")) {
            if (!inList) {
                lines[i] = '<ul><li>' + line.substring(2) + '</li>';
                inList = true;
            } else {
                lines[i] = '<li>' + line.substring(2) + '</li>';
            }
        } else {
            if (inList) {
                lines[i-1] = lines[i-1] + '</ul>';
                inList = false;
            }
        }
    }
    if (inList) {
        lines[lines.length-1] = lines[lines.length-1] + '</ul>';
    }
    
    return lines.join('\n').replace(/\n/g, '<br>');
}

// --- Dynamic Visualizer Drawings ---

// Canvas 1: Vowel Space (F1 vs F2)
function drawVowelBackground(f1Series, f2Series) {
    const width = vowelCanvas.width;
    const height = vowelCanvas.height;
    
    vowelCtx.clearRect(0, 0, width, height);
    vowelCtx.fillStyle = "#0c101b";
    vowelCtx.fillRect(0, 0, width, height);
    
    // Grid Lines
    vowelCtx.strokeStyle = "rgba(255, 255, 255, 0.03)";
    vowelCtx.lineWidth = 1;
    for (let i = 1; i < 5; i++) {
        // Horizontal
        vowelCtx.beginPath();
        vowelCtx.moveTo(0, height * i / 5);
        vowelCtx.lineTo(width, height * i / 5);
        vowelCtx.stroke();
        
        // Vertical
        vowelCtx.beginPath();
        vowelCtx.moveTo(width * i / 5, 0);
        vowelCtx.lineTo(width * i / 5, height);
        vowelCtx.stroke();
    }
    
    // Standard Vowel Centers relative to canvas coordinate system
    // Y-axis represents F1 (typically 200 - 1000 Hz, low frequencies at the top for closed vowels)
    // X-axis represents F2 (typically 500 - 2500 Hz, high frequencies on the right for front vowels)
    const mapFormants = (f1, f2) => {
        // Normalize F2 to X (2500Hz -> 90% of width, 500Hz -> 10% of width)
        const x = width - (((f2 - 500) / 2000.0) * (width * 0.8) + (width * 0.1));
        // Normalize F1 to Y (200Hz -> 10% of height, 1000Hz -> 90% of height)
        const y = ((f1 - 200) / 800.0) * (height * 0.8) + (height * 0.1);
        return { x, y };
    }
    
    // Draw Vowel Reference Zones (F1, F2 centers)
    const vowelZones = [
        { label: "/i/", f1: 300, f2: 2200, color: "rgba(0, 240, 255, 0.08)", borderColor: "rgba(0, 240, 255, 0.2)" },
        { label: "/u/", f1: 300, f2: 950, color: "rgba(188, 52, 250, 0.08)", borderColor: "rgba(188, 52, 250, 0.2)" },
        { label: "/ɑ/", f1: 800, f2: 1100, color: "rgba(255, 214, 0, 0.08)", borderColor: "rgba(255, 214, 0, 0.2)" },
        { label: "Neutral Zone", f1: 500, f2: 1500, color: "rgba(0, 230, 118, 0.08)", borderColor: "rgba(0, 230, 118, 0.3)", radius: 45 }
    ];
    
    vowelZones.forEach(zone => {
        const coords = mapFormants(zone.f1, zone.f2);
        const r = zone.radius || 35;
        
        vowelCtx.fillStyle = zone.color;
        vowelCtx.strokeStyle = zone.borderColor;
        vowelCtx.lineWidth = 1.5;
        vowelCtx.beginPath();
        vowelCtx.arc(coords.x, coords.y, r, 0, 2 * Math.PI);
        vowelCtx.fill();
        vowelCtx.stroke();
    });
    
    // Plot user voiced trajectory
    if (f1Series && f1Series.length > 0) {
        const pts = [];
        for (let i = 0; i < f1Series.length; i++) {
            if (f1Series[i] > 0 && f2Series[i] > 0) {
                pts.push(mapFormants(f1Series[i], f2Series[i]));
            }
        }
        
        if (pts.length > 0) {
            // Draw path line
            vowelCtx.strokeStyle = "rgba(0, 240, 255, 0.5)";
            vowelCtx.lineWidth = 3;
            vowelCtx.beginPath();
            vowelCtx.moveTo(pts[0].x, pts[0].y);
            for (let i = 1; i < pts.length; i++) {
                vowelCtx.lineTo(pts[i].x, pts[i].y);
            }
            vowelCtx.stroke();
            
            // Draw glowing points
            pts.forEach((pt, index) => {
                vowelCtx.fillStyle = index === pts.length - 1 ? "#00f0ff" : "rgba(188, 52, 250, 0.4)";
                vowelCtx.beginPath();
                vowelCtx.arc(pt.x, pt.y, index === pts.length - 1 ? 7 : 3, 0, 2 * Math.PI);
                vowelCtx.fill();
                
                if (index === pts.length - 1) {
                    vowelCtx.strokeStyle = "#ffffff";
                    vowelCtx.lineWidth = 1.5;
                    vowelCtx.stroke();
                }
            });
        }
    }
}

// Canvas 2: Stability (Pitch and back pressure over time)
function drawStabilityBackground(stamps, f0Series, backpressureSeries) {
    const width = stabilityCanvas.width;
    const height = stabilityCanvas.height;
    
    stabilityCtx.clearRect(0, 0, width, height);
    stabilityCtx.fillStyle = "#0c101b";
    stabilityCtx.fillRect(0, 0, width, height);
    
    // Grid Lines
    stabilityCtx.strokeStyle = "rgba(255, 255, 255, 0.03)";
    stabilityCtx.lineWidth = 1;
    for (let i = 1; i < 5; i++) {
        stabilityCtx.beginPath();
        stabilityCtx.moveTo(0, height * i / 5);
        stabilityCtx.lineTo(width, height * i / 5);
        stabilityCtx.stroke();
    }
    
    if (f0Series && f0Series.length > 0) {
        // Find min/max values for scaling F0 (ignoring zeros/silent frames)
        const voicedF0 = f0Series.filter(f => f > 0);
        if (voicedF0.length === 0) return;
        
        const minF0 = Math.min(...voicedF0) * 0.9;
        const maxF0 = Math.max(...voicedF0) * 1.1;
        const f0Range = maxF0 - minF0;
        
        // Draw Back-Pressure fill under the graph
        stabilityCtx.fillStyle = "rgba(0, 240, 255, 0.05)";
        stabilityCtx.beginPath();
        stabilityCtx.moveTo(0, height);
        
        const points = [];
        for (let i = 0; i < f0Series.length; i++) {
            const x = (i / (f0Series.length - 1)) * width;
            
            // Map F0 to Y
            let y = height;
            if (f0Series[i] > 0) {
                y = height - (((f0Series[i] - minF0) / f0Range) * height * 0.7 + (height * 0.15));
            }
            points.push({ x, y, val: f0Series[i] });
            
            if (f0Series[i] > 0) {
                stabilityCtx.lineTo(x, y);
            }
        }
        stabilityCtx.lineTo(width, height);
        stabilityCtx.fill();
        
        // Draw actual Pitch stability path
        stabilityCtx.strokeStyle = "rgba(188, 52, 250, 0.85)";
        stabilityCtx.lineWidth = 3;
        stabilityCtx.beginPath();
        
        let started = false;
        points.forEach(pt => {
            if (pt.val > 0) {
                if (!started) {
                    stabilityCtx.moveTo(pt.x, pt.y);
                    started = true;
                } else {
                    stabilityCtx.lineTo(pt.x, pt.y);
                }
            }
        });
        stabilityCtx.stroke();
        
        // Draw Back-pressure overlay curve
        if (backpressureSeries && backpressureSeries.length > 0) {
            stabilityCtx.strokeStyle = "rgba(0, 240, 255, 0.75)";
            stabilityCtx.lineWidth = 2.5;
            stabilityCtx.beginPath();
            
            let bpStarted = false;
            for (let i = 0; i < backpressureSeries.length; i++) {
                const x = (i / (backpressureSeries.length - 1)) * width;
                const bp = backpressureSeries[i];
                if (f0Series[i] > 0) {
                    const y = height - (bp / 100.0) * height * 0.7 - (height * 0.15);
                    if (!bpStarted) {
                        stabilityCtx.moveTo(x, y);
                        bpStarted = true;
                    } else {
                        stabilityCtx.lineTo(x, y);
                    }
                }
            }
            stabilityCtx.stroke();
        }
    }
}

// --- History Logs Panel ---
async function loadHistory() {
    const listContainer = document.getElementById("history-list-container");
    if (!listContainer) return;
    
    try {
        const response = await fetch("/api/history");
        const sessions = await response.json();
        historySessions = sessions;
        
        if (sessions.length === 0) {
            listContainer.innerHTML = '<div class="loading-history"><span>No practice sessions logged yet.</span></div>';
            drawLongitudinalChart([], currentTrendMetric);
            return;
        }
        
        drawLongitudinalChart(historySessions, currentTrendMetric);
        
        listContainer.innerHTML = "";
        sessions.forEach(sess => {
            const item = document.createElement("div");
            item.className = "history-item";
            item.onclick = () => selectHistorySession(sess.session_id, item);
            
            const dateStr = new Date(sess.timestamp).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
            
            item.innerHTML = `
                <div class="history-item-header">
                    <span class="history-item-date">${dateStr}</span>
                    <span class="history-item-score">${Math.round(sess.summary.dryness_friction_index)} Index</span>
                </div>
                <div class="history-item-metrics">
                    <span>Back-P: <strong>${Math.round(sess.summary.back_pressure_index)}</strong></span>
                    <span>Jitter: <strong>${sess.summary.jitter_percentage.toFixed(2)}%</strong></span>
                    <span>Vowel: <strong>${sess.summary.vowel_space}</strong></span>
                </div>
            `;
            listContainer.appendChild(item);
        });
        
    } catch (e) {
        console.error(e);
        listContainer.innerHTML = '<div class="loading-history"><span>Failed to load history list.</span></div>';
    }
}

async function selectHistorySession(sessionId, element) {
    // Toggle active class on list
    document.querySelectorAll(".history-item").forEach(item => item.classList.remove("active"));
    element.classList.add("active");
    
    const detailPanel = document.getElementById("history-detail-panel");
    detailPanel.innerHTML = `
        <div class="loading-history">
            <div class="spinner-small"></div>
            <span>Fetching session details...</span>
        </div>
    `;
    
    try {
        const response = await fetch(`/api/history/${sessionId}`);
        const data = await response.json();
        
        const dateStr = new Date(data.timestamp).toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
        
        detailPanel.innerHTML = `
            <div class="history-detail-header">
                <h2>Practice Session Dashboard</h2>
                <div class="history-detail-date"><i class="fa-solid fa-calendar-days"></i> ${dateStr} | ID: ${data.session_id}</div>
            </div>
            
            <div class="history-detail-grid">
                <div class="history-detail-metric">
                    <h4>Dryness & Friction Index</h4>
                    <div style="color: var(--accent-green)">${Math.round(data.summary.dryness_friction_index)}/100</div>
                </div>
                <div class="history-detail-metric">
                    <h4>Acoustic Back-Pressure</h4>
                    <div style="color: var(--accent-cyan)">${Math.round(data.summary.back_pressure_index)}/100</div>
                </div>
                <div class="history-detail-metric">
                    <h4>Dominant Vowel</h4>
                    <div style="color: var(--accent-purple)">${data.summary.vowel_space}</div>
                </div>
                <div class="history-detail-metric">
                    <h4>Average Jitter</h4>
                    <div style="color: ${data.summary.jitter_percentage > 1.0 ? 'var(--accent-red)' : 'var(--text-primary)'}">
                        ${data.summary.jitter_percentage.toFixed(3)}%
                    </div>
                </div>
            </div>
            
            <div class="history-detail-feedback">
                <h3><i class="fa-solid fa-brain-circuit"></i> Antigravity Agent Pedagogical Evaluation</h3>
                <div class="history-detail-feedback-content">
                    ${parseMarkdown(data.feedback)}
                </div>
            </div>
        `;
        
    } catch (e) {
        console.error(e);
        detailPanel.innerHTML = `
            <div class="detail-placeholder" style="color: var(--accent-red)">
                <i class="fa-solid fa-triangle-exclamation"></i>
                <p>Failed to load session details: ${e.message}</p>
            </div>
        `;
    }
}

// --- Google Sheets Settings Integration ---

async function loadSettings() {
    try {
        const response = await fetch("/api/settings");
        const data = await response.json();
        
        document.getElementById("sheets-url-input").value = data.webapp_url || "";
        document.getElementById("sheets-token-input").value = data.secret_token || "voxgrip_secret_12345";
    } catch (e) {
        console.error("Failed to load settings:", e);
    }
}

async function saveSettings() {
    const webappUrl = document.getElementById("sheets-url-input").value.trim();
    const secretToken = document.getElementById("sheets-token-input").value.trim();
    const statusMsg = document.getElementById("settings-save-status");
    
    statusMsg.textContent = "Saving...";
    statusMsg.style.color = "var(--text-secondary)";
    
    try {
        const response = await fetch("/api/settings", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                webapp_url: webappUrl,
                secret_token: secretToken
            })
        });
        
        if (!response.ok) {
            throw new Error("Failed to save settings on server.");
        }
        
        statusMsg.textContent = "✅ Settings saved successfully!";
        statusMsg.style.color = "var(--accent-green)";
        
        // Clear message after 3 seconds
        setTimeout(() => {
            statusMsg.textContent = "";
        }, 3000);
    } catch (e) {
        statusMsg.textContent = `❌ Error: ${e.message}`;
        statusMsg.style.color = "var(--accent-red)";
    }
}

function copyCode() {
    const codeText = document.getElementById("apps-script-code").innerText;
    const btn = document.querySelector(".copy-code-btn");
    
    navigator.clipboard.writeText(codeText).then(() => {
        const originalText = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
        btn.style.color = "var(--accent-green)";
        btn.style.borderColor = "var(--accent-green)";
        
        setTimeout(() => {
            btn.innerHTML = originalText;
            btn.style.color = "var(--text-secondary)";
            btn.style.borderColor = "var(--border-glass)";
        }, 2000);
    }).catch(e => {
        console.error("Clipboard copy failed:", e);
        alert("Failed to copy code to clipboard. Please copy manually.");
    });
}

// --- Longitudinal Progress Chart Rendering ---
function switchTrendMetric(metric) {
    currentTrendMetric = metric;
    
    // Toggle active tab buttons
    document.querySelectorAll(".trend-tab-btn").forEach(btn => btn.classList.remove("active"));
    document.getElementById(`trend-tab-${metric}`).classList.add("active");
    
    drawLongitudinalChart(historySessions, metric);
}

function drawLongitudinalChart(sessions, metric) {
    if (!trendCanvas || !trendCtx) return;
    
    // Clear canvas
    trendCtx.clearRect(0, 0, trendCanvas.width, trendCanvas.height);
    
    // Draw dark background grid lines
    trendCtx.lineWidth = 1;
    trendCtx.strokeStyle = "rgba(255, 255, 255, 0.05)";
    
    const marginX = 50;
    const marginY = 30;
    const plotWidth = trendCanvas.width - marginX - 20;
    const plotHeight = trendCanvas.height - marginY - 20;
    
    // Draw 4 horizontal grid lines
    for (let i = 0; i <= 4; i++) {
        const y = marginY + (plotHeight * i) / 4;
        trendCtx.beginPath();
        trendCtx.moveTo(marginX, y);
        trendCtx.lineTo(trendCanvas.width - 20, y);
        trendCtx.stroke();
        
        // Draw grid labels based on metric
        let label = "";
        if (metric === 'dryness' || metric === 'backpressure') {
            label = Math.round(100 - (i * 100 / 4));
        } else if (metric === 'perturbations') {
            label = (10 - (i * 10 / 4)).toFixed(1) + "%";
        }
        
        trendCtx.fillStyle = "var(--text-secondary)";
        trendCtx.font = "10px Inter";
        trendCtx.textAlign = "right";
        trendCtx.fillText(label, marginX - 10, y + 4);
    }
    
    if (!sessions || sessions.length === 0) {
        trendCtx.fillStyle = "var(--text-secondary)";
        trendCtx.font = "13px Inter";
        trendCtx.textAlign = "center";
        trendCtx.fillText("No history data to display trend.", trendCanvas.width / 2, trendCanvas.height / 2);
        return;
    }
    
    // Sort sessions chronological (oldest to newest)
    const sorted = [...sessions].reverse();
    
    // Calculate points coordinates
    const points = [];
    const count = sorted.length;
    
    sorted.forEach((sess, idx) => {
        const x = marginX + (count > 1 ? (plotWidth * idx) / (count - 1) : plotWidth / 2);
        
        let val1 = 0, val2 = 0;
        if (metric === 'dryness') {
            val1 = sess.summary.dryness_friction_index;
        } else if (metric === 'backpressure') {
            val1 = sess.summary.back_pressure_index;
        } else if (metric === 'perturbations') {
            val1 = sess.summary.jitter_percentage;
            val2 = sess.summary.shimmer_percentage;
        }
        
        // Map value to Y coordinate
        let y1 = 0, y2 = 0;
        if (metric === 'dryness' || metric === 'backpressure') {
            y1 = marginY + plotHeight * (1 - val1 / 100);
        } else {
            y1 = marginY + plotHeight * (1 - Math.min(10, val1) / 10);
            y2 = marginY + plotHeight * (1 - Math.min(10, val2) / 10);
        }
        
        points.push({ x, y1, y2, val1, val2, date: new Date(sess.timestamp) });
    });
    
    // Draw threshold boundary lines
    trendCtx.lineWidth = 1;
    trendCtx.setLineDash([4, 4]);
    if (metric === 'dryness') {
        const ySafe = marginY + plotHeight * (1 - 60 / 100);
        trendCtx.strokeStyle = "rgba(46, 204, 113, 0.25)";
        trendCtx.beginPath();
        trendCtx.moveTo(marginX, ySafe);
        trendCtx.lineTo(trendCanvas.width - 20, ySafe);
        trendCtx.stroke();
    } else if (metric === 'backpressure') {
        const ySafe = marginY + plotHeight * (1 - 65 / 100);
        trendCtx.strokeStyle = "rgba(46, 204, 113, 0.25)";
        trendCtx.beginPath();
        trendCtx.moveTo(marginX, ySafe);
        trendCtx.lineTo(trendCanvas.width - 20, ySafe);
        trendCtx.stroke();
    } else if (metric === 'perturbations') {
        const yJit = marginY + plotHeight * (1 - 1.0 / 10);
        trendCtx.strokeStyle = "rgba(0, 240, 255, 0.25)";
        trendCtx.beginPath();
        trendCtx.moveTo(marginX, yJit);
        trendCtx.lineTo(trendCanvas.width - 20, yJit);
        trendCtx.stroke();
        
        const yShim = marginY + plotHeight * (1 - 3.0 / 10);
        trendCtx.strokeStyle = "rgba(168, 85, 247, 0.25)";
        trendCtx.beginPath();
        trendCtx.moveTo(marginX, yShim);
        trendCtx.lineTo(trendCanvas.width - 20, yShim);
        trendCtx.stroke();
    }
    trendCtx.setLineDash([]);
    
    // Draw lines connecting points
    if (metric === 'perturbations') {
        drawLine(points, 'y1', 'var(--accent-cyan)', 'rgba(0, 240, 255, 0.05)');
        drawLine(points, 'y2', 'var(--accent-purple)', 'rgba(168, 85, 247, 0.05)');
    } else {
        const color = metric === 'dryness' ? 'var(--accent-green)' : 'var(--accent-cyan)';
        const gradColor = metric === 'dryness' ? 'rgba(46, 204, 113, 0.05)' : 'rgba(0, 240, 255, 0.05)';
        drawLine(points, 'y1', color, gradColor);
    }
    
    // Draw points and hover indicators
    points.forEach(pt => {
        const color1 = metric === 'perturbations' ? 'var(--accent-cyan)' : (metric === 'dryness' ? 'var(--accent-green)' : 'var(--accent-cyan)');
        drawDot(pt.x, pt.y1, color1, pt.val1, metric === 'perturbations' ? 'Jit' : '');
        if (metric === 'perturbations') {
            drawDot(pt.x, pt.y2, 'var(--accent-purple)', pt.val2, 'Shim');
        }
        
        // Draw X-axis date labels
        trendCtx.fillStyle = "var(--text-secondary)";
        trendCtx.font = "9px Inter";
        trendCtx.textAlign = "center";
        const dateStr = pt.date.toLocaleDateString([], { month: 'short', day: 'numeric' });
        trendCtx.fillText(dateStr, pt.x, trendCanvas.height - 5);
    });
    
    function drawLine(pts, key, color, fillGrad) {
        trendCtx.lineWidth = 3;
        trendCtx.strokeStyle = color;
        trendCtx.beginPath();
        
        pts.forEach((pt, idx) => {
            if (idx === 0) {
                trendCtx.moveTo(pt.x, pt[key]);
            } else {
                const prev = pts[idx - 1];
                const cp1x = prev.x + (pt.x - prev.x) / 2;
                const cp1y = prev[key];
                const cp2x = prev.x + (pt.x - prev.x) / 2;
                const cp2y = pt[key];
                trendCtx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, pt.x, pt[key]);
            }
        });
        trendCtx.stroke();
        
        // Fill area under line
        if (pts.length > 1) {
            trendCtx.fillStyle = fillGrad;
            trendCtx.beginPath();
            trendCtx.moveTo(pts[0].x, trendCanvas.height - marginY);
            pts.forEach((pt, idx) => {
                if (idx === 0) {
                    trendCtx.lineTo(pt.x, pt[key]);
                } else {
                    const prev = pts[idx - 1];
                    const cp1x = prev.x + (pt.x - prev.x) / 2;
                    const cp1y = prev[key];
                    const cp2x = prev.x + (pt.x - prev.x) / 2;
                    const cp2y = pt[key];
                    trendCtx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, pt.x, pt[key]);
                }
            });
            trendCtx.lineTo(pts[pts.length - 1].x, trendCanvas.height - marginY);
            trendCtx.closePath();
            trendCtx.fill();
        }
    }
    
    function drawDot(x, y, color, value, labelPrefix) {
        trendCtx.fillStyle = color;
        trendCtx.beginPath();
        trendCtx.arc(x, y, 4, 0, 2 * Math.PI);
        trendCtx.fill();
        
        trendCtx.strokeStyle = "rgba(255,255,255,0.8)";
        trendCtx.lineWidth = 1;
        trendCtx.stroke();
        
        // Write value above dot
        trendCtx.fillStyle = "var(--text-primary)";
        trendCtx.font = "9px Inter";
        trendCtx.textAlign = "center";
        const label = labelPrefix ? `${labelPrefix}: ${value.toFixed(1)}%` : value.toFixed(1);
        trendCtx.fillText(label, x, y - 8);
    }
}

// --- Instrumental Spillover Profile Handling ---
async function saveProfile() {
    const instWoodwinds = document.getElementById("inst-woodwinds").checked;
    const instViolin = document.getElementById("inst-violin").checked;
    const instGuitar = document.getElementById("inst-guitar").checked;
    const statusMsg = document.getElementById("profile-save-status");
    
    statusMsg.textContent = "Saving profile...";
    statusMsg.style.color = "var(--text-secondary)";
    
    const instruments = [];
    if (instWoodwinds) instruments.push("woodwinds");
    if (instViolin) instruments.push("violin");
    if (instGuitar) instruments.push("guitar");
    
    try {
        const response = await fetch("/api/profile", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                instruments: instruments
            })
        });
        
        if (!response.ok) {
            throw new Error("Failed to save profile on server.");
        }
        
        statusMsg.textContent = "✅ Profile saved successfully!";
        statusMsg.style.color = "var(--accent-green)";
        
        setTimeout(() => {
            statusMsg.textContent = "";
        }, 3000);
    } catch (e) {
        statusMsg.textContent = `❌ Error: ${e.message}`;
        statusMsg.style.color = "var(--accent-red)";
    }
}

async function loadProfile() {
    try {
        const response = await fetch("/api/profile");
        const data = await response.json();
        
        const instruments = data.instruments || [];
        document.getElementById("inst-woodwinds").checked = instruments.includes("woodwinds");
        document.getElementById("inst-violin").checked = instruments.includes("violin");
        document.getElementById("inst-guitar").checked = instruments.includes("guitar");
    } catch (e) {
        console.error("Failed to load profile:", e);
    }
}

