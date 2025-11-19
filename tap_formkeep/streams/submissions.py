from tap_formkeep.streams.abstracts import IncrementalStream

class Submissions(IncrementalStream):
    tap_stream_id = "submissions"
    key_properties = ["id"]
    replication_method = "INCREMENTAL"
    replication_keys = ["created_at"]

