from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.malt_profile import MaltProfile, ProfileStatus
from app.services.malt_scrapper import MaltScrapper


class ProfileService:
    def __init__(self, db: Session):
        self.db = db

    def get_profile_by_id(self, profile_id: str) -> Optional[MaltProfile]:
        """Get a profile by its ID."""
        return (
            self.db.query(MaltProfile)
            .filter(MaltProfile.profile_id == profile_id)
            .first()
        )

    def create_profile(self, profile_id: str, profile_url: str) -> MaltProfile:

        profile = MaltProfile(
            profile_id=profile_id,
            profile_url=profile_url,
            status=ProfileStatus.TODO,
        )

        self.db.add(profile)
        self.db.commit()

        return profile

    def update_profile_status(
        self, profile: MaltProfile, status: ProfileStatus
    ) -> None:
        """Update the status of a profile."""
        profile.status = status
        self.db.commit()

    def update_profile_data(self, profile: MaltProfile, data: Dict[str, Any]) -> None:
        print("Update profile with scraped data.")

        for key, value in data.items():
            if hasattr(profile, key):
                setattr(profile, key, value)
            else:
                print(f"Warning: unknown key {key} in scraped data.")
        self.db.commit()

    def format_profile_response(self, profile: MaltProfile) -> Dict[str, Any]:
        """Format profile data for API response."""
        return {
            "profile_id": profile.profile_id,
            "fullname": profile.fullname,
            "title": profile.title,
            "experience_years": profile.experience_years,
            "categories": profile.categories,
            "daily_rate": profile.daily_rate,
            "image_url": profile.image_url,
            "profile_url": profile.profile_url,
            "location": profile.location,
            "work_locations": profile.work_locations,
            "top_skills": profile.top_skills,
            "skills": profile.skills,
            "response_rate": profile.response_rate,
            "languages": profile.languages,
            "availability": profile.availability,
            "missions_count": profile.missions_count,
            "description": profile.description,
            "education": profile.education,
            "experience": profile.experience,
            "certifications": profile.certifications,
            "status": profile.status,
        }

    def process_profile(self, url: str, force_scrapping: bool = False) -> Dict[str, Any]:
        url = url.split("?")[0]

        print(f"Processing profile: {url}")

        """Process a profile URL: check if exists, create if not, and scrape data."""
        if not url.startswith(
            ("https://malt.fr/profile/", "https://www.malt.fr/profile/")
        ):
            raise ValueError("Invalid URL")

        profile_id = url.split("/")[-1]

        # Check if profile already exists
        profile = self.get_profile_by_id(profile_id)
        print("Existing profile: ", profile)

        if profile:
            if not force_scrapping and profile.status == ProfileStatus.SCRAPPED:
                return {
                    "message": "Profile found in database",
                    "data": self.format_profile_response(profile),
                }
        else:
            # Create new profile
            profile = self.create_profile(profile_id, url)

        try:
            print("Update status to IN_PROGRESS")
            self.update_profile_status(profile, ProfileStatus.IN_PROGRESS)

            print("Scrape profile data")
            scraper = MaltScrapper(headless=False, profil_url=url)
            result = scraper.extract_profile_data()

            # Update profile with scraped data
            self.update_profile_data(profile, result)
            self.update_profile_status(profile, ProfileStatus.SCRAPPED)

            return {
                "message": "Profile scraped and stored successfully",
                "data": self.format_profile_response(profile),
            }

        except Exception as e:
            # Update status to ERROR if scraping fails
            self.update_profile_status(profile, ProfileStatus.ERROR)
            raise e
