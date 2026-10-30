"""The music analysis of the whole song simplification by levels (implementation 04-3, Phase 3): no AI here.

* ``grid``: the grid of the song, the times where a new note of a level may start (the negras the pulse finds, their
  divisions, and the onsets of the original notes);
* ``harmony``: the chord of each stretch of the song, from the notes (the harmony a level keeps);
* ``hands``: how hard a passage is to play, per hand: the research's hand tracker (an open hand of one octave that
  moves only when a note is out of reach) on the app's frames, and the measures of a level (notes per second, chords,
  spans, moves per second, the pattern that repeats).

The AI side (the prompts of each level, the plan of the song, the check of an answer) is ``sheet.llm.levels``.
"""
