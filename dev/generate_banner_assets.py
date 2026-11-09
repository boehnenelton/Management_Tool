#!/usr/bin/env python3
"""
Generate minimal, sleek logo skeletons (Dark and Light, no text)
and the official Management Tool repository banner (Dark, minimal, subtle cube, no fluff).
"""

from pathlib import Path
from playwright.sync_api import sync_playwright
from PIL import Image

ASSETS_DIR = Path("/storage/emulated/0/Admin/System/tools/management_tool/assets")
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# 1. Dark Logo Skeleton (No Text)
DARK_SKELETON_SVG = """<svg width="1280" height="640" viewBox="0 0 1280 640" xmlns="http://www.w3.org/2000/svg">
  <!-- Pitch Black Substrate -->
  <rect width="1280" height="640" fill="#0A0A0C" />

  <!-- Outer Structural Boundary Inset -->
  <rect x="48" y="48" width="1184" height="544" rx="0" fill="none" stroke="#1A1A22" stroke-width="1.5" />

  <!-- Corner Precision Ticks (Zero Curvature) -->
  <path d="M 48 76 L 48 48 L 76 48" fill="none" stroke="#333340" stroke-width="2" />
  <path d="M 1204 48 L 1232 48 L 1232 76" fill="none" stroke="#333340" stroke-width="2" />
  <path d="M 48 564 L 48 592 L 76 592" fill="none" stroke="#333340" stroke-width="2" />
  <path d="M 1204 592 L 1232 592 L 1232 564" fill="none" stroke="#333340" stroke-width="2" />

  <!-- Vertical Red Accent Marker -->
  <rect x="48" y="270" width="4" height="100" rx="0" fill="#DE2626" />

  <!-- Subtle Professional 3D Isometric Branding Cube (Centered Stage, Zero Text) -->
  <g transform="translate(640, 320)">
    <!-- Top Face (White border, dark inner recess) -->
    <polygon points="0,-48 56,-18 0,12 -56,-18" fill="#FFFFFF" stroke="#FFFFFF" stroke-width="1.5" stroke-linejoin="round" />
    <polygon points="0,-36 40,-15 0,6 -40,-15" fill="#0A0A0C" />
    <!-- Left Face (Obsidian Dark) -->
    <polygon points="-56,-18 0,12 0,72 -56,42" fill="#181820" stroke="#FFFFFF" stroke-width="1.5" stroke-linejoin="round" />
    <!-- Right Face (Elton Boehnen Signature Red #DE2626) -->
    <polygon points="0,12 56,-18 56,42 0,72" fill="#DE2626" stroke="#FFFFFF" stroke-width="1.5" stroke-linejoin="round" />
  </g>
</svg>"""

# 2. Light Logo Skeleton (No Text)
LIGHT_SKELETON_SVG = """<svg width="1280" height="640" viewBox="0 0 1280 640" xmlns="http://www.w3.org/2000/svg">
  <!-- Pure White Substrate -->
  <rect width="1280" height="640" fill="#FFFFFF" />

  <!-- Outer Structural Boundary Inset -->
  <rect x="48" y="48" width="1184" height="544" rx="0" fill="none" stroke="#E5E7EB" stroke-width="1.5" />

  <!-- Corner Precision Ticks (Zero Curvature) -->
  <path d="M 48 76 L 48 48 L 76 48" fill="none" stroke="#9CA3AF" stroke-width="2" />
  <path d="M 1204 48 L 1232 48 L 1232 76" fill="none" stroke="#9CA3AF" stroke-width="2" />
  <path d="M 48 564 L 48 592 L 76 592" fill="none" stroke="#9CA3AF" stroke-width="2" />
  <path d="M 1204 592 L 1232 592 L 1232 564" fill="none" stroke="#9CA3AF" stroke-width="2" />

  <!-- Vertical Red Accent Marker -->
  <rect x="48" y="270" width="4" height="100" rx="0" fill="#DE2626" />

  <!-- Subtle Professional 3D Isometric Branding Cube (Centered Stage, Zero Text) -->
  <g transform="translate(640, 320)">
    <!-- Top Face (Black border, white inner recess) -->
    <polygon points="0,-48 56,-18 0,12 -56,-18" fill="#000000" stroke="#000000" stroke-width="1.5" stroke-linejoin="round" />
    <polygon points="0,-36 40,-15 0,6 -40,-15" fill="#FFFFFF" />
    <!-- Left Face (Clean Light Gray) -->
    <polygon points="-56,-18 0,12 0,72 -56,42" fill="#E5E7EB" stroke="#000000" stroke-width="1.5" stroke-linejoin="round" />
    <!-- Right Face (Elton Boehnen Signature Red #DE2626) -->
    <polygon points="0,12 56,-18 56,42 0,72" fill="#DE2626" stroke="#000000" stroke-width="1.5" stroke-linejoin="round" />
  </g>
</svg>"""

