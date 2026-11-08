# Photo Lab

A small Photoshop-style toolkit for Paws & Play images. It runs entirely on this Mac, and nothing is uploaded.
It is for editing only and is not part of the website.

Run every command from the site folder with `tools/photo-lab/lab`.

## What each tool does (and its Photoshop equivalent)

| Command | What it does | Photoshop equivalent |
|---|---|---|
| `cutout` | Lifts a person or pet off its background with Apple's on-device Vision. `--mode person` gives better hair on headshots. | Select Subject / Remove Background |
| `refine` | Pulls the edge in slightly and softens it, then removes leftover background color in the fringe. | Select and Mask, Decontaminate Colors |
| `match` | Nudges a cutout's brightness and color temperature toward a target scene. The changes are capped so skin and fur stay natural. | Match Color |
| `adjust` | Brightness, contrast, saturation and warmth. | Adjustment layers |
| `compose` | Builds a finished image from a recipe: background, layers, shadows, light wrap and grain. | Layers panel |
| `preview` | Shows a cutout on a checkerboard so you can judge the edges. | Transparency grid |
| `web` | Saves the two sizes the website uses, with no hidden camera or location data. | Export As |

## Examples

```bash
tools/photo-lab/lab cutout photo.jpg me.png --mode person
tools/photo-lab/lab preview me.png check.jpg
tools/photo-lab/lab compose my-recipe.json
tools/photo-lab/lab web finished.jpg images/pets/meet-your-sitter
```

## Recipe format (for `compose`)

```json
{
  "size": [1600, 1200],
  "background": { "color": "#E3F4F2", "color2": "#FBF7F0" },
  "layers": [
    { "src": "me.png", "x": 0.5, "y": 0.98, "width": 0.45 },
    { "src": "cat.png", "x": 0.78, "y": 0.95, "width": 0.25, "shadow_opacity": 0.4 }
  ],
  "grain": 2,
  "output": "result.jpg"
}
```

- **Background:** `background.image` uses a photo instead of a color. Layers are then automatically color-matched to it.
- **Position:** `x` and `y` place each layer's bottom-center as a fraction of the canvas, where 0.5 is the middle.
- **Size:** `width` is the layer's width as a fraction of the canvas.
- **Other layer options:**
  - `flip`, `rotate`
  - `match_strength` (0–1)
  - `light_wrap` (0–1)
  - `contact_shadow` (true/false) and `shadow_opacity`
  - `drop_shadow`
  - `soften` (blur radius to match a softer photo)
- **Cut-off warning:** if a cutout was cut off by its original photo's border, `compose` prints a warning. Hide that edge off-frame or behind another layer.

## Honest limits

- **It combines existing photos; it can't create new poses.** Hands can't be made to hold a pet, and a person can't be made to walk. Realistic "candid" shots of someone holding or walking a pet need a real photo or a generative-AI tool.
- **It works best for:** clean cutouts, branded graphics, scrapbook collages, and putting a person and pets side by side on one background.
