import unittest

import numpy as np

from config import ROLES
from game import Game
from sounds import Sounds, fire_sample, groan_sample


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
