# Prompt — the piano overlay, found from the black keys

Read @context/implementations/04-synthesia-to-notes/04-plan.md, @context/implementations/04-synthesia-to-notes/04-decisions.md,
@context/implementations/04-synthesia-to-notes/04-phase-2-implementation.md and @context/language/communication-implementation-plans.md
before planning anything. The pictures to work against are the 24 screenshots in @context/implementations/04-synthesia-to-notes/examples,
one per rendering, and the calibration UI to replace is `aitu-frontend/src/components/video/CalibrationEditor.tsx`.

Implementation 04 builds the overlay from a grid: the user places one white key and the app repeats its width across the picture.
That is wrong and it has to go. These videos are not recorded square to the keyboard, so perspective makes one white key wider than
another, and some pianos sit at a slight diagonal. No uniform grid fits either, and no amount of nudging will make one.

Replace the whole of it with **one rectangle**. The user drags it over the piano area — resizable and **rotatable**, so it can take
whatever shape the picture needs — and the piano is static for the whole video, so it is placed once. Everything inside it is found.

Find the **black keys** first. They are the strongest thing in the picture: dark, tall, and grouped in twos and threes. Hands cover
some of them in 17 of the 24 examples, so find enough to fix the pattern, **extrapolate the rest through the occlusion**, and check
the extrapolated pattern back against the pixels before trusting it.

Then derive the **white keys** from them. This is the hard part and it is not one rule: on some pianos a white key border sits at the
midpoint between two black keys and on others it does not — in the picture supplied, F# sits well off the midpoint between F and G.
Find the families of piano these 24 pictures actually use and fit the right one; do not assume symmetry.

A second route is worth measuring against the first: the **thin dark line between two white keys** is narrow but it is there, and
reading those lines gives the white key borders directly instead of inferring them. Measure both over the example set and ship the one
that scores better, with the number beside it (V-20).

This replaces **Story 2.1 of implementation 04 and nothing else**: the detector, the frame window rule, the annotation page, the score
board and Phases 3 to 5 all stand and all read the overlay through the same `Calibration`. That model carries one white key width for
the whole keyboard, so it has to become per-key borders — say what that costs `video/geometry.py`, `overlayGeometry.ts`, the lanes of
V-13 and the white-key-width unit of V-22 before you change it, and keep the two services' geometry check passing.

**V-09 says the app never finds the keyboard by itself and that the user calibrates it.** This work contradicts that frozen decision.
Raise it, have it changed in writing, and do not reinterpret it quietly.

On the screen, `/video/examples` keeps its three steps, but step 1 becomes the one rectangle and the overlay that was found from it.
Every button of the old flow — place the white key, place the black key, render one octave, render the piano, move the piano — goes.
