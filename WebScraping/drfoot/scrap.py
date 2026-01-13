import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import os

# --- Configuration ---
BASE_ARCHIVE_PREFIX = "https://web.archive.org"
START_URL = "https://web.archive.org/web/20250708180027/https://www.myfootdr.com.au/our-clinics/"
OUTPUT_FILE = "myfootdr_clinics.csv"
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

def get_soup(url, retries=3):
    headers = {'User-Agent': USER_AGENT}
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=45)
            if response.status_code == 200:
                return BeautifulSoup(response.content, 'html.parser')
            elif response.status_code == 429:
                print(f"  !! Rate limited. Waiting 3 minutes...")
                time.sleep(180)
            else:
                print(f"  !! Status {response.status_code}. Retry {attempt+1}/{retries}...")
                time.sleep(15)
        except Exception as e:
            print(f"  !! Error: {type(e).__name__}. Waiting 90s...")
            time.sleep(90)
    return None

def clean_address(text):
    if not text:
        return "N/A"
    text = re.sub(r'^[ib]\s+', '', text.strip())
    text = " ".join(text.split())
    return text if len(text) > 5 else "N/A"

def format_phone(digits):
    if not digits:
        return "N/A"
    digits = re.sub(r'\D', '', digits)
    if len(digits) < 8:
        return "N/A"
    if len(digits) == 10 and digits.startswith('1'):
        return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    if len(digits) == 10 and digits.startswith('04'):
        return f"{digits[:4]} {digits[4:7]} {digits[7:]}"
    if len(digits) == 10 and digits.startswith('0'):
        return f"({digits[:2]}) {digits[2:6]} {digits[6:]}"
    if len(digits) == 8:
        return f"{digits[:4]} {digits[4:]}"
    return digits

