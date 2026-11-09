import math
import os
import time
import zlib

import numpy as np
import pygame

from config import COMBO_KIT

# Sound effects are synthesized here, so there are no audio files to ship. The spoken callouts for human
# units are WAV files made once by make_voices.py. Missing files fall back to a chime.

SR = 22050  # Must match the mixer format set up in main.py
HERE = os.path.dirname(os.path.abspath(__file__))
VOICE_DIR = os.path.join(HERE, "sounds", "voices")
RATE_LIMIT = 0.05  # Seconds between two shots of the same unit type: stops a crowd of shots becoming noise
VOLUME = 0.6
GROAN_VARIANTS = 3
SHOT_PITCHES = (0.96, 1.0, 1.04)  # Each unit has three slightly different shots, so rapid fire does not buzz
FADE_IN = 0.004  # Seconds of ramp at each end, so no sound starts or stops with a click
FADE_OUT = 0.03
RMS_TARGET = 0.13  # Loudness is matched by average level, so a deep boom and a crack sit at a similar volume
PEAK_CEILING = 0.9  # Peaks above this are softly limited instead of clipping


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
    if role == "rocket":  # Rocket: a hiss that climbs away, with a short kick at the launch
        t = _time(0.45)
        hiss = 0.4 * _lowpass(_noise(len(t), 13), 1800) * (1 - np.exp(-t * 40)) * np.exp(-t * 7)
        return _mix(0.5 * _sweep(260, 700, t, 6), hiss, _crack(14, 0.06))
    raise ValueError(role)


def _repitch(x, factor):
    """Shift the pitch by `factor` (above 1 is higher). The length changes with it, as with tape speed."""
    idx = np.arange(int(len(x) / factor)) * factor
    return np.interp(idx, np.arange(len(x)), x)


def _zombie_fire_sample(role):
    """The zombie shots are their own sounds, not the human ones pitched down: wet spits, lobs and sprays."""
    if role == "rapid":  # Spit: a fast glob that drops in pitch, with bubbles breaking on it
        t = _time(0.2)
        return _mix(0.5 * _sweep(420, 160, t, 14), 0.6 * _lowpass(_noise(len(t), 21), 900) * np.exp(-t * 18))
    if role == "sniper":  # Lob: a heavy wet thump that wobbles as the glob tumbles through the air
        t = _time(0.6)
        wobble = 1 + 0.35 * np.sin(2 * np.pi * 9 * t)
        return _mix(0.7 * _sweep(170, 55, t, 6) * wobble,
                    0.3 * _lowpass(_noise(len(t), 22), 500) * np.exp(-t * 5))
    if role == "splash":  # Bloat: a squelch that pulses, then a wet pop
        t = _time(0.4)
        squelch = _lowpass(_noise(len(t), 23), 350) * (0.5 + 0.5 * np.sin(2 * np.pi * 22 * t)) * np.exp(-t * 7)
        return _mix(0.7 * squelch, 0.5 * _sweep(260, 90, t, 22))
    if role == "support":  # Shaman: a low moan with a wavering pitch and a rough second voice
        t = _time(0.7)
        phase = 2 * np.pi * np.cumsum(150 + 6 * np.sin(2 * np.pi * 5.5 * t)) / SR
        env = (1 - np.exp(-t * 15)) * np.exp(-t * 3)
        return 0.5 * (np.sin(phase) + 0.4 * np.sin(2 * phase)) * env
    if role == "flame":  # Bile spray: a wet hiss over a bubbling gurgle
        t = _time(0.5)
        hiss = _lowpass(_noise(len(t), 24), 3200) * (1 - np.exp(-t * 30)) * np.exp(-t * 4) * 0.5
        gurgle = _lowpass(_noise(len(t), 25), 300) * (0.5 + 0.5 * np.sin(2 * np.pi * 12 * t)) * np.exp(-t * 3) * 0.4
        return _mix(hiss, gurgle)
    if role == "artillery":  # Spore mortar: a thump, then a spore pop and a hiss trailing off
        t = _time(0.45)
        pop = _lowpass(_noise(len(t), 26), 1200) * np.exp(-t * 40) * 0.9
        tail = _lowpass(_noise(len(t), 27), 2000) * np.exp(-t * 10) * 0.2
        return _mix(0.8 * _sweep(120, 40, t, 9), pop, tail)
    if role == "flak":  # Spore caster: a soft puff with a small bloop under it
        t = _time(0.25)
        puff = _lowpass(_noise(len(t), 28), 600) * np.sin(np.pi * np.minimum(t / 0.25, 1)) * 0.6
        return _mix(puff, 0.4 * _sweep(330, 220, t, 10))
    if role == "rocket":  # Colony launch: a rising squelch with a wet crackle at the start
        t = _time(0.5)
        rise = 0.4 * _sweep(180, 520, t, 4)
        squelch = _lowpass(_noise(len(t), 29), 700) * (0.4 + 0.6 * np.abs(np.sin(2 * np.pi * 16 * t)))
        return _mix(rise, 0.5 * squelch * (1 - np.exp(-t * 25)), _crack(30, 0.06))
    raise ValueError(role)


