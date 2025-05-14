import requests
from bs4 import BeautifulSoup

def get_image(card_name, card_id, set_name="Celestial_Guardians"):

    # Directly search for the card's page and extract the image
    card_name_parsed = card_name.replace(" ", "")
    from urllib.parse import quote
    encoded_set = quote(f"({set_name}_{card_id})")
    search_url = f"https://bulbapedia.bulbagarden.net/wiki/{card_name.replace(' ', '_')}_{encoded_set}"
    headers = {"User-Agent": "Mozilla/5.0"}

    response = requests.get(search_url, headers=headers)
    if response.status_code != 200:
        # Try fallback to just card name (in case set_name is not in URL)
        search_url = f"https://bulbapedia.bulbagarden.net/wiki/{card_name.replace(' ', '_')}_(TCG_Pocket)"
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            return None

    soup = BeautifulSoup(response.text, "html.parser")
    # Find the first image in the infobox
    infobox = soup.find("a", class_="mw-file-description", href=lambda href: href and card_name_parsed in href)
    if infobox:
        img = infobox.find("img")
        if img and img.get("src"):
            img_url = img["src"]
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            img_url = img_url.replace("thumb/", "").split(".png")[0] + ".png"
            return img_url
    return None

if __name__ == "__main__":
    card_name = "Dartrix"
    card_id = '11'
    image_url = get_image(card_name=card_name, card_id=card_id)
    print(f"Image URL for {card_name}: {image_url}")