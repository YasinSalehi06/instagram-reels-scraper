import logging
import pathlib
import platform
import sys
import time
import requests
import re
import os

from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchWindowException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains

# Configure logging
logging.basicConfig(format="[%(levelname)s] instagram-download-reels: %(message)s", level=logging.INFO)
logging.info("Starting...")

# Define directory to save videos
videos_dir = "videos"
os.makedirs(videos_dir, exist_ok=True)

"""Sanitize the file's name to remove any invalid characters."""
def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*\n\r\t]', '', filename)

"""Configure the Chrome WebDriver."""
def configure_webdriver():
    mobile_emulation = {
        "deviceMetrics": {"width": 400, "height": 700, "pixelRatio": 3.0},
        "userAgent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 "
                      "(KHTML, like Gecko) Version/14.0 Mobile/15A372 Safari/604.1")
    }

    options = Options()
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_experimental_option("mobileEmulation", mobile_emulation)
    options.add_argument("--start-maximized")


    if platform.system() == "Windows":
        wd = pathlib.Path().absolute()
        options.add_argument(f"user-data-dir={wd}\\chrome-profile")
    else:
        options.add_argument("user-data-dir=chrome-profile")

    return webdriver.Chrome(options=options)

"""Wait for the user to log in to Instagram."""
def wait_for_login(driver):
    while True:
        if driver.current_url.startswith("https://www.instagram.com/accounts/onetap/") or driver.current_url == ("https://www.instagram.com/"):
            logging.info("Login detected")
            break
        try:
            logging.info("Waiting for sign in... (Please sign in and don't click anything else after signing in!)")

            def is_not_now_div_present(driver):
                try:
                    div = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='button']")))
                    return div.text == "Not Now"
                except:
                    return False

            WebDriverWait(driver, 10).until(is_not_now_div_present)
            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "div[role='button']"))).send_keys(Keys.ENTER)
            logging.info("Clicked 'Not now' on 'Save Your Login Info?'")
            break
        except TimeoutException:
            pass

"""Download the video and save it, with the top comment as the file's name."""
def download_video(video_url, filename):
    response = requests.get(video_url, stream=True)
    with open(os.path.join(videos_dir, filename), "wb") as video_file:
        for chunk in response.iter_content(chunk_size=1024):
            if chunk:
                video_file.write(chunk)
    logging.info(f"Downloaded {filename}")

"""Close the comments section after extracting video details"""
def close_comments_section(driver):
    target_element = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.XPATH, "//div[text()='Comments' and @class='']")))

    time.sleep(1)
    actions = ActionChains(driver)
    actions.move_to_element_with_offset(target_element, 0, -51).click().perform()
    time.sleep(2)

try:
    driver = configure_webdriver()
    logging.info("Opened Chrome browser")

    driver.get("https://www.instagram.com/accounts/login/")
    logging.info("Opening https://www.instagram.com/accounts/login/")

    wait_for_login(driver)

    """Main loop that scrolls through your FYP and downloads each reel"""
    while True:
        driver.get("https://www.instagram.com/reels/")
        time.sleep(2)
        video_elements = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.TAG_NAME, 'video')))
        comment_buttons = WebDriverWait(driver, 20).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'svg[aria-label="Comment"]')))

        for video_element, comment_button in zip(video_elements, comment_buttons):
            actions = ActionChains(driver)
            actions.move_to_element(video_element).perform()
            comment_button.click()
            time.sleep(2)

            comments = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[style="display: inline;"]')))
            
            text_comments = [comment.text.strip() for comment in comments if comment.text.strip()]

            if text_comments[1]:
                filename = f"{sanitize_filename(text_comments[1])}.mp4"
            else:
                filename = f"video_{datetime.now().strftime('%Y%m%d%H%M%S')}.mp4"

            video_url = video_element.get_attribute("src")
            download_video(video_url, filename)

            close_comments_section(driver)

except KeyboardInterrupt:
    logging.info("Quitting on keyboard interrupt...")
except NoSuchWindowException:
    logging.exception("Browser window closed unexpectedly")
except Exception:
    logging.exception("Unknown error occurred")
finally:
    try:
        driver.quit()
    except:
        pass
    sys.exit(1)
