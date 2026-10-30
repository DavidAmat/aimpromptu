import sys
from PIL import Image, ImageChops
for p in sys.argv[1:]:
    im = Image.open(p).convert("RGB")
    box = ImageChops.difference(im, Image.new("RGB", im.size, (255, 255, 255))).getbbox()
    if box:
        im.crop((0, 0, im.size[0], min(im.size[1], box[3] + 20))).save(p)
