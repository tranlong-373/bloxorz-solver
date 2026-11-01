"""Procedural sound effects and ambient music for the 3D scene.

Owner: VT3 | Prototype (not yet a task card).

Every sound is synthesised with the standard library (no audio files, no new
dependency) and written once to a cache folder as 16-bit mono WAV. Playback
uses Ursina's Audio; if Audio is missing (headless tests) or the sound card
fails, play() silently does nothing so the game never breaks because of sound.
"""

import array
import logging
import math
import random
import tempfile
import threading
import wave
from pathlib import Path

logger = logging.getLogger(__name__)

RATE = 22050
# Bump when a sound's recipe changes so stale cached WAVs are rebuilt.
VERSION = 2
CACHE_DIR = Path(tempfile.gettempdir()) / "bloxorz_sounds"

SFX_VOLUME = 1.0
MUSIC_VOLUME = 0.45

_enabled = True
_clips = {}
_music = None
_music_requested = False


# ---------------------------------------------------------------- synthesis

def _buffer(seconds):
    return [0.0] * int(seconds * RATE)


def _add_tone(buf, start, length, freq, amp, attack=0.005, decay=None,
              freq_end=None, shape="sine", wrap=False):
    """Mix one tone into buf; frequency glides from freq to freq_end."""
    n = int(length * RATE)
    s0 = int(start * RATE)
    f1 = freq if freq_end is None else freq_end
    phase = 0.0
    for i in range(n):
        t = i / RATE
        f = freq + (f1 - freq) * (i / n)
        phase += 2 * math.pi * f / RATE
        if shape == "sine":
            v = math.sin(phase)
        elif shape == "triangle":
            v = 2 / math.pi * math.asin(math.sin(phase))
        else:  # soft square
            v = math.tanh(3 * math.sin(phase))
        env = min(1.0, t / attack) if attack else 1.0
        if decay:
            env *= math.exp(-t / decay)
        else:
            env *= min(1.0, (length - t) / 0.02)  # short release, no click
        k = s0 + i
        if wrap:
            buf[k % len(buf)] += v * env * amp
        elif k < len(buf):
            buf[k] += v * env * amp


def _add_noise(buf, start, length, amp, decay, smooth=0.0, seed=1):
    """Decaying noise burst; smooth in [0,1) low-passes it (darker)."""
    rng = random.Random(seed)
    s0 = int(start * RATE)
    last = 0.0
    for i in range(int(length * RATE)):
        t = i / RATE
        last = smooth * last + (1 - smooth) * rng.uniform(-1, 1)
        k = s0 + i
        if k < len(buf):
            buf[k] += last * amp * math.exp(-t / decay)


def _bell(buf, start, freq, amp, decay=0.5):
    """Soft bell: fundamental plus two quiet inharmonic partials."""
    _add_tone(buf, start, decay * 4, freq, amp, attack=0.003, decay=decay)
    _add_tone(buf, start, decay * 3, freq * 2.01, amp * 0.35, attack=0.003, decay=decay * 0.6)
    _add_tone(buf, start, decay * 2, freq * 3.02, amp * 0.15, attack=0.003, decay=decay * 0.4)


def _recipe_land(buf):
    # Stone block settling: low pitch-dropping thud plus a dull click.
    _add_tone(buf, 0, 0.22, 120, 0.9, attack=0.002, decay=0.06, freq_end=55)
    _add_noise(buf, 0, 0.06, 0.35, 0.012, smooth=0.6, seed=3)


def _recipe_land_cube(buf):
    _add_tone(buf, 0, 0.16, 210, 0.7, attack=0.002, decay=0.045, freq_end=110)
    _add_noise(buf, 0, 0.04, 0.3, 0.008, smooth=0.5, seed=4)


def _recipe_switch(buf):
    # Mechanical button: two quick clicks and a short confirm tone.
    _add_tone(buf, 0.00, 0.03, 1400, 0.35, attack=0.001, decay=0.008, shape="square")
    _add_tone(buf, 0.04, 0.03, 900, 0.35, attack=0.001, decay=0.008, shape="square")
    _add_tone(buf, 0.06, 0.12, 660, 0.25, attack=0.004, decay=0.05)


def _recipe_bridge_open(buf):
    _add_tone(buf, 0, 0.32, 260, 0.45, attack=0.02, decay=0.25, freq_end=780, shape="triangle")
    _add_tone(buf, 0.02, 0.30, 390, 0.2, attack=0.02, decay=0.2, freq_end=1170)
    _add_noise(buf, 0, 0.3, 0.08, 0.15, smooth=0.9, seed=5)


