"""The story of each side. Every line is keyed by the faction the player chose, so the same battle is told from
the defender's side or the attacker's side.

Round lines rotate, so a long run does not repeat itself right away. Milestone rounds have their own lines.
"""

STORY = {
    "human": {
        "title": "THE LAST LINE",
        "tagline": "Hold the road. The Hollow do not stop, and they do not tire.",
        "briefing": [
            "Harrow Gap was the last town with a working radio. Then the Hollow came up the river road, and the "
            "radio went quiet.",
            "You are the garrison. Riflemen, medics and a few guns that still have shells. Behind you is the "
            "bridge, the granary and the people who could not run.",
            "The Hollow walk the road the way water finds a crack. Stop them at the marked route. Every wave is "
            "bigger than the last, and nobody is coming to relieve you.",
            "Build quickly. Hold the line. Count the rounds, not the dead.",
        ],
        "rounds": [
            "The first column is coming up the road. Hold the bridge.",
            "They came in a crowd this time. Keep your riflemen in a tight group.",
            "Runners on the flanks. Do not let them slip past the medics.",
            "Something big is walking behind the front line. Brace the mortars.",
            "The radio crackled once. A voice said the coast was clear. It was not.",
            "Ammunition is running low. Make every shot count.",
            "The granary took a hit. We lost the east field and kept the road.",
            "A flock is overhead. Get the marksmen and the flak up before they drop.",
        ],
        "milestones": {
            5: "The sky has changed. Drones are circling the town, and the Hollow have started to fly.",
            10: "The road has moved. The Hollow dug a new way through the ruins. Rebuild the line where it runs.",
            15: "Fifteen rounds. The garrison is tired, but the people behind the walls are still counting on you.",
            20: "The river is quiet tonight. Hold it one more round.",
        },
        "boss": "The Colonel's ghost rides the front of the column. He held this town once. Stop him again.",
        "overrun": [
            "The Hollow came through the gap. The bridge is gone, but the town is not. Not yet.",
            "The line broke at the granary. The garrison fell back to the church and held it until the end.",
            "Nothing held. The radio is silent, and the road is theirs.",
        ],
    },
    "zombie": {
        "title": "THE HUNGER",
        "tagline": "Walk toward the walls. Every wave ends where it began: in the hungry crowd.",
        "briefing": [
            "The Hollow were the people of Harrow Gap once. The fever took them one at a time, and then all at once.",
            "The Bloom is what remains: a hunger with no end, moving down the river road toward the last town "
            "that still has lights.",
            "You are the Bloom. Spitters, bloaters and the great brutes. Your shamans make the crowd move faster. "
            "Your casters can even reach the sky.",
            "The humans are dug in behind their walls. Break their line, and the Bloom grows.",
        ],
        "rounds": [
            "The Bloom spreads over the field. Walk on.",
            "Pack tighter. The walls remember how many of us they have already stopped.",
            "Runners ahead of the crowd. Let them find the gap.",
            "A brute is coming up the road, and the humans are scared of it.",
            "Their radio is still talking. We can hear it through the walls.",
            "The lights are going out one by one. Keep the crowd moving.",
            "The granary is burning. The Bloom lights the way.",
            "Something is circling overhead. Their drones are watching. Let the casters answer.",
        ],
        "milestones": {
            5: "The humans have taken to the sky. The casters are ready to answer them.",
            10: "The walls have moved. The Bloom goes around them, and it finds the soft ground beneath.",
            15: "Fifteen rounds of hunger. The Bloom has no memory of being tired.",
            20: "The last lights of the town are flickering. Walk on until they go out.",
        },
        "boss": "The Colonel comes out to meet the Bloom in person. Bring the whole crowd to his door.",
        "overrun": [
            "The walls came down. The crowd moves into the streets, and the town is quiet.",
            "The last defenders fell back into the church. The Bloom waits outside until the lights go out.",
            "Nothing left to hunt. The Bloom spreads on down the river road, looking for the next town.",
        ],
    },
}


def briefing(faction):
    """The paragraphs of the opening card for this faction."""
    return STORY[faction]["briefing"]


def tagline(faction):
    return STORY[faction]["tagline"]


def round_line(faction, wave):
    """What the story says at the start of round `wave` (starting at 1)."""
    story = STORY[faction]
    if wave in story["milestones"]:
        return story["milestones"][wave]
    lines = story["rounds"]
    return lines[(wave - 1) % len(lines)]


def boss_line(faction):
    return STORY[faction]["boss"]


def overrun_line(faction, wave):
    """One line for the end of a run. Longer runs get the bleaker ending."""
    lines = STORY[faction]["overrun"]
    if wave < 5:
        return lines[0]
    if wave < 15:
        return lines[1]
    return lines[2]
