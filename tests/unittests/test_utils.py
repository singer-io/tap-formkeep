import unittest

from tap_formkeep.utils import sanitize_field_name, sanitize_record_keys


class TestUtils(unittest.TestCase):
    """ Unit tests for utility functions. """

    field_names = [
        # (original, expected)
        ("Space Name", "Space_Name"),
        (" Leading Space", "Leading_Space"),
        ("Trailing Space ", "Trailing_Space"),
        ("Multiple   Spaces", "Multiple_Spaces"),
        ("With'Quote", "With_Quote"),
        ("NoSpaces", "NoSpaces"),
        ("With-Dash", "With_Dash"),
        ("With.Dot", "With_Dot"),
        ("With/Slash", "With_Slash"),
        ("With Emoji 😁 Data", "With_Emoji_Data"),
        ("Special!@#$%^&*()Chars", "Special_Chars"),
    ]

    actual_nested_record = {
        "Space Key": "value1",
        "Nested Dict": {
            "Multiple  Space Key": "value2",
            "List of Dicts": [
                {" Leading Space": "value3 with space"},
                {"Trailing Space ": "value4"},
                {"Multiple   Spaces": "value5"},
            ],
            "Key-With-Dash": "value6",
            "Key.With.Dot": "value7",
            "Key/With/Slash": "value8",
            "Again-/ Some Nesting": {
                "Special!@#Chars": "value9"
            }
        }
    }

    sanitized_nested_record = {
        "Space_Key": "value1",
        "Nested_Dict": {
            "Multiple_Space_Key": "value2",
            "List_of_Dicts": [
                {"Leading_Space": "value3 with space"},
                {"Trailing_Space": "value4"},
                {"Multiple_Spaces": "value5"},
            ],
            "Key_With_Dash": "value6",
            "Key_With_Dot": "value7",
            "Key_With_Slash": "value8",
            "Again_Some_Nesting": {
                "Special_Chars": "value9"
            }
        }
    }

    def test_sanitize_field_name(self):
        """ Test sanitization of individual field names. """
        for original, expected in self.field_names:
            with self.subTest(original=original, expected=expected):
                self.assertEqual(sanitize_field_name(original), expected)

    def test_sanitize_record_keys(self):
        """ Test sanitization of nested record keys. """
        input_data = self.actual_nested_record
        expected_output = self.sanitized_nested_record

        self.assertEqual(sanitize_record_keys(input_data), expected_output)
