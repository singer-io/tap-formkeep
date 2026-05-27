
from base import formkeepBaseTest
from tap_tester.base_suite_tests.interrupted_sync_test import InterruptedSyncTest


class formkeepInterruptedSyncTest(InterruptedSyncTest, formkeepBaseTest):
    """Test tap sets a bookmark and respects it for the next sync of a
    stream."""

    @staticmethod
    def name():
        return "tap_tester_formkeep_interrupted_sync_test"

    def streams_to_test(self):
        return self.expected_stream_names()

    def manipulate_state(self):
        return {
            "currently_syncing": "5e5ee5b14b02",
            "bookmarks": {
                "5e5ee5b14b02": {"created_at": "2026-05-27T00:00:00Z"},
                "a934600be226": {"created_at": "2026-05-27T00:00:00Z"},
            }
        }