def extract_phone(soup):
    tel_links = soup.select('a[href^="tel:"]')
    for tel in tel_links:
        phone_href = tel['href'].replace('tel:', '').strip()
        phone_href = re.sub(r'^\+61\s*', '0', phone_href)
        digits = re.sub(r'\D', '', phone_href)
        if len(digits) >= 8:
            return format_phone(digits)
    
    metabox = soup.find('div', class_='clinic-metabox')
    if metabox:
        text = metabox.get_text(separator=' ')
        patterns = [
            r'1800\s*\d{3}\s*\d{3}',
            r'1300\s*\d{3}\s*\d{3}',
            r'$0[2-9]$\s*\d{4}\s*\d{4}',
            r'0[2-9]\s*\d{4}\s*\d{4}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                digits = re.sub(r'\D', '', match.group(0))
                return format_phone(digits)
    
    page_text = soup.get_text(separator=' ')
    call_match = re.search(r'Call\s*(\d[\d\s]{8,})', page_text)
    if call_match:
        digits = re.sub(r'\D', '', call_match.group(1))
        if len(digits) >= 8:
            return format_phone(digits[:10])
    
    return "N/A"

def extract_services(soup):
    """Extract clinic-specific services."""
    
    # These are the ACTUAL service terms we're looking for
    valid_services = [
        'sports podiatry', 'digital gait analysis', 'custom orthotics',
        'paediatric assessments', 'pediatric assessments', 'footwear assessments',
        'ingrown toenail', 'diabetic foot', 'diabetes', 'nail surgery',
        'biomechanical', 'orthotic', 'heel pain', 'plantar fasciitis',
        'gait analysis', 'video gait', 'shockwave', 'dry needling',
        'corn', 'callus', 'wart', 'verruca', 'fungal nail', 'elderly',
        'aged care', 'ndis', 'senior', 'children', 'kids foot'
    ]
    
    # These are navigation/blog items we want to EXCLUDE
    exclude_items = [
        'dancing', 'running', 'hiking', 'falls prevention', 'beautiful nails',
        'menu', 'home', 'about', 'contact', 'careers', 'privacy', 'telehealth',
        'our team', 'book online', 'find a clinic', 'brisbane', 'sydney',
        'melbourne', 'queensland', 'new south wales', 'victoria', 'job',
        'student', 'referral', 'altra', 'archies', 'propet', 'ecco'
    ]
    
    def is_valid_service(text):
        text_lower = text.lower()
        # Exclude navigation items
        for ex in exclude_items:
            if ex in text_lower:
                return False
        # Check if it contains a valid service term
        for svc in valid_services:
            if svc in text_lower:
                return True
        # Also accept if it ends with common service patterns
        if re.search(r'(assessment|therapy|treatment|analysis|care|orthotics|podiatry)s?$', text_lower):
            return True
        return False
    
    services = []
    
    # Method 1: Look for UL lists where MOST items look like services
    for ul in soup.find_all('ul'):
        items = []
        for li in ul.find_all('li', recursive=False):
            text = li.get_text(strip=True)
            if 3 < len(text) < 80:
                items.append(text)
        
        if not items or len(items) < 3 or len(items) > 15:
            continue
        
        # Count valid service items
        valid_count = sum(1 for item in items if is_valid_service(item))
        
        # If at least half the items are valid services, use this list
        if valid_count >= len(items) / 2 and valid_count >= 2:
            for item in items:
                if is_valid_service(item) or (len(item) > 3 and not any(ex in item.lower() for ex in exclude_items)):
                    services.append(item)
            break
    
    # Method 2: Find "Services Available" header and look for nearby list
    if not services:
        svc_header = soup.find(lambda tag: tag.name in ['h2', 'h3', 'h4', 'h5'] and 
                               'Services Available' in tag.get_text())
        if svc_header:
            # Look for UL in parent or nearby
            parent = svc_header.find_parent(['div', 'section', 'article'])
            if parent:
                ul = parent.find('ul')
                if ul:
                    for li in ul.find_all('li', recursive=False):
                        text = li.get_text(strip=True)
                        if 3 < len(text) < 80:
                            services.append(text)
    
    # Method 3: Look for specific service headers as services themselves
    if not services:
        service_headers = [
            'Clinical Podiatry', 'Custom Foot Orthotics', 'Video Gait Analysis',
            'Diabetes and Footcare', 'Seniors Footcare', 'Sports Podiatry',
            'Paediatric Podiatry', 'Biomechanical Assessment'
        ]
        for header in soup.find_all(['h3', 'h4', 'h5']):
            text = header.get_text(strip=True)
            for svc in service_headers:
                if svc.lower() in text.lower():
                    services.append(svc)
    
    # Deduplicate
    seen = set()
    unique_services = []
    for s in services:
        s_clean = s.strip()
        s_lower = s_clean.lower()
        if s_lower not in seen and len(s_clean) > 2:
            seen.add(s_lower)
            unique_services.append(s_clean)
    
    return ", ".join(unique_services) if unique_services else "General Podiatry"

def extract_clinic_urls(soup):
    clinic_urls = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/our-clinics/' not in href:
            continue
        if '/regions/' in href:
            continue
        href = href.split('#')[0]
        if href.startswith('/web/'):
            full_url = BASE_ARCHIVE_PREFIX + href
        elif href.startswith('https://web.archive.org'):
            full_url = href
        else:
            continue
        if full_url.rstrip('/').endswith('/our-clinics'):
            continue
        match = re.search(r'/our-clinics/([^/]+)/?$', full_url)
        if match and len(match.group(1)) > 2:
            clinic_urls.add(full_url.rstrip('/'))
    return sorted(clinic_urls)

def scrape_clinic_page(clinic_url):
    soup = get_soup(clinic_url)
    if not soup:
        return None

    # 1. NAME
    name = "N/A"
    h1 = soup.find('h1')
    if h1:
        name = " ".join(h1.get_text().split())

    # 2. ADDRESS
    address = "N/A"
    address_div = soup.find('div', class_='address')
    if address_div:
        address = clean_address(address_div.get_text(separator=' ', strip=True))
    
    if address == "N/A":
        address_elem = soup.select_one('.address, [class*="address"]')
        if address_elem:
            address = clean_address(address_elem.get_text(separator=' ', strip=True))

    # 3. EMAIL
    email = "N/A"
    mailto = soup.select_one('a[href^="mailto:"]')
    if mailto:
        email = mailto['href'].replace('mailto:', '').split('?')[0].strip()
    
    if email == "N/A":
        page_text = soup.get_text()
        email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', page_text)
        if email_match:
            email = email_match.group(0)

    # 4. PHONE
    phone = extract_phone(soup)

    # 5. SERVICES
    services = extract_services(soup)

    return {
        "Name of Clinic": name,
        "Address": address,
        "Email": email,
        "Phone": phone,
        "Services": services
    }

def main():
    print("=" * 60)
    print("MyFootDr Clinic Scraper - v7 (Services Fix 2)")
    print("=" * 60)

    if os.path.exists(OUTPUT_FILE):
        print(f"⚠ Removing old {OUTPUT_FILE} to re-scrape")
        os.remove(OUTPUT_FILE)

    print("\n[1/3] Fetching main clinic listing...")
    main_soup = get_soup(START_URL)
    if not main_soup:
        print("✗ Failed to fetch main page!")
        return

    print("[2/3] Extracting clinic URLs...")
    clinic_urls = extract_clinic_urls(main_soup)
    print(f"✓ Found {len(clinic_urls)} unique clinic pages")

    print(f"[3/3] Scraping clinic pages...\n")
    print("-" * 60)

    results = []
    failed_count = 0

    for i, url in enumerate(clinic_urls):
        slug = url.split('/our-clinics/')[-1].rstrip('/')
        print(f"[{i+1}/{len(clinic_urls)}] {slug}")

        data = scrape_clinic_page(url)

        if data:
            results.append(data)
            print(f"  ✓ {data['Name of Clinic']}")
            print(f"    📍 {data['Address']}")
            print(f"    📞 {data['Phone']} | ✉️  {data['Email']}")
            
            svc_display = data['Services'][:60] + "..." if len(data['Services']) > 60 else data['Services']
            print(f"    🏥 {svc_display}")
        else:
            print(f"  ✗ Failed to scrape")
            failed_count += 1

        if len(results) > 0 and len(results) % 10 == 0:
            temp_df = pd.DataFrame(results)
            temp_df = temp_df[['Name of Clinic', 'Address', 'Email', 'Phone', 'Services']]
            temp_df.to_csv(OUTPUT_FILE, index=False)
            print(f"\n  💾 Progress saved: {len(results)} clinics\n")

        time.sleep(8)

    print("\n" + "=" * 60)
    
    if results:
        final_df = pd.DataFrame(results)
        final_df = final_df[['Name of Clinic', 'Address', 'Email', 'Phone', 'Services']]
        final_df = final_df.drop_duplicates(subset=['Name of Clinic'], keep='first')
        final_df.to_csv(OUTPUT_FILE, index=False)
        
        print(f"✓ COMPLETE!")
        print(f"  Total clinics: {len(final_df)}")
        print(f"  Failed: {failed_count}")
        print(f"  Output file: {OUTPUT_FILE}")
        
        na_phones = final_df[final_df['Phone'] == 'N/A'].shape[0]
        na_emails = final_df[final_df['Email'] == 'N/A'].shape[0]
        na_addresses = final_df[final_df['Address'] == 'N/A'].shape[0]
        default_services = final_df[final_df['Services'] == 'General Podiatry'].shape[0]
        
        print(f"\n📊 Data Quality:")
        print(f"  Phones: {len(final_df) - na_phones}/{len(final_df)} found")
        print(f"  Emails: {len(final_df) - na_emails}/{len(final_df)} found")
        print(f"  Addresses: {len(final_df) - na_addresses}/{len(final_df)} found")
        print(f"  Services: {len(final_df) - default_services}/{len(final_df)} specific")
        
    else:
        print("⚠ No data to save")

    print("=" * 60)

if __name__ == "__main__":
    main()