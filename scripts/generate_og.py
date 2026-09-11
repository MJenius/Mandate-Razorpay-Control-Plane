import os
from PIL import Image, ImageDraw, ImageFont

# Canvas dimensions (LinkedIn recommended OpenGraph preview: 1200 x 627)
W, H = 1200, 627

# Base background: deep slate dark theme #090d16
img = Image.new("RGB", (W, H), (9, 13, 22))
draw = ImageDraw.Draw(img)

# 1. Subtle radial glows (rendered onto separate RGBA surface)
glow_surface = Image.new("RGBA", (W, H), (0, 0, 0, 0))
glow_draw = ImageDraw.Draw(glow_surface)

def draw_radial_glow(canvas, center_x, center_y, radius, color_rgb, max_alpha):
    for r in range(radius, 0, -6):
        alpha = int(max_alpha * (1.0 - (r / radius)) ** 2.2)
        canvas.ellipse(
            [center_x - r, center_y - r, center_x + r, center_y + r],
            fill=(color_rgb[0], color_rgb[1], color_rgb[2], alpha)
        )

# Soft futuristic lighting
draw_radial_glow(glow_draw, 220, 160, 520, (37, 99, 235), 65)   # Electric Blue
draw_radial_glow(glow_draw, 960, 420, 480, (99, 102, 241), 45)  # Indigo
draw_radial_glow(glow_draw, 1080, 140, 360, (16, 185, 129), 35) # Emerald

img.paste(Image.alpha_composite(Image.new("RGBA", (W, H), (9, 13, 22, 255)), glow_surface).convert("RGB"))
draw = ImageDraw.Draw(img)

# 2. Subtle Tech Grid (very faint, opacity simulated with dark slate colors)
grid_col = (18, 26, 43)
for x in range(0, W, 48):
    draw.line([(x, 0), (x, H)], fill=grid_col, width=1)
for y in range(0, H, 48):
    draw.line([(0, y), (W, y)], fill=grid_col, width=1)

# Fonts
font_dir = "C:/Windows/Fonts"
def get_font(name, size):
    try:
        return ImageFont.truetype(os.path.join(font_dir, name), size)
    except:
        return ImageFont.load_default()

font_title = get_font("segoeuib.ttf", 52)
font_subtitle = get_font("segoeui.ttf", 21)
font_badge = get_font("segoeuib.ttf", 13)
font_chip = get_font("segoeuib.ttf", 15)
font_item_title = get_font("segoeuib.ttf", 17)
font_item_desc = get_font("segoeui.ttf", 14)

font_mono_xs = get_font("consola.ttf", 12)
font_mono_sm = get_font("consola.ttf", 13)
font_mono_md = get_font("consolab.ttf", 14)
font_stat_num = get_font("segoeuib.ttf", 26)

# 3. Top Accent Line (Blue to Indigo gradient)
for i in range(W):
    ratio = i / W
    r = int(37 + ratio * (99 - 37))
    g = int(99 + ratio * (102 - 99))
    b = int(235 + ratio * (241 - 235))
    draw.line([(i, 0), (i, 3)], fill=(r, g, b))

# 4. LEFT SECTION: Hero, Taglines, Architecture Badges
# Top Tag: RAZORPAY & AGENTIC FINANCE
bx, by = 64, 52
draw.rounded_rectangle([bx, by, bx + 360, by + 32], radius=7, fill=(15, 23, 42), outline=(59, 130, 246), width=1)
draw.ellipse([bx + 14, by + 11, bx + 22, by + 19], fill=(59, 130, 246))
draw.text((bx + 32, by + 7), "FINANCIAL CONTROL PLANE FOR AI AGENTS", font=font_badge, fill=(191, 219, 254))

# Brand Title
draw.text((64, 102), "MANDATE", font=font_title, fill=(255, 255, 255))
# Subtitle
draw.text((64, 172), "Autonomous Payment Authorization & Execution", font=font_subtitle, fill=(203, 213, 225))

# Triad Chips: SAFE • BOUNDED • OBSERVABLE
chip_y = 222
chips = [
    ("SAFE", (16, 185, 129), 110),      # Emerald
    ("BOUNDED", (59, 130, 246), 132),   # Blue
    ("OBSERVABLE", (168, 85, 247), 154) # Purple
]

