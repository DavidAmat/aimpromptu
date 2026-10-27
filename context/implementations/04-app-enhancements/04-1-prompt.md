# Context
Read `context/implementations/03-apply-poc-research/03-context.md`. It was the context of the previous implementation in which we finalized porting all the logic that we researched into the current application, so we made several changes to the initial design.

Currently there are several things that we need to polish so we will take this implementation to tackle them

# Sheet

- With Command + Wheel in mac we should be able to make a zoom in so we see the sheet bigger and still make it all fit with the current browser window size.
- Remove the "Enahnced with AI" green badge and put the same symbol as you use next to the song name in the Projects page, when the user hovers over this sign we will see a text saying "Enahnced with AI"
- The floating toolbox that we currently have is great that it is floating, but currently it would be great if it were kind of duplicated so that it is always fixed on the top header of the sheet page next to the "Enahnced with AI" symbol. 
- The cursor that moves whenever we're playing the song (the blue one) should be able to be dragged and dropped. Currently, when we hover over it, there is no kind of mouse selection, and we should allow the user to see a different mouse behavior to make him understand that it can be dragged and dropped. The drag and drop can happen also between lines.
- When we hide the toolbox floating we don't have a way to unhide it

# Transcription logic with the LLM

- See `context/implementations/04-app-enhancements/images/abuse-decoration-notes.png` image. There is a tendency of the LLM to abuse this kind of ornamental notes before a given figure that normaly is a "negra" or a "blanca". We have set some rules about whenever we have a figure whose value is kind of two magnitudes below another figure (for example "negra" is two orders of magnitude above a "semicorchea") we will render it as a decoration note. However, I see a lot of cases in which it is used to mark notes that should not be decoration because, simply, they are part of the rhythm and part of the melody, especially in the right hand. We have an example at `context/implementations/04-app-enhancements/images/abuse-decoration-notes-right.png`. So overall, it's very subtle because whenever we start the song, we define some histogram about the note duration, and we associate a given figure to its note duration. Whatever has a very low duration, we set it as an ornament note. Here, the left hand, it's true that there is a very short note before a long note, so it kind of makes sense. To me, it feels awkward to see these ornaments because normally these ornaments are because of really fast, really short notes, as we do in classical music. What I propose to do is to change them and to use the real value of this figure, and if there is something that is kind of two orders of magnitude above, in terms of the relative difference in the two figures that are consecutive. If we have, for example a "semicorchea" and a "blanca" then make the short note to be at maximum at 2 levels of magnitude from the long note, for example here the "semicorchea" will become a "corchea" since now it will be at 2 levels of magnitude below the "blanca" value, instead of the 3 levels that the "semicorchea" is. This way, we will allow very abrupt changes of figures, and we are not going to use these ornament nodes only if the given node is shorter than a "semicorchea" and it is followed by a note that is 2 orders of magnitude above. This way, all the fast passages that are in "fusas" or "semifusas" will not be rendered as ornament notes. 

I am not asking you to rewrite all of the songs. Do it only for the song "7 years" using Sonnet 5 because this consumes API tokens. 

## Left hand

Sometimes the left hand is not very clear because it has a lot of small variations in a sequence that in theory visually should be uniform. See example `context/implementations/04-app-enhancements/images/left-patterns.png`. This is the case for some passages, for example, in the left hand, in this one, in which we are playing maybe the same chord over and over. Because we are using an algorithm to convert from audio to piano notes, it is possible that there are some minor mistakes. We want the LLM to visually see these mistakes and understand that there are some rules of simplicity.The rules of simplicity should explain that whenever you see a given pattern in a given passage, we should try to keep this pattern. For example, if we are playing chords or we are playing octaves in a given "semicorchea" and some of them are single nodes, and some of them are cores. This is not good because we need some simplicity and some uniformity. This can also apply to the right hand because maybe we're playing an even sequence that's getting repeated, and in some parts it's played with chords. In some parts, it's played with single notes. I'm not telling you to change the single note key placement, I am just saying that maybe if something breaks a given pattern, we should try to convert it so that it fits into something that visually has some symmetry. For example, for the left-hand case, if we put everything with octava chords, it will be very symmetric. Or the LLM can also decide to make just simple notes in the left hand, and we remove all the kinds of octava chords. This is up to the LLM to decide, but we should be really clear that these kinds of small variations on a given pattern can lead to high visual charge to the pianist so that they are not optimal

