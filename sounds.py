import math
import os
import time

import numpy as np
import pygame

# Sound effects are synthesized here, so there are no audio files to ship. The spoken callouts for human
# units are WAV files made once by make_voices.py. Missing files fall back to a chime.

SR = 22050  # Must match the mixer format set up in main.py
HERE = os.path.dirname(os.path.abspath(__file__))
VOICE_DIR = os.path.join(HERE, "sounds", "voices")
RATE_LIMIT = 0.05  # Seconds between two shots of the same unit type: stops a crowd of shots becoming noise
VOLUME = 0.6
GROAN_VARIANTS = 3


# --- SYNTHESIS (pure numpy, no pygame needed) ---

def _time(seconds):
    return np.arange(int(SR * seconds)) / SR


def _noise(n, seed):
    return np.random.default_rng(seed).uniform(-1, 1, n)


def _lowpass(x, cutoff):
    a = 1 - math.exp(-2 * math.pi * cutoff / SR)
    out = np.empty_like(x)
    y = 0.0
    for i, v in enumerate(x):
        y += a * (v - y)
        out[i] = y
    return out


def _sweep(f0, f1, t, decay):
    freq = np.linspace(f0, f1, len(t))
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-decay * t)


def _mix(*parts):
    out = np.zeros(max(len(p) for p in parts))
    for p in parts:
        out[:len(p)] += p
    return out


def _crack(seed, dur=0.12):
    t = _time(dur)
    n = _noise(len(t), seed)
    return (n - _lowpass(n, 1500)) * np.exp(-t * 55)  # Bright, sharp, very short


def _fire_sample(role):
    if role == "rapid":  # Rifle: a crack
        return _crack(1)
    if role == "sniper":  # Long rifle: crack plus a deep boom
        t = _time(0.5)
        return _mix(_crack(2, 0.08), 0.6 * _sweep(120, 50, t, 9), 0.2 * _lowpass(_noise(len(t), 3), 800) * np.exp(-t * 12))
    if role == "splash":  # Grenade launcher: a heavy thump with a pop
        t = _time(0.35)
        return _mix(_sweep(140, 45, t, 11), 0.5 * _lowpass(_noise(len(t), 4), 900) * np.exp(-t * 14))
    if role == "support":  # Medic: a soft two-note chime
        t = _time(0.3)
        return 0.5 * _sweep(880, 1320, t, 9) + 0.2 * _sweep(1760, 2640, t, 14)
    if role == "flame":  # Flamethrower: a rising whoosh
        t = _time(0.5)
        return _lowpass(_noise(len(t), 5), 2500) * (1 - np.exp(-t * 18)) * np.exp(-t * 5)
    if role == "artillery":  # Mortar: a falling whistle
        t = _time(0.4)
        return 0.6 * _sweep(900, 350, t, 4) + 0.1 * _lowpass(_noise(len(t), 6), 1200) * np.exp(-t * 6)
    if role == "flak":  # Flak gun: a sharp rising pop, high and quick
        t = _time(0.25)
        return _mix(0.5 * _sweep(1400, 500, t, 14), _crack(5, 0.25))
    raise ValueError(role)


def _zombie(x, seed):
    """Lower and slower, with a wet gurgle, so zombie shots sound like the other faction."""
    idx = np.arange(int(len(x) / 0.7)) * 0.7
    stretched = np.interp(idx, np.arange(len(x)), x)
    t = np.arange(len(stretched)) / SR
    gurgle = _lowpass(_noise(len(stretched), seed), 400) * np.exp(-t * 5) * 0.5
    return _mix(stretched, gurgle)


def fire_sample(faction, role):
    x = _fire_sample(role)
    return _zombie(x, 9) if faction == "zombie" else x


def groan_sample(seed, dur=1.2, pitch=110):
    """A low, drawn-out groan with vibrato, a falling pitch, and some breath."""
    t = np.arange(int(SR * dur)) / SR
    rng = np.random.default_rng(seed)
    base = pitch * (1 + 0.2 * rng.random())
    freq = base * (1 - 0.3 * t / dur) * (1 + 0.03 * np.sin(2 * np.pi * 5 * t))
    phase = 2 * np.pi * np.cumsum(freq) / SR
    source = sum(np.sin(k * phase) / k for k in range(1, 12))  # Sawtooth-like, like vocal cords
    voice = _lowpass(source, 700) + 0.4 * _lowpass(source, 350)
    envelope = np.sin(np.pi * t / dur) ** 0.6
    breath = _lowpass(_noise(len(t), seed + 7), 2000) * 0.12
    return (voice * 0.5 + breath) * envelope


