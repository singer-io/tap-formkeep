import unittest
import requests
from unittest.mock import patch
from parameterized import parameterized
from requests.exceptions import Timeout, ConnectionError, ChunkedEncodingError
from tap_formkeep.client import Client
from tap_formkeep.exceptions import *


default_config = {
    "base_url": "https://api.example.com",
    "request_timeout": 30,
    "api_token": "dummy_token",
}

DEFAULT_REQUEST_TIMEOUT = 300


class MockRequest:
    """Mocked request object attached to a response."""
    def __init__(self, url="https://formkeep.com/api/v1/forms/test_form_id/submissions.json"):
        self.url = url


class MockResponse:
    """Mocked standard HTTPResponse to test error handling."""

    def __init__(
        self, status_code, resp="", content=[""], headers=None, raise_error=True, text={},
        url="https://formkeep.com/api/v1/forms/test_form_id/submissions.json"
    ):
        self.json_data = resp
        self.status_code = status_code
        self.content = content
        self.headers = headers
        self.raise_error = raise_error
        self.text = text
        self.reason = "error"
        self.url = url
        self.request = MockRequest(url)

    def raise_for_status(self):
        """If an error occur, this method returns a HTTPError object.

        Raises:
            requests.HTTPError: Mock http error.

        Returns:
            int: Returns status code if not error occurred.
        """
        if not self.raise_error:
            return self.status_code

        raise requests.HTTPError("mock sample message")

    def json(self):
        """Returns a JSON object of the result."""
        return self.text


class TestClient(unittest.TestCase):

    def setUp(self):
        """Set up the client with default configuration."""
        self.client = Client(default_config)

    @parameterized.expand([    
        ["empty value", "", DEFAULT_REQUEST_TIMEOUT],
        ["string value", "12", 12.0],
        ["integer value", 10, 10.0],
        ["float value", 20.0, 20.0],
        ["zero value", 0, DEFAULT_REQUEST_TIMEOUT]
    ])
    @patch("tap_formkeep.client.session")
    def test_client_initialization(self, test_name, input_value, expected_value, mock_session):
        default_config["request_timeout"] = input_value
        client = Client(default_config)
        assert client.request_timeout == expected_value
        assert isinstance(client._session, mock_session().__class__)

    @parameterized.expand([
        ["400 error", 400, MockResponse(400), formkeepBadRequestError, "A validation exception has occurred."],
        ["401 error", 401, MockResponse(401), formkeepUnauthorizedError, "The access token provided is expired, revoked, malformed or invalid for other reasons."],
        ["403 error", 403, MockResponse(403), formkeepForbiddenError, "Invalid form_id or insufficient permissions to access the requested resource"],
        ["404 error", 404, MockResponse(404), formkeepNotFoundError, "The resource you have specified cannot be found."],
        ["409 error", 409, MockResponse(409), formkeepConflictError, "The API request cannot be completed because the requested operation would conflict with an existing item."],
    ])
    def test_make_request_http_failure_without_retry(self, test_name, error_code, mock_response, error, error_message):

        with patch.object(self.client._session, "request", return_value=mock_response):
            with self.assertRaises(error) as e:
                self.client._Client__make_request("GET", "https://api.example.com/resource")

        expected_error_message = (
            f"HTTP-error-code: {error_code}, Error: {error_message}"
        )
        self.assertEqual(str(e.exception), expected_error_message)

    @parameterized.expand([
        ["422 error", 422, MockResponse(422), formkeepUnprocessableEntityError, "The request content itself is not processable by the server."],
        ["429 error", 429, MockResponse(429), formkeepRateLimitError, "The API rate limit for your organisation/application pairing has been exceeded."],
        ["500 error", 500, MockResponse(500), formkeepInternalServerError, "The server encountered an unexpected condition which prevented it from fulfilling the request."],
        ["501 error", 501, MockResponse(501), formkeepNotImplementedError, "The server does not support the functionality required to fulfill the request."],
        ["502 error", 502, MockResponse(502), formkeepBadGatewayError, "Server received an invalid response."],
        ["503 error", 503, MockResponse(503), formkeepServiceUnavailableError, "API service is currently unavailable."],
    ])
    @patch("time.sleep")
    def test_make_request_http_failure_with_retry(self, test_name, error_code, mock_response, error, error_message, mock_sleep):

        with patch.object(self.client._session, "request", return_value=mock_response) as mock_request:
            with self.assertRaises(error) as e:
                self.client._Client__make_request("GET", "https://api.example.com/resource")

            expected_error_message = (
                f"HTTP-error-code: {error_code}, Error: {error_message}"
            )
            self.assertEqual(str(e.exception), expected_error_message)
            self.assertEqual(mock_request.call_count, 5)

    # -------------------------------------------------------
    # Tests for check_api_credentials
    # -------------------------------------------------------

    @parameterized.expand([
        ["missing form_ids key", {}],
        ["empty string form_ids", {"form_ids": ""}]
    ])
    def test_check_api_credentials_raises_bad_request_when_form_ids_missing(
        self, test_name, extra_config
    ):
        config = {**default_config, **extra_config}
        client = Client(config)
        with self.assertRaises(formkeepBadRequestError) as ctx:
            client.check_api_credentials()
        self.assertIn("form_ids is required", str(ctx.exception))

    @patch("tap_formkeep.client.Client.make_request")
    def test_check_api_credentials_success(self, mock_make_request):
        mock_make_request.return_value = {"submissions": []}
        config = {**default_config, "form_ids": "form_1, form_2"}
        client = Client(config)
        # Should not raise
        client.check_api_credentials()
        mock_make_request.assert_called_once_with(
            method="GET",
            endpoint="https://formkeep.com/api/v1/forms/form_1/submissions.json",
            params={"page": 1, "include_attachments": "true"},
        )

    @patch("tap_formkeep.client.Client.make_request")
    def test_check_api_credentials_uses_first_form_id_only(self, mock_make_request):
        mock_make_request.return_value = {"submissions": []}
        config = {**default_config, "form_ids": "abc, def, ghi"}
        client = Client(config)
        client.check_api_credentials()
        # Only the first form_id should be used for the credential check
        call_endpoint = mock_make_request.call_args[1]["endpoint"]
        self.assertIn("abc", call_endpoint)
        self.assertNotIn("def", call_endpoint)
        self.assertNotIn("ghi", call_endpoint)

    @parameterized.expand([
        ["ConnectionResetError", ConnectionResetError],
        ["ConnectionError", ConnectionError],
        ["ChunkedEncodingError", ChunkedEncodingError],
        ["Timeout", Timeout],
    ])
    @patch("time.sleep")
    def test_make_request_other_failure_with_retry(self, test_name, error, mock_sleep):

        with patch.object(self.client._session, "request", side_effect=error) as mock_request:
            with self.assertRaises(error) as e:
                self.client._Client__make_request("GET", "https://api.example.com/resource")

            self.assertEqual(mock_request.call_count, 5)
