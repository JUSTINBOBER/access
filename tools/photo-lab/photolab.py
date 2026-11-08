#!/usr/bin/env python3
"""Photo Lab: a small Photoshop-style toolkit for Paws & Play images.

Everything runs on this Mac. Nothing is uploaded.

Commands (run with tools/photo-lab/lab, see README.md):
  cutout   <in> <out.png> [--mode subject|person] [--instances all|1,2]
  refine   <cutout.png> <out.png> [--shrink 1] [--feather 1.2]
  match    <cutout.png> <reference.jpg> <out.png> [--strength 0.7]
  adjust   <in> <out> [--brightness 1] [--contrast 1] [--saturation 1] [--warmth 0]
  compose  <recipe.json>
  preview  <cutout.png> <out.jpg>          (shows a cutout on a checkerboard)
  web      <in> <out-base>                 (exports -sm.webp and .webp for the site)
"""
import argparse
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
LIFT = os.path.join(HERE, "bin", "lift")


# ---------- basics ----------
def load(path):
    """Open an image the right way up, as RGBA."""
    return ImageOps.exif_transpose(Image.open(path)).convert("RGBA")


def save(img, path, quality=90):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".jpg", ".jpeg"):
        img.convert("RGB").save(path, quality=quality, optimize=True)
    elif ext == ".webp":
        img.save(path, quality=quality, method=6)
    else:
        img.save(path, optimize=True)
    return path


def trim(img, pad=0):
    """Crop away empty transparent space around a cutout."""
    box = img.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if not box:
        return img
    l, t, r, b = box
    return img.crop((max(l - pad, 0), max(t - pad, 0), min(r + pad, img.width), min(b + pad, img.height)))


# ---------- cutouts (select subject + mask) ----------
def cutout(src, out, mode="subject", instances="all"):
    """Lift a person or pet off its background (Apple Vision, on-device)."""
    if not os.path.exists(LIFT):
        sys.exit("The cutout tool isn't built yet. Run: xcrun swiftc -O lift.swift -o bin/lift")
    subprocess.run([LIFT, src, out, "--mode", mode, "--instances", instances], check=True)
    return out


def refine(img, shrink=1, feather=1.2):
    """Clean the cutout edge: pull it in slightly to remove halos, then soften it.
    (Like Photoshop's Select and Mask > Shift Edge / Feather.)"""
    a = img.getchannel("A")
    if shrink > 0:
        a = a.filter(ImageFilter.MinFilter(int(shrink) * 2 + 1))
    if feather > 0:
        a = a.filter(ImageFilter.GaussianBlur(feather))
    out = img.copy()
    out.putalpha(a)
    return defringe(out)


