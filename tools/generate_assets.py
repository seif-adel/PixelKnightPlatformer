"""Generates every image, sound and music file used by the game.

This script is a one-off, offline art/audio tool. It only uses the Python
standard library (struct, zlib, wave, math, random, os) so that the actual
game code (main.py) can stay limited to Pygame Zero, math and random, as
required. Run it once with:

    python tools/generate_assets.py

to (re)create the images/, sounds/ and music/ folders next to main.py.
"""
import math
import os
import random
import struct
import wave
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMAGES_DIR = os.path.join(ROOT, "images")
SOUNDS_DIR = os.path.join(ROOT, "sounds")
MUSIC_DIR = os.path.join(ROOT, "music")


# ---------------------------------------------------------------------------
# Minimal PNG writer (RGBA, no external dependencies).
# ---------------------------------------------------------------------------
def write_png(path, width, height, pixels):
    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    raw = bytearray()
    for y in range(height):
        raw.append(0)  # no scanline filter
        for x in range(width):
            raw += bytes(pixels[y][x])
    compressed = zlib.compress(bytes(raw), 9)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\n")
        handle.write(chunk(b"IHDR", header))
        handle.write(chunk(b"IDAT", compressed))
        handle.write(chunk(b"IEND", b""))


class Canvas:
    """Tiny drawing surface used to build sprite frames pixel by pixel."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.pixels = [[(0, 0, 0, 0)] * width for _ in range(height)]

    def set_pixel(self, x, y, color):
        x, y = int(x), int(y)
        if 0 <= x < self.width and 0 <= y < self.height:
            self.pixels[y][x] = color

    def fill_rect(self, x0, y0, w, h, color):
        for y in range(y0, y0 + h):
            for x in range(x0, x0 + w):
                self.set_pixel(x, y, color)

    def fill_ellipse(self, cx, cy, rx, ry, color):
        rx = max(rx, 1)
        ry = max(ry, 1)
        for y in range(int(cy - ry), int(cy + ry) + 1):
            for x in range(int(cx - rx), int(cx + rx) + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1.0:
                    self.set_pixel(x, y, color)

    def fill_triangle(self, ax, ay, bx, by, cx, cy, color):
        def sign(p1x, p1y, p2x, p2y, p3x, p3y):
            return (p1x - p3x) * (p2y - p3y) - (p2x - p3x) * (p1y - p3y)

        min_x, max_x = int(min(ax, bx, cx)), int(max(ax, bx, cx))
        min_y, max_y = int(min(ay, by, cy)), int(max(ay, by, cy))
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                d1 = sign(x, y, ax, ay, bx, by)
                d2 = sign(x, y, bx, by, cx, cy)
                d3 = sign(x, y, cx, cy, ax, ay)
                has_neg = d1 < 0 or d2 < 0 or d3 < 0
                has_pos = d1 > 0 or d2 > 0 or d3 > 0
                if not (has_neg and has_pos):
                    self.set_pixel(x, y, color)

    def save(self, name):
        path = os.path.join(IMAGES_DIR, name + ".png")
        write_png(path, self.width, self.height, self.pixels)


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
HELMET = (176, 182, 194, 255)
VISOR = (40, 40, 48, 255)
TUNIC = (58, 116, 206, 255)
TUNIC_HURT = (206, 66, 58, 255)
BELT = (94, 70, 32, 255)
LEG = (70, 52, 40, 255)
BOOT = (36, 34, 32, 255)
SLIME_BODY = (78, 198, 96, 255)
SLIME_DARK = (46, 150, 64, 255)
BAT_BODY = (52, 40, 70, 255)
BAT_WING = (78, 60, 104, 255)
EYE_WHITE = (250, 250, 250, 255)
EYE_BLACK = (20, 20, 20, 255)
GOLD = (250, 200, 60, 255)
GOLD_LIGHT = (255, 235, 150, 255)
POLE = (90, 90, 90, 255)
FLAG_RED = (210, 60, 60, 255)


def draw_hero(leg_shift, arm_shift, bob, tunic_color=TUNIC):
    canvas = Canvas(32, 40)
    top = 6 + bob
    canvas.fill_ellipse(16, top + 2, 7, 7, HELMET)
    canvas.fill_rect(11, top + 1, 10, 2, VISOR)
    canvas.fill_rect(10, top + 8, 12, 13, tunic_color)
    canvas.fill_rect(9, top + 19, 14, 3, BELT)
    canvas.fill_rect(6 - arm_shift, top + 9, 4, 10, tunic_color)
    canvas.fill_rect(22 + arm_shift, top + 9, 4, 10, tunic_color)
    canvas.fill_rect(11 - leg_shift, 22 + bob, 5, 11, LEG)
    canvas.fill_rect(17 + leg_shift, 22 + bob, 5, 11, LEG)
    canvas.fill_rect(11 - leg_shift, 32 + bob, 5, 4, BOOT)
    canvas.fill_rect(17 + leg_shift, 32 + bob, 5, 4, BOOT)
    return canvas


def generate_hero_frames():
    draw_hero(0, 0, 0).save("hero_idle_0")
    draw_hero(0, 1, -1).save("hero_idle_1")
    for i, (leg, arm, bob) in enumerate([(3, 3, 0), (0, 0, -1), (-3, -3, 0), (0, 0, -1)]):
        draw_hero(leg, arm, bob).save(f"hero_walk_{i}")
    canvas = Canvas(32, 40)
    canvas.fill_ellipse(16, 8, 7, 7, HELMET)
    canvas.fill_rect(11, 7, 10, 2, VISOR)
    canvas.fill_rect(10, 14, 12, 13, TUNIC)
    canvas.fill_rect(9, 25, 14, 3, BELT)
    canvas.fill_rect(4, 15, 4, 9, TUNIC)
    canvas.fill_rect(24, 15, 4, 9, TUNIC)
    canvas.fill_rect(10, 27, 6, 8, LEG)
    canvas.fill_rect(16, 27, 6, 8, LEG)
    canvas.fill_rect(10, 33, 6, 3, BOOT)
    canvas.fill_rect(16, 33, 6, 3, BOOT)
    canvas.save("hero_jump")
    draw_hero(0, 0, 0, tunic_color=TUNIC_HURT).save("hero_hurt")


def draw_slime(rx, ry, foot_shift):
    canvas = Canvas(32, 26)
    base_y = 22
    canvas.fill_ellipse(16, base_y - ry, rx, ry, SLIME_BODY)
    canvas.fill_rect(11 - foot_shift, 20, 5, 3, SLIME_DARK)
    canvas.fill_rect(17 + foot_shift, 20, 5, 3, SLIME_DARK)
    eye_y = base_y - ry - 1
    canvas.fill_ellipse(12, eye_y, 3, 3, EYE_WHITE)
    canvas.fill_ellipse(20, eye_y, 3, 3, EYE_WHITE)
    canvas.fill_ellipse(12, eye_y, 1, 1, EYE_BLACK)
    canvas.fill_ellipse(20, eye_y, 1, 1, EYE_BLACK)
    return canvas


def generate_slime_frames():
    draw_slime(12, 10, 0).save("slime_idle_0")
    draw_slime(12, 9, 0).save("slime_idle_1")
    pattern = [(13, 8, 3), (11, 11, 0), (13, 8, -3), (11, 11, 0)]
    for i, (rx, ry, foot) in enumerate(pattern):
        draw_slime(rx, ry, foot).save(f"slime_walk_{i}")


def draw_bat(wing_offset):
    canvas = Canvas(34, 24)
    cx, cy = 17, 12
    canvas.fill_triangle(cx - 4, cy, cx - 16, cy - wing_offset, cx - 4, cy + 6, BAT_WING)
    canvas.fill_triangle(cx + 4, cy, cx + 16, cy - wing_offset, cx + 4, cy + 6, BAT_WING)
    canvas.fill_ellipse(cx, cy, 6, 5, BAT_BODY)
    canvas.fill_ellipse(cx - 2, cy - 1, 1, 1, (200, 40, 40, 255))
    canvas.fill_ellipse(cx + 2, cy - 1, 1, 1, (200, 40, 40, 255))
    return canvas


def generate_bat_frames():
    draw_bat(1).save("bat_idle_0")
    draw_bat(3).save("bat_idle_1")
    for i, offset in enumerate([10, 4, -4, 4]):
        draw_bat(offset).save(f"bat_fly_{i}")


def generate_coin_frames():
    widths = [8, 5, 2, 5]
    for i, rx in enumerate(widths):
        canvas = Canvas(20, 20)
        canvas.fill_ellipse(10, 10, rx, 8, GOLD)
        if rx > 3:
            canvas.fill_ellipse(10, 10, max(rx - 3, 1), 4, GOLD_LIGHT)
        canvas.save(f"coin_{i}")


def generate_flag_frames():
    for i, tip_shift in enumerate([0, 5]):
        canvas = Canvas(30, 46)
        canvas.fill_rect(3, 0, 3, 46, POLE)
        canvas.fill_triangle(6, 2, 6, 16, 6 + 18 + tip_shift, 9, FLAG_RED)
        canvas.save(f"flag_{i}")


def generate_platform_tile():
    canvas = Canvas(40, 40)
    canvas.fill_rect(0, 0, 40, 40, (120, 82, 46, 255))
    canvas.fill_rect(0, 0, 40, 8, (74, 168, 74, 255))
    rng = random.Random(7)
    for _ in range(14):
        x = rng.randint(1, 37)
        y = rng.randint(10, 37)
        canvas.fill_rect(x, y, 2, 2, (96, 64, 34, 255))
    canvas.save("platform_tile")


def generate_background():
    canvas = Canvas(800, 600)
    top = (140, 200, 235)
    bottom = (222, 240, 250)
    for y in range(600):
        t = y / 599
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(800):
            canvas.pixels[y][x] = (r, g, b, 255)
    for cx, cy, rr in [(120, 470, 90), (330, 500, 120), (600, 480, 100), (740, 500, 80)]:
        canvas.fill_ellipse(cx, cy, rr, rr // 2, (96, 168, 96, 255))
    for cx, cy in [(120, 90), (420, 60), (650, 110)]:
        for dx, dy, rr in [(-18, 4, 16), (0, 0, 20), (18, 4, 16)]:
            canvas.fill_ellipse(cx + dx, cy + dy, rr, rr - 4, (255, 255, 255, 230))
    canvas.save("background")


def generate_hearts():
    for name, color in [("heart_full", (216, 48, 64, 255)), ("heart_empty", (110, 110, 110, 255))]:
        canvas = Canvas(20, 18)
        canvas.fill_ellipse(6, 6, 5, 5, color)
        canvas.fill_ellipse(13, 6, 5, 5, color)
        canvas.fill_triangle(1, 8, 19, 8, 10, 17, color)
        canvas.save(name)


# ---------------------------------------------------------------------------
# Sound synthesis (mono 16-bit PCM WAV, standard-library only).
# ---------------------------------------------------------------------------
SAMPLE_RATE = 22050


def _envelope(i, n, fade):
    if n <= 1:
        return 1.0
    if i < fade:
        return i / fade
    if i > n - fade:
        return max(0.0, (n - i) / fade)
    return 1.0


def synthesize(notes, path, volume=0.35, shape="sine"):
    frames = bytearray()
    for freq, duration in notes:
        n = max(1, int(SAMPLE_RATE * duration))
        fade = max(1, int(n * 0.1))
        for i in range(n):
            if freq <= 0:
                sample = 0.0
            else:
                t = i / SAMPLE_RATE
                wave_value = math.sin(2 * math.pi * freq * t)
                if shape == "square":
                    wave_value = 1.0 if wave_value >= 0 else -1.0
                sample = wave_value * volume * _envelope(i, n, fade)
            frames += struct.pack("<h", int(max(-1.0, min(1.0, sample)) * 32767))
    with wave.open(path, "w") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        handle.writeframes(bytes(frames))


def generate_sounds():
    synthesize([(500, 0.05), (900, 0.1)], os.path.join(SOUNDS_DIR, "jump.wav"))
    synthesize([(988, 0.08), (1319, 0.12)], os.path.join(SOUNDS_DIR, "coin.wav"))
    synthesize([(160, 0.06), (110, 0.1)], os.path.join(SOUNDS_DIR, "hit.wav"), shape="square", volume=0.3)
    synthesize([(220, 0.05), (90, 0.08)], os.path.join(SOUNDS_DIR, "stomp.wav"), volume=0.3)
    synthesize(
        [(523, 0.15), (659, 0.15), (784, 0.15), (1046, 0.25)],
        os.path.join(SOUNDS_DIR, "win.wav"),
    )
    synthesize(
        [(392, 0.2), (330, 0.2), (262, 0.3)],
        os.path.join(SOUNDS_DIR, "lose.wav"),
        volume=0.3,
    )


def generate_music():
    melody_notes = [392, 440, 523, 440, 392, 330, 349, 392]
    notes = [(freq, 0.5) for freq in melody_notes]
    notes += [(freq * 2, 0.4) for freq in melody_notes]
    synthesize(notes, os.path.join(MUSIC_DIR, "theme.wav"), volume=0.22)


def main():
    for directory in (IMAGES_DIR, SOUNDS_DIR, MUSIC_DIR):
        os.makedirs(directory, exist_ok=True)
    generate_hero_frames()
    generate_slime_frames()
    generate_bat_frames()
    generate_coin_frames()
    generate_flag_frames()
    generate_platform_tile()
    generate_background()
    generate_hearts()
    generate_sounds()
    generate_music()
    print("Assets generated in:", IMAGES_DIR, SOUNDS_DIR, MUSIC_DIR)


if __name__ == "__main__":
    main()