def _combo_shot(faction, combo):
    """A combined unit's own shot, from its kit: a pitch that slides, wavers and rattles, with a hiss on top.
    The hiss is seeded from the combination's name, so each combination has its own noise."""
    p = COMBO_KIT[faction][combo]["sound"]
    t = _time(p["length"])
    wobble_rate, wobble_depth = p["wobble"]
    freq = np.linspace(p["tone"][0], p["tone"][1], len(t)) * (1 + wobble_depth * np.sin(2 * np.pi * wobble_rate * t))
    tone = np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-p["decay"] * t)
    hiss = _lowpass(_noise(len(t), zlib.crc32(combo.encode())), 3000) * np.exp(-p["decay"] * t) * p["noise"]
    env = np.ones(len(t))
    if p["pulses"]:  # Rattles: the level dips and swells this many times over the shot
        env = 0.55 + 0.45 * np.cos(2 * np.pi * (p["pulses"] / p["length"]) * t)
    return (tone + hiss) * env


def fire_sample(faction, role, variant=0, combo=None):
    """The shot for a unit. `variant` picks one of the SHOT_PITCHES, so repeated shots differ a little. A combined
    unit (`combo` is its recipe id) has its own shot, instead of the sound of its role."""
    if combo:
        base = _combo_shot(faction, combo)
    elif faction == "zombie":
        base = _zombie_fire_sample(role)
    else:
        base = _fire_sample(role)
    return _repitch(base, SHOT_PITCHES[variant % len(SHOT_PITCHES)])


def death_sample(faction):
    """An enemy falling. Zombies collapse with a last wet gurgle; humans give a short cry and a thud."""
    if faction == "zombie":
        t = _time(0.7)
        fall = 0.5 * _sweep(200, 50, t, 3)
        gurgle = _lowpass(_noise(len(t), 31), 400) * np.exp(-t * 4) * 0.6
        return _mix(fall, gurgle)
    t = _time(0.5)
    cry = 0.4 * _sweep(520, 260, t, 5)
    thud = _lowpass(_noise(len(t), 32), 300) * np.exp(-t * 12) * 0.4
    return _mix(cry, thud)


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


def charged_sample():
    """A bright two-step rising ping: a unit's charge is full and its next shot will be a charged attack."""
    up = np.concatenate([_sweep(660, 660, _time(0.07), 14), _sweep(990, 990, _time(0.12), 10)])
    return 0.45 * up


def cash_sample():
    """Two bright coin clicks: a sale went through."""
    t = _time(0.25)
    first = 0.6 * _sweep(1400, 1400, t, 22)
    second = np.concatenate([np.zeros(int(0.07 * SR)), 0.5 * _sweep(2100, 2100, t, 22)])
    return _mix(first, second)


# --- PLAYBACK ---

def _finish(x):
    """Fade the ends so the sound starts and stops in silence."""
    x = np.array(x, dtype=float)
    n_in = min(int(SR * FADE_IN), len(x))
    x[:n_in] *= np.linspace(0, 1, n_in)
    n_out = min(int(SR * FADE_OUT), len(x))
    if n_out:
        x[-n_out:] *= np.linspace(1, 0, n_out)
    return x


def _level(x):
    """Match the average level to RMS_TARGET, then soften any peak that would clip."""
    rms = np.sqrt(np.mean(x ** 2)) if len(x) else 0.0
    if rms > 0:
        x = x * (RMS_TARGET / rms)
    peak = np.max(np.abs(x)) if len(x) else 0.0
    if peak > PEAK_CEILING:
        x = np.tanh(x / PEAK_CEILING) * PEAK_CEILING
    return x


class Sounds:
    """Turns game events into sound. Does nothing if there is no audio device, so the game still runs."""

    def __init__(self):
        self.enabled = pygame.mixer.get_init() is not None
        self.muted = False
        self.level = 1.0  # Master volume, 0 to 1, set from the keyboard
        self._cache = {}
        self._last_played = {}
        self._shots = {}  # How many shots each (faction, role) has fired, to rotate the variants

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
        elif kind == "charged":
            self._play_limited(("charged",), lambda: self._cached(("charged",), lambda: _array_sound(charged_sample())))
        elif kind == "boss":
            self._play_limited(("boss",), lambda: self._cached(("boss",), lambda: _array_sound(boss_sample())))
        elif kind == "death":
            _, faction = event
            self._play_limited(("death", faction), lambda: self._cached(
                ("death", faction), lambda: _array_sound(death_sample(faction))))
        elif kind == "fire":
            _, faction, role, *rest = event
            combo = rest[0] if rest else None
            self._play_limited(("fire", faction, role, combo), lambda: self._fire(faction, role, combo))
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

    def _fire(self, faction, role, combo=None):
        key = (faction, role) if combo is None else (faction, role, combo)
        count = self._shots.get(key, 0)
        self._shots[key] = count + 1
        variant = count % len(SHOT_PITCHES)
        return self._cached(("fire", faction, role, combo, variant),
                            lambda: _array_sound(fire_sample(faction, role, variant, combo)))

    def _groan(self, variant):
        index = variant % GROAN_VARIANTS
        return self._cached(("groan", index), lambda: _array_sound(groan_sample(index, pitch=90 + 25 * index)))

    def _voice(self, role):
        path = os.path.join(VOICE_DIR, f"{role}.wav")
        if not os.path.exists(path):
            return self._fire("human", "support")  # No voice file yet: a chime instead
        return self._cached(("voice", role), lambda: pygame.mixer.Sound(path))


def _array_sound(x):
    x = np.clip(_level(_finish(x)) * VOLUME * 32767, -32767, 32767).astype(np.int16)
    stereo = np.ascontiguousarray(np.column_stack([x, x]))
    return pygame.sndarray.make_sound(stereo)
