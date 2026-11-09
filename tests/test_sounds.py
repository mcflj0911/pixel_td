import unittest
from unittest import mock

import numpy as np

from config import ROLES
from game import Game
from sounds import PEAK_CEILING, RMS_TARGET, SHOT_PITCHES, Sounds, _finish, _level, fire_sample, groan_sample


class SynthesisTests(unittest.TestCase):

    def test_every_role_has_a_clean_shot_sound(self):
        for role in ROLES:
            x = fire_sample("human", role)
            self.assertTrue(np.all(np.isfinite(x)), role)
            self.assertGreater(np.max(np.abs(x)), 0.01, role)

    def test_each_unit_sounds_different(self):
        samples = {role: fire_sample("human", role) for role in ROLES}
        for a in ROLES:
            for b in ROLES:
                if a < b:
                    n = min(len(samples[a]), len(samples[b]))
                    self.assertGreater(np.abs(samples[a][:n] - samples[b][:n]).mean(), 0.01, f"{a} vs {b}")

    def test_zombie_shots_differ_from_human_shots(self):
        for role in ROLES:
            human = fire_sample("human", role)
            zombie = fire_sample("zombie", role)
            self.assertGreater(len(zombie), len(human) * 0.9, role)  # Stretched, so longer
            self.assertFalse(np.allclose(human[:200], zombie[:200]), role)

    def test_groans_are_low_and_long(self):
        groan = groan_sample(0)
        self.assertGreater(len(groan), 20000)  # More than a second at 22 kHz
        self.assertTrue(np.all(np.isfinite(groan)))
        self.assertGreater(np.max(np.abs(groan)), 0.05)

    def test_groan_variants_differ(self):
        self.assertFalse(np.allclose(groan_sample(0)[:500], groan_sample(1)[:500]))


class ShapingTests(unittest.TestCase):

    def finished_samples(self):
        for role in ROLES:
            yield role, _level(_finish(fire_sample("human", role)))
            yield role + " zombie", _level(_finish(fire_sample("zombie", role)))

    def test_every_sound_starts_and_ends_in_silence(self):
        for name, x in self.finished_samples():
            self.assertLess(abs(x[0]), 1e-6, name)
            self.assertLess(abs(x[-1]), 1e-6, name)

    def test_every_sound_is_at_the_same_average_level(self):
        for name, x in self.finished_samples():
            rms = np.sqrt(np.mean(x ** 2))  # Sharp cracks are softly limited, so they can sit a little under the target
            self.assertLessEqual(rms, RMS_TARGET + 1e-9, name)
            self.assertGreater(rms, RMS_TARGET * 0.85, name)

    def test_no_sound_peaks_above_the_ceiling(self):
        for name, x in self.finished_samples():
            self.assertLessEqual(np.max(np.abs(x)), PEAK_CEILING + 1e-9, name)

    def test_shot_variants_differ(self):
        for role in ROLES:
            variants = [fire_sample("human", role, v) for v in range(len(SHOT_PITCHES))]
            self.assertFalse(np.allclose(variants[0][:300], variants[1][:300]), role)
            self.assertFalse(np.allclose(variants[1][:300], variants[2][:300]), role)

    def test_shots_rotate_through_the_variants(self):
        sounds = Sounds()
        with mock.patch("sounds._array_sound", side_effect=lambda x: object()) as make:
            for _ in range(4):
                sounds._fire("human", "rapid")
        self.assertEqual(make.call_count, len(SHOT_PITCHES))  # Four shots, three variants built once each
        self.assertEqual(sounds._shots[("human", "rapid")], 4)


class EventTests(unittest.TestCase):

    def test_firing_units_emit_fire_events(self):
        game = Game("human")
        game.gold = 500
        game.place(5, 0, "rapid")  # Row 0 runs beside the first lane of the classic map
        game.place(6, 0, "flame")
        game.start_wave()
        for _ in range(200):
            game.update(0.05)
        events = game.drain_sounds()
        fires = {(e[1], e[2]) for e in events if e[0] == "fire"}
        self.assertIn(("human", "rapid"), fires)

    def test_selecting_a_unit_emits_a_select_event(self):
        game = Game("zombie")
        game.gold = 500
        game.place(5, 0, "support")
        game.drain_sounds()
        game.click_cell(5, 0)
        self.assertEqual(game.drain_sounds(), [("select", "zombie", "support")])

    def test_zombie_enemies_groan(self):
        game = Game("human")  # Enemies are zombies
        game.start_wave()
        for _ in range(100):
            game.update(0.05)
        self.assertIn(("groan",), game.drain_sounds())

    def test_drain_empties_the_queue(self):
        game = Game("human")
        game.start_wave()
        game.update(0.05)
        game.drain_sounds()
        self.assertEqual(game.drain_sounds(), [])


class PlaybackTests(unittest.TestCase):

    def test_silent_without_an_audio_device(self):
        sounds = Sounds()  # pygame.mixer is not initialised in the tests
        self.assertFalse(sounds.enabled)
        sounds.play_event(("fire", "human", "rapid"))  # Must not raise


if __name__ == "__main__":
    unittest.main()
