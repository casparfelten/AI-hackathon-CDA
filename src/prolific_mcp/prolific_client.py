"""Prolific API client wrapper."""

import json
from typing import Any, Optional

import requests

from .config import config


class ProlificAPIError(Exception):
    """Exception raised for Prolific API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class ProlificClient:
    """Client for interacting with Prolific API."""

    def __init__(self):
        """Initialize the Prolific client with configuration."""
        config.validate()
        self.base_url = config.base_url
        self.headers = {
            "Content-Type": "application/json",
            **config.get_auth_header(),
        }

    def _request(
        self, method: str, endpoint: str, data: Optional[dict] = None, params: Optional[dict] = None
    ) -> dict[str, Any]:
        """Make an HTTP request to the Prolific API."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_data = None
            try:
                error_data = e.response.json()
            except (ValueError, AttributeError):
                pass
            
            raise ProlificAPIError(
                f"Prolific API error: {str(e)}",
                status_code=e.response.status_code if hasattr(e, 'response') else None,
                response=error_data,
            )
        except requests.exceptions.RequestException as e:
            raise ProlificAPIError(f"Request failed: {str(e)}")

    def create_study(self, study_config: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new study on Prolific.
        
        Args:
            study_config: Study configuration dictionary with required fields:
                - name: Study name (public title)
                - description: Study description
                - external_study_url: URL to the study
                - prolific_id_option: How to collect Prolific ID ("question", "url_parameters", "not_required")
                - completion_codes: Array of completion code objects
                - estimated_completion_time: Time in minutes
                - reward: Reward amount in cents
                - total_available_places: Number of participants
                - Optional: internal_name, device_compatibility, filters, etc.
        
        Returns:
            Created study data
        """
        return self._request("POST", "studies/", data=study_config)

    def get_study(self, study_id: str) -> dict[str, Any]:
        """
        Get study details by ID.
        
        Args:
            study_id: Prolific study ID
        
        Returns:
            Study data
        """
        return self._request("GET", f"studies/{study_id}/")

    def update_study(self, study_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """
        Update a study.
        
        Args:
            study_id: Prolific study ID
            updates: Dictionary of fields to update
        
        Returns:
            Updated study data
        """
        return self._request("PATCH", f"studies/{study_id}/", data=updates)

    def launch_study(self, study_id: str) -> dict[str, Any]:
        """
        Launch a study (start recruitment).
        
        Args:
            study_id: Prolific study ID
        
        Returns:
            Launch response data
        """
        return self._request("POST", f"studies/{study_id}/transition/", data={"action": "PUBLISH"})

    def get_submissions(self, study_id: str) -> list[dict[str, Any]]:
        """
        Get all submissions/results for a study.
        
        Args:
            study_id: Prolific study ID
        
        Returns:
            List of submission data
        """
        response = self._request("GET", f"studies/{study_id}/submissions/")
        # API returns SubmissionListResponse with results array
        return response.get("results", [])

    def get_study_status(self, study_id: str) -> dict[str, Any]:
        """
        Get study status information.
        
        Args:
            study_id: Prolific study ID
        
        Returns:
            Study status data
        """
        study = self.get_study(study_id)
        return {
            "id": study.get("id"),
            "status": study.get("status"),
            "total_available_places": study.get("total_available_places"),
            "places_taken": study.get("places_taken"),
            "completion_rate": study.get("completion_rate"),
        }

    def list_studies(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        """
        List all studies.
        
        Args:
            limit: Optional limit on number of studies to return
        
        Returns:
            List of study data
        """
        params = {}
        if limit:
            params["limit"] = limit
        response = self._request("GET", "studies/", params=params)
        # API returns StudiesListResponse with results array
        return response.get("results", [])

    def create_test_participant(self, email: str) -> dict[str, Any]:
        """
        Create a test participant account for testing studies without consuming credits.
        
        Args:
            email: Email address for the test participant (cannot be an email already registered with Prolific)
        
        Returns:
            Response containing participant_id
        
        Note:
            - Test participants can only take studies in workspaces where the feature is enabled
            - Test participants cannot cash out any balance earned
            - A randomly generated password is assigned; you may want to request a password reset
        """
        return self._request("POST", "researchers/participants/", data={"email": email})

    def launch_test_study(self, study_id: str) -> dict[str, Any]:
        """
        Launch a study in test mode (doesn't consume credits).
        
        Args:
            study_id: Prolific study ID (must be in draft status)
        
        Returns:
            TestStudySetUpResponse containing study_id and study_url
        
        Note:
            - Requires at least one test participant to exist (created via create_test_participant)
            - Study must be in draft status
            - Feature must be enabled for your workspace (contact support if unavailable)
        """
        return self._request("POST", f"studies/{study_id}/test-study")

    def delete_study(self, study_id: str) -> None:
        """
        Delete a study. Only draft studies can be deleted.
        
        Args:
            study_id: Prolific study ID
        
        Raises:
            ProlificAPIError: If deletion fails or study is published
        """
        # DELETE endpoint returns 200 with empty body on success
        self._request("DELETE", f"studies/{study_id}/")

