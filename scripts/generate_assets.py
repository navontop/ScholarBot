"""
Generates high-resolution (512x512) PNG card assets for ScholarBot.
Creates distinct, premium themed icons for each scholarship type and Action Hub workflow.
"""

import os
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets"))
os.makedirs(ASSETS_DIR, exist_ok=True)

THEMES = {
    "central": {
        "bg_top": (30, 58, 138),      # Deep Navy
        "bg_bottom": (59, 130, 246),  # Blue
        "accent": (251, 191, 36),     # Gold
        "title": "CENTRAL SCHEME",
        "subtitle": "National Scholarship Portal",
        "badge": "GOVT OF INDIA"
    },
    "state": {
        "bg_top": (6, 95, 70),        # Deep Emerald
        "bg_bottom": (16, 185, 129),  # Emerald
        "accent": (254, 240, 138),    # Light Gold
        "title": "STATE SCHOLARSHIP",
        "subtitle": "State Post-Matric & Merit",
        "badge": "STATE GOVT"
    },
    "csr": {
        "bg_top": (91, 33, 182),      # Deep Purple
        "bg_bottom": (139, 92, 246),  # Violet
        "accent": (244, 114, 182),    # Pink
        "title": "CSR & FOUNDATION",
        "subtitle": "Corporate & Trust Grants",
        "badge": "PRIVATE MERIT"
    },
    "girls": {
        "bg_top": (159, 18, 57),      # Deep Rose
        "bg_bottom": (236, 72, 153),  # Pink
        "accent": (254, 240, 138),    # Gold
        "title": "GIRLS IN EDUCATION",
        "subtitle": "AICTE Pragati & Women Aid",
        "badge": "FEMALE ONLY"
    },
    "pwd": {
        "bg_top": (15, 118, 110),     # Deep Teal
        "bg_bottom": (20, 184, 166),  # Cyan
        "accent": (253, 224, 71),     # Yellow
        "title": "SPECIALLY ABLED (PwD)",
        "subtitle": "AICTE Saksham & DEPwD",
        "badge": "BENCHMARK PwD"
    },
    "minority": {
        "bg_top": (120, 53, 15),      # Amber Bronze
        "bg_bottom": (217, 119, 6),   # Amber
        "accent": (254, 243, 199),    # Cream
        "title": "MINORITY COMMUNITIES",
        "subtitle": "MoMA Notified Minorities",
        "badge": "MINORITY AID"
    },
    "merit": {
        "bg_top": (133, 77, 14),      # Dark Gold
        "bg_bottom": (234, 179, 8),   # Radiant Gold
        "accent": (255, 255, 255),    # White
        "title": "MERIT DISTINCTION",
        "subtitle": "Top Percentile & Ranks",
        "badge": "MERIT BASED"
    },
    "school": {
        "bg_top": (3, 105, 161),      # Sky Deep
        "bg_bottom": (14, 165, 233),  # Sky
        "accent": (253, 224, 71),     # Gold
        "title": "SCHOOL (CLASS 9-12)",
        "subtitle": "Pre-Matric & Secondary",
        "badge": "SCHOOL LEVEL"
    },
    "hub_find": {
        "bg_top": (29, 78, 216),
        "bg_bottom": (37, 99, 235),
        "accent": (255, 255, 255),
        "title": "FIND SCHOLARSHIPS",
        "subtitle": "Range Matching & Criteria",
        "badge": "DISCOVERY"
    },
    "hub_audit": {
        "bg_top": (17, 24, 39),
        "bg_bottom": (31, 41, 55),
        "accent": (52, 211, 153),     # Green
        "title": "PRE-CHECK AUDIT",
        "subtitle": "Anti-Rejection Verification",
        "badge": "COMPLIANCE"
    },
    "hub_deadlines": {
        "bg_top": (194, 65, 12),      # Orange Red
        "bg_bottom": (234, 88, 12),   # Orange
        "accent": (255, 255, 255),
        "title": "DEADLINES & ALERTS",
        "subtitle": "Closing Dates & iCalendar",
        "badge": "CALENDAR"
    },
    "hub_whatif": {
        "bg_top": (67, 56, 202),      # Indigo
        "bg_bottom": (99, 102, 241),
        "accent": (253, 224, 71),
        "title": "WHAT-IF SIMULATION",
        "subtitle": "Marks & Income Scenarios",
        "badge": "ADVISORY"
    },
    "hub_concierge": {
        "bg_top": (24, 24, 27),       # Zinc Black
        "bg_bottom": (63, 63, 70),    # Slate
        "accent": (251, 191, 36),     # Gold
        "title": "CONCIERGE PACK",
        "subtitle": "SOP Essay & Application Dossier",
        "badge": "PAYMENT PROTOCOL"
    },
    "hub_profile": {
        "bg_top": (51, 65, 85),       # Slate
        "bg_bottom": (71, 85, 105),
        "accent": (148, 163, 184),
        "title": "STUDENT PROFILE",
        "subtitle": "Saved Data & Shortlists",
        "badge": "MY PROFILE"
    },
    "hub_home": {
        "bg_top": (15, 23, 42),       # Dark Slate
        "bg_bottom": (30, 41, 59),
        "accent": (56, 189, 248),     # Cyan
        "title": "ACTION HUB MENU",
        "subtitle": "ScholarBot Core Navigation",
        "badge": "HOME"
    },
    "fallback": {
        "bg_top": (31, 41, 55),
        "bg_bottom": (55, 65, 81),
        "accent": (243, 244, 246),
        "title": "SCHOLARBOT",
        "subtitle": "AI Scholarship Advisory",
        "badge": "OFFICIAL SCHEME"
    }
}