cx = 64
for word, col, w in chips:
    draw.rounded_rectangle([cx, chip_y, cx + w, chip_y + 34], radius=6, fill=(15, 23, 42), outline=col, width=1)
    draw.ellipse([cx + 12, chip_y + 13, cx + 20, chip_y + 21], fill=col)
    draw.text((cx + 28, chip_y + 7), word, font=font_chip, fill=(241, 245, 249))
    cx += w + 14

# Feature Highlights
feat_y = 286
feats = [
    ("Deterministic Policy Engine", "8-rule security engine enforcing velocity, budget ceilings & limits", (59, 130, 246)),
    ("Scoped Sub-Delegation", "Cryptographic parent-child authorization tokens with strict depth gates", (16, 185, 129)),
    ("Razorpay Integration", "Production-grade UPI & Card recurring mandate execution pipelines", (245, 158, 11)),
    ("Model Context Protocol (MCP)", "Standardized native tool gateway for Claude & LLM agent runtimes", (168, 85, 247))
]

for title, desc, dot_col in feats:
    draw.ellipse([64, feat_y + 6, 74, feat_y + 16], fill=dot_col)
    draw.text((88, feat_y), title, font=font_item_title, fill=(255, 255, 255))
    draw.text((88, feat_y + 24), desc, font=font_item_desc, fill=(148, 163, 184))
    feat_y += 66

# 5. RIGHT SECTION: Sleek Glassmorphic Telemetry Console
px, py, pw, ph = 640, 52, 496, 510
# Outer panel
draw.rounded_rectangle([px, py, px + pw, py + ph], radius=12, fill=(15, 23, 42), outline=(51, 65, 85), width=1)

# Window bar
draw.rounded_rectangle([px, py, px + pw, py + 42], radius=12, fill=(30, 41, 59))
draw.rectangle([px, py + 30, px + pw, py + 42], fill=(30, 41, 59))
draw.line([(px, py + 42), (px + pw, py + 42)], fill=(51, 65, 85), width=1)

draw.ellipse([px + 16, py + 16, px + 26, py + 26], fill=(239, 68, 68))
draw.ellipse([px + 34, py + 16, px + 44, py + 26], fill=(245, 158, 11))
draw.ellipse([px + 52, py + 16, px + 62, py + 26], fill=(34, 197, 94))
draw.text((px + 78, py + 14), "CONTROL PLANE // LIVE EXECUTION TELEMETRY", font=font_mono_md, fill=(203, 213, 225))

# Card 1: Active Mandate Contract
c1_y = py + 56
draw.rounded_rectangle([px + 18, c1_y, px + pw - 18, c1_y + 112], radius=8, fill=(11, 19, 36), outline=(37, 99, 235), width=1)
draw.text((px + 32, c1_y + 14), "MANDATE_ID", font=font_mono_sm, fill=(148, 163, 184))
draw.text((px + 125, c1_y + 14), "man_live_9a7f3c428e", font=font_mono_md, fill=(96, 165, 250))

# Status pill
draw.rounded_rectangle([px + pw - 110, c1_y + 11, px + pw - 30, c1_y + 33], radius=4, fill=(6, 78, 59), outline=(16, 185, 129), width=1)
draw.text((px + pw - 96, c1_y + 14), "ACTIVE", font=font_badge, fill=(52, 211, 153))

# Budget Bar
draw.text((px + 32, c1_y + 44), "BUDGET UTILIZATION", font=font_mono_xs, fill=(148, 163, 184))
draw.text((px + pw - 165, c1_y + 44), "INR 3,250 / 5,000", font=font_mono_md, fill=(241, 245, 249))

bar_y = c1_y + 68
draw.rounded_rectangle([px + 32, bar_y, px + pw - 32, bar_y + 10], radius=5, fill=(30, 41, 59))
fill_w = int((pw - 64) * 0.65)
draw.rounded_rectangle([px + 32, bar_y, px + 32 + fill_w, bar_y + 10], radius=5, fill=(37, 99, 235))

