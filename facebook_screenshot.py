#!/usr/bin/env python3
import os
import time
import argparse
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image
import logging
import shutil
import io
import base64

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Configuration
FACEBOOK_URL = "https://www.facebook.com/EMHansele"
SCREENSHOT_DIR = os.path.dirname(os.path.abspath(__file__))  # Save in the project directory
SCREENSHOT_FILENAME = "screenshot.png"  # Fixed filename
SCREENSHOT_PATH = os.path.join(SCREENSHOT_DIR, SCREENSHOT_FILENAME)
# Default browser viewport size
BROWSER_WIDTH = 2000  # Changed from 1000 to 2000 as requested
BROWSER_HEIGHT = 2000
# We'll get the actual screenshot dimensions from the browser
USE_LOGIN = os.environ.get("USE_LOGIN", "false").lower() == "true"
USE_POPUP_LOGIN = os.environ.get("USE_POPUP_LOGIN", "false").lower() == "true"
FB_EMAIL = os.environ.get("FB_EMAIL")
FB_PASSWORD = os.environ.get("FB_PASSWORD")
# Screenshot interval in seconds (12 hours)
SCREENSHOT_INTERVAL = 12 * 60 * 60

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Facebook screenshot tool")
    parser.add_argument("--use-login", action="store_true", help="Use Facebook login before taking screenshot")
    parser.add_argument("--use-popup-login", action="store_true", help="Use the popup login dialog instead of removing it")
    parser.add_argument("--email", help="Facebook login email")
    parser.add_argument("--password", help="Facebook login password")
    parser.add_argument("--disable-headless", action="store_true", help="Disable headless mode (shows browser UI)")
    parser.add_argument("--single-run", action="store_true", help="Run once and exit instead of continuous mode")
    return parser.parse_args()

def setup_driver(headless=True):
    """Configure and return a Chrome webdriver instance."""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(f"--window-size={BROWSER_WIDTH},{BROWSER_HEIGHT}")
    chrome_options.add_argument("--disable-notifications")
    
    # Add user agent to avoid detection
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def login_to_facebook(driver):
    """Log in to Facebook using provided credentials."""
    try:
        logger.info("Attempting to log in to Facebook")
        driver.get("https://www.facebook.com/")
        
        # Handle cookie consent if it appears
        try:
            cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Allow') or contains(text(), 'Accept') or contains(text(), 'OK')]")
            if cookie_buttons:
                cookie_buttons[0].click()
                logger.info("Accepted cookies")
        except Exception as e:
            logger.warning(f"Could not handle cookie consent: {e}")
        
        # Find and fill email field
        email_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "email"))
        )
        email_field.send_keys(FB_EMAIL)
        
        # Find and fill password field
        password_field = driver.find_element(By.ID, "pass")
        password_field.send_keys(FB_PASSWORD)
        
        # Submit the form
        password_field.submit()
        
        # Wait for login to complete
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='main']"))
        )
        logger.info("Successfully logged in to Facebook")
        return True
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return False

def login_via_popup(driver, email, password):
    """Log in to Facebook using the popup dialog that appears on the page."""
    try:
        logger.info("Attempting to log in via popup dialog")
        
        # Wait for the popup dialog to appear
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//div[@role='dialog']"))
        )
        
        # Look for email field in the popup
        email_field = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.XPATH, "//form[@id='login_popup_cta_form']//input[@name='email']"))
        )
        email_field.send_keys(email)
        
        # Find and fill password field
        password_field = driver.find_element(By.XPATH, "//form[@id='login_popup_cta_form']//input[@name='pass']")
        password_field.send_keys(password)
        
        # Find and click the login button
        login_button = driver.find_element(By.XPATH, "//form[@id='login_popup_cta_form']//div[@aria-label='Log in to Facebook' or contains(text(), 'Log in')]")
        login_button.click()
        
        # Wait for the page to load after login
        time.sleep(5)
        
        # Check if login was successful by looking for some element that would indicate we're logged in
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='main']"))
            )
            logger.info("Successfully logged in via popup dialog")
            return True
        except Exception:
            logger.warning("Could not confirm successful login via popup")
            return False
        
    except Exception as e:
        logger.error(f"Popup login failed: {e}")
        return False

