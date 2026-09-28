"""Stitch and read the notes with a given plate and roll bounds, without touching the project's data."""
import sys, json, time
import numpy as np
from aitu_backend.video import store, stitch, notes as notes_module, geometry
from aitu_backend.video.detector import DetectorSettings, DEFAULTS
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]; plate_path = sys.argv[2]; roll_top = float(sys.argv[3]); guard = float(sys.argv[4]); out = sys.argv[5]
speed = float(sys.argv[6]) if len(sys.argv) > 6 else None
settings = DEFAULTS
if len(sys.argv) > 7:
    settings = DetectorSettings(**json.loads(sys.argv[7]))
plate = np.load(plate_path)
if plate.shape[0] < 720:
    full = np.zeros((720, 1280, 3), np.float32); full[:plate.shape[0]] = plate; plate = full
store.load_plate = lambda uuid: plate
cal = store.load_calibration(U)
cal.roll_top = roll_top; cal.guard_band = guard
store.load_calibration = lambda uuid: cal
meas = store.load_measurement(U)
if speed is not None:
    meas.scroll_speed.px_per_frame = speed
    meas.scroll_speed.px_per_second = speed * 10
store.load_measurement = lambda uuid: meas
notes_module.store.save_notes = lambda uuid, answer: None
t0 = time.time()
answer = notes_module.read_notes(U, settings=settings, compare_connected=False)
print('notes', len(answer.notes), 'in', round(time.time() - t0, 1), 's', 'report', answer.report.model_dump(by_alias=True))
json.dump({'notes': [n.model_dump(by_alias=True) for n in answer.notes]}, open(out, 'w'))