draw.text((px + 32, c1_y + 88), "AGENT: procurement-bot-04", font=font_mono_xs, fill=(148, 163, 184))
draw.text((px + pw - 170, c1_y + 88), "MAX_VELOCITY: 5 tx/hr", font=font_mono_xs, fill=(148, 163, 184))

# Card 2: Deterministic Policy Pipeline
c2_y = c1_y + 126
draw.rounded_rectangle([px + 18, c2_y, px + pw - 18, c2_y + 178], radius=8, fill=(11, 19, 36), outline=(51, 65, 85), width=1)
draw.text((px + 32, c2_y + 14), "POLICY EVALUATION ENGINE (DETERMINISTIC)", font=font_mono_md, fill=(226, 232, 240))

eval_steps = [
    ("PASS", (34, 197, 94), "RULE_1: Token Signature & HMAC Verified"),
    ("PASS", (34, 197, 94), "RULE_2: Delegation Depth < Max Allowed (1/3)"),
    ("PASS", (34, 197, 94), "RULE_3: Transaction Amount within Mandate Ceiling"),
    ("PASS", (34, 197, 94), "RULE_4: Merchant Category Permitted (MCC 5734)"),
    ("PASS", (34, 197, 94), "RULE_5: Anomaly & Velocity Threshold Verified"),
]

ey = c2_y + 44
for tag, col, desc in eval_steps:
    draw.rounded_rectangle([px + 32, ey, px + 76, ey + 18], radius=3, fill=(15, 23, 42), outline=col, width=1)
    draw.text((px + 40, ey + 2), tag, font=font_mono_md, fill=col)
    draw.text((px + 88, ey + 2), desc, font=font_mono_sm, fill=(203, 213, 225))
    ey += 25

# Card 3: Metrics Strip (Latency, Concurrency, Idempotency)
c3_y = c2_y + 192
box_w = (pw - 36 - 20) // 3

# Metric 1
m1_x = px + 18
draw.rounded_rectangle([m1_x, c3_y, m1_x + box_w, c3_y + 80], radius=8, fill=(11, 19, 36), outline=(51, 65, 85), width=1)
draw.text((m1_x + 14, c3_y + 12), "LATENCY (P99)", font=font_mono_xs, fill=(148, 163, 184))
draw.text((m1_x + 14, c3_y + 36), "4.2 ms", font=font_stat_num, fill=(56, 189, 248))

# Metric 2
m2_x = m1_x + box_w + 10
draw.rounded_rectangle([m2_x, c3_y, m2_x + box_w, c3_y + 80], radius=8, fill=(11, 19, 36), outline=(51, 65, 85), width=1)
draw.text((m2_x + 14, c3_y + 12), "CONCURRENCY", font=font_mono_xs, fill=(148, 163, 184))
draw.text((m2_x + 14, c3_y + 36), "100%", font=font_stat_num, fill=(52, 211, 153))

# Metric 3
m3_x = m2_x + box_w + 10
draw.rounded_rectangle([m3_x, c3_y, m3_x + box_w, c3_y + 80], radius=8, fill=(11, 19, 36), outline=(51, 65, 85), width=1)
draw.text((m3_x + 14, c3_y + 12), "IDEMPOTENCY", font=font_mono_xs, fill=(148, 163, 184))
draw.text((m3_x + 14, c3_y + 36), "STRICT", font=font_stat_num, fill=(168, 85, 247))

# 6. Bottom Clean Branding Bar
bot_y = 582
draw.line([(0, bot_y), (W, bot_y)], fill=(30, 41, 59), width=1)
draw.text((64, bot_y + 12), "mandate-razorpay-control-plane.vercel.app", font=font_mono_sm, fill=(148, 163, 184))
draw.text((px + pw - 280, bot_y + 12), "Razorpay Autonomous Mandate Protocol", font=font_mono_sm, fill=(148, 163, 184))

# Save output image
out_path = "c:/Users/mjeni/OneDrive/Desktop/Own Projects/Mandate - Razorpay/apps/web/public/og-image.png"
img.save(out_path, format="PNG", optimize=True)
print(f"Generated clean high-res {out_path} ({img.size[0]}x{img.size[1]})")