def remove_login_overlay(driver):
    """Remove the login overlay by clicking the Close button instead of modifying HTML."""
    try:
        logger.info("Checking for login overlay...")
        
        # Wait for a short time to ensure popup has appeared if it's going to
        time.sleep(2)
        
        # Try to find the Close button using aria-label attribute
        try:
            close_button = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//div[@aria-label='Close' and @role='button']"))
            )
            logger.info("Found Close button, clicking it...")
            close_button.click()
            logger.info("Successfully clicked the Close button")
            
            # Give it a moment to dismiss
            time.sleep(1)
            
            # Also remove the login banner at the bottom if present
            try:
                logger.info("Attempting to remove login banner...")
                remove_banner_script = """
                // Find and remove the login banner at the bottom
                const banners = document.querySelectorAll('div[data-nosnippet]');
                let removed = false;
                
                for (const banner of banners) {
                    if (banner.textContent.includes('Log in or sign up for Facebook') || 
                        banner.textContent.includes('connect with friends') ||
                        banner.textContent.includes('Create new account')) {
                        banner.remove();
                        console.log("Login banner removed");
                        removed = true;
                    }
                }
                
                // Also look for any element containing the specific text
                const allElements = document.querySelectorAll('div');
                for (const elem of allElements) {
                    if (elem.textContent.includes('Log in or sign up for Facebook') && 
                        elem.textContent.includes('connect with friends')) {
                        // Try to find a parent container to remove the entire banner
                        let parent = elem;
                        for (let i = 0; i < 5; i++) {
                            if (parent.parentElement) {
                                parent = parent.parentElement;
                            }
                        }
                        parent.remove();
                        console.log("Found and removed login banner via text content");
                        removed = true;
                        break;
                    }
                }
                
                return removed;
                """
                banner_removed = driver.execute_script(remove_banner_script)
                if banner_removed:
                    logger.info("Successfully removed login banner")
                else:
                    logger.info("No login banner found or couldn't be removed")
            except Exception as e:
                logger.warning(f"Error removing login banner: {e}")
            
            return True
        except Exception as e:
            logger.info(f"Could not find Close button with exact selector: {e}")
            
            # Try a more general approach to find the close button
            try:
                # Look for any close button or element that might dismiss the popup
                close_buttons = driver.find_elements(By.XPATH, "//div[contains(@aria-label, 'Close') or contains(@aria-label, 'close')]")
                if close_buttons:
                    logger.info("Found Close button with broader selector, clicking it...")
                    close_buttons[0].click()
                    logger.info("Successfully clicked the Close button")
                    time.sleep(1)
                    return True
                else:
                    logger.info("No Close button found with broader selector")
            except Exception as e2:
                logger.warning(f"Error trying to find any close button: {e2}")
        
        # If we couldn't find or click a close button, log the result
        logger.warning("Could not find or click the Close button, the overlay may still be present")
        return False
    except Exception as e:
        logger.warning(f"Error while trying to remove login overlay: {e}")
        return False

