# AImpromptu

This project is a ambitious project that aims to receive any URL from YouTube of a given video of a piano only being played OR simply receive an upload of a .mp3 or .aac or .m4a file of a recording in a mobile phone or any recording of music and convert it into a music score. The particularity of this music score is that it is a HTML file, this means that any browser can open it and the display of the music notation depends on the screen width, so that the music is not on a pdf. Plus, we can make annotations on top of the music score, put the lyrics, etc... 

Everything is standardized in a new numerical format for encoding notes onsets and note sounding. This format is basic in the sense that it does not meant to reproduce exactly the same format as the MIDI file or the MP3 sound, but it is a simplistic representation of the music played by a piano so that the resulting piano sheet is clear, minimalist and simple to read. Most of the current softwares that create a piano sheet are very sensitive to note durations, creating very cluttered piano sheets of notes sounding during many long. I propose a new methodology that first samples time in a very fine-grained way, and then we start collapsing temporal granularity into a more broad time buckets so that the final piano sheet is not as cluttered as the fine-grained one.


# The new notation

Whenever we receive a .mp3 file, there are python libraries that convert this file into a kind of midi file.

We want to convert this kind of Midi files format into a sparse matrix format.

Since music is not only about onset of a note but also the duration of it, we to know when a note was pressed (onset) and when a note keeps sounding and when it stops (sustain)

For all the details read the `context/music/notation-logic/01-matrix-notation-logic.md`, read the terminology clarification appendix too:

Whenever a note starts an onset (appears a `1` in the matrix) we can either find in the next column:
- another `1`: meaning that the note is not sustained, but released and pressed again, so its a new sudden onset
- a `0`: this is like a "pizzicato" the note is onset but very quickly released so that next time frame it does not sound
- a `-1`: this is a sustained. This is what marks what is the value of the note in the piano sheet (if it is a "negra", a "corchea", etc.)

## State transitions

For a given row (a given piano key) treat the temporal sequence (one time step is one column of the matrix) as a Markov state. These states are either 0, 1 or -1. Transition rules are:
It is impossible and should NEVER be allowed to see a sequence like [0, -1] or [0, -1, 0] because the allowed transitions states are:
- initial state: [0] -> we can only go to a 0 or a 1 state
- onset state: [1] -> we can either sustain (-1), do another onset of that note (1) or silence that note (0)
- sustain [-1] -> we can go to another onset of that note (1), we can go to a silence (0) or we can keep the sustain of that note (-1)


## Temporal Granularity
A very simple example is:
```m
At 60 BPM, one negra = 1 second.

| Note | Beats | Duration |
|------|-------|----------|
| Negra | 1.0 | 1 s |
| Corchea | 0.5 | 0.5 s |
| Semicorchea | 0.25 | 0.25 s |
| Fusa | 0.125 | 0.125 s |
| Semifusa | 0.0625 | 0.0625 s |
```

So if we set the time step between columns duration to 0.5 seconds (`timeStepSeconds = 0.5`) and the BPM = 60, this means that 1 single column represents 0.5 seconds as stated by `timeStepSeconds`, which in terms of notes, it means that Corchea (Duration = 0.5s) is the maximum granularity note that we can represent with a `timeStepSeconds = 0.5` and `BPM=60`. This is what we mean by **temporal granularity**, which depending on how granular will be the onsets of the note, we will not be able to catch that granularity if we dont make the `timeStepSeconds` smaller.

We will always make the `timeStepSeconds` into something that is proportional to the `Duration` column. Sometimes the user will simply say, I want to set the temporal granularity as "Fusas", which by default you will assume a BPM=60 (if not specified), so the `timeStepSeconds=0.125` will be automatically set just by mentioning that note duration each column should represent.

This way if we assume a granularity of "fusas" we can write the following matrix notation sounding in a single key (single row) of this matrix as:

### Single note sounding
```
Fusa: 1 0 0 0 0 (1 onset, no sustain because we are in the granularity of Fusas)
Semicorchea: 1 -1 0 0 0 (1 onset, one sustain to indicate that the note duration is 0.25 seconds)
Corchea: 1 -1 -1 -1 (1 onset, 3 sustains, so that it indicates the duration is 0.125 s for the onset + 3 x 0.125 s for the sustan, which is a total of 0.5s)
```

### Two notes sounding consecutively without any silence between them

```
Fusa: 1 1 0 0 0 (2 onsets consecutively)
Semicorchea: 1 -1 1 -1 0 0 0 (1 onset and 1 sustain for the first Semicorchea, and thne we do again 1 onset and 1 sustain for the next consecutive semicorchea)
Corchea: 1 -1 -1 -1 1 -1 -1 -1 (1 onset and 3 sustains, and then 1 onset and 3 sustains again)
```

### Two notes sounding but a silence of semicorchea is between them
In this setting, a silence of semicorchea means that two columns (since one column is at fusa temporal granularity) span the temporal duration of a semicorchea. Silences are 0's so:

```
Fusa: 1 0 0 1 0 (2 onsets, separated by two 0's that indicate the silence of a semicorchea)
Semicorchea: 1 -1 0 0 1 -1 0 0 0 
Corchea: 1 -1 -1 -1 0 0 1 -1 -1 -1
```

Remember this is just 1 single ROW of the matrix (1 row represents 1 key). We will need to do this for all the keys

With this you need to find a super efficient way to convert any midi format file into this kind of matrix formulation.

Since there are a lot of 0's we recommend sparse formatting.

## Collapsing temporal resolution

Timings are never perfect. Specially in recordings where a person is performing, the durations of notes or the sustains may not be clearly specified.

Temporal resolutions are treated as a **hierarchy**:
- We will order the music figures from a  **high hierarchy** to a **lower hierarchy** (considering a lower hierarchy those notes that are faster in time like the Semifusa):
    - 1st) Redonda (highest hierarchy note)
    - 2nd) Blanca
    - 3rd) Negra
    - 4th) Corchea
    - 5th) Semicorchea
    - 6th) Fusa
    - 7th) SemiFusa (lowest hierarchy)
    (we will not allow more granularity)

This is why we will need to first encode a given midi music with the highest hierarchy (Semifusa level). Then if the user wants the temporal granularity to be Fusa level, we will need to compress that matrix. For example, we will need to merge 2 columns into a single column to pass from Semifusa level to Fusa level of granularity. 

There should be **rules** in what to do when merging:

### Merging rules

The merging of the different temporal resultions must be done sequentially (from a Fusa temporal granularity we can only merge into a Semicorchea one, and then from Semicorchea we can merge into Corchea one). There are no rules to merge from a two step away note (i.e from a Semicorchea to a Negra, we need to do Semicorchea -> Corchea -> Negra).

