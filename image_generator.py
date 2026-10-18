import os
import time
import textwrap
from typing import Optional, Dict, Any
from PIL import Image, ImageDraw, ImageFont
from config import IMAGES_DIR

try:
    os.makedirs(IMAGES_DIR, exist_ok=True)
except Exception:
    pass

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/SFNS.ttf"
]

def get_font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, size)
            except Exception:
                continue
    return ImageFont.load_default()

THEMES = {
    "buy": {
        "title": "DEX BUY ALERT",
        "badge": "🟢 BUY",
        "primary": (16, 185, 129),     # Emerald
        "secondary": (5, 150, 105),
        "accent": (52, 211, 153),
        "bg_top": (10, 25, 20),
        "bg_bottom": (5, 15, 12),
        "icon": "▲"
    },
    "sell": {
        "title": "DEX SELL ALERT",
        "badge": "🔴 SELL",
        "primary": (239, 68, 68),      # Crimson
        "secondary": (220, 38, 38),
        "accent": (248, 113, 113),
        "bg_top": (28, 12, 14),
        "bg_bottom": (16, 8, 9),
        "icon": "▼"
    },
    "whale": {
        "title": "WHALE MOVEMENT ALERT",
        "badge": "🐋 WHALE ALERT",
        "primary": (6, 182, 212),      # Cyan
        "secondary": (14, 116, 144),
        "accent": (103, 232, 249),
        "bg_top": (8, 24, 32),
        "bg_bottom": (5, 14, 20),
        "icon": "◆"
    },
    "staking": {
        "title": "STAKING & LIQUIDITY",
        "badge": "💎 STAKING",
        "primary": (168, 85, 247),     # Purple
        "secondary": (126, 34, 206),
        "accent": (216, 180, 254),
        "bg_top": (24, 12, 32),
        "bg_bottom": (14, 7, 20),
        "icon": "◈"
    },
    "summary": {
        "title": "ENI CHAIN LIVE METRICS",
        "badge": "📊 LIVE METRICS",
        "primary": (245, 158, 11),     # Amber
        "secondary": (217, 119, 6),
        "accent": (252, 211, 77),
        "bg_top": (28, 20, 10),
        "bg_bottom": (16, 12, 6),
        "icon": "★"
    },
    "news": {
        "title": "GLOBAL CRYPTO BREAKING NEWS",
        "badge": "🌍 GLOBAL NEWS",
        "primary": (14, 165, 233),     # Sky Blue
        "secondary": (2, 132, 199),
        "accent": (56, 189, 248),
        "bg_top": (10, 30, 52),
        "bg_bottom": (5, 16, 32),
        "icon": "⚡"
    },
    "tech": {
        "title": "ENI MODULAR L1 ARCHITECTURE",
        "badge": "⚡ CORE TECH",
        "primary": (99, 102, 241),      # Indigo
        "secondary": (79, 70, 229),
        "accent": (165, 180, 252),
        "bg_top": (15, 18, 48),
        "bg_bottom": (8, 10, 28),
        "icon": "⚛"
    }
}

