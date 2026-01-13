import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import os

def get_soup(url, retries=3):
    for attempt in range(retries):
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=45)
            if r.status_code == 200:
                return BeautifulSoup(r.content, 'html.parser')
            if r.status_code == 429:
                print("(rate limited, waiting 60s) ", end="")
                time.sleep(60)
        except:
            if attempt < retries - 1:
                print("(retry) ", end="")
                time.sleep(15)
    return None

def format_phone(digits):
    if not digits or len(digits) < 10:
        return None
    digits = digits[-10:]
    if digits.startswith('1'):
        return digits[:4] + ' ' + digits[4:7] + ' ' + digits[7:]
    if digits.startswith('0'):
        return '(' + digits[:2] + ') ' + digits[2:6] + ' ' + digits[6:]
    return None

def get_specific_phone(soup):
    if not soup:
        return None
    for a in soup.find_all('a'):
        cls = a.get('class', [])
        if 'smart-button' in cls:
            text = a.get_text()
            href = a.get('href', '')
            if 'Call' in text and '1800' not in text:
                digits = re.sub(r'\D', '', href)
                if len(digits) >= 10:
                    phone_digits = digits[-10:]
                    if phone_digits != '1800366837':
                        return format_phone(phone_digits)
    return None

ALL_SLUGS = [
    "albany-creek-allsports-podiatry", "aldinga-podiatry-centre", "allsports-podiatry-parkwood",
    "aspley-allsports-podiatry", "back-in-motion-podiatry-bacchus-marsh", "back-in-motion-podiatry-melton",
    "ballarat-podiatry-centre", "bargara-advanced-foot-care-podiatry-clinic", "bathurst-podiatry-centre",
    "bayswater-back-in-motion-podiatry", "beerwah-podiatry-clinic", "bim-podiatry-balcatta",
    "bim-podiatry-woodville", "blacktown-podiatry-centre", "blackwood-podiatry-centre",
    "boronia-podiatry-centre", "brisbane-cbd-podiatry-centre", "brookwater-podiatry-centre",
    "bundaberg-advanced-foot-care-podiatry-centre", "bundall-back-in-motion-podiatry",
    "burleigh-waters-back-in-motion-podiatry", "burwood-podiatry-centre", "cairns-podiatry-centre",
    "calamvale-podiatry-centre-allsports", "camp-hill-podiatry-centre", "camp-hill-podiatry-centre-allsports",
    "casula-podiatry-centre", "cessnock-back-in-motion-podiatry", "chadstone-the-foot-and-ankle-clinic-podiatry-clinic",
    "charlestown", "christies-beach-podiatry-centre", "cleveland-podiatry-centre", "como-back-in-motion-podiatry",
    "cowboys-centre-of-excellence-nq-foot-ankle-centre", "cranbourne-podiatry-centre", "currambine-podiatry-centre",
    "devonport-podiatry-centre", "dubbo-podiatry-centre", "east-bentleigh-the-foot-and-ankle-clinic-podiatry-clinic",
    "forest-lake-podiatry-centre-allsports", "fortitude-valley-podiatry-centre", "foundation-podiatry",
    "gladstone-podiatry-centre", "gumdale-podiatry-centre", "hawthorne-podiatry-clinic-allsports-podiatry",
    "hervey-bay-advanced-foot-care-podiatry-centre", "hope-island-podiatry-centre", "hove-podiatry-centre",
    "indooroopilly-podiatry-centre", "indooroopilly-podiatry-centre-allsports", "ipswich-podiatry-centre",
    "jindalee-podiatry-centre-allsports", "kangaroo-point-allsports-podiatry-centre", "mackay-podiatry-centre",
    "mitchelton-podiatry-centre", "mittagong-podiatry-centre", "modbury-podiatry-centre",
    "moe-the-foot-and-ankle-clinic-podiatry-clinic", "monto-advanced-foot-care-podiatry-clinic",
    "moorebank-podiatry-centre", "mountgravatt-podiatry-orthotics-customfootwear", "mudgeeraba-back-in-motion-podiatry",
    "my-footdr-nq-foot", "narellan-podiatry-centre", "newstead-podiatry-clinic-anytime-physio-podiatry",
    "noosa", "north-lakes-podiatry-centre", "orange-podiatry-centre", "pakenham-podiatry-centre",
    "palmerston-podiatry-centre", "pimpama-allsports-podiatry", "red-hill", "red-hill-podiatry-centre-allsports",
    "redcliffe-podiatry-centre", "robina-physiologic-podiatry-centre", "robina-podiatry-centre",
    "rockhampton-podiatry-centre", "sale-the-foot-and-ankle-clinic-podiatry-clinic", "semaphore-podiatry-clinic",
    "shailer-park-podiatry-centre", "south-hobart-ispahan-podiatry-centre", "stafford-podiatry-centre",
    "stirling-podiatry-centre", "the-gap-podiatry-centre-allsports", "thuringowa-podiatry-centre",
    "toowong-podiatry-centre-allsports", "toowoomba-podiatry-centre", "townsville-podiatry-centre",
    "traralgon-the-foot-and-ankle-clinic-podiatry-clinic", "tweed-heads-podiatry-centre", "unley-podiatry-centre",
    "wantirna-podiatry-centre", "warragul-podiatry-centre", "warwick-podiatry-centre",
    "wavell-heights-podiatry-centre-allsports", "wellington-point-podiatry-centre-allsports",
    "wembley-downs-podiatry-centre", "wodonga-podiatry-centre", "yeppoon-podiatry-centre"
]

PROGRESS_FILE = "phone_progress.json"

# Load progress
phone_data = {}
if os.path.exists(PROGRESS_FILE):
    with open(PROGRESS_FILE, 'r') as f:
        phone_data = json.load(f)
    print(f"Resuming... {len(phone_data)} done\n")

remaining = [s for s in ALL_SLUGS if s not in phone_data]
print(f"Fetching {len(remaining)} remaining...\n")

for i, slug in enumerate(remaining):
    url = "https://web.archive.org/web/20250708180027/https://www.myfootdr.com.au/our-clinics/" + slug + "/"
    print(f"[{i+1}/{len(remaining)}] {slug}", end=" ")
    
    soup = get_soup(url)
    if soup:
        h1 = soup.find('h1')
        name = h1.get_text(strip=True) if h1 else slug
        phone = get_specific_phone(soup)
        phone_data[slug] = {"name": name, "phone": phone}
        
        # Save progress
        with open(PROGRESS_FILE, 'w') as f:
            json.dump(phone_data, f)
        
        print("-> " + (phone if phone else "no specific"))
    else:
        print("-> failed (will retry next run)")
    
    time.sleep(6)

# Update CSV
print("\nUpdating CSV...")
df = pd.read_csv('myfootdr_clinics.csv')

updated = 0
for slug, data in phone_data.items():
    if data.get('phone'):
        mask = df['Name of Clinic'] == data['name']
        if mask.any():
            current = df.loc[mask, 'Phone'].iloc[0]
            if current == '1800 366 837':
                df.loc[mask, 'Phone'] = data['phone']
                updated += 1

df.to_csv('myfootdr_clinics.csv', index=False)

generic = (df['Phone'] == '1800 366 837').sum()
print(f"\nDONE!")
print(f"  Updated: {updated}")
print(f"  Specific: {len(df) - generic}/99")
print(f"  Generic: {generic}/99")

# Keep progress file for re-runs if there were failures
failed = len(ALL_SLUGS) - len(phone_data)
if failed > 0:
    print(f"\n  {failed} failed - run again to retry")
else:
    os.remove(PROGRESS_FILE)
    print("\n  All complete! Progress file removed.")