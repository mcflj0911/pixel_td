"""Makes the spoken unit callouts with Windows' built-in speech voice. Run once: python make_voices.py

The files go to sounds/voices/<role>.wav. Needs Windows (System.Speech). The game runs without them.
"""
import os
import subprocess
import sys

LINES = {
    "rapid": "Rifleman, on target",
    "sniper": "Marksman, hold steady",
    "splash": "Grenadier, fire in the hole",
    "support": "Medic, moving up",
    "flame": "Flamethrower, lighting it up",
    "artillery": "Mortar, shells away",
    "flak": "Flak gun, sky's on fire",
}

SCRIPT = (
    "Add-Type -AssemblyName System.Speech;"
    "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer;"
    "$s.Rate = 0;"
    "$s.SetOutputToWaveFile($env:VOICE_OUT);"
    "$s.Speak($env:VOICE_TEXT);"
    "$s.Dispose()"
)


def main():
    if sys.platform != "win32":
        sys.exit("make_voices.py needs Windows (System.Speech). The game still runs without the voice files.")
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds", "voices")
    os.makedirs(out_dir, exist_ok=True)
    for role, text in LINES.items():
        out = os.path.join(out_dir, f"{role}.wav")
        env = dict(os.environ, VOICE_OUT=out, VOICE_TEXT=text)
        subprocess.run(["powershell", "-NoProfile", "-Command", SCRIPT], env=env, check=True)
        print("wrote", out)


if __name__ == "__main__":
    main()
