from base import formkeepBaseTest
from tap_tester.base_suite_tests.bookmark_test import BookmarkTest


class formkeepBookMarkTest(BookmarkTest, formkeepBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a
    stream."""
    bookmark_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    initial_bookmarks = {
        "bookmarks": {
            "5e5ee5b14b02": { "created_at" : "2025-11-17T00:00:00Z"},
            "a934600be226": { "created_at" : "2025-11-17T00:00:00Z"},
        }
    }
    @staticmethod
    def name():
        return "tap_tester_formkeep_bookmark_test"

    def streams_to_test(self):
        streams_to_exclude = {}
        return self.expected_stream_names().difference(streams_to_exclude)

    def calculate_new_bookmarks(self):
        """Calculates new bookmarks by looking through sync 1 data to determine
        a bookmark that will sync 2 records in sync 2 (plus any necessary look
        back data)"""
        new_bookmarks = {
            "5e5ee5b14b02": { "created_at" : "2026-05-26T06:30:00Z"},
            "a934600be226": { "created_at" : "2026-05-26T06:30:00Z"},
        }

        return new_bookmarks
