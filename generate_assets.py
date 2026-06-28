import os
import random
import hashlib
from pathlib import Path
from dataclasses import dataclass

from PIL import Image, ImageDraw


CATEGORIES = [
    ("plumber", "Plumber"),
    ("electrician", "Electrician"),
    ("carpenter", "Carpenter"),
    ("cleaner", "Cleaner"),
    ("painter", "Painter"),
    ("gardener", "Gardener"),
    ("ac-repair", "AC Repair"),
    ("appliance-repair", "Appliance Repair"),
]


def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def rand_color(rng: random.Random, lo=30, hi=235):
    return (rng.randint(lo, hi), rng.randint(lo, hi), rng.randint(lo, hi))


def draw_provider(jpeg_out: Path, seed: int) -> str:
    rng = random.Random(seed)

    w, h = 900, 900
    bg = rand_color(rng, 40, 215)

    # Variations
    skin_tones = [
        (220, 176, 141),
        (201, 154, 118),
        (184, 134, 101),
        (242, 204, 170),
        (214, 168, 132),
        (173, 121, 90),
        (230, 188, 155),
    ]
    skin = list(rng.choice(skin_tones))

    hair_colors = [
        (40, 30, 25),
        (70, 50, 35),
        (110, 80, 55),
        (150, 105, 70),
        (210, 160, 105),
        (90, 70, 60),
    ]
    hair = list(rng.choice(hair_colors))

    shirt_colors = [
        (33, 96, 187),
        (19, 130, 112),
        (178, 64, 54),
        (110, 86, 164),
        (145, 111, 51),
        (70, 70, 70),
        (230, 160, 60),
    ]
    shirt = list(rng.choice(shirt_colors))

    beard_enabled = rng.random() < 0.55
    glasses_enabled = rng.random() < 0.45
    hair_style = rng.choice(["short", "curly", "bald", "sidepart"])
    face_shape = rng.choice(["round", "oval", "square"])

    # Face geometry
    face_center = (w // 2, int(h * 0.43))
    if face_shape == "round":
        face_w, face_h = 330, 360
    elif face_shape == "oval":
        face_w, face_h = 320, 390
    else:  # square
        face_w, face_h = 340, 360

    img = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(img)

    # Soft background blur effect (simple overlay)
    for _ in range(18):
        cx = rng.randint(-50, w + 50)
        cy = rng.randint(-50, h + 50)
        rx = rng.randint(60, 170)
        ry = rng.randint(60, 170)
        col = tuple(rand_color(rng, 0, 255))
        alpha = int(rng.randint(25, 65))
        # PIL ImageDraw doesn't support alpha on RGB; fake by mixing with bg
        mixed = tuple(int((bg[i] * (255 - alpha) + col[i] * alpha) / 255) for i in range(3))
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=mixed)

    # Shirt / shoulders
    shoulder_y = int(h * 0.72)
    d.rounded_rectangle(
        (int(w * 0.15), shoulder_y - 260, int(w * 0.85), h - 40),
        radius=80,
        fill=tuple(shirt),
    )

    # neck
    neck_w = 90
    neck_h = 85
    nx1 = face_center[0] - neck_w // 2
    ny1 = face_center[1] + int(face_h * 0.22)
    d.rounded_rectangle((nx1, ny1, nx1 + neck_w, ny1 + neck_h), radius=22, fill=tuple(skin))

    # Face
    x1 = face_center[0] - face_w // 2
    y1 = face_center[1] - face_h // 2
    x2 = x1 + face_w
    y2 = y1 + face_h

    if face_shape == "square":
        d.rounded_rectangle((x1, y1, x2, y2), radius=40, fill=tuple(skin))
    else:
        d.ellipse((x1, y1, x2, y2), fill=tuple(skin))

    # Hair base
    hair_top = y1 - int(face_h * 0.15)
    if hair_style == "bald":
        # Slight bald cap shine
        d.ellipse((x1 - 10, hair_top, x2 + 10, y1 + int(face_h * 0.12)), fill=tuple(skin))
        # subtle edges
        d.ellipse((x1 - 10, hair_top, x2 + 10, y1 + int(face_h * 0.12)), outline=(50, 20, 20), width=2)
    elif hair_style == "short":
        d.rectangle((x1 - 40, hair_top + 10, x2 + 40, y1 + int(face_h * 0.2)), fill=tuple(hair))
        # front curve
        d.pieslice((x1 - 80, hair_top - 80, x2 + 80, y1 + 160), 180, 360, fill=tuple(hair))
        # sides
        d.rectangle((x1 - 90, hair_top + 40, x1 + 30, y1 + 120), fill=tuple(hair))
        d.rectangle((x2 - 30, hair_top + 40, x2 + 90, y1 + 120), fill=tuple(hair))
    elif hair_style == "sidepart":
        # cap
        d.ellipse((x1 - 70, hair_top - 30, x2 + 70, y1 + int(face_h * 0.28)), fill=tuple(hair))
        # part line
        px = rng.randint(int(w * 0.48), int(w * 0.55))
        d.line((px, hair_top, px - 80, y1 + 120), fill=(0, 0, 0), width=8)
        # fringe
        d.pieslice((x1 - 80, hair_top - 100, x2 + 40, y1 + 200), 180, 290, fill=tuple(hair))
    else:  # curly
        d.ellipse((x1 - 90, hair_top - 20, x2 + 90, y1 + int(face_h * 0.32)), fill=tuple(hair))
        # curls overlay
        for i in range(14):
            cx = rng.randint(x1 - 60, x2 + 60)
            cy = rng.randint(hair_top - 10, y1 + 120)
            r = rng.randint(22, 48)
            d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=tuple(hair), width=6)

    # Beard
    if beard_enabled:
        beard_col = tuple(hair)
        # Beard shape
        d.polygon([
            (face_center[0] - int(face_w * 0.18), int(face_center[1] + face_h * 0.18)),
            (face_center[0] + int(face_w * 0.18), int(face_center[1] + face_h * 0.18)),
            (face_center[0] + int(face_w * 0.24), int(face_center[1] + face_h * 0.52)),
            (face_center[0] - int(face_w * 0.24), int(face_center[1] + face_h * 0.52)),
        ], fill=beard_col)

        # Add chin highlight by mixing with skin
        mix = tuple(int((skin[i] * 0.55 + beard_col[i] * 0.45)) for i in range(3))
        d.ellipse((face_center[0] - 90, face_center[1] + 170, face_center[0] + 90, face_center[1] + 340), fill=mix)

    # Eyes
    eye_y = face_center[1] - int(face_h * 0.05)
    eye_dx = int(face_w * 0.18)
    for side in [-1, 1]:
        ex = face_center[0] + side * eye_dx
        d.ellipse((ex - 28, eye_y - 18, ex + 28, eye_y + 18), fill=(255, 255, 255))
        pupil = (rng.randint(35, 70), rng.randint(35, 70), rng.randint(20, 60))
        d.ellipse((ex - 10, eye_y - 8, ex + 10, eye_y + 8), fill=pupil)
        # eyelid line
        d.arc((ex - 36, eye_y - 26, ex + 36, eye_y + 26), 200, 340, fill=(80, 50, 40), width=5)

    # Nose
    d.line((face_center[0], eye_y + 25, face_center[0] + int(face_w * 0.03), eye_y + 95), fill=(140, 110, 100), width=6)
    d.ellipse((face_center[0] - 10, eye_y + 70, face_center[0] + 20, eye_y + 105), fill=(160, 125, 110))

    # Mouth / smile
    mouth_y = int(face_center[1] + face_h * 0.25)
    mouth_w = int(face_w * 0.18)
    smile = rng.choice(["smile", "neutral"])
    if smile == "smile":
        d.arc((face_center[0] - mouth_w, mouth_y - 30, face_center[0] + mouth_w, mouth_y + 40), 200, 340, fill=(120, 60, 60), width=6)
    else:
        d.line((face_center[0] - mouth_w, mouth_y, face_center[0] + mouth_w, mouth_y), fill=(120, 60, 60), width=6)

    # Cheeks tint
    cheek = (int(skin[0] * 0.85), int(skin[1] * 0.65), int(skin[2] * 0.65))
    d.ellipse((face_center[0] - eye_dx - 70, eye_y + 10, face_center[0] - eye_dx - 10, eye_y + 60), fill=cheek)
    d.ellipse((face_center[0] + eye_dx + 10, eye_y + 10, face_center[0] + eye_dx + 70, eye_y + 60), fill=cheek)

    # Glasses
    if glasses_enabled:
        frame = (40, 40, 50)
        lens_col = (200, 235, 255)
        for side in [-1, 1]:
            ex = face_center[0] + side * eye_dx
            d.ellipse((ex - 44, eye_y - 34, ex + 44, eye_y + 34), outline=frame, width=6)
            d.ellipse((ex - 34, eye_y - 24, ex + 34, eye_y + 24), outline=None, fill=lens_col)
        d.line((face_center[0] - 44, eye_y, face_center[0] + 44, eye_y), fill=frame, width=8)

    # Shirt accents
    # add subtle pattern lines
    for i in range(10):
        x = rng.randint(int(w * 0.2), int(w * 0.8))
        y = rng.randint(int(h * 0.55), int(h * 0.86))
        if rng.random() < 0.5:
            d.line((x, y, x + rng.randint(-60, 60), y + rng.randint(0, 80)), fill=(255, 255, 255), width=3)

    # Export to JPEG
    jpg_bytes = None
    jpeg_out.parent.mkdir(parents=True, exist_ok=True)
    img.save(jpeg_out, format="JPEG", quality=95, optimize=True)

    # Remove metadata: for generated images, Pillow won't add much; but we can strip by re-saving already done.
    return sha256_file(jpeg_out)


