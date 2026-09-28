"""Draw a notes.json back on one frame the way the Notes tab does, to see what is false."""
import sys, json
import numpy as np
from PIL import Image, ImageDraw
from aitu_backend.video import store, geometry
U = 'b99bc3ae-30a5-4aa0-9b3b-8f11eea5fba7'
S = sys.argv[1]; notes_path = sys.argv[2]; index = int(sys.argv[3]); out = sys.argv[4]
speed = float(sys.argv[5]) if len(sys.argv) > 5 else 201.62576069144842
cal = store.load_calibration(U)
keys = {k.midi: k for k in geometry.keys(cal)}
upper = cal.upper_line
t = index * 0.1
data = json.load(open(notes_path))
notes = data['notes'] if isinstance(data, dict) else data
img = Image.fromarray(store.load_frame(U, index).astype(np.uint8))
draw = ImageDraw.Draw(img)
drawn = 0
for n in notes:
    tip = upper - (n['start'] - t) * speed
    top = upper - (n['end'] - t) * speed
    if tip < 0 or top > upper:
        continue
    k = keys[n['midi']]
    draw.rectangle([k.left, max(0, top), k.right, min(upper, tip)], outline=(0, 255, 0) if n.get('widthKeys', 1) > 0.35 else (255, 0, 0), width=2)
    drawn += 1
img.save(out)
print('drawn', drawn, 'of', len(notes))
