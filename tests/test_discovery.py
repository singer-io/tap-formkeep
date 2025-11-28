"""Test tap discovery mode and metadata."""
from base import formkeepBaseTest
from tap_tester.base_suite_tests.discovery_test import DiscoveryTest
from tap_tester import menagerie


class formkeepDiscoveryTest(DiscoveryTest, formkeepBaseTest):
    """Test tap discovery mode and metadata conforms to standards."""

    @staticmethod
    def name():
        return "tap_tester_formkeep_discovery_test"

    def streams_to_test(self):
        return self.expected_stream_names()

    def test_stream_naming(self):
        """Verify stream names follow naming convention (12-char lowercase hex)."""
        pattern = r"^[a-f0-9]{12}$"
        for stream in self.streams_to_test():
            with self.subTest(stream=stream):
                self.assertRegex(stream, pattern,
                                f"{stream} must be a 12-character lowercase hex ID")