def create_alert_card(
    event_type: str,
    data: Dict[str, Any]
) -> str:
    """
    Generates a 1200x675 high-res alert card suitable for Twitter and Telegram.
    Returns the file path of the generated PNG image.
    """
    width, height = 1200, 675
    theme = THEMES.get(event_type.lower(), THEMES["whale"])

    # Create canvas
    img = Image.new("RGBA", (width, height), (10, 15, 25, 255))
    draw = ImageDraw.Draw(img)

    # Background gradient
    bg_top = theme["bg_top"]
    bg_bottom = theme["bg_bottom"]
    for y in range(height):
        ratio = y / height
        r = int(bg_top[0] * (1 - ratio) + bg_bottom[0] * ratio)
        g = int(bg_top[1] * (1 - ratio) + bg_bottom[1] * ratio)
        b = int(bg_top[2] * (1 - ratio) + bg_bottom[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Outer decorative glow border
    p_color = theme["primary"]
    draw.rectangle([20, 20, width - 20, height - 20], outline=(p_color[0], p_color[1], p_color[2], 90), width=2)
    draw.rectangle([24, 24, width - 24, height - 24], outline=(255, 255, 255, 15), width=1)

    # Accent top-left corner ornament
    draw.polygon([(20, 20), (120, 20), (20, 120)], fill=(p_color[0], p_color[1], p_color[2], 40))

    # Header fonts
    font_brand = get_font(22, bold=True)
    font_badge = get_font(18, bold=True)
    font_title = get_font(38, bold=True)
    font_main_val = get_font(54, bold=True)
    font_sub_val = get_font(30)
    font_label = get_font(18)
    font_val = get_font(20, bold=True)
    font_footer = get_font(16)
    font_news_body = get_font(24)

    # Brand Title
    draw.text((60, 48), "NEWTON PROTOCOL  ×  ENI CHAIN", fill=(180, 195, 215, 255), font=font_brand)

    # Status Badge
    badge_text = theme["badge"]
    badge_box = [width - 250, 42, width - 60, 80]
    draw.rounded_rectangle(badge_box, radius=8, fill=(p_color[0], p_color[1], p_color[2], 50), outline=p_color, width=2)
    draw.text((width - 230, 48), badge_text, fill=(255, 255, 255, 255), font=font_badge)

    # Main Card Title
    draw.text((60, 105), theme["title"], fill=theme["accent"], font=font_title)

    # Divider
    draw.line([(60, 160), (width - 60, 160)], fill=(255, 255, 255, 30), width=1)

    # Render body based on event type
    if event_type == "news":
        # Global Breaking News Layout
        news_title = data.get("news_title", "Global Blockchain Breaking Event")
        news_source = data.get("news_source", "Crypto Intelligence")
        news_time = data.get("news_time", "")
        news_summary = data.get("news_summary", "")

        # Wrap headline (max ~42 chars per line)
        wrapped_title = textwrap.fill(news_title, width=42)
        draw.text((60, 185), wrapped_title[:130], fill=(255, 255, 255, 255), font=font_news_body)

        # News Box Info
        grid_y = 350
        grid_h = 220
        draw.rounded_rectangle([60, grid_y, width - 60, grid_y + grid_h], radius=12, fill=(15, 23, 42, 190), outline=(255, 255, 255, 30), width=1)

        draw.text((90, grid_y + 25), "SOURCE & PUBLISHER", fill=(148, 163, 184, 255), font=font_label)
        draw.text((90, grid_y + 55), news_source, fill=(255, 255, 255, 255), font=font_val)

        draw.text((450, grid_y + 25), "CATEGORY & TOPIC", fill=(148, 163, 184, 255), font=font_label)
        draw.text((450, grid_y + 55), "Blockchain / Macro / Web3", fill=theme["accent"], font=font_val)

        draw.text((820, grid_y + 25), "BROADCAST TIME", fill=(148, 163, 184, 255), font=font_label)
        draw.text((820, grid_y + 55), news_time[:24] if news_time else "Just Now", fill=(255, 255, 255, 255), font=font_val)

        # Brief summary excerpt inside box
        if news_summary:
            wrapped_summary = textwrap.fill(news_summary[:160], width=75)
            draw.text((90, grid_y + 115), f"\"{wrapped_summary}\"", fill=(203, 213, 225, 255), font=get_font(18))

    elif event_type == "summary":
        # Live Stats / Summary Layout
        tot_blocks = data.get("total_blocks", 0)
        tot_txs = data.get("total_txs", 0)
        tot_addrs = data.get("active_addresses", 0)
        tx_today = data.get("transactions_today", 0)
        gas = data.get("gas_price", "87.3")

        main_text = f"#{tot_blocks:,} BLOCKS"
        sub_text = f"ENI Mainnet (ChainID: 173) · {tot_txs:,} Total Transactions"
        draw.text((60, 185), main_text, fill=(255, 255, 255, 255), font=font_main_val)
        draw.text((60, 260), sub_text, fill=theme["accent"], font=font_sub_val)

        grid_y = 330
        grid_h = 240
        draw.rounded_rectangle([60, grid_y, width - 60, grid_y + grid_h], radius=12, fill=(15, 23, 42, 180), outline=(255, 255, 255, 30), width=1)

        cols = [
            ("TOTAL TRANSACTIONS", f"{tot_txs:,}"),
            ("WALLET ADDRESSES", f"{tot_addrs:,}"),
            ("24H TRANSACTIONS", f"{tx_today:,}"),
            ("AVERAGE GAS PRICE", f"{gas} Gwei")
        ]
        col_w = (width - 160) // 4
        for i, (lbl, val) in enumerate(cols):
            x = 85 + i * col_w
            draw.text((x, grid_y + 35), lbl, fill=(148, 163, 184, 255), font=font_label)
            draw.text((x, grid_y + 75), val, fill=(255, 255, 255, 255), font=get_font(28, bold=True))

    elif event_type == "tech":
        # Tech Architecture & Official Vision Card
        tech_title = data.get("tech_title", "PARALLEL EXECUTION & REAL-TIME SETTLEMENT")
        tech_sub = data.get("tech_sub", "ENI Enterprise Modular L1 · Mainnet, Hub & AppChains")
        draw.text((60, 185), tech_title[:45], fill=(255, 255, 255, 255), font=font_main_val)
        draw.text((60, 260), tech_sub, fill=theme["accent"], font=font_sub_val)

        grid_y = 330
        grid_h = 240
        draw.rounded_rectangle([60, grid_y, width - 60, grid_y + grid_h], radius=12, fill=(15, 23, 42, 180), outline=(255, 255, 255, 30), width=1)

        cols = [
            ("CONSENSUS & SPEED", "Parallel EVM (1.0s)"),
            ("ENTERPRISE INFRA", "Modular AppChains"),
            ("GAS & UTILITY", "EGAS Native Fuel"),
            ("OFFICIAL EXPLORER", "scan.eniac.network")
        ]
        col_w = (width - 160) // 4
        for i, (lbl, val) in enumerate(cols):
            x = 85 + i * col_w
            draw.text((x, grid_y + 35), lbl, fill=(148, 163, 184, 255), font=font_label)
            draw.text((x, grid_y + 75), val, fill=(255, 255, 255, 255), font=get_font(20, bold=True))

        desc_snippet = data.get("tech_desc", "Ultra-high performance modular L1 combining Mainnet, Hub & AppChains with parallel execution.")
        wrapped_d = textwrap.fill(desc_snippet[:150], width=75)
        draw.text((85, grid_y + 140), f"📌 \"{wrapped_d}\"", fill=(203, 213, 225, 255), font=get_font(18))

    else:
        # Standard Transactions (Buy / Sell / Whale / Staking)
        amount = data.get("amount", 0.0)
        symbol = data.get("symbol", "ENI")
        usd_val = data.get("usd_value", 0.0)

        main_text = f"{amount:,.0f} {symbol}"
        sub_text = f"≈ ${usd_val:,.2f} USD"
        draw.text((60, 185), main_text, fill=(255, 255, 255, 255), font=font_main_val)
        draw.text((60, 260), sub_text, fill=theme["accent"], font=font_sub_val)

        grid_y = 330
        grid_h = 240
        draw.rounded_rectangle([60, grid_y, width - 60, grid_y + grid_h], radius=12, fill=(15, 23, 42, 180), outline=(255, 255, 255, 30), width=1)

        row1_y = grid_y + 25
        row2_y = grid_y + 125

        p_label = "UNIT PRICE" if event_type in ["buy", "sell"] else "ESTIMATED VALUE"
        p_val = f"${data.get('price', 0.15):.4f}" if event_type in ["buy", "sell"] else f"${usd_val:,.2f}"
        draw.text((90, row1_y), p_label, fill=(148, 163, 184, 255), font=font_label)
        draw.text((90, row1_y + 30), p_val, fill=(255, 255, 255, 255), font=font_val)

        draw.text((620, row1_y), "NETWORK & EXPLORER", fill=(148, 163, 184, 255), font=font_label)
        draw.text((620, row1_y + 30), "ENI Mainnet (ChainID: 173) · scan.eniac.network", fill=(255, 255, 255, 255), font=font_val)

        if event_type == "buy":
            addr_label = "BUYER ADDRESS"
            addr_val = data.get("buyer", "0x0000...0000")
        elif event_type == "sell":
            addr_label = "SELLER ADDRESS"
            addr_val = data.get("seller", "0x0000...0000")
        elif event_type == "staking":
            addr_label = "STAKER ADDRESS"
            addr_val = data.get("user", "0x0000...0000")
        else:
            addr_label = "FROM / TO WALLET"
            f_short = (data.get("from_addr", "")[:6] + "..." + data.get("from_addr", "")[-4:]) if len(data.get("from_addr", "")) > 10 else "Unknown"
            t_short = (data.get("to_addr", "")[:6] + "..." + data.get("to_addr", "")[-4:]) if len(data.get("to_addr", "")) > 10 else "Unknown"
            addr_val = f"{f_short} ➔ {t_short}"

        if len(addr_val) > 28 and "➔" not in addr_val:
            addr_val = addr_val[:12] + "..." + addr_val[-8:]

        draw.text((90, row2_y), addr_label, fill=(148, 163, 184, 255), font=font_label)
        draw.text((90, row2_y + 30), addr_val, fill=(255, 255, 255, 255), font=font_val)

        tx_hash = data.get("tx_hash", "0x" + "0"*64)
        tx_display = tx_hash[:16] + "..." + tx_hash[-10:] if len(tx_hash) > 26 else tx_hash
        draw.text((620, row2_y), "TRANSACTION HASH", fill=(148, 163, 184, 255), font=font_label)
        draw.text((620, row2_y + 30), tx_display, fill=theme["accent"], font=font_val)

    # Footer note
    draw.text((60, 605), "⚡ REAL-TIME MONITORING  |  NEWTON INITIATIVE PROTOCOL LAB  |  SCAN.ENIAC.NETWORK", fill=(100, 116, 139, 255), font=font_footer)

    # Save image
    timestamp = int(time.time() * 1000)
    filename = f"alert_{event_type}_{timestamp}.png"
    filepath = os.path.join(IMAGES_DIR, filename)
    img.save(filepath, "PNG")
    return filepath

def generate_banner_image(theme: str = "tech", title: str = "", subtitle: str = "", footer_text: str = "") -> str:
    """Convenience alias for create_alert_card"""
    data = {
        "title": title or "ENI MODULAR L1 ARCHITECTURE",
        "subtitle": subtitle or "Automated Operations System",
        "tech_title": title or "ENI Protocol Intelligence",
        "tech_subtitle": subtitle or "Newton Protocol × ENI High-speed execution",
        "news_title": title,
        "news_source": "ENI Intelligence Desk",
        "summary_title": title or "Daily Ecosystem Pulse",
        "blocks": "41,568,000+",
        "txs": "26,914,000+",
        "addresses": "5,223,000+",
        "block_time": "1.00s",
        "gas": "87.25 Gwei"
    }
    return create_alert_card(theme, data)
