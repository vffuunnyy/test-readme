import os
import niquests
from pathlib import Path

SHIKI_USER_ID = os.environ.get("SHIKI_USER_ID")
if not SHIKI_USER_ID:
    raise SystemExit("SHIKI_USER_ID env required")

OUT_DIR = Path("assets")
OUT_DIR.mkdir(parents=True, exist_ok=True)
HERO_IMG = os.environ.get("HERO_IMAGE_PATH", "assets/hero.jpg")

query = """
query($page: Int!, $userId: ID!) {
  userRates(userId: $userId, targetType: Anime, page: $page, limit: 50) {
    status
    episodes
    anime { duration }
  }
}
"""

status_names = {
    "planned": "Запланировано",
    "watching": "Смотрю",
    "rewatching": "Пересматриваю",
    "completed": "Завершено",
    "on_hold": "Отложено",
    "dropped": "Брошено",
}


def fetch_all():
    url = "https://shikimori.one/api/graphql"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    page = 1
    all_rates = []
    while True:
        payload = {
            "query": query,
            "variables": {"page": page, "userId": int(SHIKI_USER_ID)},
        }
        r = niquests.post(url, json=payload, headers=headers, timeout=30)
        r.raise_for_status()
        data = r.json()
        rates = (data.get("data") or {}).get("userRates") or []
        if not rates:
            break
        all_rates.extend(rates)
        page += 1
    return all_rates


def aggregate(rates):
    stats = {k: {"anime": 0, "episodes": 0, "minutes": 0} for k in status_names}
    for rate in rates:
        st = rate.get("status")
        if st not in stats:
            continue
        ep = rate.get("episodes") or 0
        dur = (rate.get("anime") or {}).get("duration") or 0
        stats[st]["anime"] += 1
        stats[st]["episodes"] += ep
        stats[st]["minutes"] += ep * (dur or 0)
    total = {
        "anime": sum(v["anime"] for v in stats.values()),
        "episodes": sum(v["episodes"] for v in stats.values()),
        "minutes": sum(v["minutes"] for v in stats.values()),
    }
    return stats, total


def fmt_hours(mins):
    return int(mins / 60)


