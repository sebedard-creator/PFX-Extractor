import numpy as np
import librosa
import noisereduce as nr
from scipy import signal
import soundfile as sf
import os

TARGET_SR = 48000
TRUE_PEAK_DB = -0.3

def dc_blocker(y: np.ndarray, sr: int, cutoff: float = 20.0) -> np.ndarray:
    """Filtre Passe-Haut ultra-raide à 20Hz pour supprimer le Rumble et DC Offset."""
    sos = signal.butter(4, cutoff, 'hp', fs=sr, output='sos')
    return signal.sosfiltfilt(sos, y).astype(np.float32)

def calculate_mask_multires(y: np.ndarray, sr: int, sensitivity: float) -> np.ndarray:
    """
    Détection Transitoire Multi-Résolution.
    Combine une FFT courte (guenille/clics) et une FFT longue (pas lourds).
    Retourne un masque lissé entre 0.0 et 1.0.
    """
    # Passe Rapide (Guenille / Hautes Fréquences)
    margin_fast = np.interp(sensitivity, [0, 100], [4.0, 1.2]) # Plus sensible = plus bas
    _, p_fast = librosa.effects.hpss(y, margin=(1.0, margin_fast), n_fft=512, hop_length=128)
    
    # Passe Lente (Pas lourds / Basses Fréquences)
    margin_slow = np.interp(sensitivity, [0, 100], [3.0, 1.1])
    _, p_slow = librosa.effects.hpss(y, margin=(1.0, margin_slow), n_fft=2048, hop_length=512)
    
    # Extraction d'enveloppe RMS
    rms_fast = librosa.feature.rms(y=p_fast, frame_length=512, hop_length=128)[0]
    rms_slow = librosa.feature.rms(y=p_slow, frame_length=2048, hop_length=512)[0]
    
    # Interpolation à la taille originale du signal
    times_fast = librosa.times_like(rms_fast, sr=sr, hop_length=128)
    times_slow = librosa.times_like(rms_slow, sr=sr, hop_length=512)
    times_y = np.arange(len(y)) / sr
    
    env_fast = np.interp(times_y, times_fast, rms_fast)
    env_slow = np.interp(times_y, times_slow, rms_slow)
    
    # Fusion des masques
    mask = env_fast + env_slow
    
    # Normalisation agressive (on veut que les petits bruits montent à 1.0 rapidement)
    max_val = np.max(mask) if np.max(mask) > 1e-6 else 1.0
    mask = (mask / max_val) * (sensitivity / 50.0) # Scaling selon sensibilité
    
    # Lissage (Lowpass filter sur le masque pour éviter les clics de modulation)
    mask = signal.savgol_filter(mask, window_length=int(sr * 0.05), polyorder=2)
    return np.clip(mask, 0.0, 1.0).astype(np.float32)

def find_autofocus_10s(mask: np.ndarray, sr: int) -> tuple[int, int]:
    """Trouve la fenêtre de 10 secondes contenant l'énergie de masque maximale."""
    window_samples = 10 * sr
    if len(mask) <= window_samples:
        return 0, len(mask)
        
    # Calcul de la somme glissante avec convolution
    kernel = np.ones(window_samples)
    energy_sliding = signal.fftconvolve(mask, kernel, mode='valid')
    start_idx = np.argmax(energy_sliding)
    end_idx = start_idx + window_samples
    return int(start_idx), int(end_idx)

def true_peak_limit(y: np.ndarray) -> np.ndarray:
    """Limiteur transparent pour éviter le clipping numérique en 24-bit post-export."""
    peak_linear = 10 ** (TRUE_PEAK_DB / 20)
    # Soft clipper basique (idéalement un vrai limiteur avec lookahead, mais tanh est robuste ici)
    driven = y / peak_linear
    return (np.tanh(driven) * peak_linear).astype(np.float32)

def process_channel(y_bg: np.ndarray, sr: int, sensitivity: float, denoise_ratio: float, release: float) -> tuple[np.ndarray, np.ndarray]:
    """
    Traite un canal complet.
    1. DC Blocker
    2. Création du Masque
    3. Dénoiseur Non-Stationnaire
    4. Mixage Wet/Dry piloté par le Masque (Sidechain virtuel)
    5. True Peak Limit
    """
    # 1. DC Blocker
    y_bg = dc_blocker(y_bg, sr)
    
    # 2. Masque PFX Multi-Res
    mask = calculate_mask_multires(y_bg, sr, sensitivity)
    
    # Adaptation du Release au Masque
    release_samples = int(sr * (release / 100.0) * 0.5) # max 500ms
    if release_samples > 0:
        kernel = np.ones(release_samples) / release_samples
        mask = signal.fftconvolve(mask, kernel, mode='same')
        mask = np.clip(mask, 0.0, 1.0)
    
    # 3. Dénoiseur Non-Stationnaire (Apprentissage continu)
    # On utilise prop_decrease pour contrôler le ratio
    ratio = denoise_ratio / 100.0
    denoised = nr.reduce_noise(
        y=y_bg, 
        sr=sr, 
        stationary=False, # Profil dynamique (Statistique)
        prop_decrease=ratio,
        time_mask_smooth_ms=50, # Très rapide pour éviter le pre-echo (Smearing)
        freq_mask_smooth_hz=200
    )
    
    # 4. Crossfade Sidechain (Masque = 1 -> PFX brut, Masque = 0 -> Denoised)
    # L'empreinte de la pièce reste naturelle sous les pas.
    final_audio = (y_bg * mask) + (denoised * (1.0 - mask))
    
    # 5. Peak Limit
    final_audio = true_peak_limit(final_audio)
    
    return final_audio.astype(np.float32), mask.astype(np.float32)

def align_sync(y_ref: np.ndarray, y_proc: np.ndarray) -> np.ndarray:
    """Correction de synchro Sample-Accurate en cas de padding IA (non utilisé ici car on mixe wet/dry direct sur le même fichier, mais utile si on charge le Brut et l'IA séparement)."""
    # Actuellement, puisque le masque s'applique directement sur l'audio renvoyé par Colab,
    # le fichier reste à la longueur de l'IA. 
    # Pour une V1.0, on se fie au fichier IA.
    return y_proc
