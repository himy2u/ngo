"""Integration tests for data ingestion."""

from unittest.mock import MagicMock, patch

import pytest

from data.ingestion.fetch_petitions import PetitionIngester


class TestPetitionIngester:
    """Integration tests for petition ingestion."""

    @pytest.fixture
    def mock_api_response(self):
        """Sample API response."""
        return {
            "data": [
                {
                    "id": 1,
                    "attributes": {
                        "action": "Test petition 1",
                        "background": "Background text",
                        "state": "open",
                        "signature_count": 1000,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-02T00:00:00Z",
                    },
                },
                {
                    "id": 2,
                    "attributes": {
                        "action": "Test petition 2",
                        "state": "closed",
                        "signature_count": 500,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-02T00:00:00Z",
                    },
                },
            ]
        }

    @patch("data.ingestion.fetch_petitions.httpx.Client")
    def test_fetch_and_validate(self, mock_client, mock_api_response, tmp_path):
        """Test fetching and validating petitions."""
        # Setup mock
        mock_response = MagicMock()
        mock_response.json.return_value = mock_api_response
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        # Run ingestion
        ingester = PetitionIngester(output_dir=str(tmp_path))
        result = ingester.run(pages=1, run_id="test")

        # Verify results
        assert result["valid_count"] == 2
        assert result["quarantine_count"] == 0

    @patch("data.ingestion.fetch_petitions.httpx.Client")
    def test_invalid_record_quarantined(self, mock_client, tmp_path):
        """Test that invalid records are quarantined."""
        # Response with invalid record (missing required field)
        bad_response = {
            "data": [
                {
                    "id": 1,
                    "attributes": {
                        # missing "action" field
                        "state": "open",
                        "signature_count": 1000,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-02T00:00:00Z",
                    },
                }
            ]
        }

        mock_response = MagicMock()
        mock_response.json.return_value = bad_response
        mock_client.return_value.__enter__.return_value.get.return_value = mock_response

        ingester = PetitionIngester(output_dir=str(tmp_path))
        result = ingester.run(pages=1, run_id="test")

        assert result["valid_count"] == 0
        assert result["quarantine_count"] == 1
