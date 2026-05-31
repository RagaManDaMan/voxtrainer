# VoxGrip (VoxTrainer): Offline Advanced Voice Trainer

VoxGrip (VoxTrainer) is a standalone offline vocal diagnostics and pedagogical training application. It features expert signal processing (DSP) for pitch, pertubations, and vibrato tracking, integrated feedback templates tailored to instrumentalists (woodwind, violin, and guitar), and a premium glassmorphic dashboard with longitudinal progress visualization.

## Key Features

1. **Vocal Diagnostics & DSP Engine**:
   - Offline pitch extraction without external API calls.
   - **Vibrato Tracking**: Zero-crossing analysis for Vibrato Rate (Hz) and log-pitch variance for Vibrato Depth (semitones). Detects wobbles and tremolos.
   - **Perturbation & Quality Metrics**: Dryness Index (spectral roll-off), Jitter/Shimmer, and Acoustic Back-pressure.

2. **Instrumental Spillover Profiles**:
   - Factors in habits of woodwind, violin, and guitar players.
   - Compares vocal breath support to a violin bow-stroke and warns against guitar-playing fretboard postures that collapse the cervical spine.

3. **Practice Exercises**:
   - Lip/Tongue Trill Sustainer
   - Vowel Migration (high-register vowel vowel tracking)
   - Voiced Fricative Support (/v/ or /z/)
   - Vocal Fry Onset (stabilization of glottal flow)
   - Messa di Voce (crescendo and decrescendo dynamics)
   - Free-scaling & Phonation Stability

4. **Longitudinal Progress Canvas**:
   - Local canvas-rendered history trend-line charts visualizing improvement over sessions.

5. **Google Sheets Sync**:
   - Log practice sessions automatically via Google Apps Script web app endpoint.

## Getting Started

### Prerequisites

Install required local python libraries:
```bash
pip install numpy scipy fastapi uvicorn pydantic python-multipart python-dotenv
```

### Configuration

Create a local `.env` file from the template:
```bash
cp .env.template .env
```
Ensure your `GEMINI_API_KEY` (if using optional remote models) and `SHEETS_WEBAPP_URL` are set.

### Running the App

Start the local server:
```bash
python3 voxgrip_app.py
```
Open your browser and navigate to `http://localhost:8003` to start training.