def defringe(img, radius=3):
    """Replace leftover background color in semi-transparent edge pixels with the subject's own color.
    (Like Photoshop's Decontaminate Colors.)"""
    rgba = np.asarray(img).astype(np.float32)
    alpha = rgba[..., 3:4] / 255.0
    solid = (alpha > 0.95).astype(np.float32)
    pm = Image.fromarray((rgba[..., :3] * solid).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    wt = Image.fromarray((solid[..., 0] * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius))
    pm = np.asarray(pm).astype(np.float32)
    wt = np.asarray(wt).astype(np.float32)[..., None] / 255.0
    spread = np.where(wt > 0.01, pm / np.maximum(wt, 1e-3), rgba[..., :3])
    edge = ((alpha > 0.02) & (alpha < 0.95)).astype(np.float32)
    rgb = rgba[..., :3] * (1 - edge) + spread * edge
    return Image.fromarray(np.dstack([rgb, rgba[..., 3:]]).clip(0, 255).astype(np.uint8))


# ---------- color & tone ----------
def _lab_stats(img, mask=None):
    lab = np.asarray(img.convert("RGB").convert("LAB")).astype(np.float32).reshape(-1, 3)
    if mask is not None:
        m = np.asarray(mask).reshape(-1) > 200
        if m.sum() > 50:
            lab = lab[m]
    return lab.mean(0), lab.std(0) + 1e-5


def color_match(fg, reference, strength=0.5):
    """Match a cutout's colors and brightness to the scene it's going into.
    (Like Photoshop's Image > Adjustments > Match Color.)"""
    alpha = fg.getchannel("A")
    src_mean, src_std = _lab_stats(fg, alpha)
    ref_mean, ref_std = _lab_stats(reference.convert("RGB"))
    lab = np.asarray(fg.convert("RGB").convert("LAB")).astype(np.float32)
    # Cap contrast/saturation changes so skin and fur never go neon or flat
    ratio = np.clip(ref_std / src_std, 0.85, 1.15)
    shift = ref_mean - src_mean
    shift[1:] = np.clip(shift[1:], -6, 6)          # only a gentle color-temperature nudge
    matched = (lab - src_mean) * ratio + src_mean + shift
    # brightness follows the scene most; color follows it only a little
    matched = lab + (matched - lab) * np.array([strength, strength * 0.5, strength * 0.5])
    lab_u8 = np.ascontiguousarray(matched.clip(0, 255).astype(np.uint8))
    rgb = Image.frombytes("LAB", fg.size, lab_u8.tobytes()).convert("RGB")
    rgb.putalpha(alpha)
    return rgb


def adjust(img, brightness=1.0, contrast=1.0, saturation=1.0, warmth=0.0):
    """Basic adjustments. warmth: -1 (cooler/bluer) .. +1 (warmer/golden)."""
    alpha = img.getchannel("A") if img.mode == "RGBA" else None
    rgb = img.convert("RGB")
    rgb = ImageEnhance.Brightness(rgb).enhance(brightness)
    rgb = ImageEnhance.Contrast(rgb).enhance(contrast)
    rgb = ImageEnhance.Color(rgb).enhance(saturation)
    if warmth:
        r, g, b = rgb.split()
        k = 1 + 0.12 * warmth
        r = r.point(lambda v: min(255, int(v * k)))
        b = b.point(lambda v: min(255, int(v / k)))
        rgb = Image.merge("RGB", (r, g, b))
    if alpha:
        rgb.putalpha(alpha)
    return rgb


def light_wrap(fg_layer, background, amount=0.35, radius=18):
    """Let background light spill softly onto the subject's edges so it sits *in* the scene.
    fg_layer and background must be the same size."""
    a = fg_layer.getchannel("A")
    inner_edge = ImageChops.subtract(a, a.filter(ImageFilter.GaussianBlur(radius / 2)))
    edge = inner_edge.point(lambda v: min(255, int(v * 3 * amount)))
    glow = background.convert("RGB").filter(ImageFilter.GaussianBlur(radius))
    rgb = Image.composite(glow, fg_layer.convert("RGB"), edge)
    rgb.putalpha(a)
    return rgb


def match_grain(img, amount=4.0, seed=7):
    """Add fine film/phone-camera noise so pasted pieces have the same texture as the photo."""
    rng = np.random.default_rng(seed)
    arr = np.asarray(img).astype(np.float32)
    noise = rng.normal(0, amount, arr.shape[:2])[..., None]
    arr[..., :3] = (arr[..., :3] + noise).clip(0, 255)
    return Image.fromarray(arr.astype(np.uint8))


def soften(img, radius=0.6):
    """Slight blur to match a softer background photo (sharpness matching)."""
    return img.filter(ImageFilter.GaussianBlur(radius))


# ---------- shadows ----------
def contact_shadow(layer, opacity=0.45, squash=0.12, blur=14, spread=1.05):
    """A soft shadow under feet/paws where the subject touches the floor.
    Returns a layer the same size as `layer` to place *beneath* it."""
    a = layer.getchannel("A")
    box = a.getbbox()
    if not box:
        return Image.new("RGBA", layer.size)
    l, t, r, b = box
    w, h = r - l, b - t
    # Flatten the silhouette onto the floor: only the parts near the ground make a dark shadow
    piece = a.crop(box).point(lambda v: int(v * opacity))
    flat_h = max(4, int(h * squash))
    flat = piece.resize((int(w * spread), flat_h), Image.LANCZOS)
    fade = Image.linear_gradient("L").resize(flat.size)          # darker at the bottom (contact point)
    flat = ImageChops.multiply(flat, fade)
    sh = Image.new("L", layer.size, 0)
    sh.paste(flat, (int(l - (w * spread - w) / 2), int(b - flat_h * 0.75)))
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    out = Image.new("RGBA", layer.size, (20, 22, 30, 0))
    out.putalpha(sh)
    return out


def drop_shadow(layer, offset=(10, 14), blur=16, opacity=0.35, color=(20, 22, 30)):
    """Soft shadow cast by the whole subject (for cutout/sticker-style graphics)."""
    a = layer.getchannel("A").point(lambda v: int(v * opacity))
    sh = Image.new("RGBA", layer.size, color + (0,))
    sh.putalpha(a)
    sh = ImageChops.offset(sh, *offset).filter(ImageFilter.GaussianBlur(blur))
    return sh


# ---------- compositing ----------
def make_background(spec, size):
    w, h = size
    if spec.get("image"):
        bg = load(spec["image"]).convert("RGB")
        if spec.get("crop"):                      # [left, top, right, bottom] as fractions of the photo
            l, t, r, b = spec["crop"]
            bg = bg.crop((int(l * bg.width), int(t * bg.height), int(r * bg.width), int(b * bg.height)))
        bg = ImageOps.fit(bg, size, Image.LANCZOS, centering=tuple(spec.get("focus", (0.5, 0.5))))
        if spec.get("blur"):                      # phone "portrait mode" background blur
            bg = bg.filter(ImageFilter.GaussianBlur(spec["blur"]))
        if spec.get("adjust"):
            bg = adjust(bg, **spec["adjust"])
        return bg.convert("RGBA")
    c1 = spec.get("color", "#FBF7F0")
    c2 = spec.get("color2")
    bg = Image.new("RGBA", size, c1)
    if c2:
        top = Image.new("RGBA", size, c1)
        bottom = Image.new("RGBA", size, c2)
        grad = Image.linear_gradient("L").resize(size)
        bg = Image.composite(bottom, top, grad)
    return bg


def cut_edges(img, threshold=0.04):
    """Which sides of a cutout were cut off by the original photo's border."""
    a = np.asarray(img.getchannel("A")) > 100
    # look a few pixels in from each border (cutout edges are slightly feathered)
    sides = {"top": a[:4].any(0), "bottom": a[-4:].any(0), "left": a[:, :4].any(1), "right": a[:, -4:].any(1)}
    return [k for k, v in sides.items() if v.mean() > threshold]


def place(canvas_size, img, x, y, scale=1.0, rotate=0.0, flip=False):
    """Put an image on a transparent layer the size of the canvas.
    x, y = where the image's bottom-center goes (0..1 of the canvas)."""
    if flip:
        img = ImageOps.mirror(img)
    if scale != 1:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    if rotate:
        img = img.rotate(rotate, resample=Image.BICUBIC, expand=True)
    layer = Image.new("RGBA", canvas_size)
    px = int(x * canvas_size[0] - img.width / 2)
    py = int(y * canvas_size[1] - img.height)
    layer.alpha_composite(img, (max(px, 0), max(py, 0)), (max(-px, 0), max(-py, 0)))
    return layer


def compose(recipe):
    """Build an image from a recipe (see README.md for the format)."""
    base_dir = recipe.get("_dir", ".")
    path = lambda p: p if os.path.isabs(p) else os.path.join(base_dir, p)
    size = tuple(recipe.get("size", (1600, 1200)))
    bg_spec = dict(recipe.get("background", {}))
    if bg_spec.get("image"):
        bg_spec["image"] = path(bg_spec["image"])
    canvas = make_background(bg_spec, size)
    bg_only = canvas.copy()

    for L in recipe.get("layers", []):
        img = load(path(L["src"]))
        edges = cut_edges(img)
        if edges:
            print(f"  note: {L['src']} is cut off on the {', '.join(edges)} edge. Hide that edge off-frame or behind something.")
        if L.get("trim", True):
            img = trim(img)
        if L.get("refine", True):
            img = refine(img, L.get("shrink", 1), L.get("feather", 1.2))
        if L.get("match", True) and bg_spec.get("image"):
            img = color_match(img, bg_only, L.get("match_strength", 0.5))
        if "adjust" in L:
            img = adjust(img, **L["adjust"])
        scale = L.get("scale", 1.0)
        if "width" in L:          # size as a fraction of the canvas width (easier than guessing a scale)
            scale = L["width"] * size[0] / img.width
        layer = place(size, img, L.get("x", 0.5), L.get("y", 0.95), scale, L.get("rotate", 0), L.get("flip", False))
        if L.get("soften"):
            layer = soften(layer, L["soften"])
        if L.get("contact_shadow", True):
            canvas.alpha_composite(contact_shadow(layer, L.get("shadow_opacity", 0.45)))
        if L.get("drop_shadow"):
            canvas.alpha_composite(drop_shadow(layer, **L["drop_shadow"]))
        if L.get("light_wrap", 0.3):
            layer = light_wrap(layer, bg_only, L.get("light_wrap", 0.3))
        canvas.alpha_composite(layer)

    out = canvas.convert("RGB")
    if recipe.get("grain", 3):
        out = match_grain(out, recipe.get("grain", 3))
    if recipe.get("finish"):
        out = adjust(out, **recipe["finish"])
    return out


# ---------- output ----------
def checker_preview(img, out, tile=24):
    """Show a cutout over a checkerboard (like Photoshop's transparency grid)."""
    bg = Image.new("RGB", img.size, "#ffffff")
    d = ImageDraw.Draw(bg)
    for yy in range(0, img.height, tile):
        for xx in range((yy // tile % 2) * tile, img.width, tile * 2):
            d.rectangle((xx, yy, xx + tile - 1, yy + tile - 1), fill="#d9dde3")
    bg.paste(img, (0, 0), img)
    bg.thumbnail((1400, 1400))
    return save(bg, out)


def export_web(img, out_base):
    """Save the two sizes the website uses: <name>.webp (1400px) and <name>-sm.webp (640px).
    Saved fresh, so no hidden camera/location data is kept."""
    img = img.convert("RGB")
    for suffix, size in (("", 1400), ("-sm", 640)):
        c = img.copy()
        c.thumbnail((size, size), Image.LANCZOS)
        save(c, f"{out_base}{suffix}.webp", quality=80)
    return f"{out_base}.webp", f"{out_base}-sm.webp"


# ---------- command line ----------
def main():
    ap = argparse.ArgumentParser(description="Paws & Play Photo Lab")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("cutout"); c.add_argument("src"); c.add_argument("out")
    c.add_argument("--mode", default="subject"); c.add_argument("--instances", default="all")
    r = sub.add_parser("refine"); r.add_argument("src"); r.add_argument("out")
    r.add_argument("--shrink", type=int, default=1); r.add_argument("--feather", type=float, default=1.2)
    m = sub.add_parser("match"); m.add_argument("src"); m.add_argument("ref"); m.add_argument("out")
    m.add_argument("--strength", type=float, default=0.7)
    a = sub.add_parser("adjust"); a.add_argument("src"); a.add_argument("out")
    for k in ("brightness", "contrast", "saturation"):
        a.add_argument(f"--{k}", type=float, default=1.0)
    a.add_argument("--warmth", type=float, default=0.0)
    co = sub.add_parser("compose"); co.add_argument("recipe"); co.add_argument("--out")
    p = sub.add_parser("preview"); p.add_argument("src"); p.add_argument("out")
    w = sub.add_parser("web"); w.add_argument("src"); w.add_argument("out_base")
    args = ap.parse_args()

    if args.cmd == "cutout":
        cutout(args.src, args.out, args.mode, args.instances)
    elif args.cmd == "refine":
        print(save(refine(load(args.src), args.shrink, args.feather), args.out))
    elif args.cmd == "match":
        print(save(color_match(load(args.src), load(args.ref), args.strength), args.out))
    elif args.cmd == "adjust":
        print(save(adjust(load(args.src), args.brightness, args.contrast, args.saturation, args.warmth), args.out))
    elif args.cmd == "compose":
        recipe = json.load(open(args.recipe))
        recipe["_dir"] = os.path.dirname(os.path.abspath(args.recipe))
        out = args.out or recipe.get("output", "composite.jpg")
        out = out if os.path.isabs(out) else os.path.join(recipe["_dir"], out)
        print(save(compose(recipe), out))
    elif args.cmd == "preview":
        print(checker_preview(load(args.src), args.out))
    elif args.cmd == "web":
        print(*export_web(load(args.src), args.out_base))


if __name__ == "__main__":
    main()