def _recipe_bridge_close(buf):
    _add_tone(buf, 0, 0.32, 780, 0.45, attack=0.01, decay=0.25, freq_end=230, shape="triangle")
    _add_tone(buf, 0.02, 0.30, 1170, 0.18, attack=0.01, decay=0.2, freq_end=345)
    _add_noise(buf, 0, 0.3, 0.08, 0.15, smooth=0.9, seed=6)


def _recipe_crack(buf):
    # Fragile tile collapsing: sharp crackles over a crumbling rumble.
    _add_noise(buf, 0, 0.4, 0.6, 0.12, smooth=0.75, seed=7)
    rng = random.Random(8)
    for _ in range(9):
        _add_noise(buf, rng.uniform(0, 0.18), 0.02, 0.6, 0.004, smooth=0.1, seed=rng.randint(0, 99))
    _add_tone(buf, 0, 0.35, 80, 0.5, attack=0.003, decay=0.12, freq_end=45)


def _recipe_fall(buf):
    # Falling into space: a whistle gliding down and fading out.
    _add_tone(buf, 0, 0.9, 820, 0.35, attack=0.03, decay=0.45, freq_end=140)
    _add_tone(buf, 0, 0.9, 827, 0.2, attack=0.03, decay=0.45, freq_end=143)
    _add_noise(buf, 0, 0.9, 0.12, 0.4, smooth=0.95, seed=9)


def _recipe_split(buf):
    # One tone splitting into two diverging ones.
    _add_tone(buf, 0, 0.3, 520, 0.35, attack=0.005, decay=0.15, freq_end=880)
    _add_tone(buf, 0, 0.3, 520, 0.35, attack=0.005, decay=0.15, freq_end=330)
    _bell(buf, 0.02, 1320, 0.12, decay=0.12)


def _recipe_merge(buf):
    # Two tones converging, then a clean chime.
    _add_tone(buf, 0, 0.18, 880, 0.3, attack=0.005, decay=0.1, freq_end=660)
    _add_tone(buf, 0, 0.18, 330, 0.3, attack=0.005, decay=0.1, freq_end=660)
    _bell(buf, 0.16, 660, 0.35, decay=0.2)


def _recipe_select(buf):
    _add_tone(buf, 0, 0.08, 1050, 0.3, attack=0.002, decay=0.025)


def _recipe_win(buf):
    # Rising C-major arpeggio, then the chord ringing out.
    notes = (523.25, 659.25, 783.99, 1046.5)
    for i, f in enumerate(notes):
        _bell(buf, i * 0.09, f, 0.32, decay=0.35)
    for f in notes[:3]:
        _add_tone(buf, 0.36, 1.1, f, 0.12, attack=0.05, decay=0.5)


def _recipe_music(buf):
    """Slow space pad looping seamlessly: Am - F - C - G, 4 s per chord.

    Notes are mixed with wraparound, so the tail of the last chord fades into
    the start of the first one and the loop has no seam.
    """
    chords = (
        (220.00, 261.63, 329.63),  # A minor
        (174.61, 220.00, 261.63),  # F major
        (196.00, 261.63, 329.63),  # C major (C4 E4 over G3)
        (196.00, 246.94, 293.66),  # G major
    )
    span = 4.0
    for i, chord in enumerate(chords):
        start = i * span
        for f in chord:
            for detune in (0.997, 1.003):  # slow beating, a soft chorus
                _pad_note(buf, start, span * 1.6, f * detune, 0.055)
        _pad_note(buf, start, span * 1.6, chord[0] / 2, 0.06)  # bass
    rng = random.Random(10)
    scale = (659.25, 783.99, 880.0, 987.77, 1174.66, 1318.51)
    for _ in range(10):  # distant twinkles
        _bell(buf, rng.uniform(0, len(chords) * span - 2), rng.choice(scale), 0.04, decay=0.6)


def _pad_note(buf, start, length, freq, amp):
    n = int(length * RATE)
    s0 = int(start * RATE)
    for i in range(n):
        t = i / RATE
        # Smooth swell in and out (sine-shaped), so overlaps blend.
        env = math.sin(math.pi * t / length) ** 2
        v = math.sin(2 * math.pi * freq * t) + 0.25 * math.sin(4 * math.pi * freq * t)
        buf[(s0 + i) % len(buf)] += v * env * amp


