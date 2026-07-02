import time
import os
import requests
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime



driver = webdriver.Chrome()

driver.get("https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&is_targeted_country=false&media_type=all&search_type=page&sort_data[mode]=total_impressions&sort_data[direction]=desc&view_all_page_id=15087023444")

WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Library ID')]")))
time.sleep(2)

library_id_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Library ID')]")
print(f"Found {len(library_id_elements)} ad cards")

os.makedirs("ad_assets", exist_ok=True)
os.makedirs("csv_exports", exist_ok=True)   


# lkp table for platform positions
PLATFORM_POSITIONS = {
    "-387px -766px": "Facebook",
    "-387px -753px": "Instagram",
    "-387px -805px": "Messenger",
    "-387px -818px": "Audience Network",
    "-387px -1017px": "WhatsApp",
}

# looks at an ad card and figures out which platforms (Facebook, Instagram, etc.) the ad ran on, using that lookup table above.
def get_platforms(container):
    try:
        icon_divs = container.find_elements(By.XPATH, ".//*[contains(@style, 'mask-image')]")
        platform_names = set()
        for div in icon_divs:
            position = driver.execute_script(
                "return window.getComputedStyle(arguments[0]).maskPosition;", div
            )
            if position and position.startswith("-387px") and position in PLATFORM_POSITIONS:
                platform_names.add(PLATFORM_POSITIONS[position])
        return ", ".join(sorted(platform_names))
    except Exception:
        return ""

 # reads the text inside the ad card and grabs the actual ad copy (the sentence that appears right after the word "Sponsored").
def get_ad_text(container):
    try:
        full_lines = container.text.split("\n")
        for idx, line in enumerate(full_lines):
            if line.strip() == "Sponsored" and idx + 1 < len(full_lines):
                return full_lines[idx + 1].strip()
    except Exception:
        pass
    return ""

# finds the ad's picture on the page and saves it as a file into a folder called ad_assets.
def download_image(container, library_id, card_index):
    asset_path = ""
    try:
        all_imgs = container.find_elements(By.TAG_NAME, "img")
        img_url = None
        for img in all_imgs:
            alt_text = (img.get_attribute("alt") or "").strip()
            src = img.get_attribute("src")
            if alt_text in ("Facebook", "Instagram", "Messenger", "Audience Network", "Threads"):
                continue
            if src and not src.startswith("data:"):
                img_url = src
                break
        if img_url:
            file_name = f"ad_assets/{library_id}.jpg"
            response = requests.get(img_url, timeout=10)
            with open(file_name, "wb") as f:
                f.write(response.content)
            asset_path = file_name
        else:
            print(f"Card #{card_index} — no valid image URL found")
    except Exception as e:
        print(f"Card #{card_index} — could not download asset: {e}")
    return asset_path

#  handles a normal, single ad
def scrape_card(card, full_card, source_id, card_index):
    lines = card.text.split("\n")
    if len(lines) < 3:
        print(f"Card #{card_index} skipped — only {len(lines)} line(s): {lines}")
        return None

    status = lines[0]
    library_id = lines[1].replace("Library ID: ", "")
    date_line = lines[2]

    if " - " in date_line:
        start_date, end_date = date_line.split(" - ")
    else:
        start_date = date_line.replace("Started running on ", "")
        end_date = ""

    platforms = get_platforms(full_card)
    ad_text = get_ad_text(full_card)
    asset_path = download_image(full_card, library_id, card_index)

    return {
        "Asset Path": asset_path,
        "Source ID": source_id,
        "ID": library_id,
        "Status": status,
        "Platform": platforms,
        "Ad Text": ad_text,
        "Start Date": start_date,
        "End Date": end_date
    }

