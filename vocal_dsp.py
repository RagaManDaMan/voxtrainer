import os
import warnings
# Silence librosa and scipy audio-read/deprecation warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

import numpy as np
import librosa
import scipy.signal

def classify_vowel(f1, f2):
    """Classifies vowel based on distance to standard formant centers (F1, F2)."""
    if f1 <= 0 or f2 <= 0:
        return "Silence"
        
    vowel_centers = {
        "/i/": (300, 2200),
        "/ɪ/": (400, 1950),
        "/u/": (300, 950),
        "/ʊ/": (450, 1150),
        "/ɑ/": (800, 1100),
        "/ɔ/": (600, 900),
        "/æ/": (750, 1750),
        "/ɛ/": (550, 1800)
    }
    
    min_dist = float('inf')
    best_vowel = "Unknown"
    for vowel, center in vowel_centers.items():
        # Normalize distances since F2 range is wider than F1
        dist = np.sqrt(((f1 - center[0]) / 300.0)**2 + ((f2 - center[1]) / 1000.0)**2)
        if dist < min_dist:
            min_dist = dist
            best_vowel = vowel
            
    return best_vowel

def analyze_vocal_dsp(file_path: str) -> dict:
    """
    Extracts pitch (F0), Jitter, Shimmer, F1/F2 formants, vowel space,
    and Acoustic Back-Pressure from an audio file.
    """
    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
        
    try:
        # Load audio (downsample to 16kHz for speech/formant analysis efficiency)
        y, sr = librosa.load(file_path, sr=16000)
        
        # Guard against empty/very short audio
        if len(y) < 512:
            return {"error": "Audio signal too short."}
            
        # Analysis parameters
        frame_length = int(0.05 * sr)  # 50ms frames
        hop_length = int(0.02 * sr)    # 20ms hops (50 fps)
        
        # 1. Pitch Tracking (F0) using YIN
        # Human singing pitch fmin=80 (E2), fmax=1000 (C6)
        f0 = librosa.yin(y, fmin=80, fmax=1000, sr=sr, frame_length=frame_length, hop_length=hop_length)
        
        # Apply threshold on RMS energy to ignore silent frames (voicing threshold)
        rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        
        # Consider a frame silent/unvoiced if RMS is lower than -40dB relative to max
        voicing_thresh = -40.0
        f0[rms_db < voicing_thresh] = 0.0
        
        # 2. Formant Tracking (LPC roots)
        # Pre-emphasis filter to boost higher frequencies for formants
        y_pre = np.append(y[0], y[1:] - 0.97 * y[:-1])
        frames = librosa.util.frame(y_pre, frame_length=frame_length, hop_length=hop_length)
        
        lpc_order = int(2 + sr / 1000) # For 16kHz, order is 18
        
        f1_series = []
        f2_series = []
        vowels_series = []
        
        for i in range(frames.shape[1]):
            frame_f0 = f0[i] if i < len(f0) else 0.0
            if frame_f0 > 0:
                frame_data = frames[:, i]
                windowed = frame_data * np.hamming(len(frame_data))
                try:
                    # Calculate Linear Predictive Coding coefficients
                    a = librosa.lpc(windowed, order=lpc_order)
                    roots = np.roots(a)
                    # Keep roots in the positive half of the complex plane
                    roots = [r for r in roots if np.imag(r) > 0]
                    
                    # Convert roots to frequencies (angles)
                    freqs = []
                    for r in roots:
                        freq = np.abs(np.arctan2(np.imag(r), np.real(r))) * sr / (2 * np.pi)
                        freqs.append(freq)
                    
                    # Filter resonances in typical vowel formant ranges (250Hz to 3500Hz)
                    valid_freqs = sorted([f for f in freqs if 250 < f < 3500])
                    
                    f1 = valid_freqs[0] if len(valid_freqs) > 0 else 0.0
                    f2 = valid_freqs[1] if len(valid_freqs) > 1 else 0.0
                    
                    f1_series.append(float(f1))
                    f2_series.append(float(f2))
                    vowels_series.append(classify_vowel(f1, f2))
                except Exception:
                    f1_series.append(0.0)
                    f2_series.append(0.0)
                    vowels_series.append("Silence")
            else:
                f1_series.append(0.0)
                f2_series.append(0.0)
                vowels_series.append("Silence")
                
        # Trim arrays to match sizes
        num_frames = min(len(f0), frames.shape[1])
        f0 = f0[:num_frames]
        f1_series = f1_series[:num_frames]
        f2_series = f2_series[:num_frames]
        vowels_series = vowels_series[:num_frames]
        rms_db = rms_db[:num_frames]
        
        # 3. Local Jitter and Shimmer Calculation (Frame-level)
        jitter_series = [0.0]
        shimmer_series = [0.0]
        
        # Get frame amplitudes (max absolute values)
        frames_orig = librosa.util.frame(y, frame_length=frame_length, hop_length=hop_length)
        amps = np.max(np.abs(frames_orig), axis=0)[:num_frames]
        
        for i in range(1, num_frames):
            prev_f0 = f0[i-1]
            curr_f0 = f0[i]
            
            # Jitter (frequency perturbation)
            if prev_f0 > 0 and curr_f0 > 0:
                diff_f = abs(curr_f0 - prev_f0)
                avg_f = (curr_f0 + prev_f0) / 2.0
                j_val = (diff_f / avg_f) * 100.0
                jitter_series.append(float(j_val))
            else:
                jitter_series.append(0.0)
                
            # Shimmer (amplitude perturbation)
            if prev_f0 > 0 and curr_f0 > 0 and amps[i-1] > 0 and amps[i] > 0:
                diff_a = abs(amps[i] - amps[i-1])
                avg_a = (amps[i] + amps[i-1]) / 2.0
                s_val = (diff_a / avg_a) * 100.0
                shimmer_series.append(float(s_val))
            else:
                shimmer_series.append(0.0)
                
        # 4. Calculate Acoustic Back-Pressure Index
        # A heuristic based on:
        # - Low Jitter (stable mucosal wave)
        # - Low Shimmer
        # - Low spectral flatness (meaning high harmonic peaks rather than white noise/breathiness)
        flatness = librosa.feature.spectral_flatness(y=y, n_fft=frame_length, hop_length=hop_length)[0][:num_frames]
        
        back_pressure_series = []
        for i in range(num_frames):
            if f0[i] > 0:
                # Start from 100
                bp_score = 100.0
                # Jitter penalty (jitter > 1.0% is unstable)
                bp_score -= min(30.0, jitter_series[i] * 15.0)
                # Shimmer penalty (shimmer > 3.0% is unstable)
                bp_score -= min(25.0, shimmer_series[i] * 5.0)
                # Flatness penalty (flatness is typically 0 to 1, higher flatness means noisier/less occluded)
                bp_score -= min(45.0, flatness[i] * 200.0)
                
                back_pressure_series.append(max(0.0, float(bp_score)))
            else:
                back_pressure_series.append(0.0)
                
        # 5. Aggregate Summary Metrics (voiced portions only)
        voiced_indices = [i for i, val in enumerate(f0) if val > 0]
        
        if voiced_indices:
            avg_f0 = float(np.mean([f0[i] for i in voiced_indices]))
            avg_jitter = float(np.mean([jitter_series[i] for i in voiced_indices]))
            avg_shimmer = float(np.mean([shimmer_series[i] for i in voiced_indices]))
            avg_f1 = float(np.mean([f1_series[i] for i in voiced_indices if f1_series[i] > 0]))
            avg_f2 = float(np.mean([f2_series[i] for i in voiced_indices if f2_series[i] > 0]))
            avg_back_pressure = float(np.mean([back_pressure_series[i] for i in voiced_indices]))
            
            # Find dominant vowel
            vowel_counts = {}
            for i in voiced_indices:
                vw = vowels_series[i]
                if vw != "Silence" and vw != "Unknown":
                    vowel_counts[vw] = vowel_counts.get(vw, 0) + 1
            dominant_vowel = max(vowel_counts, key=vowel_counts.get) if vowel_counts else "Unknown"
        else:
            avg_f0 = 0.0
            avg_jitter = 0.0
            avg_shimmer = 0.0
            avg_f1 = 0.0
            avg_f2 = 0.0
            avg_back_pressure = 0.0
            dominant_vowel = "Silence"
            
        # 6. Vibrato Rate & Depth Diagnostics
        vibrato_detected = False
        vibrato_rate = 0.0
        vibrato_depth = 0.0
        
        if voiced_indices:
            f0_voiced = np.array([f0[idx] for idx in voiced_indices])
            sr_hop = sr / hop_length
            if len(f0_voiced) >= int(sr_hop * 1.0): # need at least 1.0 second of voicing
                f0_mean = np.mean(f0_voiced)
                f0_detrend = f0_voiced - f0_mean
                # Detrended sign crossing estimation
                zero_crossings = np.where(np.diff(np.sign(f0_detrend)))[0]
                if len(zero_crossings) >= 4:
                    intervals = np.diff(zero_crossings) / sr_hop
                    avg_cycle = np.mean(intervals) * 2
                    if avg_cycle > 0:
                        rate = 1.0 / avg_cycle
                        if 3.5 <= rate <= 8.5:
                            vibrato_rate = float(rate)
                            f0_90 = np.percentile(f0_voiced, 90)
                            f0_10 = np.percentile(f0_voiced, 10)
                            if f0_10 > 0:
                                depth = 12 * np.log2(f0_90 / f0_10)
                                vibrato_depth = float(depth)
                                # Vocal vibrato is typical between 4.0 - 8.0 Hz rate & 0.3 - 2.0 semitones depth
                                if 0.3 <= depth <= 2.2:
                                    vibrato_detected = True

        # Compile response
        time_stamps = [float(i * hop_length / sr) for i in range(num_frames)]
        
        # Calculate session score (Dryness/Friction index):
        # Higher score (out of 100) indicates longer, cleaner phonation with low jitter
        total_duration = num_frames * hop_length / sr
        voiced_duration = len(voiced_indices) * hop_length / sr
        voicing_ratio = voiced_duration / total_duration if total_duration > 0 else 0.0
        
        # Dryness/Friction Index: base is back-pressure, scaled by voicing ratio, penalized by high average jitter
        dryness_friction_index = max(0.0, avg_back_pressure * 0.8 + (1.0 - min(1.0, avg_jitter / 2.0)) * 20.0)
        
        return {
            "summary": {
                "f0_hz": avg_f0,
                "jitter_percentage": avg_jitter,
                "shimmer_percentage": avg_shimmer,
                "f1_formant_hz": avg_f1,
                "f2_formant_hz": avg_f2,
                "vowel_space": dominant_vowel,
                "back_pressure_index": avg_back_pressure,
                "dryness_friction_index": dryness_friction_index,
                "voiced_duration_sec": voiced_duration,
                "total_duration_sec": total_duration,
                "vibrato_detected": vibrato_detected,
                "vibrato_rate_hz": vibrato_rate,
                "vibrato_depth_semitones": vibrato_depth
            },
            "time_series": {
                "time_stamps": time_stamps,
                "f0": [float(v) for v in f0],
                "f1": f1_series,
                "f2": f2_series,
                "vowels": vowels_series,
                "jitter": jitter_series,
                "shimmer": shimmer_series,
                "back_pressure": back_pressure_series
            }
        }
    except Exception as e:
        return {"error": f"DSP processing error: {str(e)}"}

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_file = sys.argv[1]
        print(f"Analyzing test file: {test_file}")
        results = analyze_vocal_dsp(test_file)
        if "error" in results:
            print("Error:", results["error"])
        else:
            print("Summary Metrics:")
            for k, v in results["summary"].items():
                print(f"  {k}: {v}")
    else:
        print("Usage: python3 vocal_dsp.py <audio_file_path>")