def draw_service(jpeg_out: Path, category_slug: str, seed: int) -> str:
    rng = random.Random(seed)

    w, h = 1280, 720  # landscape
    # Background gradient-ish bands
    bg1 = rand_color(rng, 30, 150)
    bg2 = rand_color(rng, 150, 240)

    img = Image.new("RGB", (w, h), bg1)
    d = ImageDraw.Draw(img)

    # banding
    for i in range(20):
        y1 = int(i * h / 20)
        y2 = int((i + 1) * h / 20)
        col = tuple(int(bg1[j] * (1 - i / 20) + bg2[j] * (i / 20)) for j in range(3))
        d.rectangle((0, y1, w, y2), fill=col)

    # Palette by category
    palette = {
        "plumber": ((0, 140, 255), (10, 70, 160), (0, 170, 120)),
        "electrician": ((255, 200, 0), (255, 120, 0), (40, 40, 60)),
        "carpenter": ((160, 90, 40), (110, 70, 30), (40, 120, 90)),
        "cleaner": ((0, 190, 140), (0, 120, 170), (10, 60, 60)),
        "painter": ((220, 60, 60), (120, 50, 160), (20, 80, 120)),
        "gardener": ((50, 170, 90), (120, 200, 70), (30, 60, 30)),
        "ac-repair": ((40, 160, 220), (0, 110, 170), (220, 220, 255)),
        "appliance-repair": ((90, 90, 110), (20, 140, 120), (250, 160, 60)),
    }[category_slug]

    c1, c2, c3 = palette

    # Center area cards
    card_margin = 70
    card = (card_margin, 80, w - card_margin, h - 80)
    d.rounded_rectangle(card, radius=50, fill=(255, 255, 255))
    d.rounded_rectangle(card, radius=50, outline=(0, 0, 0), width=6)

    # Icon area
    icon_cx = w // 2
    icon_top = 140
    icon_h = h - 220

    def draw_tool_box(x, y, ww, hh, fill, outline=None, radius=30):
        if outline is None:
            outline = (30, 30, 30)
        d.rounded_rectangle((x, y, x + ww, y + hh), radius=radius, fill=fill, outline=outline, width=6)

    # Category-specific icons
    if category_slug == "plumber":
        # pipe
        d.ellipse((icon_cx - 190, icon_top + 60, icon_cx - 50, icon_top + 200), fill=c1, outline=c2, width=6)
        d.rectangle((icon_cx - 90, icon_top + 85, icon_cx + 100, icon_top + 175), fill=c1, outline=c2, width=6)
        d.ellipse((icon_cx + 40, icon_top + 60, icon_cx + 180, icon_top + 200), fill=c1, outline=c2, width=6)
        # wrench
        draw_tool_box(icon_cx - 360, icon_top + 230, 220, 170, fill=c2, outline=c1, radius=38)
        d.line((icon_cx - 330, icon_top + 260, icon_cx - 140, icon_top + 420), fill=(240, 240, 240), width=10)
        d.ellipse((icon_cx - 155, icon_top + 300, icon_cx - 80, icon_top + 370), fill=c3, outline=c2, width=6)
        # small wrench circle
        d.ellipse((icon_cx - 100, icon_top + 260, icon_cx - 30, icon_top + 330), fill=c3)

    elif category_slug == "electrician":
        # bulb
        d.ellipse((icon_cx - 140, icon_top + 110, icon_cx + 140, icon_top + 420), fill=c1, outline=c2, width=6)
        # base
        d.rectangle((icon_cx - 70, icon_top + 330, icon_cx + 70, icon_top + 430), fill=c2, outline=c3, width=6)
        # rays
        for ang in range(-60, 61, 30):
            import math
            a = ang * math.pi / 180
            x1 = icon_cx + int(math.cos(a) * 190)
            y1 = icon_top + 280 + int(math.sin(a) * 190)
            x2 = icon_cx + int(math.cos(a) * 80)
            y2 = icon_top + 280 + int(math.sin(a) * 80)
            d.line((x1, y1, x2, y2), fill=(255, 255, 255), width=10)
        # wire
        d.arc((icon_cx - 360, icon_top + 180, icon_cx - 80, icon_top + 520), 200, 320, fill=c3, width=18)
        d.arc((icon_cx + 80, icon_top + 180, icon_cx + 360, icon_top + 520), 210, 330, fill=c3, width=18)
        # bolt
        d.polygon([(icon_cx + 240, icon_top + 190), (icon_cx + 120, icon_top + 250), (icon_cx + 190, icon_top + 290), (icon_cx + 90, icon_top + 390), (icon_cx + 250, icon_top + 330), (icon_cx + 180, icon_top + 280)], fill=c2, outline=c3)

    elif category_slug == "carpenter":
        # wood plank
        draw_tool_box(icon_cx - 320, icon_top + 150, 640, 260, fill=c1, outline=c2, radius=55)
        for i in range(8):
            y = icon_top + 190 + i * 30
            d.line((icon_cx - 300, y, icon_cx + 300, y), fill=c2, width=6)
        # hammer
        d.rectangle((icon_cx - 420, icon_top + 420, icon_cx - 330, icon_top + 565), fill=c3, outline=c2, width=6,)
        d.rectangle((icon_cx - 470, icon_top + 360, icon_cx - 330, icon_top + 420), fill=c2, outline=c3, width=6)
        d.rounded_rectangle((icon_cx - 500, icon_top + 420, icon_cx - 320, icon_top + 565), radius=40, fill=c1, outline=c2, width=6)
        d.polygon([(icon_cx - 510, icon_top + 380), (icon_cx - 380, icon_top + 380), (icon_cx - 450, icon_top + 330)], fill=c2)
        # hammer head
        d.rounded_rectangle((icon_cx - 460, icon_top + 360, icon_cx - 350, icon_top + 430), radius=30, fill=c3, outline=c2, width=6)

    elif category_slug == "cleaner":
        # bucket
        d.ellipse((icon_cx - 220, icon_top + 210, icon_cx + 220, icon_top + 540), fill=c1, outline=c2, width=8)
        d.rectangle((icon_cx - 260, icon_top + 270, icon_cx + 260, icon_top + 520), fill=c1, outline=c2, width=8)
        # bucket rim
        d.rounded_rectangle((icon_cx - 260, icon_top + 150, icon_cx + 260, icon_top + 290), radius=60, fill=c2, outline=c3, width=8)
        # spray bottle
        draw_tool_box(icon_cx + 250, icon_top + 160, 250, 380, fill=c3, outline=c2, radius=40)
        d.rectangle((icon_cx + 360, icon_top + 90, icon_cx + 430, icon_top + 170), fill=c2, outline=c3, width=8)
        d.ellipse((icon_cx + 320, icon_top + 220, icon_cx + 420, icon_top + 420), fill=(255, 255, 255), outline=c2, width=6)
        # droplets
        for i in range(6):
            x = icon_cx + 70 + i * 40
            y = icon_top + 430 - (i % 2) * 20
            d.ellipse((x, y, x + 28, y + 28), fill=c2)

    elif category_slug == "painter":
        # roller
        draw_tool_box(icon_cx - 430, icon_top + 240, 460, 220, fill=c1, outline=c2, radius=60)
        d.rounded_rectangle((icon_cx - 430, icon_top + 270, icon_cx - 60, icon_top + 360), radius=50, fill=c3, outline=c2, width=6)
        # roller handle
        d.rectangle((icon_cx - 90, icon_top + 160, icon_cx + 320, icon_top + 260), fill=c2, outline=c3, width=8)
        d.rectangle((icon_cx + 250, icon_top + 130, icon_cx + 340, icon_top + 290), fill=c3, outline=c2, width=8)
        # paint blob
        for i in range(10):
            x = icon_cx + 40 + i * 28
            y = icon_top + 420 + (i % 2) * 16
            d.ellipse((x, y, x + 24, y + 24), fill=c1, outline=c2, width=4)

    elif category_slug == "gardener":
        # plant
        d.rounded_rectangle((icon_cx - 90, icon_top + 170, icon_cx + 90, icon_top + 520), radius=40, fill=c2, outline=c1, width=8)
        # leaves
        for sgn in [-1, 1]:
            for i in range(4):
                cx = icon_cx + sgn * (60 + i * 20)
                cy = icon_top + 230 + i * 70
                d.ellipse((cx - 80, cy - 50, cx + 80, cy + 50), fill=c1, outline=c2, width=6)
        # pot
        draw_tool_box(icon_cx - 260, icon_top + 430, 520, 240, fill=c3, outline=c2, radius=60)
        # soil lines
        for i in range(6):
            y = icon_top + 480 + i * 22
            d.line((icon_cx - 230, y, icon_cx + 230, y), fill=c2, width=6)

    elif category_slug == "ac-repair":
        # air conditioner unit
        draw_tool_box(icon_cx - 380, icon_top + 210, 760, 320, fill=c1, outline=c2, radius=60)
        d.rectangle((icon_cx - 260, icon_top + 260, icon_cx + 260, icon_top + 350), fill=c3, outline=c2, width=8)
        # vents
        for i in range(16):
            x = icon_cx - 240 + i * 30
            d.rectangle((x, icon_top + 270, x + 18, icon_top + 340), fill=c2)
        # fan blades waves
        for i in range(5):
            d.arc((icon_cx - 200, icon_top + 220, icon_cx + 200, icon_top + 420), 200 + i * 10, 340 + i * 10, fill=c3, width=10)
        # cool icon
        d.ellipse((icon_cx - 480, icon_top + 180, icon_cx - 320, icon_top + 340), fill=c3, outline=c2, width=8)
        d.ellipse((icon_cx - 450, icon_top + 210, icon_cx - 340, icon_top + 310), fill=c1, outline=c2, width=8)
        d.ellipse((icon_cx - 430, icon_top + 240, icon_cx - 350, icon_top + 300), fill=c2, outline=c3, width=6)

    else:  # appliance-repair
        # washing machine
        draw_tool_box(icon_cx - 320, icon_top + 180, 640, 380, fill=c1, outline=c2, radius=70)
        # door
        d.ellipse((icon_cx - 170, icon_top + 250, icon_cx + 170, icon_top + 540), fill=c3, outline=c2, width=10)
        # dial
        d.ellipse((icon_cx - 70, icon_top + 330, icon_cx + 70, icon_top + 470), fill=(255, 255, 255), outline=c2, width=8)
        # toolbox
        draw_tool_box(icon_cx + 240, icon_top + 120, 300, 200, fill=c2, outline=c3, radius=55)
        d.rectangle((icon_cx + 260, icon_top + 150, icon_cx + 520, icon_top + 190), fill=c3, outline=c2, width=6)
        # toolbox handle
        d.arc((icon_cx + 270, icon_top + 165, icon_cx + 500, icon_top + 245), 180, 360, fill=c3, width=10)
        # small tools
        d.rectangle((icon_cx - 70, icon_top + 560, icon_cx + 80, icon_top + 610), fill=c3, outline=c2, width=6)
        d.polygon([(icon_cx + 110, icon_top + 560), (icon_cx + 180, icon_top + 595), (icon_cx + 110, icon_top + 630)], fill=c2, outline=c3)

    # Subtle “title band” with no text (just color blocks) 
    d.rounded_rectangle((card[0] + 20, card[1] + 20, card[2] - 20, card[1] + 80), radius=30, fill=c3)
    for i in range(6):
        x = card[0] + 50 + i * 120
        d.ellipse((x - 18, card[1] + 35, x + 18, card[1] + 70), fill=c2)

    jpeg_out.parent.mkdir(parents=True, exist_ok=True)
    jpeg_out = jpeg_out
    img.save(jpeg_out, format="JPEG", quality=95, optimize=True)
    return sha256_file(jpeg_out)


