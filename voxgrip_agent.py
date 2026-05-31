import asyncio
import os
import numpy as np
from vocal_dsp import analyze_vocal_dsp

def hz_to_note(hz: float) -> str:
    """Converts a frequency in Hz to its corresponding musical note name and octave."""
    if hz <= 0:
        return "Silence"
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    hertz_c0 = 16.35
    semitones = 12 * np.log2(hz / hertz_c0)
    pitch_index = int(round(semitones))
    octave = pitch_index // 12
    note_name = notes[pitch_index % 12]
    return f"{note_name}{octave}"

async def run_voxgrip_agent(file_path: str, api_key: str = None, exercise_type: str = None, instruments: list = None) -> str:
    """
    Runs a local rule-based expert analysis on vocal DSP metrics to generate 
    a highly technical, actionable vocal pedagogy report completely offline.
    Factors in the user's active instruments (woodwinds, violin, guitar) for custom analogies.
    """
    if not os.path.exists(file_path):
        return f"Error: Audio file not found at {file_path}"
        
    # Run the local DSP pipeline to extract acoustic metrics
    results = analyze_vocal_dsp(file_path)
    if "error" in results:
        return f"### ⚠️ DSP Analysis Error\n\n{results['error']}"
        
    summary = results.get("summary", {})
    time_series = results.get("time_series", {})
    
    f0_avg = summary.get("f0_hz", 0.0)
    jitter_avg = summary.get("jitter_percentage", 0.0)
    shimmer_avg = summary.get("shimmer_percentage", 0.0)
    f1_avg = summary.get("f1_formant_hz", 0.0)
    f2_avg = summary.get("f2_formant_hz", 0.0)
    vowel_space = summary.get("vowel_space", "Silence")
    back_pressure_avg = summary.get("back_pressure_index", 0.0)
    dryness_index = summary.get("dryness_friction_index", 0.0)
    
    # Vibrato metrics
    vibrato_detected = summary.get("vibrato_detected", False)
    vibrato_rate = summary.get("vibrato_rate_hz", 0.0)
    vibrato_depth = summary.get("vibrato_depth_semitones", 0.0)
    
    # Identify the exercise label
    exercise_labels = {
        "lip_trill": "The Trill Sustainer (Lip / Tongue Roll)",
        "vowel_migration": "Vowel Migration (High-Register /i/ or /u/)",
        "voiced_fricative": "Voiced Fricative (/v/ or /z/ Support)",
        "vocal_fry": "Vocal Fry Onset (Gentle Cord Realignment)",
        "messa_di_voce": "Messa di Voce (Crescendo & Support Test)",
        "free_singing": "Free Scaling & Phonation Stability"
    }
    exercise_name = exercise_labels.get(exercise_type, "Free Scaling & Phonation Stability")
    
    f0_note = hz_to_note(f0_avg) if f0_avg > 0 else "Silence"
    
    # Build report parts
    report = []
    report.append(f"**Exercise Mode:** {exercise_name}\n")
    report.append("### 📊 Aerodynamic Summary\n")
    
    # 1. Pitch Profile
    if f0_avg > 0:
        voiced_f0 = [v for v in time_series.get("f0", []) if v > 0]
        if len(voiced_f0) > 1:
            f0_min = min(voiced_f0)
            f0_max = max(voiced_f0)
            f0_range = f0_max - f0_min
            f0_min_note = hz_to_note(f0_min)
            f0_max_note = hz_to_note(f0_max)
            
            if f0_range > 30: # Multi-tone slide or scale
                report.append(f"- **Pitch Profile ($F_0$):** Your pitch averaged **{f0_avg:.1f} Hz** (approx. **{f0_note}**). The recording shows a dynamic pitch sweep spanning from **{f0_min_note}** ({f0_min:.1f} Hz) up to **{f0_max_note}** ({f0_max:.1f} Hz).")
            else: # Sustained single note
                report.append(f"- **Pitch Profile ($F_0$):** You held a steady target pitch averaging **{f0_avg:.1f} Hz** (approx. **{f0_note}**).")
        else:
            report.append(f"- **Pitch Profile ($F_0$):** Your pitch averaged **{f0_avg:.1f} Hz** (approx. **{f0_note}**).")
    else:
        report.append("- **Pitch Profile ($F_0$):** No active voicing detected in this segment.")
        
    # 2. Vocal Perturbation (Jitter)
    # Note: In vocal fry, high jitter is actually normal and expected.
    if exercise_type == "vocal_fry":
        jitter_status = "Typical Fry (high frequency perturbation is normal in creaky voice as cord margins relax)"
    elif jitter_avg <= 1.0:
        jitter_status = "Optimal (healthy mucosal wave stability, low cycle-to-cycle friction)"
    elif jitter_avg <= 3.0:
        jitter_status = "Elevated (moderate glottal friction, suggesting mild dryness or minor throat tension)"
    else:
        jitter_status = "High / Severe (significant cycle-to-cycle frequency instability, representing 'sticky' mucosal wave friction or pressed phonation)"
    report.append(f"- **Vocal Jitter ($J_{{loc}}$):** **{jitter_avg:.2f}%** — *{jitter_status}*. (Target threshold for normal singing: <1.0%)")
    
    # 3. Vocal Perturbation (Shimmer)
    if shimmer_avg <= 3.0:
        shimmer_status = "Optimal (stable subglottic pressure and airflow regulation)"
    elif shimmer_avg <= 6.0:
        shimmer_status = "Elevated (minor fluctuations in breath support or subglottic pressure)"
    else:
        shimmer_status = "High (significant cycle-to-cycle amplitude perturbation, indicating unstable breath support or muscular fight-to-hold tension)"
    report.append(f"- **Vocal Shimmer ($Sh_{{loc}}$):** **{shimmer_avg:.2f}%** — *{shimmer_status}*. (Target threshold for stable support: <3.0%)")
    
    # 4. Acoustic Back-Pressure
    if back_pressure_avg >= 70:
        bp_status = "Excellent (well-cushioned vocal tract with high acoustic back-pressure)"
    elif back_pressure_avg >= 55:
        bp_status = "Moderate (acceptable acoustic cushion, but room to optimize lips/straw constriction)"
    else:
        bp_status = "Low / Weak (insufficient back-pressure support, vocal folds are taking the direct force of the air)"
    report.append(f"- **Acoustic Back-Pressure:** **{back_pressure_avg:.1f}/100** — *{bp_status}*.")
    
    # 5. Dryness/Friction Index
    if dryness_index >= 70:
        dryness_status = "Excellent (minimal fatigue, well-lubricated mucosal glide)"
    elif dryness_index >= 50:
        dryness_status = "Moderate Fatigue (borderline friction, keep hydrating and avoid pressing)"
    else:
        dryness_status = "High Fatigue / Strain (high mucosal friction, larynx is worked and dehydrated)"
    report.append(f"- **Dryness & Friction Index:** **{dryness_index:.1f}/100** — *{dryness_status}*.")
    
    # Acoustic & Formant Analysis Section
    report.append("\n### 🧠 Acoustic & Formant Analysis\n")
    report.append(f"- **Formant Tracking:** Average Formants detected at **$F_1$ = {f1_avg:.1f} Hz** and **$F_2$ = {f2_avg:.1f} Hz**.")
    report.append(f"- **Vowel Space Classification:** Dominant acoustic vowel space classified as **{vowel_space}**.")
    
    # Vibrato tracking output
    if vibrato_detected:
        if vibrato_rate < 4.5:
            rate_desc = "Slow Vibrato ('wobble') — indicating loose breath support or lazy abdominal regulation"
        elif vibrato_rate > 7.5:
            rate_desc = "Fast Vibrato ('tremolo') — indicating high laryngeal tension or nervous subglottic pressure"
        else:
            rate_desc = "Optimal Vibrato Rate (healthy artistic oscillation)"
            
        if vibrato_depth > 1.8:
            depth_desc = "Wide Depth (wobbling pitch range)"
        elif vibrato_depth < 0.4:
            depth_desc = "Narrow/Rigid Depth (flat, pressed tone)"
        else:
            depth_desc = "Optimal Vibrato Depth"
            
        report.append(f"- **Vibrato Metrics:** Detected **{vibrato_rate:.2f} Hz** rate at **{vibrato_depth:.2f} semitones** depth. (Status: *{rate_desc}* / *{depth_desc}*).")
    else:
        report.append("- **Vibrato Metrics:** No active, stable periodic vibrato detected (normal for sustained straight tones or slides).")

    # Specific evaluations based on exercise mode
    if exercise_type == "vowel_migration":
        report.append("\n**Vowel Migration Evaluation:**")
        if vowel_space in ["/i/", "/u/"]:
            report.append("- ⚠️ **Acoustic Squeeze Detected:** Your vowel space remains locked in closed **" + vowel_space + "**. As you scale upward, this creates a high-pressure pinch where $F_1$ narrows too drastically. This triggers pitch breaks or laryngeal squeeze.")
            report.append("- **Recommendation:** Actively modify your vowel shape. Shifting from closed `/i/` to open `/ɪ/` (as in 'bit') or from `/u/` to `/ʊ/` (as in 'book') helps couple the formants and release the throat.")
        elif vowel_space in ["/ɪ/", "/ʊ/"]:
            report.append("- **Successful Vowel Migration:** Your vowel successfully migrated to **" + vowel_space + "**. This formant shading prevents the acoustic squeeze, allowing you to glide past register boundaries without laryngeal strain.")
        else:
            report.append("- **Formant Shading:** The detected vowel space was **" + vowel_space + "**. For this high-register exercise, ensure you start on `/i/` or `/u/` and shade them towards `/ɪ/` and `/ʊ/` as pitch climbs.")
            
    elif exercise_type == "lip_trill":
        report.append("\n**Lip/Tongue Trill Evaluation:**")
        if back_pressure_avg >= 65:
            report.append("- **Optimal Semi-Occlusion:** Your back-pressure is healthy (**" + f"{back_pressure_avg:.1f}" + "/100**). The lip/tongue vibration is creating a sufficient acoustic cushion, which unloads the vocal fold contact pressure.")
        else:
            report.append("- ⚠️ **Weak Back-Pressure Support:** The back-pressure is below the target 65%. This indicates that either the lips are too loose, too much air is leaking unoccluded, or the trill is dropping out.")
            
    elif exercise_type == "voiced_fricative":
        report.append("\n**Voiced Fricative Evaluation:**")
        if back_pressure_avg >= 60:
            report.append("- **Good Fricative Occlusion:** Your voiced fricative (/v/ or /z/) is successfully generating back-pressure. This pressure helps expand the vocal tract and assists vocal fold closure with minimal muscle force.")
        else:
            report.append("- ⚠️ **Insufficient Fricative Back-Pressure:** Your back-pressure is low. Ensure you maintain a steady constriction of the lips/teeth (/v/) or teeth/tongue (/z/) to force the air back into the vocal tract.")
            
    elif exercise_type == "vocal_fry":
        report.append("\n**Vocal Fry Evaluation:**")
        if f0_avg > 0 and f0_avg < 95:
            report.append("- **Healthy Fry Phonation:** Your fundamental frequency is low (**" + f"{f0_avg:.1f}" + " Hz**), showing successful coordination of the vocal fry register. This helps relax the vocal fold margins and lower the larynx.")
        else:
            report.append("- ⚠️ **High Pitch for Fry:** Your average pitch is **" + f"{f0_avg:.1f}" + " Hz** (above the typical fry boundary). Ensure you relax your breath completely, let out a 'creaky' sound, and drop the pitch as low as possible without forcing.")

    elif exercise_type == "messa_di_voce":
        report.append("\n**Messa di Voce Evaluation:**")
        if shimmer_avg < 3.0:
            report.append("- **Stable Support under Dynamic Volume:** Your Shimmer is low (**" + f"{shimmer_avg:.2f}%" + "**). This shows excellent breath support stability, meaning your vocal folds maintain steady contact even as volume increases and decreases.")
        else:
            report.append("- ⚠️ **Breath Instability:** Your Shimmer is elevated (**" + f"{shimmer_avg:.2f}%" + "**). The change in subglottic pressure is destabilizing the cords. Focus on smooth, gradual transitions in volume rather than sudden pushes.")

    else: # free_singing or general
        report.append("\n**Phonation Stability Evaluation:**")
        voiced_f0 = [v for v in time_series.get("f0", []) if v > 0]
        if len(voiced_f0) > 1:
            f0_std = np.std(voiced_f0)
            if f0_std < 5.0 and (jitter_avg > 1.5 or shimmer_avg > 3.5):
                report.append("- ⚠️ **Held Note Perturbation:** While holding a constant pitch (pitch standard deviation: " + f"{f0_std:.2f}" + " Hz), your jitter/shimmer is elevated. This confirms that holding a note is requiring significant laryngeal muscle effort, indicating pressed phonation or lack of breath cushion.")
            elif f0_std >= 5.0:
                report.append("- **Scale Trajectory:** You are moving through a frequency range (pitch standard deviation: " + f"{f0_std:.2f}" + " Hz). Your vocal tract must dynamically adapt to prevent pitch breaks.")
        else:
            report.append("- **No active pitch stability data** can be evaluated from silent frames.")
            
    # Pedagogical Adjustments Section
    report.append("\n### 🛠️ Pedagogical Adjustments\n")
    
    recommendations = []
    
    # 1. Jitter adjustment
    if jitter_avg > 1.0 and exercise_type != "vocal_fry":
        recommendations.append("1. **Reduce Air Volume:** You are likely blowing too much air to sustain the note or the trill. **Halve your air flow.** Let a tiny, soft stream of breath glide through the larynx.")
        recommendations.append("2. **Yawn-Sigh Reset:** Perform a silent, wide yawn to open the throat, and let out a gentle sigh from high to low pitch on `/h-h-h-u-u-u/` (breathy onset) to release throat squeeze and reset the larynx.")
    elif exercise_type == "vocal_fry":
        recommendations.append("1. **Zero Air-Push:** Do not blow air to make the fry sound. Let the breath bubble up lazily through the throat. Think of a creaking door.")
        recommendations.append("2. **Maintain Cord Relaxation:** Ensure your neck muscles, tongue, and jaw are completely passive during the fry onset.")
    else:
        recommendations.append("1. **Maintain Steady Flow:** Your mucosal wave is highly stable (Jitter < 1.0%). Keep this relaxed, non-pressed vocal fold coordination during scales.")
        recommendations.append("2. **Consistent support:** Continue focusing on low vocal fold contact forces and relaxed neck support.")
        
    # 2. Shimmer adjustment
    if shimmer_avg > 3.0:
        recommendations.append("3. **Stabilize Subglottic Pressure:** Your Shimmer is elevated, indicating uneven breath support. Focus on maintaining a steady abdominal core engagement. Avoid sudden pushes of air at the start of notes.")
        recommendations.append("4. **Narrow Straw Phonation:** Hum gently through a drinking straw (with the far end in a glass of water) to physically enforce a steady back-pressure and unload the vocal fold collision force.")
    else:
        recommendations.append("3. **Excellent Breath Support:** Your amplitude perturbation (Shimmer) is excellent, demonstrating stable lung pressure and steady air supply.")
        
    # 3. Mode specific adjustment
    if exercise_type == "vowel_migration" and vowel_space in ["/i/", "/u/"]:
        recommendations.append("5. **Actively Shade the Vowel:** Release your jaw and widen the throat. Let `/i/` migrate to `/ɪ/` (bit) or `/u/` migrate to `/ʊ/` (book) as you sing higher in pitch to bypass laryngeal pinching.")
    elif back_pressure_avg < 60 and exercise_type in ["lip_trill", "voiced_fricative"]:
        recommendations.append("5. **Increase Occlusion Resistance:** Narrow your lip corners during lip trills, or make your voiced fricative `/v/` tighter against the teeth to build a healthier back-pressure cushion.")
    elif exercise_type == "messa_di_voce":
        recommendations.append("5. **Dynamic Core Balance:** During crescendo/decrescendo, balance the expansion of your lower ribs. Do not let the throat narrow to make the sound softer (decrescendo); instead, decrease the support weight while keeping the throat wide.")
    else:
        recommendations.append("5. **Vocal Tract Openness:** Keep the throat open and the tongue relaxed to optimize vowel resonance space.")
        
    # 4. Dryness/fatigue adjustment
    if dryness_index < 55:
        recommendations.append("6. **Hydration & Rest:** Your overall dryness/fatigue index is poor. Give your voice a **2-hour vocal rest**, sip lukewarm water, and avoid pressed speech.")

    # 5. Instrumental Spillover Profile Hooks
    if instruments:
        report.append("\n**🎸🎻 Instrumental Spillover Adjustments:**")
        
        if "woodwinds" in instruments:
            report.append("- **Woodwind Aerodynamic Habit:** Because you play flute/saxophone, you are prone to over-blowing. Focus on reducing expiratory breath velocity. Keep jaw relaxed and embouchure muscles neutral, avoiding tongue-root retraction. Singing requires a much lower, more cushioned airflow than woodwinds.")
            
        if "violin" in instruments:
            report.append("- **Violin Bow-Stroke Analogy:** Think of your breath support as drawing a violin bow. Pushing the bow too hard against the strings chokes the sound (pressed phonation/high Jitter); drawing it too fast with too little friction creates a breathy whisper. Aim for a balanced, fluid 'vocal bow stroke' that maintains steady support friction without choking.")
            
        if "guitar" in instruments:
            report.append("- **Guitar Postural Check:** Avoid 'fretboard posture' (craning your neck forward or looking down). Align your spine, keep your head level, and relax your neck. Also, make sure you don't 'pluck' your vocal notes (avoid hard glottal attacks at the start of words); instead, transition smoothly with a soft, breathy onset.")
        
    # Join recommendations
    for rec in recommendations:
        report.append(rec)
        
    return "\n".join(report)

if __name__ == "__main__":
    # Test script running standalone
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 voxgrip_agent.py <audio_file_path> [exercise_type] [instruments]")
        sys.exit(1)
        
    audio_path = sys.argv[1]
    ex_type = sys.argv[2] if len(sys.argv) > 2 else "free_singing"
    insts = sys.argv[3].split(",") if len(sys.argv) > 3 else []
    
    print(f"Initializing VoxGrip Offline Local Expert on {audio_path} ({ex_type}) with instruments {insts}...")
    feedback = asyncio.run(run_voxgrip_agent(audio_path, exercise_type=ex_type, instruments=insts))
    print("\n--- LOCAL EXPERT FEEDBACK ---")
    print(feedback)
