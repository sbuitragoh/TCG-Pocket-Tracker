import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
import re


def build_search_url(card_name, card_id, set_name, card_rarity):

    encoded_set = quote(f"({set_name}_{card_id})")
    base_url = f"https://bulbapedia.bulbagarden.net/wiki/{card_name.replace(' ', '_')}_{encoded_set}"
    rarity_anchors = {
        "Full Art": "#Illustration_Rare-0",
        "Full Art EX/Support": "#Super_Rare-0",
        "Special Full Art": "#Special_Illustration_Rare-0",
        "Immersive": "#Immersive-0",
        "Gold Crown": "#Ultra_Rare-0",
        "One shiny star": "#Shiny_Rare-0",
        "Two shiny star": "#Shiny_Super_Rare-0"
    }

    if card_rarity in rarity_anchors:
        base_url += rarity_anchors[card_rarity]

    return base_url


def extract_image_url(soup, card_name_parsed, card_rarity):

    rarity_anchors = {
        "Full Art": "Illustration Rare",
        "Full Art EX/Support": "Super Rare",
        "Special Full Art": "Special Illustration Rare",
        "Immersive": "Immersive",
        "Gold Crown": "Ultra Rare",
        "One shiny star": "Shiny Rare",
        "Two shiny star": "Shiny Super Rare"
    }

    ## Special symbol case
    card_name_parsed = re.sub(r"[♂♀]", "", card_name_parsed)
    card_name_parsed = quote(card_name_parsed)

    if card_rarity in rarity_anchors:
        infobox = soup.find(title=rarity_anchors[card_rarity])
    else:
        infobox = soup.find(title=card_rarity)
    if not infobox:
        infobox = soup.find(
            "a", href=lambda href: href and card_name_parsed in href)

    if infobox:
        img = infobox.find("img")
        if img and img.get("src"):
            img_url = img["src"]
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            img_url = img_url.replace("thumb/", "").split(".png")[0] + ".png"
            return img_url

    return None


def get_image(card_name, card_id, set_name="Celestial_Guardians", card_rarity=None):
    
    card_name_parsed = card_name.replace(" ", "")
    search_url = build_search_url(card_name, card_id, set_name, card_rarity)
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(search_url, headers=headers)

    if response.status_code != 200:

        fallback_url = f"https://bulbapedia.bulbagarden.net/wiki/{card_name.replace(' ', '_')}_(TCG_Pocket)"
        response = requests.get(fallback_url, headers=headers)
        if response.status_code != 200:
            return None

    soup = BeautifulSoup(response.text, "html.parser")
    img_url = extract_image_url(soup, card_name_parsed, card_rarity)
    return img_url