def verify_unique_hashes(folder: Path) -> int:
    hashes = {}
    for p in folder.iterdir():
        if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"}:
            h = sha256_file(p)
            hashes[h] = hashes.get(h, 0) + 1
    dup = sum(1 for v in hashes.values() if v > 1)
    return dup


def main():
    root = Path("assets")
    providers_dir = root / "provider_headshots"
    services_dir = root / "service_images"

    ensure_dir(providers_dir)
    ensure_dir(services_dir)

    for slug, _ in CATEGORIES:
        ensure_dir(services_dir / slug)

    # Provider avatars
    base_seed = 1337
    used_hashes = set()
    for i in range(1, 51):
        out = providers_dir / f"provider_{i:03d}.jpg"
        # deterministic but unique attempt
        seed = base_seed + i * 1009
        h = draw_provider(out, seed)
        if h in used_hashes:
            # in extremely unlikely case, bump seed and redraw
            j = 1
            while True:
                seed2 = seed + j * 99991
                h2 = draw_provider(out, seed2)
                if h2 not in used_hashes:
                    h = h2
                    break
                j += 1
        used_hashes.add(h)

    # Service images
    used_hashes_services = set()
    for slug, _label in CATEGORIES:
        for i in range(1, 11):
            out = services_dir / slug / f"{slug.replace('-', '_')}_{i:03d}.jpg"
            seed = 4242 + (hash(slug) % 100000) + i * 7777
            h = draw_service(out, slug, seed)
            if h in used_hashes_services or h in used_hashes:
                j = 1
                while True:
                    seed2 = seed + j * 88889
                    h2 = draw_service(out, slug, seed2)
                    if h2 not in used_hashes_services and h2 not in used_hashes:
                        h = h2
                        break
                    j += 1
            used_hashes_services.add(h)

    # Verify counts
    provider_files = list(providers_dir.glob("provider_*.jpg"))
    service_counts = {slug: len(list((services_dir / slug).glob("*.jpg"))) for slug, _ in CATEGORIES}

    all_jpgs = []
    all_jpgs.extend(provider_files)
    for slug, _ in CATEGORIES:
        all_jpgs.extend(list((services_dir / slug).glob("*.jpg")))

    # SHA-256 duplicates
    hashes = {}
    dup_pairs = 0
    for p in all_jpgs:
        h = sha256_file(p)
        hashes[h] = hashes.get(h, 0) + 1

    duplicate_hash_count = sum(1 for v in hashes.values() if v > 1)

    print(f"Providers: {len(provider_files)}")
    for slug, label in CATEGORIES:
        print(f"{label}: {service_counts[slug]}")

    print(f"Total images generated: {len(all_jpgs)}")
    print(f"Duplicate hash groups: {duplicate_hash_count}")

    if len(provider_files) != 50:
        raise SystemExit("Provider image count verification failed")

    for slug, _label in CATEGORIES:
        if service_counts[slug] < 10:
            raise SystemExit(f"Service image count verification failed for {slug}")

    # Duplicate check must be exact: no duplicates
    if duplicate_hash_count != 0:
        raise SystemExit("Duplicate SHA-256 hashes detected")


if __name__ == "__main__":
    main()

