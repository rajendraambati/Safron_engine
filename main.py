import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import re
from bs4 import BeautifulSoup
import requests
import io
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)

# Function to extract data using XPath
def extract_data(xpath, driver):
    try:
        element = driver.find_element(By.XPATH, xpath)
        return element.text
    except:
        return "N/A"

# Main function to scrape Google Maps
def scrape_google_maps(search_query, driver):
    try:
        driver.get("https://www.google.com/maps")
        time.sleep(5)
        
        search_box = driver.find_element(By.XPATH, '//input[@id="searchboxinput"]')
        search_box.send_keys(search_query)
        search_box.send_keys(Keys.ENTER)
        time.sleep(5)
        
        actions = ActionChains(driver)
        for _ in range(10):
            actions.key_down(Keys.CONTROL).send_keys("-").key_up(Keys.CONTROL).perform()
            time.sleep(1)
        
        all_listings = set()
        previous_count = 0
        max_scrolls = 50
        scroll_attempts = 0
        
        while scroll_attempts < max_scrolls:
            scrollable_div = driver.find_element(By.XPATH, '//div[contains(@aria-label, "Results for")]')
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", scrollable_div)
            time.sleep(3)
            
            current_listings = driver.find_elements(By.XPATH, '//a[contains(@href, "https://www.google.com/maps/place")]')
            current_count = len(current_listings)
            
            for listing in current_listings:
                href = listing.get_attribute("href")
                if href:
                    all_listings.add(href)
            
            if current_count == previous_count:
                break
            
            previous_count = current_count
            scroll_attempts += 1
        
        results = []
        for i, href in enumerate(all_listings):
            driver.get(href)
            time.sleep(3)
            
            name = extract_data('//h1[contains(@class, "DUwDvf lfPIob")]', driver)
            address = extract_data('//button[@data-item-id="address"]//div[contains(@class, "fontBodyMedium")]', driver)
            phone = extract_data('//button[contains(@data-item-id, "phone:tel:")]//div[contains(@class, "fontBodyMedium")]', driver)
            website = extract_data('//a[@data-item-id="authority"]//div[contains(@class, "fontBodyMedium")]', driver)
            
            results.append({
                "Name": name,
                "Address": address,
                "Phone Number": phone,
                "Website": website
            })
        
        return pd.DataFrame(results)
    
    except Exception as e:
        logging.error(f"Error occurred: {e}")
        return None

# Main function to process the workflow
def main():
    st.set_page_config(page_title="Calibrage Info Systems", page_icon="🔍", layout="wide")
    
    st.title("🔍 Calibrage Info Systems Data Search Engine")
    search_query = st.text_input("Enter the search Term Below 👇", "")
    placeholder = st.empty()
    
    if st.button("Scrap It!"):
        if not search_query.strip():
            st.error("Please enter a valid search query.")
            return
        
        placeholder.markdown("**Processing..... Please Wait**")
        
        options = webdriver.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        df = scrape_google_maps(search_query, driver)
        driver.quit()
        
        if df is not None:
            websites = df["Website"].tolist()
            email_results = []
            for website in websites:
                if website != "N/A" and isinstance(website, str) and website.strip():
                    urls_to_try = [f"http://{website}", f"https://{website}"]
                    emails_found = []
                    for url in urls_to_try:
                        emails = scrape_website_for_emails(url)
                        emails_found.extend(emails)
                    email_results.append(", ".join(set(emails_found)) if emails_found else "N/A"
                else:
                    email_results.append("N/A")
            
            df["Email"] = email_results
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            
            placeholder.empty()
            st.success("Done! 👇Click Download Button Below")
            st.download_button(
                label="Download Results",
                data=output,
                file_name="final_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

if __name__ == "__main__":
    main()
