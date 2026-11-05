import unittest

import story
from game import Game


class StoryContentTests(unittest.TestCase):

    def test_both_factions_have_a_full_story(self):
        for faction in ("human", "zombie"):
            content = story.STORY[faction]
            self.assertTrue(content["title"])
            self.assertTrue(content["tagline"])
            self.assertGreaterEqual(len(content["briefing"]), 3)
            self.assertGreaterEqual(len(content["rounds"]), 6)
            self.assertEqual(len(content["overrun"]), 3)
            self.assertTrue(content["boss"])

    def test_round_lines_rotate_and_milestones_win(self):
        lines = story.STORY["human"]["rounds"]
        self.assertEqual(story.round_line("human", 1), lines[0])
        self.assertEqual(story.round_line("human", 1 + len(lines)), lines[0])
        self.assertEqual(story.round_line("human", 5), story.STORY["human"]["milestones"][5])

    def test_each_faction_tells_its_own_side(self):
        self.assertNotEqual(story.STORY["human"]["title"], story.STORY["zombie"]["title"])
        self.assertNotEqual(story.round_line("human", 2), story.round_line("zombie", 2))

    def test_overrun_line_gets_bleaker_with_longer_runs(self):
        lines = story.STORY["zombie"]["overrun"]
        self.assertEqual(story.overrun_line("zombie", 2), lines[0])
        self.assertEqual(story.overrun_line("zombie", 8), lines[1])
        self.assertEqual(story.overrun_line("zombie", 30), lines[2])

    def test_briefing_is_available_for_both_factions(self):
        for faction in ("human", "zombie"):
            self.assertEqual(story.briefing(faction), story.STORY[faction]["briefing"])


class StoryInGameTests(unittest.TestCase):

    def test_starting_a_round_shows_its_story_line(self):
        game = Game("human")
        game.start_wave()
        self.assertEqual(game.narrative, story.round_line("human", 1))
        self.assertGreater(game.narrative_life, 0)

    def test_the_story_line_fades_out(self):
        game = Game("zombie")
        game.start_wave()
        game._tick_hud(100.0)
        self.assertEqual(game.narrative_life, 0.0)

    def test_a_boss_round_shows_the_boss_line(self):
        game = Game("human")
        game.enemy_faction = "zombie"
        game._spawn("boss")
        self.assertEqual(game.narrative, story.boss_line("human"))


if __name__ == "__main__":
    unittest.main()
