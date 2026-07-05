# AImpromptu

This project is a ambitious project that aims to receive any URL from YouTube of a given video of a piano only being played OR simply receive an upload of a .mp3 or .aac or .m4a file of a recording in a mobile phone or any recording of music and convert it into a music score. The particularity of this music score is that it is a HTML file, this means that any browser can open it and the display of the music notation depends on the screen width, so that the music is not on a pdf. Plus, we can make annotations on top of the music score, put the lyrics, etc... 

Everything is standardized in a new numerical format for encoding notes onsets and note sounding. This format is basic in the sense that it does not meant to reproduce exactly the same format as the MIDI file or the MP3 sound, but it is a simplistic representation of the music played by a piano so that the resulting piano sheet is clear, minimalist and simple to read. Most of the current softwares that create a piano sheet are very sensitive to note durations, creating very cluttered piano sheets of notes sounding during many long. I propose a new methodology that first samples time in a very fine-grained way, and then we start collapsing temporal granularity into a more broad time buckets so that the final piano sheet is not as cluttered as the fine-grained one.


# The new notation

Whenever we receive a .mp3 file, there are python libraries that convert this file into a kind of midi file.

We want to convert this kind of Midi files format into a sparse matrix format.

Since music is not only about onset of a note but also the duration of it, we need 2 matrices to denote when a note was pressed (onset matrix) and when a note

A matrix has a 2D dimension:
- 