#  handles a "grouped" ad (multiple versions under one card)
def scrape_summary_page(parent_library_id, card_index):
    """Scrape only the sub-ads inside the '3 ads' grid on a summary page,
    scoped to the container so we don't pick up unrelated 'Library ID'
    text elsewhere on the page."""
    rows = []
    try:
        scope_marker = driver.find_element(By.XPATH, "//*[contains(text(), 'Any filters you applied')]")
        ads_container = scope_marker.find_element(By.XPATH, "./ancestor::div[3]")
    except Exception as e:
        print(f"  Could not find scoped ads container, falling back to full page: {e}")
        ads_container = driver

    summary_library_id_elements = ads_container.find_elements(By.XPATH, ".//*[contains(text(), 'Library ID')]")
    print(f"  Summary page — found {len(summary_library_id_elements)} sub-ads in scoped container")

    shared_asset_path = ""
    for j in range(len(summary_library_id_elements)):
        try:
            summary_library_id_elements = ads_container.find_elements(By.XPATH, ".//*[contains(text(), 'Library ID')]")
            sub_el = summary_library_id_elements[j]
            sub_card = sub_el.find_element(By.XPATH, "./ancestor::div[6]")
            sub_full_card = sub_el.find_element(By.XPATH, "./ancestor::div[10]")
        except Exception as e:
            print(f"    Sub-ad #{j} — could not build card refs: {e}")
            continue

        sub_lines = sub_card.text.split("\n")
        if len(sub_lines) < 3:
            print(f"    Sub-ad #{j} skipped — only {len(sub_lines)} line(s): {sub_lines}")
            continue

        sub_status = sub_lines[0]
        sub_library_id = sub_lines[1].replace("Library ID: ", "")
        sub_date_line = sub_lines[2]

        if " - " in sub_date_line:
            sub_start_date, sub_end_date = sub_date_line.split(" - ")
        else:
            sub_start_date = sub_date_line.replace("Started running on ", "")
            sub_end_date = ""

        sub_platforms = get_platforms(sub_full_card)
        sub_ad_text = get_ad_text(sub_full_card)

        if not shared_asset_path:
            shared_asset_path = download_image(sub_full_card, parent_library_id, card_index)

        rows.append({
            "Asset Path": shared_asset_path,
            "Source ID": parent_library_id,
            "ID": sub_library_id,
            "Status": sub_status,
            "Platform": sub_platforms,
            "Ad Text": sub_ad_text,
            "Start Date": sub_start_date,
            "End Date": sub_end_date
        })
        print(f"    Sub-ad #{j} (ID: {sub_library_id}) scraped")

    return rows

ads_data = []

# --- PASS 1: scrape all normal ads, expand and scrape summary cards inline ---
i = 0
while i < len(library_id_elements):
    try:
        library_id_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'Library ID')]")
        el = library_id_elements[i]
        card = el.find_element(By.XPATH, "./ancestor::div[6]")
        button_card = el.find_element(By.XPATH, "./ancestor::div[7]")
        full_card = el.find_element(By.XPATH, "./ancestor::div[10]")
    except Exception as e:
        print(f"Card #{i} — could not build card refs: {e}")
        i += 1
        continue

    lines = card.text.split("\n")

    if len(lines) < 3:
        print(f"Card #{i} skipped — only {len(lines)} line(s): {lines}")
        i += 1
        continue

    parent_library_id = lines[1].replace("Library ID: ", "")

    button = None
    button_text = ""
    all_buttons = button_card.find_elements(By.XPATH, ".//div[@role='button'] | .//button")
    for btn in all_buttons:
        txt = btn.text.strip()
        if "details" in txt.lower():
            button = btn
            button_text = txt
            break

    print(f"Card #{i} (ID: {parent_library_id}) — button text: '{button_text}'")

    if "summary" in button_text.lower():
        print(f"Card #{i} (ID: {parent_library_id}) — summary card, opening summary view")
        if button:
            original_url = driver.current_url
            button.click()
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Library ID')]"))
            )
            time.sleep(2)

            summary_rows = scrape_summary_page(parent_library_id, i)
            ads_data.extend(summary_rows)

            print(f"Card #{i} (ID: {parent_library_id}) — {len(summary_rows)} sub-ads scraped, returning to results")
            driver.get(original_url)
            WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Library ID')]"))
            )
            time.sleep(2)
        i += 1
        continue

    else:
        row = scrape_card(card, full_card, parent_library_id, i)
        if row:
            ads_data.append(row)

    i += 1

print(f"\nPass 1 done. {len(ads_data)} total rows scraped.\n")


# --- SAVE ---
df = pd.DataFrame(ads_data)
timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
csv_filename = f"csv_exports/ads_export_{timestamp}.csv"
df.to_csv(csv_filename, index=False)
print(f"\nSaved {len(ads_data)} total rows to {csv_filename}")

driver.quit()