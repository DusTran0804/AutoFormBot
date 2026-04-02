from PIL import Image
import os

images_dir = "WebApp/frontend/assets"

for i in range(1, 11):
    path = os.path.join(images_dir, f"guide-{i}.png")
    if os.path.exists(path):
        img = Image.open(path)
        w, h = img.size
        # Crop to remove grey border and mac frame
        left = 40
        top = 80
        right = w - 40
        bottom = h - 60
        cropped = img.crop((left, top, right, bottom))
        cropped.save(path)
        print(f"Cropped {path} to {cropped.size}")
