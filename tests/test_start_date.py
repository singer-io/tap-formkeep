from base import formkeepBaseTest
from tap_tester.base_suite_tests.start_date_test import StartDateTest



class formkeepStartDateTest(StartDateTest, formkeepBaseTest):
    """Instantiate start date according to the desired data set and run the
    test."""

    @staticmethod
    def name():
        return "tap_tester_formkeep_start_date_test"

    def streams_to_test(self):
        streams_to_exclude = {}
        return self.expected_stream_names().difference(streams_to_exclude)

    @property
    def start_date_1(self):
        return "2025-03-25T00:00:00Z"

    @property
    def start_date_2(self):
        return "2026-05-27T00:00:00Z"
