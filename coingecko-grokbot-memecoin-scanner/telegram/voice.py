"""Local speech-to-text with faster-whisper (CPU int8). Model loads lazily once per process."""
import os, subprocess, tempfile, time
MODEL = os.environ.get("TG_WHISPER_MODEL", "base.en"); _m = None
PROMPT = "Paper trading commands: buy 100 dollars, sell half, sell 30 percent, take profits, PnL, positions, ticker, contract."
def model():
    global _m
    if _m is None:
        from faster_whisper import WhisperModel
        _m = WhisperModel(MODEL, device="cpu", compute_type="int8", cpu_threads=4)
    return _m
def transcribe(path, tickers=()):
    t0 = time.time()
    import numpy as np   # decode with ffmpeg ourselves (avoids PyAV version issues)
    pcm = subprocess.run(["ffmpeg", "-nostdin", "-loglevel", "error", "-i", path, "-f", "s16le", "-ac", "1", "-ar", "16000", "-"],
                         check=True, timeout=60, capture_output=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768.0
    if True:
        segs, _ = model().transcribe(audio, beam_size=1, language="en", initial_prompt=PROMPT + (" Tickers: " + ", ".join(tickers) + "." if tickers else ""), vad_filter=True)
        text = " ".join(s.text.strip() for s in segs).strip()
    return text, time.time() - t0
