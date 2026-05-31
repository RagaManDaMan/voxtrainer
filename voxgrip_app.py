import os
import json
import datetime
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import uvicorn
import urllib.request

# Import our custom logic
from vocal_dsp import analyze_vocal_dsp
from voxgrip_agent import run_voxgrip_agent

# Initialize FastAPI
app = FastAPI(title="VoxGrip API", description="Vocal Training & Aerodynamic Monitor Backend")

# Setup directory paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static" / "voxgrip"
SESSIONS_DIR = BASE_DIR / "voxgrip_sessions"
AUDIO_DIR = SESSIONS_DIR / "audio"
LOGS_DIR = SESSIONS_DIR / "logs"

# Ensure directories exist
STATIC_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Helper to load .env variables manually to avoid extra dependencies
def load_dotenv():
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    parts = line.split("=", 1)
                    k = parts[0].strip()
                    v = parts[1].strip().strip('"').strip("'")
                    os.environ[k] = v

load_dotenv()

class SettingsRequest(BaseModel):
    webapp_url: str
    secret_token: str

class ProfileRequest(BaseModel):
    instruments: list[str]

def post_to_google_sheets(session_data: dict, webapp_url: str, secret_token: str):
    """Posts session logs to the Google Sheets Apps Script Web App in the background."""
    if not webapp_url:
        return
    try:
        summary = session_data.get("summary", {})
        payload = {
            "token": secret_token or "voxgrip_secret_12345",
            "timestamp": session_data.get("timestamp", datetime.datetime.now().isoformat()),
            "session_id": session_data.get("session_id", ""),
            "total_duration_sec": summary.get("total_duration_sec", 0.0),
            "voiced_duration_sec": summary.get("voiced_duration_sec", 0.0),
            "f0_hz": summary.get("f0_hz", 0.0),
            "jitter_percentage": summary.get("jitter_percentage", 0.0),
            "shimmer_percentage": summary.get("shimmer_percentage", 0.0),
            "f1_formant_hz": summary.get("f1_formant_hz", 0.0),
            "f2_formant_hz": summary.get("f2_formant_hz", 0.0),
            "vowel_space": summary.get("vowel_space", ""),
            "back_pressure_index": summary.get("back_pressure_index", 0.0),
            "dryness_friction_index": summary.get("dryness_friction_index", 0.0),
            "remedials": session_data.get("feedback", "")
        }
        
        data_bytes = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            webapp_url,
            data=data_bytes,
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_body = response.read().decode('utf-8')
            print(f"✅ Google Sheets Logging Status: {res_body}")
    except Exception as e:
        print(f"❌ Error logging to Google Sheets Web App: {e}")

def get_api_key():
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")

@app.get("/api/status")
def get_status():
    """Checks if the system is ready (always true now that we have local analysis)."""
    return {
        "api_key_configured": True,
        "env_path": str(BASE_DIR / ".env")
    }