def take_full_page_screenshot(driver, filepath):
    """Take a screenshot of the upper third of the page by scrolling.
    
    Args:
        driver: The Selenium WebDriver
        filepath: The path where the screenshot should be saved
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info("Taking limited scroll screenshot...")
        
        # Get total height of the page
        total_height = driver.execute_script(
            "return Math.max(document.body.scrollHeight, document.body.offsetHeight, "
            "document.documentElement.clientHeight, document.documentElement.scrollHeight, "
            "document.documentElement.offsetHeight);"
        )
        logger.info(f"Total document height: {total_height}px")
        
        # Get viewport width and height
        viewport_width = driver.execute_script("return document.documentElement.clientWidth")
        viewport_height = driver.execute_script("return document.documentElement.clientHeight")
        logger.info(f"Viewport dimensions: {viewport_width}x{viewport_height}")
        
        # Limit to approximately a third of the page (viewport height * 3)
        max_capture_height = min(viewport_height * 3, total_height)
        logger.info(f"Limiting screenshot to height: {max_capture_height}px")
        
        # Create a new image with the limited height
        from PIL import Image
        full_image = Image.new('RGB', (viewport_width, max_capture_height))
        
        # Scroll through the page and take screenshots, but only up to the maximum capture height
        current_height = 0
        while current_height < max_capture_height:
            # Scroll to position
            driver.execute_script(f"window.scrollTo(0, {current_height});")
            time.sleep(2.0)  # Increased wait time to slow down scrolling
            
            # Take screenshot
            screenshot = driver.get_screenshot_as_png()
            image = Image.open(io.BytesIO(screenshot))
            
            # Calculate the portion of the screenshot to use
            paste_height = min(viewport_height, max_capture_height - current_height)
            
            # Paste the screenshot at the correct position
            full_image.paste(image.crop((0, 0, viewport_width, paste_height)), (0, current_height))
            
            # Calculate scrolling increment (use smaller increments for smoother scrolling)
            scroll_increment = int(viewport_height * 0.5)  # Half of viewport height for overlap
            current_height += scroll_increment
            logger.info(f"Scrolled to position: {current_height}")
            
            # Stop if we've reached our target height
            if current_height >= max_capture_height:
                break
        
        # Resize to 420 x 1250 while preserving aspect ratio
        logger.info(f"Resizing screenshot from {full_image.width}x{full_image.height} without distortion")
        
        # Target dimensions
        target_width = 420
        target_height = 1250
        
        # Calculate the aspect ratio of the original image and the target dimensions
        original_ratio = full_image.width / full_image.height
        target_ratio = target_width / target_height
        
        # Resize the image to fit either width or height while preserving aspect ratio
        if original_ratio > target_ratio:
            # Image is wider than target ratio, so fit to height and crop width
            # Calculate width needed to maintain aspect ratio with target height
            fit_width = int(target_height * original_ratio)
            resized_temp = full_image.resize((fit_width, target_height), Image.LANCZOS)
            
            # Crop from center to get target width
            left = (fit_width - target_width) // 2
            right = left + target_width
            resized_image = resized_temp.crop((left, 0, right, target_height))
            logger.info(f"Image was wider than target ratio: resized to {fit_width}x{target_height} then cropped width")
            
        else:
            # Image is taller than target ratio, so fit to width and crop height
            # Calculate height needed to maintain aspect ratio with target width
            fit_height = int(target_width / original_ratio)
            resized_temp = full_image.resize((target_width, fit_height), Image.LANCZOS)
            
            # Crop from top to get target height (prioritize top content)
            bottom = min(fit_height, target_height)
            resized_image = resized_temp.crop((0, 0, target_width, bottom))
            
            # If the resized image is shorter than target height, create a new image with padding
            if fit_height < target_height:
                padded_image = Image.new('RGB', (target_width, target_height), (255, 255, 255))
                padded_image.paste(resized_image, (0, 0))
                resized_image = padded_image
                logger.info(f"Image was taller than target ratio: resized to {target_width}x{fit_height} with padding if needed")
        
        # Save the properly resized image
        resized_image.save(filepath)
        logger.info(f"Aspect-ratio preserved screenshot saved to {filepath} (420x1250)")
        return True
        
    except Exception as e:
        logger.error(f"Error taking screenshot: {e}")
        return False

def main():
    """Main function to capture Facebook page screenshot."""
    logger.info("Starting Facebook screenshot process")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Command line args take precedence over environment variables
    use_login = args.use_login or USE_LOGIN
    use_popup_login = args.use_popup_login or USE_POPUP_LOGIN
    email = args.email or FB_EMAIL
    password = args.password or FB_PASSWORD
    headless = not args.disable_headless
    single_run = args.single_run
    
    # Continuous mode - run forever with interval
    while True:
        try:
            # Get the current time for logging
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Running screenshot capture at {current_time}")
            
            driver = None
            try:
                driver = setup_driver(headless=headless)
                capture_facebook_page(
                    driver, 
                    use_login=use_login,
                    use_popup_login=use_popup_login,
                    email=email,
                    password=password
                )
                logger.info("Facebook screenshot process completed successfully")
            except Exception as e:
                logger.error(f"Error in screenshot process: {e}")
            finally:
                if driver:
                    driver.quit()
            
            # If single run mode, exit after one iteration
            if single_run:
                logger.info("Single run mode - exiting")
                break
                
            # Wait for the next interval
            next_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(f"Waiting until next capture cycle at {next_time}")
            time.sleep(SCREENSHOT_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Process interrupted by user - exiting")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            # Wait a bit before trying again
            time.sleep(60)

def capture_facebook_page(driver, use_login=False, use_popup_login=False, email=None, password=None):
    """Navigate to the Facebook page and capture a screenshot."""
    try:
        # Use standard login if requested (before navigating to the target page)
        if use_login and email and password and not use_popup_login:
            success = login_to_facebook(driver)
            if not success:
                logger.warning("Standard login failed, proceeding without login")
        
        # Navigate to the target Facebook page
        logger.info(f"Navigating to Facebook page: {FACEBOOK_URL}")
        driver.get(FACEBOOK_URL)
        
        # Give the page some time to load
        time.sleep(5)
        
        # If popup login is enabled, try to login using the popup
        if use_popup_login and email and password:
            success = login_via_popup(driver, email, password)
            if not success:
                logger.warning("Popup login failed, will try to remove the overlay instead")
                remove_login_overlay(driver)
        # Otherwise just remove the login overlay
        elif not use_login:
            remove_login_overlay(driver)
        
        # Wait for post content to load
        logger.info("Waiting for posts to load completely")
        try:
            # Wait for articles to be present
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[@role='article']"))
            )
            # Additional wait time to ensure all visible content is fully loaded
            time.sleep(10)
            logger.info("Posts have loaded successfully")
        except Exception as e:
            logger.warning(f"Could not confirm all posts loaded, but continuing: {e}")
        
        # Get the initial scroll position
        initial_scroll_position = driver.execute_script("return window.pageYOffset;")
        logger.info(f"Initial scroll position: {initial_scroll_position}")
        
        # Try to remove the login banner again before scrolling
        try:
            remove_banner_script = """
            // Find elements containing the login banner text
            const allDivs = document.querySelectorAll('div');
            let found = false;
            
            for (const div of allDivs) {
                if (div.textContent && div.textContent.includes('Log in or sign up for Facebook')) {
                    // Navigate up to find a suitable parent to remove
                    let target = div;
                    for (let i = 0; i < 5; i++) {
                        if (target.parentElement) {
                            target = target.parentElement;
                        }
                    }
                    target.remove();
                    found = true;
                    break;
                }
            }
            
            return found;
            """
            banner_removed = driver.execute_script(remove_banner_script)
            if banner_removed:
                logger.info("Removed login banner before scrolling")
        except Exception as e:
            logger.warning(f"Error trying to remove login banner: {e}")
        
        # Scroll only to 1/3 of the previous amount (approximately viewport height)
        logger.info("Scrolling to load more posts (limited scroll)")
        viewport_height = driver.execute_script("return window.innerHeight")
        target_scroll_position = int(viewport_height * 0.8)  # Scroll to 80% of viewport height
        
        logger.info(f"Target scroll position: {target_scroll_position}px")
        
        # Use a more robust scrolling method with explicit scroll targets
        for current_scroll in range(0, target_scroll_position, 100):  # Smaller increments
            # Scroll to specific position rather than relative scrolling
            driver.execute_script(f"window.scrollTo(0, {current_scroll});")
            logger.info(f"Scrolled to position: {current_scroll}")
            
            # Verify scroll position
            actual_position = driver.execute_script("return window.pageYOffset;")
            logger.info(f"Actual scroll position: {actual_position}")
            
            # Wait longer for content to load after each scroll
            time.sleep(2)  # Increased wait time to slow down scrolling
        
        # One final scroll to the target position
        driver.execute_script(f"window.scrollTo(0, {target_scroll_position});")
        final_position = driver.execute_script("return window.pageYOffset;")
        logger.info(f"Final scroll position: {final_position}")
        
        # Wait for content to load after scrolling
        logger.info("Waiting 8 seconds for content to load after scrolling")
        time.sleep(8)  # Increased wait time
        
        # Scroll back to the top
        logger.info("Scrolling back to the top of the page")
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)  # Wait for scroll to complete
        top_position = driver.execute_script("return window.pageYOffset;")
        logger.info(f"Scrolled back to top position: {top_position}")
        
        # Set zoom level to 0.88 (88%) using JavaScript
        logger.info("Setting page zoom level to 0.88 (88%)")
        zoom_script = """
        document.body.style.zoom = "0.88";
        document.body.style.transformOrigin = "0 0";
        document.body.style.transform = "scale(0.88)";
        document.body.style.width = "114%";  /* 1/0.88 = ~1.14 */
        return "Zoom level set to 0.88";
        """
        zoom_result = driver.execute_script(zoom_script)
        logger.info(f"Zoom result: {zoom_result}")
        
        # Wait a bit more before taking the screenshot
        logger.info("Waiting 5 more seconds before taking screenshot")
        time.sleep(5)
        
        # First try to take a full-page screenshot
        success = take_full_page_screenshot(driver, SCREENSHOT_PATH)
        
        # If the full-page screenshot fails, fall back to a standard screenshot
        if not success:
            logger.warning("Full-page screenshot failed, falling back to standard screenshot")
            driver.save_screenshot(SCREENSHOT_PATH)
            logger.info(f"Standard screenshot saved to {SCREENSHOT_PATH}")
        
        # Reset zoom
        driver.execute_script("""
        document.body.style.zoom = "1";
        document.body.style.transform = "none";
        document.body.style.width = "100%";
        """)
        
        return True
    except Exception as e:
        logger.error(f"Error capturing Facebook page: {e}")
        return False

if __name__ == "__main__":
    main() 