These merging rules applies only when going from a fine-grained temporal resolution to a more coarse one, it does not apply for "upsampling" resolutions rules (we will not apply these merging rules for changes from a Negra temporal resolution to a Corchea temporal resolution matrix). 

So these rules apply for each hierarchy, we will need to go 1 step at a time (i.e from 7th to 6th, from 6th to 5th, etc) in the hierarchy.
For example if the initial transcription is at 7th hierarchy and I want to simplify the music at the 4th hierarchy (Corchea) we need to apply the merge rules:
- 7 -> 6: apply merge rules here (the number of columns in the matrix will go from X to X//2)
- 6 -> 5: apply merge rules here (the number of columns in the matrix will go from X//2 to X//4)
- 5 -> 4: apply merge rules here (the number of columns in the matrix will go from X//4 to X//8)
So every transition in the hierarchy we do in merging, we are doing a division by 2 on the number of columns so we are simplifying the matrix and the `timeStep` we are doubling its duration (keeping the BPM as it is). 

**The merging rules**:
- [1,1]: two consecutive onsets will get merged as a single onset -> [1]
- [1,0]: one onset and a silence will get merged as a single onset -> [1]
- [1, -1]: one onset and a release will get merged as a single onset -> [1]

- [0,1]: merged as a singel onset [1]
- [0, 0]: merged as a single silence [0]
- [0, -1]: this is an impossible state
- [-1, 0]: merged as a released still note [-1]
- [-1, 1]: merged as a single onset [1]
- [-1, -1]: merged as a single sustain [-1]

In the moment in which we are merging to a more coarse-grained temporal granularity, we are losing some information that it makes impossible to revert in a reverse process.

This is why the only possible way to go from a 4th hierarchy to a 5th hierarchy for example will be a simple upsampling rule:
- [0]: a silence is converted into two [0,0]
- [1]: an onset is simply sustained: [1, -1]
- [-1]: a sustain is kept sustained [-1, -1]

 
## From audio to matrix
We must find the most efficient Python library that can process an audio file, either if we are in format mp3, aac, m4a, and many more. 
We will identify the format of the audio file by the suffix of the file 
Otherwise, in the web app we will allow having a "Capture Audio" feature that we will record using our microphone of the given device we are using in that web app to record.
Ideally, once recording, we would like to see in the UI the wavefront similar to what SoundCloud does (similar to a barplot plot) to simplify the display of how we are recording the audio and detecting when we did high intensity sounds and when we did lows. This is purely UI feature.
The audio should be stored locally in local storage path. If we decide in the future (this is just a POC) that we will containerize this service of the storage, we can create a MinIO bucket container that takes a given path of the hosting machine and stores there the raw audios until they get processed.
Currently, there are other ways in which we pass the input notes, and it's our textual notation that we have (see `context/music/notation-logic/02-notation-spec.md.md`). This notation is only used to visualize in the UI how the rendering of several notes is produced, but it is very cumbersome to use it for long sequences of piano notes in long temporal frames.

### [raw] Raw midi-like (matricial) format
Once we convert the audio file into our desired format which captures for each key what is the onset in terms of time when it was produced and the duration of each note, we can convert this into a matricial format. 

The first matricial format will always be on the maximum granularity as possible (fusa) (see `context/music/notation-logic/01-matrix-notation-logic.md`). We will put in this raw format all the piano sounds exactly as they are transcribed. This is the raw midi-like format, in which we will put as 0,1,-1 sparse matricial format all the events. Here it is really important to understand how to turn the moments in which a note is pressed into a given discrete temporal range in which we play with the `timeStepSeconds` and the `BPM` provided as inputs for this transcription. It is really important to apply roundings at the right granularity, for example:

```text
C3 -> onset at 00:00 (duration 1.1 seconds)
C4 -> onset at 00:01.5 (duration 0.6 seconds)
```

If we are at BPM = 60 (1 negra per second) and imagine temporal granularity is  semicorchea (4 semicorcheas = 1 negra, 1 semicorchea lasts 0.25 seconds) we will collapse the 1.1 seconds into the nearest

### [collapsed] Temporal collapsing matricial format

Then we will let the user define which is the temporal granularity it wants. So if we always start with the "fusa" temporal granularity, we can aggregate (merge) temporal columns in the matrix to form the new coarse temporal matrix by merging columns with the specified rules. The final matrix will have less columns due to the collapsing. We recommend still using the right sparse matricial format here.

### [clean] Cleaning matricial format
Finally, the matricial format will undergo a cleaning. See Appendix B of `context/music/notation-logic/01-matrix-notation-logic.md` on how we will avoid having sustained notes while other notes keep sounding. We will simplify a lot the matrix representation to avoid quick notes (like fusas, semicorcheas, etc...) flood the piano sheet with lots of useless ligatures or extensions of a given sustained note with these short sounding notes. This is why in Appendix C in `context/music/notation-logic/01-matrix-notation-logic.md` we detailed how this piano notation matrix should be cleaned.

### [two-hands] Converting the cleaned matricial format into two matrices
We will split the piano matrix into two sparse matrices. Read `APPENDIX D: Two hands` in `context/music/notation-logic/01-matrix-notation-logic.md`. We will start with a simple dummy logic.

Whenever we separate the clean matrix into two matrices, we must ensure both resulting matrices have the same format (same number of rows and columns) as the clean one. Separating does not mean cutting the matrix, it simply means that we will duplicate the clean matrix into two exact replicas, and for the right hand we will zero-out all the rows that correspond to notes below the C4 (the key acting as a threshold to decide the hand) and for the left we will zero out all the rows that correspond to notes in the C4 row or above.

### Full audio to matrix process

This means that when we receive an audio we go to a process of:
- audio to raw
- raw to collapsed
- collapsed to clean
- two-hands

It is really important to make sure that at any moment we can come back to a different collapsed granularity, for example, if we want to collapse to a "negra" temporal granularity. This is why such process of converting the audio to such kind of matricial format, should be something super quick in terms of latency.

We will always keep the clean full matrix as well as the two-hands. This is because the two-hands is useful when we start translating notes into piano notation to be displayed as piano sheets that will have the two hands format. This means that the function that will convert a given piano matrix notation into the music notation will receive separately both hands matrices, which will be treated independently and rendered one above the other (right hand goes with *treble clef* and left goes with *bass clef* by default). However, we will have the option to render the music in a "single hand" UI (only transcribing the clean matrix) either for debugging purposes or becaue there will be some songs we transcribe that will be played only by 1 hand.

# Web App UI Features

During the implementation of this project there will be a lot of testing, debugging, try and error, dummy POCs, testing on some custom-made piano audio notes that I will play in piano to see how it is rendered, etc...

We will have several sections in the app and several visualization modes within each section that are worth organizing well.

## YouTube to Audio

We will have one tab that will allow the user pasting a youtube url of a video and be able to download its audio using youtube-dl in Python (via the backend). This package normally has limits to avoid people scraping YouTube but hope we won't hit the limits since it is just manual single user (me) that will download the videos one by one.

The resulting audio should be in the maximum quality possible and saved as mp3 if possible, and stored in our storage bucket. For that URL we will let the user input a given `file name` so that apart from creating a random uuid folder we will have as metadata in that storage bucket the file name for that song. For example for the song `Levels - Avicii` this can be the file name although the folder where all the artifacts that contain this song has a uuid generated name. This lives inside this uuid folder in the `metadata.json` file. Of course this metadata will always be editable. 

Nice to have, in the future we will enable batching of downloads, in the sense that we will be able to put a collection of URLs and names (of the file names) and we will basically download them all sequentially.


## Playground


### Upload / Input tab
This will allow the user to do multiple actions like:
- upload a audio file
- record audio (using the browser capabilities to record audio using the device microphone) -> saving it into a temporal location of the backend server or in the case of a MinIO container in a bucket. there will be the option to name these audio files and store them in your personal library of audios. This way in the playground we can also have a "load from library" to load an audio from library if we have some predetermined audios of specific pieces (i.e a piece that is the C major scale for example with both hands)
- textual notation: by providing the textual notation (see Text notation in `context/music/notation-logic/02-notation-spec.md`)
- json: we will see that in the Matrix tab we will allow downloading the matricial form on a given step (i.e raw, cleaned, etc) as a json with metadata and the actual matrix. 

Sometimes we may want to upload an audio file but only select a given range of time. So, enable one stage in which after selecting the audio file and having the length, we have a kind of temporal line in which two moving selectors will be there, we will be able to select the range by moving them (on top of the selector we will see the time). The user can manually put the starting time (i.e `03:03.123`) and ending time (i.e `03:06.28`), and we will only load into a matrix this segmented part, not the full audio. This is very useful to test different parts of a music piece that we know the way the piano sheet should look like, we load the entire measure there, and we render it to see how close it gets to the real one, and from there iterate. Ideally it will be a super good user experience if we can see like `Audacity` does, in which we see the entire waveform of a given audio file, and once we select that range, we are able to play it (only that range) and see a cursor advancing as the time goes through and stopping at the edge of the final selection of that range. We can also play the full audio file once uploaded. 

In the case of audios files or recorded audios, we will need let the user input the BPM and the temporal resolution (dropdown with already defined options like "Negra", "Corchea", "SemiCorchea" and "Fusa"). By default remember that all the audios files will be processed to a "Fusa" granularity level first (raw matrix) before collapsing into the final chosen temporal resolution the user wants.

### Matrix tab

Once selected the audio or the textual notation, we will convert this into the matricial form in the different piano matrices we have already explained (raw, collapsed, clean and two-hands). In order to visualize this we will have 1 sub-tab per each format. So, for example for the `raw` matricial format we will have a UI that will:
- show as columns the names of the piano letters (i.e C3) in English abbreviated format but also in a rotation of 90 degrees on top of each column name we will have the spanish version (Do 3) in smaller letters and 90 degrees so that we can make all the columns we close to each other forming a dense matrix. 
- the rows will be each time step. WE will indicate the timestamp of each row in the leftmost part of each row in a format like:
    - f: 0 [00:00 - 00:01]
    - f: 1 [00:01 - 00:02]
    - f: 2 [00:02 - 00:03]
    ("f" stands for the time "frame" and also indicates the row index in Python)

The allowed values in the matrix are 0, 1 and -1. The 1 will be a round colored ball of a black color (no number inside, just the circle) and the -1 will be a light gray color circle. The 0's will not be printed. Very important for UI purposes to center both the circles (either the black and light gray ones) to the title of the column. Put some vertical line subtle separators between columns this way visually it is easy to see which note this circle it belongs. We want to create a beautiful UI vision effect that makes the 1's and the downwards -1's be connected by a kind of edges. Such black edges will be vertical lines that will start from the edge of the 1 circle to the edge of the below -1 (only if there is a 1 followed by a -1 for that note). Then for subsequent -1's we will also connect them with these edges. Visually we will make sure that it feels like there is a solid black circle first and then if there are several gray circles for that same column downwards in subsequent rows, we will make the edges be gray to seem like all these circles are connected. 
    
Allow as we do scrolling to Freeze the column headers (piano key names) so that we can have the static header and scroll through the rows as when we Freeze a row in Spreadsheet to ease the visualization as we go downwards. Scrolling downwards always mean going forward in the temporal axis (higher "f" number). We will always have the possibility to download the matrix with the real 0, 1 and -1 as a json, and as a temporal metadata all the bpm and temporal resolution information within the same json (as well as the column headers and the temporal rows annotations). This way a single json can be exported and imported in other sessions. These jsons are not optimized at all for lossless compression, meaning that we will have the FULL matrix with the 0, 1 and -1. We will also allow downloading/uploading a sparse-like json notation, in case we want it to be sparse to decrease storage. There will be a metadata property that will tell if it is sparse or not the piano matrix. We will also put a metadata property indicating which "matrix_processing_step" we are at (i.e "raw", "cleaned", etc...)

The most impactful UI of this matricial view will be that we will be able to modify the BPM and the temporal resolution of the matrix in situ in that view. This will make the matrix to be recomputed again, and it will be displayed automatically with the new notation. This way we can quickly test how the merge rules for aggregation works. During this process of incrementing or decrementing the temporal resolution it is important to always keep the raw matrix in the most fine-grained resolution ("Fusa" one) so that we can go into coarse granularities or fine-grained granularities without losing information due to the merge rules.

We will need to make this visualization general so that in all the different matrices we generate from an audio or from the textual notation or from another uploaded json, we are able to see the matrix representation of the notes onsets and sustains of a given melody in this matrix view so that we will have different "Pills" to click to switch between "raw", "collapsed", "clean", "two-hands". You will have to figure out the json notation for the "two-hands" processing step. Each visualization step will have the option to download that json with that matrix.

For the two-hands matrices, we will have two, make sure we adapt the json to ensure we indicate well the matrix for the left hand and the one for the right hand. In the visualization, we will simply color differently the circles of right hand and left hand, instead of black and gray, we will have dark green and light green for the left ones, and dark blue and light blue for the right ones.

Of course if the matrix notation is very large in time, simply we will have a big page in which by scrolling downwards the user will be able to advance in time to see the next time frames.

As a nice to have, in the future, we will create a player that will allow to "play" that matrix so that we will have the sound of each piano note and we will play with the amplitude of the sound to simulate a onset or a sustain this way we will be able to have a running cursor that will be the current temporal frame, that will advance in the right temporal velocity as the rows (if within rows there is a difference of 1 second, every 1 second, the cursor will move to the next row, playing all the sounds together of the notes that have a 1, and keep the sound in a damped amplitude for the sounds that keep sounding (-1) from the past time frames). This way we will create a piano player.

As other nice to have we will make the circles clickable, we will allow the user have a palette to create new circles in a given point of that grid (the grid formed by the rows and the columns of that matrix notation), this way the user can add notes, see how it sounds, etc... without having to upload again all the audio again. We will also allow the user to select a given circle or a set of circles (holding shift) to then remove them (we will need deletion rules to delete all the subsequent -1's from a deleted 1, etc...). It is important to always have a matrix validator to ensure that it fulfills the notation even after some user edits. We will not allow the user to put a -1 if a 1 has not been put in the previous timeframe (or if a -1 already existed from a previous sustain, we allow placing a -1 then in the next row of a given note column). 

It is important to ensure that for a given input file (either a audio, a json, a textual input) we will create in that bucket or temporal directory for that file a given unique identifier of that file (uuid code) that will map to its file name. This way we will be able to save all the editions on the matrices we edit, all the formats of the different matrices will already be present there in that folder, so that in other tabs if we change the visualization, we are always able to access the same matrix as we have just edited. Even though those features are nice to have, implement this storage folder structure format for each input file like this, this way when we implement the nice to have we will have already all the folder structure in place.


### Piano Roll tab

Here we will have exactly the same as the matrix tab, we will select a input file and we will load all the matrices, what is the chosen bpm and temporal resolution and we will also allow the user here to change the bpm and the temporal resolution making the re-calculation of all the matrices and saving back them again to load them from scratch after the granularity is saved.

So overall inside Playground, it does not matter which visualization we chose, either Matrix or either Piano Roll, we will always allow the user modifying and saving the new artifacts in a format that is general and optimized to be portable. Never store all the raw dense matrix of 0, 1 and -1's in that storage folder, we will simply create the dense format when we want to create a downloadable json and importing a dense matrix json, but never storing it because it can occupy a lot of storage. The sparse format is the recommended one for storage. I leave to your choice which is the most portable Pythonic format to use here for this use-case.

Here the UI is different. We will not load all the matrix vertically as we did in the Matrix tab. Instead we will have a temporal selector in a time bar on top of the visualization that will always be static and will allow the user to move it right or left to go more forward (right) or backwards (left) in time. The user can also put a temporal timestamp like 00:04 and the temporal bar will adjust to that moment in time. The user can see in some boxes, the current moving time and the frame number we are at. So that if it pauses, it can clearly see which is the time frame we are at and the current time.

For a given moment in time we will have rectangles falling from the "sky" like the app "Synthesia" does. The bars fall always in the same velocity calculated from the dimensions of the plotting window (both height and width) and the BPM and the temporal resolution are used to make the calculation of how the velocity should be so that in a given temporal frame, if a given note starts an onset, the tip of the rectangle that is falling will be at the X position of the piano plot. Inside the rectangles we will have the name of the note also printed (i.e Do, Do-#, Re-b, etc...) but with a orientation of 90 degrees since the width of the rectangles must be short to enable all the keys fit inside the screen, each with a given column width.

So, to explain this in a more technical way: we will use the SVG of a piano board that I will upload to you once you need it. This `piano.svg` file will be the image of a official piano that will be placed in a X,Y grid. This X,Y grid will have the piano image as the Y=0 (well in fact the top horizontal bar of the svg image will be at Y=0, the bottom horizontal part will be in a negative Y depending on the width of that image). But this is very good because for a rectangle (piano roll key) to "sound" we will impose that Y=0, and in that moment the rectangle will change its color to a light blue, indicating that it is sounding. The rectangles once they traverse the Y=0 to values under Y=0, they will not be rendered. This way we get the effect as if the svg image of the piano keys are "swallowing" the key rectangles. We will need to make a calculation to understand how to calibrate each rectangle width with the width of each key in the piano svg image. Also we will need to consider that black keys have smaller width. No worries because I will provide you the calculations of the assumed white keys "px" width on the svg image and we will make the proportion of the width to understand if maybe black keys have 70% of the width of a white key to differentiate them. When rectangles are falling, they will have a light gray color. Of course, since this figure will be in motion and will have a limited X and Y, especially on the Y value, we cannot have ALL the entire melody of that matrix falling at the same time, we will only allow seeing the rectangles that are close to being played because they are near in time, so that when a note like C3 is played at frame f=120 (imagine this is at 02:00) if we place ourselves in 01:50, we will be able to see the tip of the C3 starting to appear in the Y=ylim (maximum Y value of that plot) and it will start falling (so that in 10 seconds, it will reach the Y=0 position at 02:00 when it needs to sound, hence change the color to blue). 

If a user wants to modify something, it will go to the Matrix tab, then search for the exact frame in a searcher we will enable or put the time stamp (i.e 01:50) and it will be able to be located into that matrix at this point in time and see the next upcoming rows, so that it will be able to modify them and save it, and then go back to the Piano roll tab and visualize the changes.

For the two-hands, when rendered in the piano roll, we will simply use different colors for the rectangles of the left hand and the ones for the right hand. Keep the same coloring as the matrix tab colors.


### Music notation

Finally, whenever we have a clean version of a matrix, or in case the melody has two hands, the two-hands version of it, we will produce the piano sheet in html format. For this we will use VexFlow. An open-source online music notation rendering API. It is written completely in JavaScript, and runs right in the browser. VexFlow supports HTML5 Canvas and SVG. More documentation of the API in `https://0xfe.github.io/vexflow/api/modules.html`.  The GitHub repo is: https://github.com/vexflow/vexflow (if you want you can clone it and gitignore it so that we can reference it as we want locally or if we need to look for specific things how they are programmed in VexFlow, this may be useful, because some things in the documentation may not be well explained with the level of detail we need here and the flexibility we want to achieve here). 

The good thing about this library is that it produces a music representation that any browser can display. This will make any person be able to load any matricial form from the library of saved artifacts and be displayed instantaneously in HTML.

We need to produce in our Python backend the logic to translate from the sparse matricial format, which is very visual to spot errors or spot inconsistencies or failures in the collapsing of temporal frames, etc... into a format that then this javascript library can use to quickly display them without having to do any handling of this data. We aim that the backend produces the right response to already provide to the frontend the right format to simply display it. 

So the flow of the user will be:
- first upload the audio and go through the matrix generation and piano roll visualization if it wants to
- then saving the desired bpm and selected temporal granularity into our artifact repository
- once we have the saved artifact, automatically we will generate the translation into the format that this library VexFlow requires to display the music.
- then the user will go to the Music notation tab and will select a given file artifact by its name
- the frontend API will call backend to receive from the artifact repository ONLY the required vexflow format

As a nice to have, we will create the ability to incorporate metadata to this format. Such metadata will include things that the user itself will annotate. For example, the user will be able to click on a given note and add a finger number (i.e 2) so that this gets saved and whenever we render the music notation, there will be a separate process that will render the annotations, and in this annotations we will have the capability to allow the user to put some numberings in notes. Or for example, annotations like the lyrics of a song, so that we know at which point of the song we are. This needs to be very flexible and overlayed on top of the html piano notation so that it is always visual and treated as a different source of metadata. However, we need to do this in a smart way so that if the browser width changes, since this is rendered in HTML, the piano notation also wraps around the screen width as the text does, so we cannot hard-code fixed positions. We need to be clever on how we do this. In principle I think that vexflow has capabilities for adding piano finger numbers and also textual annotations that can be served as song lyrics, so we will explore in the future iterations.

Once a user is satisfied with the final result of the piano sheet, it will save these annotations (here we will not allow modifying the matrices like before, only metadata like lyrics and fingers) so we will allow saving these extra info as metadata inside the file in the bucket.

However, these buckets will live inside the `playground` folder in the main storage folder. 
To promote a given file folder into the `piano_library` of a given user, we will enable a button in this tab to finally save all these artifacts into that folder. This will allow the user to access the Piano Library only the neat works and organize them.

## Piano Library

This will be the section that a pianist, when it is about to perform, will access to.
It will select from the library of all of its saved pieces, we will allow some metadata tags to organize the works (i.e genre, artist, etc..) so the user can quickly filter what are the pieces it wants to load from a given metadata tag (we will create those).
Whenever the user clicks on a given file, it will open a simple rendering blank page with the piano sheet rendered there with all the metadata (we will also allow toggles to disable the metadata like lyrics or fingers if we don't want them to appear). 

The pianist will only need to scroll down, adjust the zoom level of the browser and also go back to the library again to search for the next piano sheet.

As a nice to have, we will have "Playlists" being a sequential series of several piano songs that the user wants to perform, so that when it reaches the end of one, with a single button click it redirects to the next one (this will be ideal for concerts). Of course we need proper UI pages for allowing the user set up a new playlist, selecting different pieces, being able to slice given section of pieces, etc...

We will have then a section in the app named Piano Library, where we will have all the consolidated files and also we will have the "Piano Playground Library" where we will store all the files (with rename and metadata edition capabilities) created in playground. 

## Composing live (nice to have)

All this section is a nice to have in the future.

Ideally when we are composing we compose a given passage of the piano piece. So for example, imagine we are creating an arragement for the piano Nocture no.2 of Chopin. We can start with an empty piano sheet and click on record. In this live composition we will have all the features included in the UI, so that the user will first record itself a given passage. Then the user will want to visualize the resulting piano sheet of that passage, it will introduce the bpm and the temporal resolution and will see the notation. If it is not happy with it, it can delete it and re-record again. Or it can also go to matrix notation to change something manually (add a new note onset, delete a sustain, delete a whole note, etc...), and during this iteration he will be modifying the matrix and seeing the change in the html notation so that the passage gets super clean in terms of the piano sheet. 

Once this passage is clean, the user may want to "integrate" it as part of the final composition, so all this editing will happen in a "stage" mode, and then the user decides where to insert that passage. When inserting, the user can inform if it wants to purely append that passage into a given frame number or a given time stamp, or if it wants to first select a given existing range of time or range of time frames, and open them in stage mode to edit them, render them after changes, and after accepting it, overwriting that passage with the changes made, etc... So all what you would expect from a nice editor that is flexible to edit, insert passages, allow playing from scratch a passage over again, changing the bpm and temporal resolution of a passage, etc...

This is a important point, in the future as a nice to have I want flexibility to be able to modify the bpm of a given passage, this way we will allow the user to make modifications maybe on some small part of the passage of a piano piece that requires maybe a more delicate playing, or maybe record it in a slow motion because sometimes playing hard passages when recording is challenging, so the pianist takes it slow and then simply by modifying the bpm we can do a conversion (for example if there is a passage at bpm 60 but we indicate that I will play it at 30 bpm, and then once I load it, I convert it back to 60 bpm this is very useful because it allows the user to play slow to get the audio correct and then in the piano notation it is rendered as if it was played at 60 bpm). 

# General Flexibility of the pieces

As a general note, a given piano "piece", since in reality the underlying data it is a matrix, it can easily be:
- slice
- cut some parts
- select a part, modify/edit it or re-record a part, and overwrite this existing selection with a new part. 

# Right and Left Alignment and editing tempo
As in music, we have to set a way to ensure that we align the proper timings of each hand so that if the Right Hand plays a note and Left Hand plays another note that should sounds simultaneously, this means the HTML render of the piano sheet should have in a given X-th measure in a given Y-th time both notes totally vertically aligned. This is because as in classical music piano sheets we have this underlying alignment. The user can at some point at new tempo to the piece. This means, it can go into a given column of the piano matrix and add new columns (as many as he wants). The piece does not need to end with the perfect timing, so this is why at any point we should be able to put new tempos that will shift all the music but at the end what matters is that this is a matrix, and we are able to add new columns (zeros by default) and we can select the granularity of the addition (fusa, corchea, negra, blanca, redonda additions, it has to be additions of this timings and cannot be more granular than the piece time granularity: if the piece granularity is for example "negras" because it is a very simple baby song, then we cannot add a tempo of a corchea in between, it needs to be as minimum granular as the time granularity (in this case a negra addition of tempo)). 

# Music Specifics
There are a lot of nuances in generating the piano sheets

## High Notes and Octaves

There are cases where, within one hand, notes are played outside the normal staff range. There are several scenarios:

- **Very low notes (both right and left hand):** if we are using the bass clef and suddenly need to play very low notes, we will define a threshold note. Any note below this threshold will be rendered using the **8vb** (ottava bassa) symbol. For even lower notes (using another threshold), **15mb** will be used.
- **High notes (right hand):** we will use **8va** starting from a configurable threshold (one threshold for the left hand and another for the right hand). The same applies to **15ma** for extremely high notes.
- **As a general rule, we will avoid using 8va and 15ma in the left hand.** Instead, for those passages, we will switch to a small treble clef. Notes above the threshold will then be rendered in the treble clef, allowing them to be played higher on the keyboard while keeping the notation much more readable.

This will only be applied once we have an algorithm that decides which notes belong to the right hand (upper staff) and which belong to the left hand (lower staff). For the first iteration, we will simply define a threshold note: notes above the threshold will be assigned to the right hand, and notes below it to the left hand.

## Naturals

We will prioritize the use of **natural signs** instead of double sharps or double flats. We know that the key signature already defines the default accidentals. Our goal is to optimize the score by minimizing the number of naturals and accidentals, making it easier to read.

For this reason, the user will be able to select a passage in the Playground (by choosing its start and end) and change the key signature for that passage. This provides a very visual way of manually finding the key signature that minimizes the number of accidentals.

Of course, some accidentals are intentionally introduced by the composer. For example, in **E major**, **A♯** is frequently used to create tension because it acts as the leading tone to **B** (the dominant). In these situations, no key signature can eliminate the need for the A♯, which is perfectly normal.

The idea is that, when the user first transcribes a matrix into a rendered score, they must specify the desired key signature. Later on, they will be able to modify passages where the composer has changed the key signature.

## Transposition

The score can be transposed at any time. This means shifting the positions of the `1`s and `-1`s in the matrix either upwards or downwards (increasing or decreasing their row indices).

This is useful when the recorded audio has been transposed, making it difficult to match the original key simply because of the recording.

During the audio-to-matrix transcription process, this step will be available to the user. Ideally, the user should be able to preview how the score would be rendered for selected sections (by choosing a short time range) in order to verify that the detected key matches the original recording and that the initial BPM (Beats Per Minute) and the selected temporal granularity are appropriate for that audio.

## Stem Direction

### 1. Single note

- If the note is below the middle line of the staff (3rd line), the stem points upwards.
- If it is above the middle line, the stem points downwards.
- If it is exactly on the middle line, either direction may be chosen depending on the context.

### 2. Beamed notes (eighth notes, sixteenth notes...)

- The stem direction is not determined note by note. The entire beamed group shares the same stem direction.
- The direction is chosen to make the group as visually clean as possible, typically according to the average pitch of the group (its visual center of gravity), rather than the first or highest note.

### 3. Polyphony (two voices in the same hand)

- The upper voice almost always has stems pointing upwards.
- The lower voice almost always has stems pointing downwards.
- This rule takes precedence over the pitch of the notes.

## Tuplets (Triplets, Quintuplets, Sextuplets, Septuplets, Octuplets)

The number (3, 5, 7, 8...) indicates that those notes occupy the duration that would normally be occupied by a different number of notes.

This feature will only be used manually by the user. When selecting a passage in the Playground, the user will be able to create tuplets.

Typically, the user may notice that notes which were not played simultaneously have been grouped into a chord simply because they were played at a higher speed. Alternatively, they may appear as thirty-second notes with rests in between.

Since this representation is often visually unintuitive, the user will be able to group those notes into tuplets instead.

The important point is that the underlying matrix remains unchanged. Tuplets do not affect the matrix generation rules in any way. They only affect rendering: some rests may be removed, or notes that would not normally be interpreted as simultaneous may instead be rendered as independent notes played with a different rhythmic subdivision.

This is a very advanced feature and will be implemented towards the end of the project.

## Ties

Many audio-to-score transcription programs overuse ties.

This happens because the timing of the transcribed notes rarely matches the exact timing of the original score. To compensate, those programs split notes into several shorter note values connected by ties, making it appear as though the note duration is perfectly represented, when in reality it is simply a sustained note.

In our project, we **do not want ties**, except when a note crosses a barline and must continue sounding into the following measure.

Within the same measure, ties should not be generated. Instead, the algorithm must choose the note duration that best approximates the detected note according to the selected temporal granularity.

## The Rule of Rendering as Simple and clean as possible

- No arpeggios. A chord whose notes are played almost simultaneously but a bit arpeggiated, is counted as a single chord.
- The **"tr"** symbol is allowed because it represents a very specific case of rapidly alternating notes without a strict rhythmic subdivision. We should be able to detect situations where two notes alternate continuously at a high speed and classify them as a trill.

  One concern is that, if the matrix is generated using the finest available temporal granularity, an extremely fast trill may still be undersampled. For example, a trill such as:

  `C D C D C D`

  could end up being sampled as:

  `C C D C C D D C`

  making the transcription unreliable.

  The proper solution is either to use an even finer temporal resolution or, preferably, to detect note onsets directly from the raw audio before aggregating them into the finest matrix granularity, resolving trills beforehand.

- We will ignore all other ornaments. The performer already knows how to interpret them, and they cannot reliably be inferred from piano audio alone.

- The only ornament that may be problematic is the **arpeggio**, since its notes are played rapidly but not exactly simultaneously. Because we will initially work with a fine-grained temporal resolution, these notes may appear as separate events.

  If several notes occur within the same temporal window, they will be considered a chord. If they are not truly simultaneous (using a smaller threshold based on an even finer temporal resolution), then they will...

## Beaming

Eighth notes, sixteenth notes, thirty-second notes and sixty-fourth notes will always be beamed together whenever the following note has the same duration.

In accompaniment patterns, it is very common to encounter arpeggiated chord figures written as regular notes (for example, as eighth notes) rather than using the arpeggio symbol.

Typically, the lowest note of the pattern (which may change over time) is visually separated from the last note of the previous arpeggio.

The rule is as follows: we must detect when we are inside such an arpeggiated accompaniment pattern and reach a note (note **X**) where the previous note is higher and the following note is also higher.

In this situation, the beam will be broken at note **X**, starting a new beam from that note onwards.

This creates a much clearer visual separation between harmonic/rhythmic groups, making the accompaniment considerably easier for the performer to read.

## Double Flats / Double Sharps -> Always Use Naturals or Infer a New Key Signature

For each measure, the algorithm should determine which key signature produces the fewest accidentals (naturals, sharps and flats).

Additionally, when editing a score in the Playground, the user should be able to select any measure and manually decide whether to apply a different key signature to it.

## Cue-sized notes and Fioritura and Small Notes and Appoggiatures

We will only let the user modify the size of some notes if they occupy a lot of horizontal space that maybe the other hand does not occupy. For this, instead of inferring them, we will let the user decide in a given passage selected from a given range of time-frames if they want to make the size of the notes smaller so that they fit in less horizontal space acting somehow like these types of notes (Cue-sized notes, Fioritura, Small Notes and Appoggiatures).

The user will be able to click on given note and add an acciaccatura / appoggiatura. This note will be in the metadata, not in the piano matrix notation.

# Tempo

To create the proper sense of tempo, ideally we will want to mark each "beat" (i.e if bpm = 60, every 1 second we should have a subtle gray dashed vertical line traversing both the treble clef and the bass clef ). Since we will be able to edit the pieces by adding new "columns" into the matrices, in the Playground I need to give the user the option to put the cursor in a given point in time inside a measure and force that the following note will go into a new start of a new next measure and fill the remaining tempo with silences. For example if it is a 4/4 and it is a measure with Do Re Mi Fa as negras, if we select the dashed line in the "Mi" note, and we select to "Cut measure up to here" we will displace the "Fa" to a new measure but the underlying matrix change will be adding new columns (if the matrix is at "negra" granularity, we will simply add a new column between the "Mi" and the "Fa" and this will force the "Fa" to appear as the new note of the next measure)

## Time Frame selection by number and time

In the rendering of the piece, we will have a render of the numbers of the time frames at the top of the dashed lines indicating each time frame.

# Playground of audio file by range of times

I want in the playground to load a .mp3 file and be able to tell, run the transcription into a matrix and render it as a sheet of a given time range (from 03:01 to 03:22) because maybe we are just iterating on a new rendering way that we want that specific passage to see how it render and how the piano matrix view looks like. 

# Metadata

It will be very important to detail some metadata in a json that will indicate some metadata info on top of the piano matrix.

The piano matrix is the main input source before rendering a music piece. On top of it we need the decisions of the BPM, temporal resolution (which will create another matrix if we decide to aggregate into a more coarse-grained temporal resolution, etc...). So it all starts with this matrix. This is the matrix that will be cleaned first to the maximum level of granularity first and being cleaned before we apply anything on top.

The following matrices that will be created from this one are simply matrices we iterate on top, saved as new matrices. Of course we need to always keep track of what is the parent matrix of a given matrix. If we decide to make editions, deletions, additions, etc... all of this will go into the matrix we are iterating in, not to the input source base matrix. So it is possible that from a given edited matrix we cannot go back to the original matrix, it is ok. Once we have the matrix okey in terms of additions, etc... we will go into the rendering. There are operations like "Transposition" which also alters the underlying piano matrix, and some others (like creating a "trino" in the piano render, is definitely not a change in the piano matrix.)

In the rendering it is where the metadata will come into play. As you have seen there are many music specific scenarios and rendering capabilities that with only a matrix of 0, 1's and -1's. Remember also we will have right and left hand matrices so the metadata should be clear in which is the modified matrix. Since matrices are numeric entities, we can refer to the metadata alterations as indices in this matrix, so for example, if we apply a trino rule, we can select for that hand which are the columns (time frames) in which we will apply a trino, so that instead of rendering all the notes we simply render that trino for that length. So for each specific music artifacts we create that do not change the underlying piano matrix, we need to define some terminology for an efficient identification of which parts are modified and how.

This is complex since this metadata terminology should be aligned with the way we render the music in HTML so that it eases the rendering. 

# Backend ease the task for Frontend

As a general rule, let's avoid any Frontend-heavy boilerplate code.
We need to use Backend as much as possible to digest and convert formats so that the way we use the frontend to render the music notation is as smooth as possible.
So maybe when we have a piano matrix and we apply the metadata on top, maybe we need to use Backend to digest all the changes into a final format that we can send to Frontend so that we display the piano sheet in very efficient way so that most of the overhead happens in Backend, because at some point maybe the Backend is GPU-based so most of the operations can be accelerated there.


# UI Visualisation of the matrix

Read how we will prepare the svg of the piano and howe we will modify on the fly the svg for the keys that are pressed at `context/music/piano_svg/01-piano-svg.md`.


## Piano roll view

Similar to the matrix visualization, we will have on the leftmost part the piano svg rotated 90 vertically, so that we will have on the right of it a div in which we will the piano notes in that matrix. 
- Instead of doing circles, here we will opt for rectangles for the notes rendering (start of the rectangle is the onset, the duration of sustain is the rectangle length and end of rectangle is when the key should be released or stopped)
- We will use the dashed vertical lines to indicate the time frames. Numerate the time frames
- Create a kind of player button that can start playing and hearing the original audio while seeing the notes in the piano roll view. Optionally we should be able to listen to the piano notes (you can create a table of the notes frequencies of a Grand piano and simply make a sound of each note to create a piano player, it will be very simple but effective). This way we can compare the sound of the original audio seeing the notes but also the rendered piano matrix how it sounds. Try to find in the internet if you see any good recommendable piano sounds for that key so that we can download it locally and we can use it to have a similar Grand Piano note sounding effect better than just a frequency of a note played but a digital audio.
- Create a filter sections on top to choose the player speed, the BPM and Time frame granularity so that it will update the player from scratch every time we do a change in that visualization. We will also select a given time range (i.e from 03:00 to 03:02) so that we will refresh the view to only that part. We will be able to click on either the play of the Original Piano audio or the Transcribed Piano only on that selected section. The user can restart to the initial position of that selection section.
- Whenever time progresses, the rolling piano keys should go to the left, meaning that when the tip of the rectangle touches the piano svg image, that key should be "pressed" and hence the color of that key should be highlighted as explained in `01-piano-svg.md`. That color will be sustained until that note ends its rectangle.
- The user can pause and restart again from the start or place the cursor at any point it wants. 
- It will be amazing if we can put the waveform in a kind of watermark background of this div section so that it also moves as the notes moves towards the left as time progresses, this way we see the piano roll keys as rectangles but also we see the original waveform. 
- We will allow scrolling horizontally so that we can quickly go to a given passage.
- Make this div fit the entire screen vertically, this is because we must try to fit the svg image of the entire vertical piano in the vertical active region of the screen is rendering it on the browser, this way we can maximize the user experience (but of course the filters section has to be also viewed, so please try to create a surrounding div that fixes that view on that surrounding div centered vertically so that when we hit the play button we have this centered vertical view). 
- While playing we cannot scroll horizontally


## Notes falling

This will be another page (another visualization tab we will have) but similar to the Piano roll view.
This is basicaly the same as the Piano roll view but the piano is placed at the bottom of that surrounding div in a horizontal position (the natural orientation of the SVG image will be horizontal), and the rectangles will be vertical rectangles falling from top part of the div. Of course, since the audio file can have several minutes length, we will not render all the rectangles (opposite to what we do in the Piano roll view where all the rectangles are rendered and via horizontal scrolling we discover them). Here the experience is more to see the piano in a natural horizontal position, and see the notes falling from the sky (and we see new notes (rectangles) appearing from the top as time progresses). Same visualisation options as before.

## Editing

These two previous views will be components that will allow visualizing a given piece or a given piano matrix with some metadata (BPM, time frame granularity, etc...).
Here of course all the dashed lines indicating the time frames will be transposed

It will be a nice to have but very useful if we can make those divs (rectangles of each note) draggable so that we can potentially move them into different "columns" so that this will mean we are attempting to "edit" a given note. We can make as many drags and drops as we want (let's try to ensure that in the sense of the UI, it is very clear when we move a rectangle, to which note we are landing to, use vertical dashed lines and try to put the names of the notes in Spanish rotated 90 degrees but that when we hover over one of such lines it colors differently so that we know which note we are landing the drag of the rectangle to). After all the changes, this will only be "staged" changes. There will be a "Save" button that will allow saving that edit change to the actual piano matrix for that piece.

# GPU Optimization

Since we are dealing with audio files (lots of matricial form) we potentially leverage GPU if the host computer has one. THis is just a nice to have, but please just take into account that at some point we may want to improve the efficiency and reduce latency. This is not something to consider now, but it's something to keep in mind in case we need to decide about which framework to use, we should be mindful if we have several alternatives and some of them can have a potential way of doing calculations in GPU and CPU, these ones should be preferred. Otherwise for simplicity try to use popular ones first even if they are CPU only. 

# Timings when editing

Read the logic in `context/music/notation-logic/03-editing-logic.md` (useful when we implement are in the "Implement editing" epic)

# Folder Structure for storage

When we are in Playground we will allow saving everything with alias names. 
The structure will be some kind of nested structure like:
```bash
- Playground
  - some kind of folder structure we decide like artists
  - piano piece alias name (folder)
    - versioning and granularity (folder)
      - metadata
      - piano matrix
    - an overall metadata_track.json
    ... (depending on the granularities we have created in different granularities or different versions)

```

The versioning system will be kept in the `metadata_track.json` so we will have all the history there of the versions and granularities. The same piano matrix in a given same version may be in different temporal granularities. When we make a change to the underlying piano matrix, we can decide if we overwrite the matrix of that granularity for that version or if we create a new version/granularity out of it. Song names will have a song slug used for the folder name as well as an artist slug. 

Granularities will have the following code (prefix "g" stands for granularity)
- blanca: `gb`
- negra: `gn`
- corchea: `gc`
- semicorchea: `gsc`
- fusa: `gf`
- semi-fusa: `gsf`

Versions will simply be: `v1`, `v2`, `v3`, ...

`metadata_track.json` will contain a "comment" on each file in case when the user saves it it wants to put a comment indicating what changed when creating this new version or granularity and why. Also we will have the appropiate Artist name and Track Name (or Piece Name) so that we can have "Avicci" and "Levels" and this will help the Search functionality in the Library to search for the tracks without having to search by the slug. 

```bash
playground/
  - avicii/
    - levels/
      - metadata_track.json
      -v1_gsc/
        - metadata.json
        - piano_matrix_v1_gsc.np
      -v1_gn/
        - metadata.json
        - piano_matrix_v1_gn.np
      -v2_gn/
        - metadata.json
        - piano_matrix_v2_gn.np
```

As we have seen each piano matrix version and granularity can have its own specific annotations to properly render specific passages in the UI, this is why we need the `metadata.json` in case in the Editing section the user decides to change a given section to another kind of displaying method (i.e converting a passage into a trino, or adding new tempos or deleting some, etc...).

However as you see here we only are at **Playground**. **Library** will be a kind of different folder that will have the playlists and some consolidated final candidate for a given playground piece. The user can select whether a given playground piece can be promoted to the Library. When we have a promotion, in the `metadata_library_track.json` of the `library/` folder for that specific track, we will keep a history of the versions that were promoted to library, this way we can rollback if we make a mistake and want to revert to the previously valid track.

So in the library we will have a kind of structure like:

```bash
library/
  tracks/
    - avicii/
      - levels/
        - metadata_library_track.json
        - piano_matrix_v2_gn.np
  playlists/
    - all_about_avicii/
      - metadata_library_playlist.json
```

So the `metadata_library_track.json` will contain the selected piano matrix from the playground (we will replicate that into here), so the `metadata.json` of that track will be inside a section of `metadata_library_track.json` but we will also have the real track name and artist name (coming from `metadata_track.json`).

If a user wants to have for the same track several version, we will have a way to also enable promotion of more than one. By default we will always have the option to promote by replacing the current one and keeping track in the history, but in the dialog that will appear in the Playground when we click on the promotion button we will have a checkbox. So make sure the `metadata_library_track.json` is prepared to allocate the metadata of many different versions from the same track. 

When promoting we will have a placeholder suggested **version name** (i.e "Levels - Avicii") but when we select this multiple option to promote we can edit it to have for example another one being (i.e "Levels (Chill) - Avicii" for example if it is a slower acoustic version transcription), this will be better for the user UI since the user will not need to know if the acoustic version was a `v3_gn` or a `v2_gn` it will know it by the name of the promotion. 

Finally, the user can create playlists, by selecting the track (and potentially if many within the same track, the version) and the version name. This way the user can filter tracks for a given Artist, or can create a custom playlist by selecting a track and adding it to a existing or a new playlist (please make this similar to Spotify way of organizing tracks and playlists).

The ultimate goal is that when the user enters the playing mode and selects a playlist, a nice UI read-only will appear and we will let the users select the first track of the playlist (potentially we can edit the order too) and show the piano score of that piece, and then when finished it can click on next to go to the next one in a seamless way.

# Song Lyrics

We potentially want the capability to annotate text on top of the piano scores specially about the text that represents the lyrics of a song. For that we should allow in Playground a specific section that is song lyrics that helps the user select a given time frame range and have an editor that will allow the user writing that lyric line. The text will need to span into a text div with the size of the length of the selected time frame range. This is complex and will require a lot of back and forth UI trial and errors so leave it as a nice to have epic to the end of the implementation priorities.

We can let the user select this in the Piano roll view for example when he hears the original song of a given selected range of time frames, puts the text and then when it selects the option to render, it shows below that passage selected rendered with the lyrics so that it can iterate maybe selecting a fewere time frames to put the message shorter or even try with multi-line text too or small size text... we should try to be flexible. I think the Vexflow allows textual annotations.

Of course this will be stored in the `metadata.json` of that track version.

# Piano Finger numbers

This is another nice to have, ideally I want to allow Vexflow have finger annotations if the user wants to specify on a given not that. This will be easy to do in the Piano Roll notation where we can first select a time fram range and then we can select a given note (rectangle div) and once selected we can put the finger number (1-5 number) and this will be stored in the `metadata.json` of that track version. Ideally we want to allow the user be able to click in the piano sheet a given note and put the fingers but this can be complex. For the chords we may need to be able to put two numbers displayed in different lines like "1/n4" or "2/n4/n5" with multiple fingers allowed. Maximum flexibility for the user here. Ideally we should be able to tune the text size of that finger text too.