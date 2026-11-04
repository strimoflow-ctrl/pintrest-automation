import random
import re

# High-converting Pinterest Title templates with explicit Visit Site CTAs
TITLE_TEMPLATES = [
    "🔥 Aesthetic {subject} PFP 4K (Visit Site To Download HD ⬇️)",
    "✨ {subject} 4K Ultra HD PFP | Download HD - Visit Link ⬇️",
    "🖤 Dark {subject} PFP & 4K Wallpaper (Visit Site To Download HD)",
    "💎 Cool {subject} Avatar 4K | Download HD (Visit Site ⬇️)",
    "⚡ {subject} Aesthetic PFP | Visit Link To Download Ultra HD ⬇️",
    "🌸 Trendy {subject} PFP 4K (Visit Site To Download HD ⬇️)",
    "👑 Ultra HD {subject} Wallpaper & PFP | Download HD (Visit Link)",
    "💜 Moody {subject} 4K Profile Picture (Visit Site To Download HD ⬇️)"
]

SUBJECTS = [
    "Boy", "Anime Boy", "Dark Boy", "Cool Boy", 
    "Girl", "Anime Girl", "Aesthetic Girl",
    "Matching Couple", "Anime", "Aesthetic Mood"
]

DESCRIPTION_TEMPLATES = [
    "Looking for the cleanest {subject} PFP in original 4K resolution? Tap visit site to download the full uncompressed HD image directly with zero quality loss! Perfect for Instagram, Discord, and Telegram avatars.",
    "Upgrade your profile picture with this aesthetic {subject} 4K icon! Visit our website to preview and download the ultra high-definition version instantly.",
    "Free Ultra HD {subject} Wallpaper & PFP. Download original uncompressed graphics, high dynamic range, and crisp colors. Click the link to download now!",
    "Best aesthetic {subject} avatar for social media! High contrast, 4K crisp detail. Visit the site for the original file download."
]

TAGS_POOL = [
    "#pfp", "#aestheticpfp", "#boypfp", "#girlpfp", "#animepfp", 
    "#darkaesthetic", "#wallpaper4k", "#discordpfp", "#profilepicture", 
    "#animeaesthetic", "#coolpfp", "#instapfp", "#aestheticwallpaper"
]

def clean_caption(caption: str) -> str:
    """Removes telegram links and garbage symbols from original caption if present."""
    if not caption:
        return ""
    # remove links
    caption = re.sub(r"https?://\S+|t\.me/\S+", "", caption)
    # remove excessive symbols
    caption = re.sub(r"[@_#*]", " ", caption)
    return " ".join(caption.split())

def generate_seo_metadata(caption: str = "", media_type: str = "photo", msg_id: int = 0):
    """
    Generates click-worthy, SEO-optimized title, description, and tags for Pinterest.
    """
    cleaned = clean_caption(caption)
    
    # Try to detect subject from caption if available
    subject = "Boy" # default common subject in Nox_oo1
    caption_lower = cleaned.lower()
    
    if "girl" in caption_lower:
        subject = "Girl"
    elif "couple" in caption_lower or "matching" in caption_lower:
        subject = "Matching Couple"
    elif "anime" in caption_lower:
        subject = "Anime Boy" if "boy" in caption_lower else "Anime"
    elif "dark" in caption_lower:
        subject = "Dark Boy"
    else:
        # Use pseudo-random based on msg_id so it's consistent
        rng = random.Random(msg_id)
        subject = rng.choice(SUBJECTS)
        
    rng = random.Random(msg_id)
    title_template = rng.choice(TITLE_TEMPLATES)
    desc_template = rng.choice(DESCRIPTION_TEMPLATES)
    
    title = title_template.format(subject=subject)
    description = desc_template.format(subject=subject)
    
    # Pick 5-7 trendy tags
    selected_tags = rng.sample(TAGS_POOL, min(6, len(TAGS_POOL)))
    tags_str = " ".join(selected_tags)
    
    # Append tags to description for Pinterest search indexing
    full_description = f"{description}\n\n{tags_str}"
    
    return {
        "title": title[:100],  # Pinterest title max length is 100
        "description": full_description[:500], # Pinterest description max is 500
        "tags": tags_str
    }

if __name__ == "__main__":
    meta = generate_seo_metadata(caption="Dark wallpaper aesthetic", msg_id=123)
    print("Sample Title:", meta["title"])
    print("Sample Desc:", meta["description"])

