import unittest
from unittest.mock import MagicMock
from tap_formkeep.schema import get_dynamic_schema
from tap_formkeep.exceptions import formkeepUnprocessableEntityError


class TestGetDynamicSchema(unittest.TestCase):

    def setUp(self):
        # Mock tap client
        self.client = MagicMock()
        self.client.base_url = "https://fake.api/forms/{form_id}"

        # Sample deeply nested structure for recursion testing
        self.sample_submission = {
            "id": 12345,
            "created_at": "2025-11-28T04:49:45.434Z",
            "spam": False,
            "data": {
                "date": "2025-11-21",
                "time": "12:30",
                "name": "Alice",

                # Nested object → recursion required
                "profile": {
                    "age": 30,
                    "address": {
                        "street": "Main St",
                        "city": "NYC",
                        "coords": {
                            "lat": 40.7,
                            "lng": -74.0
                        }
                    }
                },

                # Array of objects → recursion required
                "items": [
                    {"sku": "A1", "qty": 2}
                ],

                # Empty list → should fallback to string items
                "tags": []
            }
        }

        # Mock API response for form id "test_form"
        self.client.make_request.return_value = {
            "submissions": [self.sample_submission]
        }

    # ------------------------------
    # Test dynamic schema structure
    # ------------------------------
    def test_get_dynamic_schema_basic(self):
        schemas, field_metadata = get_dynamic_schema(
            self.client,
            {"form_ids": "test_form"}
        )

        # schema created?
        self.assertIn("test_form", schemas)

        schema = schemas["test_form"]
        props = schema["properties"]

        # Basic field checks
        self.assertEqual(props["id"]["type"], ["null", "integer"])
        self.assertEqual(props["spam"]["type"], ["null", "boolean"])
        self.assertEqual(props["created_at"]["format"], "date-time")

        # Ensure "data" exists
        self.assertIn("data", props)
        self.assertIn("properties", props["data"])

    # ------------------------------
    # Test recursive field inference
    # ------------------------------
    def test_recursive_fields(self):
        schemas, _ = get_dynamic_schema(
            self.client,
            {"form_ids": "test_form"}
        )

        schema = schemas["test_form"]
        data_props = schema["properties"]["data"]["properties"]

        # --------------------------
        # Nested dict: profile
        # --------------------------
        profile = data_props["profile"]
        self.assertEqual(profile["type"], ["null", "object"])
        self.assertIn("properties", profile)

        # Level 2 recursion: profile.address
        address = profile["properties"]["address"]
        self.assertEqual(address["type"], ["null", "object"])
        self.assertIn("properties", address)

        # Level 3 recursion: profile.address.coords.lat
        coords = address["properties"]["coords"]
        self.assertEqual(coords["type"], ["null", "object"])
        self.assertEqual(coords["properties"]["lat"]["type"], ["null", "number"])
        self.assertEqual(coords["properties"]["lng"]["type"], ["null", "number"])

        # --------------------------
        # Array of objects: items
        # --------------------------
        items = data_props["items"]
        self.assertEqual(items["type"], ["null", "array"])
        self.assertEqual(items["items"]["type"], ["null", "object"])
        self.assertEqual(items["items"]["properties"]["sku"]["type"], ["null", "string"])
        self.assertEqual(items["items"]["properties"]["qty"]["type"], ["null", "integer"])

        # --------------------------
        # Empty list: tags
        # --------------------------
        tags = data_props["tags"]
        self.assertEqual(tags["type"], ["null", "array"])
        # Default fallback for empty list
        self.assertEqual(tags["items"]["type"], ["null", "string"])

    # ------------------------------
    # Metadata tests
    # ------------------------------
    def test_metadata_generated(self):
        _, field_metadata = get_dynamic_schema(
            self.client,
            {"form_ids": "test_form"}
        )

        self.assertIn("test_form", field_metadata)
    # -------------------------------------------------------
    # Tests for no-submissions error handling
    # -------------------------------------------------------

    def test_get_dynamic_schema_raises_on_no_submissions(self):
        """Raise formkeepUnprocessableEntityError when a form has no submissions."""
        self.client.make_request.return_value = {"submissions": []}

        with self.assertRaises(formkeepUnprocessableEntityError) as ctx:
            get_dynamic_schema(self.client, {"form_ids": "empty_form"})

        self.assertIn("empty_form", str(ctx.exception))

    def test_get_dynamic_schema_raises_on_missing_submissions_key(self):
        """Raise formkeepUnprocessableEntityError when response has no submissions key."""
        self.client.make_request.return_value = {}

        with self.assertRaises(formkeepUnprocessableEntityError):
            get_dynamic_schema(self.client, {"form_ids": "empty_form"})

    def test_get_dynamic_schema_raises_on_first_failing_form_id(self):
        """Raise on the first form_id that returns no submissions, not after all."""
        responses = [
            {"submissions": []},           # form_1 → should raise immediately
            {"submissions": [{"id": 1, "created_at": "2025-01-01T00:00:00Z",
                              "spam": False, "data": {}}]},  # form_2 → never reached
        ]
        self.client.make_request.side_effect = responses

        with self.assertRaises(formkeepUnprocessableEntityError):
            get_dynamic_schema(self.client, {"form_ids": "form_1, form_2"})

        # Only one request should have been made (stopped at form_1)
        self.assertEqual(self.client.make_request.call_count, 1)

    def test_get_dynamic_schema_multiple_form_ids_success(self):
        """Build schema for every form_id when all return submissions."""
        submission = {
            "id": 1,
            "created_at": "2025-01-01T00:00:00Z",
            "spam": False,
            "data": {"name": "Alice", "age": 30},
        }
        self.client.make_request.return_value = {"submissions": [submission]}

        schemas, field_metadata = get_dynamic_schema(
            self.client, {"form_ids": "form_a, form_b"}
        )

        self.assertIn("form_a", schemas)
        self.assertIn("form_b", schemas)
        self.assertIn("form_a", field_metadata)
        self.assertIn("form_b", field_metadata)
        self.assertEqual(self.client.make_request.call_count, 2)