## Complex fast notes

See `context/implementations/04-app-enhancements/images/complex-fast-notes.png`. So here we have a problem. If we are the pianist, then we need to take a chord that is downwards and then jump very quickly upwards to play the main chord that has the figure with more duration. This is completely unfeasible. We need to think that these kinds of sheets are not to be played by super professional pianists, maybe by a normal amateur pianist. Should be able to do all of these performances and make these kinds of high jumps very quickly, or make invisible transitions of chords implying a lot of jumps to the hand. It's totally unnecessary, and this is one of the cases of seeing a totally unnecessary ornament chord that happens before a given "negra" chord, so there is no need to play this octava chord, and the LLM should be knowledgeable about this and should be smart enough to decide to simplify it to only put the "Sol-3" and ignore the "Sol-2"

# Answers of the first discussion (2026-10-27)

Asked by the agent after reading the code; the plan ([`04-plan.md`](04-plan.md) section 3) builds on them.

1. **The decoration-note rule.** Only a note shorter than a semicorchea (fusa or shorter), one or two of them, just
   before a note at least two figures longer, is a decoration note. Any other lone short note just before a much
   longer note is written as a real note, at most two figures shorter than that note (a semicorchea before a blanca
   becomes a corchea). A run of three or more fast notes stays written as today, and its last note is **not**
   lengthened: only the lone notes are.
2. **Where the rule applies.** The rule is the app's own calculation (no AI call, no credits): **every sheet, now**,
   also the sheets the AI already enhanced, when the app draws them. The user's switches (always / never a decoration
   note) still win.
3. **Notes the AI adds or leaves out** (uniform patterns, quick chords): kept **as Enhance with AI of a stretch** does
   it: the notes left out are marked removed in `notes.pmn`, the notes added are written there, within limits that a
   check enforces.
4. **Which "7 Years".** The **My library version** (`7 Years — Lukas Graham`), after a test on a temporary copy.

# Request after the Phase 3 gallery (2026-10-27)

In the user's words:

> LOVE IT! the "Now" decisions taken by the AI agent are SUPERB! I really love them! What we should do is have a kind
> of button. Whenever we click on "Enhance with AI," we should open a dialog in which we have the current option of
> enhancing the given selected range and giving a prompt. We should also have the option if we don't select a given
> range.
> - If we select a given time range, we can select either both the right and the left hand, or only the right, or
>   only the left.
> - If we don't select anything and click "Enhance AI," we can have one section or one tab of this dialog box.
>   Instead of writing the free prompt, we say something like "Simplify Left" or "Simplify Right" or "Simplify Both"
>   and it will do the different batches and will start simplifying. It is important that whenever it does some
>   batches, they can be more lengthy because now we are only feeding one single hand, and what we must do is to
>   give some context of the previously converted regions so that it sees what kind of decisions we used to simplify
>   the previous time ranges. If it detects any pattern, anything that we repeat, it uses the same simplification as
>   we used before. It's really important to make this in a kind of auto-regressive way. Even though we do batches of
>   time frame ranges, we do it auto-regressively so that any enhancement that we have done in the past will be
>   visible in the context of the LLM that does the following batch.

Answers (the plan, section 3.5, builds on them):

1. **Order**: finish Phase 3 first (the real 7 Years run, the browser check); the dialog is a new Phase 4.
2. **Simplify**: the rules of simplicity only (uniform patterns, the amateur pianist), as prompt 6 did on 7 Years.
3. **Write it all again** (today's full run) stays in the dialog next to the three Simplify choices.
4. **A stretch of one hand**: the other hand stays exactly as it is.