@app.post("/api/analyze")
async def analyze_audio(
    background_tasks: BackgroundTasks, 
    file: UploadFile = File(...),
    exercise_type: str = Form(None),
    include_feedback: str = Form("true")
):
    """
    Receives recorded WAV audio from client, saves it locally,
    performs DSP analysis, triggers the Local Pedagogue Agent,
    and logs the session history.
    """
    api_key = get_api_key()
    # Note: api_key is now optional as we run offline rule-based analysis locally.

    # 1. Save uploaded file with timestamped name
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"session_{timestamp}.wav"
    audio_path = AUDIO_DIR / filename
    
    try:
        with open(audio_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save audio: {str(e)}")

    # 2. Run DSP pipeline
    dsp_results = analyze_vocal_dsp(str(audio_path))
    if "error" in dsp_results:
        # Clean up audio file on failure
        if audio_path.exists():
            audio_path.unlink()
        raise HTTPException(status_code=422, detail=dsp_results["error"])

    # 3. Run Local / Antigravity Agent to generate technical feedback
    if include_feedback == "true" or include_feedback is True:
        load_dotenv()
        instr_str = os.environ.get("INSTRUMENTS", "")
        instruments = [i.strip() for i in instr_str.split(",") if i.strip()]
        feedback = await run_voxgrip_agent(
            str(audio_path), 
            api_key=api_key, 
            exercise_type=exercise_type,
            instruments=instruments
        )
    else:
        feedback = (
            "### ℹ️ Local Expert Feedback Disabled\n\n"
            "You have toggled off pedagogical feedback. Use the visualizers and metrics gauges "
            "to evaluate your session and determine your own remedies."
        )

    # 4. Save Session Log (JSON) for persistent history
    session_id = f"session_{timestamp}"
    session_log = {
        "session_id": session_id,
        "timestamp": datetime.datetime.now().isoformat(),
        "audio_file": str(audio_path.relative_to(BASE_DIR)),
        "summary": dsp_results["summary"],
        "time_series": dsp_results["time_series"],
        "feedback": feedback
    }
    
    log_path = LOGS_DIR / f"{session_id}.json"
    try:
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(session_log, f, indent=2)
    except Exception as e:
        print(f"Warning: Failed to save session log JSON: {e}")

    # 5. Save Session Summary (Markdown) for easy filesystem reading
    md_path = LOGS_DIR / f"{session_id}.md"
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# VoxGrip Practice Session Log: {session_id}\n\n")
            f.write(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Duration:** {dsp_results['summary']['total_duration_sec']:.2f} seconds\n")
            f.write(f"**Phonation Duration:** {dsp_results['summary']['voiced_duration_sec']:.2f} seconds\n\n")
            
            f.write("## 📊 Summary Metrics\n\n")
            f.write(f"- **Avg Fundamental Frequency (F0):** {dsp_results['summary']['f0_hz']:.1f} Hz\n")
            f.write(f"- **Avg Jitter (Mucosal Friction):** {dsp_results['summary']['jitter_percentage']:.2f}%\n")
            f.write(f"- **Avg Shimmer (Amplitude Perturbation):** {dsp_results['summary']['shimmer_percentage']:.2f}%\n")
            f.write(f"- **Formants (F1 / F2):** {dsp_results['summary']['f1_formant_hz']:.1f} Hz / {dsp_results['summary']['f2_formant_hz']:.1f} Hz\n")
            f.write(f"- **Vowel Space:** {dsp_results['summary']['vowel_space']}\n")
            f.write(f"- **Acoustic Back-Pressure:** {dsp_results['summary']['back_pressure_index']:.1f}/100\n")
            f.write(f"- **Dryness / Friction Index:** {dsp_results['summary']['dryness_friction_index']:.1f}/100\n\n")
            
            f.write("## 🤖 Antigravity Agent Report\n\n")
            f.write(feedback)
            f.write("\n")
    except Exception as e:
        print(f"Warning: Failed to save session log Markdown: {e}")

    # 6. Post log to Google Sheets in the background if configured
    sheets_url = os.environ.get("SHEETS_WEBAPP_URL")
    sheets_token = os.environ.get("SHEETS_SECRET_TOKEN")
    if sheets_url:
        background_tasks.add_task(post_to_google_sheets, session_log, sheets_url, sheets_token)

    # Return results (omit full time series if not requested to save bandwidth, but here we send it for graphing)
    return session_log

@app.get("/api/history")
def get_history():
    """Returns a list of all historical practice sessions summary metadata."""
    sessions = []
    for log_file in LOGS_DIR.glob("*.json"):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                sessions.append({
                    "session_id": data["session_id"],
                    "timestamp": data["timestamp"],
                    "summary": data["summary"]
                })
        except Exception as e:
            print(f"Warning: Failed to read log file {log_file}: {e}")
            
    # Sort sessions by timestamp descending
    sessions.sort(key=lambda s: s["timestamp"], reverse=True)
    return sessions

@app.get("/api/history/{session_id}")
def get_session_details(session_id: str):
    """Retrieves full details of a specific session."""
    log_path = LOGS_DIR / f"{session_id}.json"
    if not log_path.exists():
        raise HTTPException(status_code=404, detail="Session not found.")
        
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read session: {str(e)}")

@app.get("/api/settings")
def get_settings():
    """Retrieves current Google Sheets integration settings."""
    load_dotenv()
    url = os.environ.get("SHEETS_WEBAPP_URL", "")
    token = os.environ.get("SHEETS_SECRET_TOKEN", "voxgrip_secret_12345")
    return {
        "webapp_url": url,
        "secret_token": token
    }

@app.post("/api/settings")
def update_settings(req: SettingsRequest):
    """Updates Sheets integration settings in the .env file."""
    env_path = BASE_DIR / ".env"
    env_data = {}
    
    # Read existing key-values to preserve GEMINI_API_KEY
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, v = stripped.split("=", 1)
                    env_data[k.strip()] = v.strip().strip('"').strip("'")
                    
    # Update settings
    env_data["SHEETS_WEBAPP_URL"] = req.webapp_url
    env_data["SHEETS_SECRET_TOKEN"] = req.secret_token
    
    # Write back to .env
    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in env_data.items():
            f.write(f"{k}={v}\n")
            
    # Reload in current process
    os.environ["SHEETS_WEBAPP_URL"] = req.webapp_url
    os.environ["SHEETS_SECRET_TOKEN"] = req.secret_token
    
    return {"status": "success", "message": "Google Sheets settings saved successfully."}

@app.get("/api/profile")
def get_profile():
    """Retrieves current user instrumental spillover checklist profile."""
    load_dotenv()
    instr_str = os.environ.get("INSTRUMENTS", "")
    instruments = [i.strip() for i in instr_str.split(",") if i.strip()]
    return {
        "instruments": instruments
    }

@app.post("/api/profile")
def update_profile(req: ProfileRequest):
    """Updates the user instrumental profile in the .env file."""
    env_path = BASE_DIR / ".env"
    env_data = {}
    
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and "=" in stripped:
                    k, v = stripped.split("=", 1)
                    env_data[k.strip()] = v.strip().strip('"').strip("'")
                    
    instruments_str = ",".join(req.instruments)
    env_data["INSTRUMENTS"] = instruments_str
    
    with open(env_path, "w", encoding="utf-8") as f:
        for k, v in env_data.items():
            f.write(f"{k}={v}\n")
            
    os.environ["INSTRUMENTS"] = instruments_str
    return {"status": "success", "message": "Instrumental profile saved successfully."}

# Mount static files (Frontend app)
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    print("🚀 VoxGrip Backend running on http://127.0.0.1:8003")
    uvicorn.run(app, host="127.0.0.1", port=8003)