def flap_sample(faction):
    """Flyers: crows beat their wings in a rustle, drones buzz with their rotors."""
    t = _time(0.3)
    if faction == "zombie":
        beat = 0.5 + 0.5 * np.sin(2 * np.pi * 14 * t)
        return _lowpass(_noise(len(t), 11), 2200) * beat * np.exp(-t * 6)
    phase = 2 * np.pi * 190 * t
    buzz = sum(np.sin(k * phase) / k for k in range(1, 6))
    return _lowpass(buzz, 1500) * np.exp(-t * 4)


def boss_sample():
    """A long, low horn with a second, higher voice, for the arrival of a boss."""
    t = _time(1.6)
    return _sweep(110, 45, t, 1.2) + 0.5 * _sweep(220, 90, t, 1.2) + 0.1 * _lowpass(_noise(len(t), 12), 500)


def combo_sample():
    """A short rising three-note chime: a combo group reached a new tier."""
    parts = []
    for i, freq in enumerate((523, 659, 784)):
        t = _time(0.09)
        parts.append(np.concatenate([np.zeros(int(i * 0.07 * SR)), 0.5 * _sweep(freq, freq, t, 18)]))
    return _mix(*parts)


def cash_sample():
    """Two bright coin clicks: a sale went through."""
    t = _time(0.25)
    first = 0.6 * _sweep(1400, 1400, t, 22)
    second = np.concatenate([np.zeros(int(0.07 * SR)), 0.5 * _sweep(2100, 2100, t, 22)])
    return _mix(first, second)


# --- PLAYBACK ---

def _normalise(x, peak=0.8):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


class Sounds:
    """Turns game events into sound. Does nothing if there is no audio device, so the game still runs."""

    def __init__(self):
        self.enabled = pygame.mixer.get_init() is not None
        self.muted = False
        self.level = 1.0  # Master volume, 0 to 1, set from the keyboard
        self._cache = {}
        self._last_played = {}

    def toggle_mute(self):
        self.muted = not self.muted

    def change_level(self, step):
        self.level = round(min(1.0, max(0.0, self.level + step)), 2)

    def status_text(self):
        if not self.enabled:
            return "NO AUDIO"
        return "MUTED  (M)" if self.muted else f"VOL {round(self.level * 100)}%  (-/= M)"

    def play_event(self, event):
        if not self.enabled or self.muted:
            return
        kind = event[0]
        if kind == "flap":
            _, faction = event
            self._play_limited(("flap", faction), lambda: self._cached(("flap", faction), lambda: _array_sound(flap_sample(faction))))
        elif kind == "combo":
            self._play_limited(("combo",), lambda: self._cached(("combo",), lambda: _array_sound(combo_sample())))
        elif kind == "cash":
            self._play_limited(("cash",), lambda: self._cached(("cash",), lambda: _array_sound(cash_sample())))
        elif kind == "boss":
            self._play_limited(("boss",), lambda: self._cached(("boss",), lambda: _array_sound(boss_sample())))
        elif kind == "fire":
            _, faction, role = event
            self._play_limited(("fire", faction, role), lambda: self._fire(faction, role))
        elif kind == "select":
            _, faction, role = event
            if faction == "zombie":
                self._play_limited(("select", faction), lambda: self._groan(int(time.monotonic() * 10)))
            else:
                self._play_limited(("select", faction, role), lambda: self._voice(role))
        elif kind == "groan":
            self._play_limited(("groan",), lambda: self._groan(int(time.monotonic() * 10)))

    def _play_limited(self, key, make):
        now = time.monotonic()
        if now - self._last_played.get(key, -1e9) < RATE_LIMIT:
            return
        self._last_played[key] = now
        sound = make()
        sound.set_volume(self.level)
        sound.play()

    def _cached(self, key, build):
        if key not in self._cache:
            self._cache[key] = build()
        return self._cache[key]

    def _fire(self, faction, role):
        return self._cached(("fire", faction, role), lambda: _array_sound(fire_sample(faction, role)))

    def _groan(self, variant):
        index = variant % GROAN_VARIANTS
        return self._cached(("groan", index), lambda: _array_sound(groan_sample(index, pitch=90 + 25 * index)))

    def _voice(self, role):
        path = os.path.join(VOICE_DIR, f"{role}.wav")
        if not os.path.exists(path):
            return self._fire("human", "support")  # No voice file yet: a chime instead
        return self._cached(("voice", role), lambda: pygame.mixer.Sound(path))


def _array_sound(x):
    x = np.clip(_normalise(x) * VOLUME * 32767, -32767, 32767).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack([x, x]))
    return pygame.sndarray.make_sound(stereo)
