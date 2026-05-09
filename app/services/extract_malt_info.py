from typing import Dict, Any
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


class ExtractMaltInfo:
    def __init__(self, driver):
        self.driver = driver

    def wait_for_element(self, by, value, timeout=20):
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
        except TimeoutException:
            print(f"Timeout waiting for element: {value}")
            raise

    def extract(self) -> Dict[str, Any]:
        try:
            self.wait_for_element(By.TAG_NAME, "body")
            print("Body element found")
        except TimeoutException:
            print("Failed to find body element")
            raise

        print(f"Current URL: {self.driver.current_url}")

        print("Waiting for profile header...")
        self.wait_for_element(By.CSS_SELECTOR, "[data-testid='profile-fullname']")
        print("Profile header found")

        print("Extracting basic info...")
        fullname = self.wait_for_element(
            By.CSS_SELECTOR, "[data-testid='profile-fullname']"
        ).text
        title = self.wait_for_element(
            By.CSS_SELECTOR, "[data-testid='profile-headline']"
        ).text

        daily_rate = None
        try:
            daily_rate = self.wait_for_element(
                By.CSS_SELECTOR, "[data-testid='profile-price']"
            ).text.strip()
        except TimeoutException:
            print("Daily rate not found")

        response_rate = None
        try:
            response_rate = self.wait_for_element(
                By.CLASS_NAME, "answer-time-indicator", timeout=5
            ).text.strip()
        except TimeoutException:
            print("Response rate not found")

        experience_years = None
        try:
            experience_years = self.wait_for_element(
                By.CSS_SELECTOR,
                "[data-testid='profile-header-experience-level'] .experience-level-indicator__text",
                timeout=5,
            ).text.strip()
        except TimeoutException:
            print("Experience years not found")

        image_url = None
        try:
            image_url = self.wait_for_element(
                By.CSS_SELECTOR, ".profile-header-section__avatar-container img", timeout=5
            ).get_attribute("src")
        except TimeoutException:
            print("Image URL not found")

        top_skills = []
        skills = []
        try:
            top_skills_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                '[data-testid="profile-header-section-top-skills-list"] .profile-edition__skills_item__tag__link__content',
            )
            top_skills = [s.text for s in top_skills_elements if s.text.strip()]
            skills_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                '[data-testid="profile-main-skill-set-selected-skills-list"] .profile-edition__skills_item__tag__link__content',
            )
            skills = [s.text for s in skills_elements if s.text.strip()]
        except Exception:
            print("Skills not found")

        location = None
        try:
            location = self.wait_for_element(
                By.CSS_SELECTOR, "[data-testid='profile-location-preference-address']",
                timeout=5,
            ).text.strip()
        except Exception:
            print("Location not found")

        work_locations = []
        try:
            content = self.wait_for_element(
                By.CSS_SELECTOR,
                "[data-testid='profile-workplace-preferences-on-site-container'] .profile-workplace-preferences-item__content",
                timeout=5,
            ).text.strip()
            work_locations = [loc.strip() for loc in content.split(",") if loc.strip()]
        except Exception:
            print("Work locations not found")

        expertise_domains = []
        try:
            expertise_domains_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".profile-skills-read-only .profile-edition__skills_item__tag__link__content",
            )
            expertise_domains = [d.text for d in expertise_domains_elements]
        except Exception:
            print("Expertise domains not found")

        certifications = []
        try:
            certifications_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                ".profile-certifications__list-item__main-content-title",
            )
            certifications = [
                {"name": c.text, "date": None, "description": None}
                for c in certifications_elements
            ]
        except Exception:
            print("Certifications not found")

        availability: str = None
        try:
            availability = self.wait_for_element(
                By.CLASS_NAME, "joy-availability", timeout=5
            ).get_attribute("title")
        except TimeoutException:
            print("Availability not found")

        languages = []
        try:
            languages_elements = self.driver.find_elements(
                By.CSS_SELECTOR, ".profile-languages__item__title"
            )
            languages = [{"name": lang.text, "level": None} for lang in languages_elements]
        except Exception:
            print("Languages not found")

        categories = []
        try:
            categories_elements = self.driver.find_elements(
                By.CSS_SELECTOR, ".categories__list-item .joy-link__text"
            )
            categories = [c.text for c in categories_elements]
        except Exception:
            print("Categories not found")

        missions_count = None
        try:
            missions_count = len(
                self.driver.find_elements(By.CLASS_NAME, "profile-experiences__list-item")
            )
        except Exception:
            print("Missions count not found")

        description = None
        try:
            description = self.wait_for_element(
                By.CSS_SELECTOR, '[data-testid="profile-description"]', timeout=5
            ).text.strip()
        except TimeoutException:
            print("Description not found")

        print(f"Extraction completed for: {fullname}")

        return {
            "fullname": fullname,
            "title": title,
            "categories": categories,
            "daily_rate": daily_rate,
            "response_rate": response_rate,
            "experience_years": experience_years,
            "image_url": image_url,
            "top_skills": top_skills,
            "skills": skills,
            "location": location,
            "work_locations": work_locations,
            "languages": languages,
            "availability": availability,
            "expertise_domains": expertise_domains,
            "missions_count": missions_count,
            "description": description,
            "certifications": certifications,
        }
