import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from app.services.extract_malt_info import ExtractMaltInfo
import time
import os
import json
from app.core.config import config
import atexit
import signal
import sys


class MaltScrapper:
    _instances = set()

    @classmethod
    def _cleanup_all(cls):
        """Clean up all instances during shutdown"""
        for instance in cls._instances.copy():
            instance._cleanup(from_shutdown=True)

    def __init__(self, headless=True, profil_url=None):
        self.profil_url = profil_url
        self.id = self.profil_url.split("/")[-1] if self.profil_url else None
        self.workspace_path = (
            f"{config.WORKSPACE_BASE_PATH}/{self.id}" if self.id else None
        )
        self.driver = None
        self.wait = None
        self._is_closing = False
        MaltScrapper._instances.add(self)
        self._setup_driver(headless)

    def _setup_driver(self, headless):
        # Create workspace directory
        if self.workspace_path and not os.path.exists(self.workspace_path):
            os.makedirs(self.workspace_path)

        # Chrome options
        options = uc.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")  # Use new headless mode
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-infobars")
        options.add_argument(f"--user-data-dir=/home/chrome/.config/chromium")
        options.add_argument(f"--disk-cache-dir=/home/chrome/.cache/chromium")
        options.binary_location = os.getenv(
            "CHROME_EXECUTABLE_PATH", "/usr/bin/chromium"
        )

        # Create driver with options
        try:
            print("Initializing Chrome driver...")
            self.driver = uc.Chrome(
                options=options,
                browser_executable_path=options.binary_location,
                driver_executable_path="/usr/bin/chromedriver",
                version_main=119,
                headless=headless,
                use_subprocess=True,  # Changed to True for better process management
            )
            print("Chrome driver initialized successfully")
            self.wait = WebDriverWait(self.driver, 20)

            self._load_cookies()
        except Exception as e:
            print(f"Error initializing Chrome driver: {str(e)}")
            raise e

    def _load_cookies(self):
        if config.COOKIES:
            try:
                self.driver.get("https://www.malt.fr")

                cookie_pairs = config.COOKIES.strip().split("; ")
                for pair in cookie_pairs:
                    if "=" in pair:
                        name, value = pair.split("=", 1)
                        cookie = {
                            "name": name,
                            "value": value,
                            "domain": ".malt.fr",
                            "path": "/"
                        }
                        try:
                            self.driver.add_cookie(cookie)
                        except Exception as e:
                            print(f"Failed to add cookie {name}: {str(e)}")

                print(f"Loaded {len(cookie_pairs)} cookies")
            except Exception as e:
                print(f"Error loading cookies: {str(e)}")

    def _cleanup(self, from_shutdown=False):
        """Internal cleanup method"""
        if self._is_closing:
            return

        self._is_closing = True
        try:
            if self.driver:
                if not from_shutdown:
                    print("Closing Chrome driver...")
                    try:
                        self.driver.quit()
                    except:
                        # If quit fails, try to close the browser
                        try:
                            self.driver.close()
                        except:
                            pass
                else:
                    # During shutdown, just try to close the browser window
                    try:
                        self.driver.close()
                    except:
                        pass
                self.driver = None
                self.wait = None
        except Exception as e:
            if not from_shutdown:
                print(f"Error closing Chrome driver: {str(e)}")
        finally:
            MaltScrapper._instances.discard(self)
            self._is_closing = False

    def close(self):
        """Public cleanup method"""
        self._cleanup()

    def __del__(self):
        """Cleanup during garbage collection"""
        self._cleanup()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def take_full_page_screenshot(self, url):
        """Take a full page screenshot of the given URL.

        Args:
            url (str): The URL to take a screenshot of

        Returns:
            str: Path to the saved screenshot
        """
        try:
            # Navigate to the URL
            self.driver.get(url)

            # Wait for the page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            # Get the page height by executing JavaScript
            total_height = self.driver.execute_script(
                """
                return Math.max(
                    document.body.scrollHeight,
                    document.documentElement.scrollHeight,
                    document.body.offsetHeight,
                    document.documentElement.offsetHeight,
                    document.body.clientHeight,
                    document.documentElement.clientHeight
                );
            """
            )

            # Set window size to capture full page
            self.driver.set_window_size(1920, total_height)

            # Take screenshot
            screenshot_path = f"{self.workspace_path}/full_page.png"
            self.driver.save_screenshot(screenshot_path)

            return screenshot_path

        except (TimeoutException, WebDriverException) as e:
            print(f"Failed to take screenshot: {str(e)}")
            return None

    def extract_profile_data(self):
        try:
            print(f"Starting extraction for URL: {self.profil_url}")

            # Take full page screenshot before scraping
            screenshot_path = self.take_full_page_screenshot(self.profil_url)
            if screenshot_path:
                print(f"Full page screenshot saved to: {screenshot_path}")

            # Navigate to profile URL if not already there
            if self.driver.current_url != self.profil_url:
                self.driver.get(self.profil_url)

            # Set window size before navigating
            self.driver.set_window_size(1920, 1080)

            # Wait for page load
            # time.sleep(1)  # Initial wait
            # print("Checking if page loaded...")

            return ExtractMaltInfo(self.driver).extract()

        except Exception as e:
            print(f"Error during extraction: {str(e)}")
            # Save page source for debugging
            try:
                with open(self.workspace_path + "/page_source.html", "w") as f:
                    f.write(self.driver.page_source)
                print(
                    "Page source saved to " + self.workspace_path + "/page_source.html"
                )
            except Exception as save_error:
                print(f"Failed to save page source: {str(save_error)}")
            raise e

        finally:
            try:
                print("Quitting driver...")
                self.driver.quit()
            except:
                pass


def signal_handler(signum, frame):
    """Handle termination signals"""
    MaltScrapper._cleanup_all()
    sys.exit(0)


# Register cleanup handlers
atexit.register(MaltScrapper._cleanup_all)

# Register signal handlers if not running in a thread
if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