def create_gradient_card(name: str, config: dict):
    width, height = 512, 512
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    top_color = config["bg_top"]
    bot_color = config["bg_bottom"]
    accent = config["accent"]

    # 1. Smooth Vertical Gradient
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bot_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bot_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bot_color[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # 2. Geometric Accent Shapes (modern glassmorphism / card motifs)
    # Circle glow in top right
    draw.ellipse([320, -40, 560, 200], fill=(255, 255, 255, 20))
    draw.ellipse([360, 0, 520, 160], fill=(255, 255, 255, 15))
    # Outer Border
    draw.rounded_rectangle([16, 16, 496, 496], radius=28, outline=(255, 255, 255, 60), width=3)

    # 3. Inner Card Badge
    badge_text = config["badge"]
    draw.rounded_rectangle([48, 48, 240, 84], radius=12, fill=(0, 0, 0, 80), outline=accent, width=2)
    draw.text((62, 57), badge_text, fill=accent)

    # 4. Central Graphic Emblem (Polygons & Modern Emblem)
    cx, cy = 256, 240
    # Outer diamond
    diamond = [(cx, cy - 70), (cx + 70, cy), (cx, cy + 70), (cx - 70, cy)]
    draw.polygon(diamond, outline=(255, 255, 255, 100), fill=(0, 0, 0, 40))
    # Inner diamond
    inner_diamond = [(cx, cy - 45), (cx + 45, cy), (cx, cy + 45), (cx - 45, cy)]
    draw.polygon(inner_diamond, fill=accent)

    # Center circle
    draw.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=(255, 255, 255, 240))

    # 5. Lower Content Text Block
    title = config["title"]
    subtitle = config["subtitle"]
    
    # Title
    draw.text((48, 380), title, fill=(255, 255, 255, 255))
    # Subtitle
    draw.text((48, 420), subtitle, fill=(220, 220, 220, 240))

    # Watermark Brand
    draw.text((48, 455), "FETCH.AI · ASI:ONE VERIFIED", fill=(255, 255, 255, 120))

    file_path = os.path.join(ASSETS_DIR, f"{name}.png")
    img.save(file_path, "PNG")
    print(f"[Assets] Generated 512x512 {name}.png ({os.path.getsize(file_path)} bytes)")

def generate_all():
    print(f"Generating {len(THEMES)} high-resolution assets in {ASSETS_DIR}...")
    for name, config in THEMES.items():
        create_gradient_card(name, config)

    # Write LICENSES.md
    licenses_path = os.path.join(ASSETS_DIR, "LICENSES.md")
    with open(licenses_path, "w", encoding="utf-8") as f:
        f.write("""# ScholarBot Asset Licenses

All 512x512 PNG card assets in this directory (`central.png`, `state.png`, `csr.png`, `girls.png`, `pwd.png`, `minority.png`, `merit.png`, `school.png`, `hub_*.png`, `fallback.png`) were algorithmically generated specifically for the ScholarBot project in Fetch-A-Thon 3.0.

- **License**: Creative Commons Zero v1.0 Universal (CC0 1.0) / MIT License.
- **Permitted Use**: Commercial and non-commercial open-source distribution, modification, and reproduction.
- **Logos & Trademarks**: No proprietary or government trademarked logos are used. All emblems are stylized geometric motifs.
""")
    print("Successfully generated assets and LICENSES.md")

if __name__ == "__main__":
    generate_all()