RECIPES = {
    "land": (0.25, _recipe_land),
    "land_cube": (0.18, _recipe_land_cube),
    "switch": (0.2, _recipe_switch),
    "bridge_open": (0.35, _recipe_bridge_open),
    "bridge_close": (0.35, _recipe_bridge_close),
    "crack": (0.45, _recipe_crack),
    "fall": (0.95, _recipe_fall),
    "split": (0.35, _recipe_split),
    "merge": (0.5, _recipe_merge),
    "select": (0.1, _recipe_select),
    "win": (1.6, _recipe_win),
    "music": (16.0, _recipe_music),
}


def render(name):
    """Synthesise a sound and return its float samples in [-1, 1]."""
    seconds, recipe = RECIPES[name]
    buf = _buffer(seconds)
    recipe(buf)
    # Normalise every sound to the same peak so quiet recipes are not lost.
    peak = max(1e-9, max(abs(v) for v in buf))
    buf = [v * 0.95 / peak for v in buf]
    if name != "music":  # the music loops; effects fade out to avoid a click
        fade = int(0.02 * RATE)
        for i in range(fade):
            buf[-1 - i] *= i / fade
    return buf


def write_wav(path, samples):
    data = array.array("h", (int(max(-1.0, min(1.0, v)) * 32767) for v in samples))
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(data.tobytes())


def sound_file(name):
    """Path of the cached WAV for name, building it on first use."""
    path = CACHE_DIR / f"{name}_v{VERSION}.wav"
    if not path.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        # Per-thread temp name: the preload thread and play() may race.
        tmp = path.with_suffix(f".{threading.get_ident()}.tmp")
        write_wav(tmp, render(name))
        tmp.replace(path)
    return path


# ----------------------------------------------------------------- playback

def _audio():
    """Ursina's Audio class, or None when it is unavailable.

    Looked up on every call (a sys.modules hit), so tests that swap in a fake
    ursina without Audio always stay silent.
    """
    try:
        from ursina import Audio
    except Exception:  # fake ursina in tests has no Audio
        return None
    # Ursina halves every sound by default (volume_multiplier = .5).
    Audio.volume_multiplier = 1.0
    return Audio


def preload():
    """Build every sound up front so the first play has no delay."""
    if _audio() is None:
        return
    for name in RECIPES:
        try:
            sound_file(name)
        except Exception:
            logger.exception("Could not build sound %s", name)


def play(name, volume=1.0, pitch=1.0):
    """Play a one-shot effect. Never raises."""
    Audio = _audio()
    if not _enabled or Audio is None:
        return
    try:
        clip = _clips.get(name)
        if clip is None:
            clip = Audio(sound_file(name), autoplay=False, group="sfx")
            _clips[name] = clip
        clip.volume = SFX_VOLUME * volume
        clip.pitch = pitch
        clip.play()
    except Exception:
        logger.exception("Could not play sound %s", name)


def start_music():
    """Start the looping ambient music once. Never raises.

    The first run synthesises the music (a few seconds) on a worker thread so
    the window does not freeze; Ursina's invoke polls until the file exists.
    """
    global _music_requested
    Audio = _audio()
    if _music_requested or Audio is None:
        return
    _music_requested = True
    try:
        from ursina import invoke
    except Exception:
        return

    path = CACHE_DIR / f"music_v{VERSION}.wav"
    if not path.exists():
        threading.Thread(target=preload, daemon=True).start()

    def begin(attempts_left=60):
        global _music
        if not path.exists():
            if attempts_left > 0:  # give up after ~30 s (e.g. disk full)
                invoke(begin, attempts_left - 1, delay=0.5)
            else:
                logger.warning("Music file was never built; playing without music")
            return
        try:
            _music = Audio(path, loop=True, autoplay=False, group="music")
            _music.volume = MUSIC_VOLUME
            if _enabled:
                _music.play()
        except Exception:
            _music = None
            logger.exception("Could not start music")

    begin()


def set_enabled(enabled):
    """Mute or unmute all scene sound."""
    global _enabled
    _enabled = enabled
    if _music is not None:
        try:
            if enabled:
                _music.play()
            else:
                _music.stop()
        except Exception:
            logger.exception("Could not toggle music")


def is_enabled():
    return _enabled