# 3. Official Management Tool Banner (Dark, Minimal, Subtle Cube, No Fluff)
BANNER_SVG = """<svg width="1280" height="640" viewBox="0 0 1280 640" xmlns="http://www.w3.org/2000/svg">
  <!-- Pitch Black Substrate -->
  <rect width="1280" height="640" fill="#0A0A0C" />

  <!-- Outer Structural Boundary Inset -->
  <rect x="48" y="48" width="1184" height="544" rx="0" fill="none" stroke="#1A1A22" stroke-width="1.5" />

  <!-- Corner Precision Ticks (Zero Curvature) -->
  <path d="M 48 76 L 48 48 L 76 48" fill="none" stroke="#333340" stroke-width="2" />
  <path d="M 1204 48 L 1232 48 L 1232 76" fill="none" stroke="#333340" stroke-width="2" />
  <path d="M 48 564 L 48 592 L 76 592" fill="none" stroke="#333340" stroke-width="2" />
  <path d="M 1204 592 L 1232 592 L 1232 564" fill="none" stroke="#333340" stroke-width="2" />

  <!-- Red Accent Marker -->
  <rect x="48" y="270" width="4" height="100" rx="0" fill="#DE2626" />

  <!-- Center Balanced Brand & Title Lockup -->
  <g transform="translate(275, 320)">
    <!-- Subtle Professional 3D Isometric Branding Cube -->
    <g transform="translate(0, 0)">
      <!-- Top Face -->
      <polygon points="0,-48 56,-18 0,12 -56,-18" fill="#FFFFFF" stroke="#FFFFFF" stroke-width="1.5" stroke-linejoin="round" />
      <polygon points="0,-36 40,-15 0,6 -40,-15" fill="#0A0A0C" />
      <!-- Left Face -->
      <polygon points="-56,-18 0,12 0,72 -56,42" fill="#181820" stroke="#FFFFFF" stroke-width="1.5" stroke-linejoin="round" />
      <!-- Right Face (#DE2626) -->
      <polygon points="0,12 56,-18 56,42 0,72" fill="#DE2626" stroke="#FFFFFF" stroke-width="1.5" stroke-linejoin="round" />
    </g>

    <!-- Sharp Vertical Divider -->
    <line x1="104" y1="-56" x2="104" y2="76" stroke="#DE2626" stroke-width="3" />

    <!-- Pure Purpose Title (Zero Fluff) -->
    <text x="144" y="22" fill="#FFFFFF" font-size="64" font-family="system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-weight="800" letter-spacing="1">Management Tool</text>
  </g>
</svg>"""

def main():
    dark_path = ASSETS_DIR / "template_logo_dark_notext.svg"
    light_path = ASSETS_DIR / "template_logo_light_notext.svg"
    banner_svg_path = ASSETS_DIR / "Management_CLI_Banner_1280x640.svg"
    banner_png_path = ASSETS_DIR / "Management_CLI_Banner_1280x640.png"
    banner_webp_path = ASSETS_DIR / "Management_CLI_Banner_1280x640.webp"

    dark_path.write_text(DARK_SKELETON_SVG, encoding="utf-8")
    print(f"Wrote {dark_path}")

    light_path.write_text(LIGHT_SKELETON_SVG, encoding="utf-8")
    print(f"Wrote {light_path}")

    banner_svg_path.write_text(BANNER_SVG, encoding="utf-8")
    print(f"Wrote {banner_svg_path}")

    # Render PNG using Playwright Native Chromium
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path="/data/data/com.termux/files/usr/bin/chromium",
            args=["--no-sandbox", "--disable-gpu"]
        )
        page = browser.new_page(viewport={"width": 1280, "height": 640})
        
        # Banner
        page.goto(f"file://{banner_svg_path.resolve()}")
        page.screenshot(path=str(banner_png_path))
        print(f"Rendered {banner_png_path}")

        # Dark skeleton preview
        dark_png = ASSETS_DIR / "template_logo_dark_notext.png"
        page.goto(f"file://{dark_path.resolve()}")
        page.screenshot(path=str(dark_png))
        print(f"Rendered {dark_png}")

        # Light skeleton preview
        light_png = ASSETS_DIR / "template_logo_light_notext.png"
        page.goto(f"file://{light_path.resolve()}")
        page.screenshot(path=str(light_png))
        print(f"Rendered {light_png}")

        browser.close()

    # Convert to WebP using Pillow
    img = Image.open(banner_png_path)
    img.save(banner_webp_path, format="WEBP", quality=95)
    print(f"Rendered {banner_webp_path}")

if __name__ == "__main__":
    main()
