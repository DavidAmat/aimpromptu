
# Editing Logic

When editing a selected range of time frames, the user must be able to re-record only that part of the piece.

For example, imagine that the current track is at **60 BPM** and the selected range contains **4 beats**. Since one beat is one quarter note, the selected range lasts:

```text
4 beats × 1 second per beat = 4 seconds
```

While recording, a metronome will play according to the selected recording tempo. The UI must also indicate the current beat and time frame so that the user knows exactly which part of the selected range is being recorded.

The recording is stopped manually by the user. Therefore, it may be longer than the selected range. For example, the user may record for 5 seconds even though the selected range only lasts 4 seconds. In this case, everything after the expected end of the selected range will be trimmed.

The trimming duration must be calculated from the number of selected beats and the tempo used during the recording:

```text
expectedRecordingSeconds = selectedBeats × 60 / recordingBpm
```

Once the recording is complete, the user will see its waveform and will be able to play it before processing it.

## Recording difficult passages more slowly

Some passages may be too difficult to perform at the current track tempo. For this reason, the user will be allowed to record the selected range at a slower **practice tempo**.

The following concepts must remain independent:

* **Track tempo:** the BPM at which the passage belongs in the final piece.
* **Recording tempo:** the slower BPM used while performing the replacement.
* **Temporal granularity:** the smallest musical duration represented by one matrix column, such as negra, corchea, semicorchea or fusa.

Changing the temporal granularity does not make the metronome or the performance slower. It only changes how precisely note timings can be represented in the matrix.

For example, consider a 4-beat range whose final track tempo is 60 BPM:

```text
Track tempo: 60 BPM
Selected duration: 4 beats
Final duration: 4 seconds
```

The user may choose to record it at half speed:

```text
Recording tempo: 30 BPM
Selected duration: 4 beats
Raw recording duration: 8 seconds
```

At 30 BPM, each quarter-note beat lasts 2 seconds. Therefore, the metronome plays one beat every 2 seconds and the user has 8 seconds to perform the same 4-beat passage.

For an even more difficult passage, the user may record it four times more slowly:

```text
Recording tempo: 15 BPM
Selected duration: 4 beats
Raw recording duration: 16 seconds
```

The UI should preferably expose this through simple options such as:

```text
Recording speed:
- Original speed
- 2× slower
- 4× slower
```

The corresponding recording BPM can then be calculated automatically:

```text
recordingBpm = trackBpm / slowdownFactor
```

## Temporal granularity during slow recording

The user may also choose a finer temporal granularity while recording. This is independent of the slowdown factor and can help capture more precise note timings.

For example, when recording the 4-beat passage at 30 BPM:

```text
Granularity: negra
One column: 2 seconds
Number of columns: 4
Raw recording duration: 8 seconds
```

With corchea granularity:

```text
Granularity: corchea
One column: 1 second
Number of columns: 8
Raw recording duration: 8 seconds
```

After converting the passage back to 60 BPM, those same corchea columns represent 0.5 seconds each:

```text
8 columns × 0.5 seconds = 4 seconds
```

A finer recording granularity may therefore be used to obtain a more accurate transcription. The resulting matrix can later be collapsed to the current granularity of the track using the normal matrix merging rules.

## Previewing the recorded replacement

After recording, the raw audio must be preserved exactly as performed. The user can listen to the complete 8-second or 16-second recording and inspect its waveform.

The interface will then provide a button such as:

```text
Transcribe and preview at current track tempo
```

The recommended process is:

1. Trim the raw recording to the expected number of beats at the recording tempo.
2. Clean and normalize the audio.
3. Transcribe the raw slow recording into note events and a temporary matrix.
4. Convert the temporary matrix from the recording tempo to the current track tempo.
5. Render only the edited passage as temporary piano notation.
6. Allow the user to accept, reject or re-record the passage.

For example, when converting a recording from 30 BPM to a track at 60 BPM, all event timestamps are divided by 2:

```text
targetTime = recordedTime × recordingBpm / trackBpm
```

Therefore:

```text
recordedTime = 6 seconds
recordingBpm = 30
trackBpm = 60

targetTime = 6 × 30 / 60
targetTime = 3 seconds
```

The complete 8-second recording becomes a 4-second passage while preserving its position within the same 4 musical beats.

It is preferable to transcribe the original slow recording first and scale the resulting note timings afterwards. This avoids introducing audio time-compression artefacts before transcription.

However, the user may also be given an optional audio preview called:

```text
Play at current track tempo
```

This preview applies pitch-preserving time compression to the recorded audio. For example, an 8-second recording made at 30 BPM will be played in 4 seconds when previewed at the track tempo of 60 BPM.

The compressed audio is useful for listening, but the notation should be generated from the transcription of the original recording whenever possible.

## Non-destructive staged replacement

The newly generated matrix must not immediately overwrite the selected range of the main track.

Instead, the application will create a temporary staged replacement containing:

* The original raw recording.
* The trimmed recording.
* The recording tempo and slowdown factor.
* The recording temporal granularity.
* The temporary transcribed matrix.
* The matrix converted to the current track tempo.
* The rendered piano notation for the edited passage.
* Optionally, the pitch-preserving audio preview at the current track tempo.

Only the selected passage will be rendered. Since edited ranges normally contain only a few seconds of music, transcription and rendering should be fast and should not require regenerating the complete score.

The user can then:

* Play the raw slow recording.
* Play the recording converted to the current track tempo.
* Inspect the waveform.
* Inspect the temporary matrix.
* Inspect the resulting piano notation.
* Re-record the passage at the same speed.
* Record it even more slowly.
* Change the capture granularity.
* Accept the replacement.
* Cancel the operation without modifying the track.

When the user accepts the result, the temporary matrix is forced to have exactly the same number of columns as the selected target range. Any excess content is trimmed, and any missing ending frames are filled with silence. The validated temporary matrix then replaces only that slice of the main piano matrix.

This preview-first workflow will be the default behaviour for all recorded edits. It provides a safe and user-friendly editing process because the user can verify the new notation before modifying the main piece.
