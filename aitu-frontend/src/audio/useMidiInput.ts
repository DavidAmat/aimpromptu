/**
 * A MIDI piano, through the browser's Web MIDI API (Recording in Sheet, implementation 02, Phase 9).
 *
 * A piano with a MIDI connector, plugged into the computer, sends each key it plays: its number,
 * when it went down and when it came up, and how hard. Those are the notes of a take, exactly, with
 * no transcription. A note ends when its key comes up; the sustain pedal is not read.
 *
 * Like the microphone, the browser offers MIDI only on a secure address (HTTPS or `localhost`), and
 * asks the user once.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { PlayedNote } from "../api";

export interface MidiPiano {
  id: string;
  name: string;
}

export interface MidiInputState {
  /** This browser has Web MIDI. */
  supported: boolean;
  /** The pianos connected, once access was given. */
  inputs: MidiPiano[];
  /** Why there is no access, in words. */
  error: string | null;
  /** Ask the browser for MIDI (once; it asks the user). */
  request: () => Promise<void>;
  /** Start hearing `inputId` (every input when empty); times are counted from `zero`, a
   * `performance.now()` moment: the start of the recording the notes go with. */
  start: (inputId: string, zero: number) => void;
  /** Stop, and give the notes heard; a key still down ends now. */
  stop: () => PlayedNote[];
  /** How many keys were played since `start`, for the panel to show. */
  heard: number;
}

/** A note-on with velocity 0 is a note-off, as many keyboards send it. */
const NOTE_ON = 0x90;
const NOTE_OFF = 0x80;

export function useMidiInput(): MidiInputState {
  const supported = typeof navigator !== "undefined" && "requestMIDIAccess" in navigator;
  const access = useRef<MIDIAccess | null>(null);
  const [inputs, setInputs] = useState<MidiPiano[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [heard, setHeard] = useState(0);
  const listening = useRef<MIDIInput[]>([]);
  const zero = useRef(0);
  const down = useRef(new Map<number, { start: number; velocity: number }>());
  const played = useRef<PlayedNote[]>([]);

  const read = useCallback(() => {
    const found = access.current ? [...access.current.inputs.values()] : [];
    setInputs(found.map((input) => ({ id: input.id, name: input.name ?? "MIDI piano" })));
  }, []);

  const request = useCallback(async () => {
    if (!supported || access.current) return;
    try {
      const granted = await navigator.requestMIDIAccess();
      access.current = granted;
      granted.onstatechange = read;
      read();
      setError(null);
    } catch {
      setError("This page may not use MIDI: open the app at localhost, and allow MIDI.");
    }
  }, [supported, read]);

  const onMessage = useCallback((event: MIDIMessageEvent) => {
    const data = event.data;
    if (!data || data.length < 3) return;
    const kind = data[0]! & 0xf0;
    const key = data[1]!;
    const velocity = data[2]!;
    const at = Math.max(0, (event.timeStamp - zero.current) / 1000);
    if (kind === NOTE_ON && velocity > 0) {
      down.current.set(key, { start: at, velocity });
      setHeard((count) => count + 1);
    } else if (kind === NOTE_OFF || (kind === NOTE_ON && velocity === 0)) {
      const open = down.current.get(key);
      if (!open) return;
      down.current.delete(key);
      played.current.push({ midiNote: key, start: open.start, end: Math.max(at, open.start + 0.01), velocity: open.velocity });
    }
  }, []);

  const release = useCallback(() => {
    for (const input of listening.current) input.removeEventListener("midimessage", onMessage);
    listening.current = [];
  }, [onMessage]);

  const start = useCallback(
    (inputId: string, at: number) => {
      release();
      zero.current = at;
      down.current = new Map();
      played.current = [];
      setHeard(0);
      const all = access.current ? [...access.current.inputs.values()] : [];
      listening.current = all.filter((input) => !inputId || input.id === inputId);
      for (const input of listening.current) input.addEventListener("midimessage", onMessage);
    },
    [onMessage, release],
  );

  const stop = useCallback((): PlayedNote[] => {
    release();
    const now = Math.max(0, (performance.now() - zero.current) / 1000);
    for (const [key, open] of down.current) {
      played.current.push({ midiNote: key, start: open.start, end: Math.max(now, open.start + 0.01), velocity: open.velocity });
    }
    down.current = new Map();
    // Only the keys of a piano: the sheet has 88.
    return played.current
      .filter((note) => note.midiNote >= 21 && note.midiNote <= 108)
      .sort((a, b) => a.start - b.start);
  }, [release]);

  useEffect(() => release, [release]);

  return { supported, inputs, error, request, start, stop, heard };
}

export default useMidiInput;