def build_stats_svg(stats, total):
    W, H = 1200, 370
    pad = 24

    # Подготовка данных для баров
    items = []
    for key, name in status_names.items():
        s = stats[key]
        items.append({"key": key, "name": name, "anime": s["anime"]})
    items.sort(key=lambda x: x["anime"], reverse=True)
    max_anime = max([i["anime"] for i in items] + [1])

    colors = {
        "planned": "#4b5563",
        "watching": "#22c55e",
        "completed": "#3b82f6",
        "on_hold": "#f59e0b",
        "dropped": "#ef4444",
        "rewatching": "#10b981",
    }

    # Геометрия карточки "как у секций"
    card_y = pad
    card_h = 322  # Height calculated to keep 24px padding on all sides
    card_w = W - pad * 2
    accent_w = 6
    inner_pad_x = 24
    inner_pad_y = 24

    labelW = 220
    barH = 26
    gap = 20
    barMaxW = card_w - inner_pad_x * 2 - accent_w - labelW - 80

    bars_svg = []
    y_offset = 0
    for it in items:
        w = int((it["anime"] / max_anime) * barMaxW) if max_anime > 0 else 0
        name = it["name"]
        anime_count = it["anime"]
        value_x = labelW + w + 12
        if value_x > labelW + barMaxW + 12:
            value_x = labelW + barMaxW + 12
        bars_svg.append(
            f"""      <g transform="translate(0,{y_offset})">
        <text x="0" y="{barH-8}" font-size="15" fill="#c9d1d9" font-family="Jetbrains Mono, ui-sans-serif, system-ui">{name}</text>
        <rect x="{labelW}" y="0" width="{w}" height="{barH}" rx="6"
              fill="{colors[it["key"]]}" stroke="#1f2937" stroke-opacity="0.6"/>
        <text x="{value_x}" y="{barH-8}" font-size="14" fill="#8b949e" font-family="Jetbrains Mono, ui-sans-serif, system-ui">{anime_count}</text>
      </g>"""
        )
        y_offset += barH + gap

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="g1" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#0c1117"/><stop offset="100%" stop-color="#0a0f16"/>
    </linearGradient>
    <pattern id="grid" width="40" height="59.428" patternTransform="scale(1.1)" patternUnits="userSpaceOnUse">
        <path fill="none" stroke="#fff" stroke-linecap="square" stroke-opacity=".05" d="M0 70.975V47.881m20-1.692L8.535 52.808v13.239L20 72.667l11.465-6.62V52.808zm0-32.95 11.465-6.62V-6.619L20-13.24 8.535-6.619V6.619L20 13.24m8.535 4.927v13.238L40 38.024l11.465-6.62V18.166L40 11.546zM20 36.333 0 47.88m0 0v23.094m0 0 20 11.548 20-11.548V47.88m0 0L20 36.333m0 0 20 11.549M0 11.547l-11.465 6.619v13.239L0 38.025l11.465-6.62v-13.24L0 11.548v-23.094l20-11.547 20 11.547v23.094M20 36.333V13.24"/>
	</pattern>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#7c3aed"/>
      <stop offset="100%" stop-color="#2563eb"/>
    </linearGradient>
    <filter id="ds" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="3" stdDeviation="6" flood-color="#000" flood-opacity="0.45"/>
    </filter>
  </defs>

  <rect width="100%" height="100%" rx="18" fill="url(#g1)"/>
  <rect width="100%" height="100%" rx="18" fill="url(#grid)"/>

  <path d="M1158 {card_y}H30V{card_y + card_h}H1158C1167.94 {card_y + card_h} 1176 {card_y + card_h - 8.059} 1176 {card_y + card_h - 18}V{card_y + 18}C1176 {card_y + 8.059} 1167.94 {card_y} 1158 {card_y}Z" fill="#0E1622" fill-opacity="0.72"/>
  <path d="M1158 {card_y + 0.5}C1167.67 {card_y + 0.5} 1175.5 {card_y + 8.335} 1175.5 {card_y + 18}V{card_y + card_h - 18}C1175.5 {card_y + card_h - 8.335} 1167.67 {card_y + card_h - 0.5} 1158 {card_y + card_h - 0.5}H30.5V{card_y + 0.5}H1158Z" stroke="#1F2937" stroke-opacity="0.6" fill="none"/>
  <path d="M31 {card_y + card_h}V{card_y}C27.134 {card_y} 24 {card_y + 3.134} 24 {card_y + 7}V{card_y + card_h - 7}C24 {card_y + card_h - 3.134} 27.134 {card_y + card_h} 31 {card_y + card_h}Z" fill="url(#accent)"/>

  <g transform="translate({pad + accent_w + inner_pad_x},{card_y + inner_pad_y})">
{chr(10).join(bars_svg)}
  </g>
</svg>
"""
    (OUT_DIR / "stats.svg").write_text(svg, encoding="utf-8")


def build_hero_svg(stats, total):
    W, H = 1200, 400
    title = "vffuunnyy"
    watched_anime = total["anime"] - stats["planned"]["anime"]
    watched_episodes = total["episodes"] - stats["planned"]["episodes"]
    watched_minutes = total["minutes"] - stats["planned"]["minutes"]
    sub = f"{watched_anime} тайтлов • {watched_episodes} эпизодов • {fmt_hours(watched_minutes)} ч"

    svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <clipPath id="r">
      <rect x="0" y="0" width="{W}" height="{H}" rx="18"/>
    </clipPath>
    <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#000" stop-opacity="0.25"/>
      <stop offset="100%" stop-color="#000" stop-opacity="0.6"/>
    </linearGradient>
  </defs>

  <g clip-path="url(#r)">
    <image href="{HERO_IMG}" x="0" y="0" width="{W}" height="{H}" preserveAspectRatio="xMidYMid slice"/>
    <rect x="0" y="0" width="{W}" height="{H}" fill="url(#fade)"/>
    <!-- Нижний бордер профиля -->
    <rect x="0" y="{H-1}" width="{W}" height="1" fill="#1f2937" fill-opacity="0.6"/>
  </g>

  <g transform="translate(50,{H-120})">
    <text x="0" y="0" font-size="60" font-weight="800" fill="#ffffff" font-family="Jetbrains Mono, ui-sans-serif, system-ui">{title}</text>
    <text x="5" y="55" font-size="26" fill="#e5e7eb" font-family="Jetbrains Mono, ui-sans-serif, system-ui">{sub}</text>
  </g>
</svg>
"""
    (OUT_DIR / "hero.svg").write_text(svg, encoding="utf-8")


def anime_stats():
    rates = fetch_all()
    stats, total = aggregate(rates)
    build_stats_svg(stats, total)
    build_hero_svg(stats, total)
