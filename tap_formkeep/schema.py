import os
import json
import singer
from typing import Dict, Tuple
from singer import metadata
from tap_formkeep.streams import STREAMS
import re
import ast

LOGGER = singer.get_logger()


def get_abs_path(path: str) -> str:
    """
    Get the absolute path for the schema files.
    """
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), path)


def load_schema_references() -> Dict:
    """
    Load the schema files from the schema folder and return the schema references.
    """
    shared_schema_path = get_abs_path("schemas/shared")

    shared_file_names = []
    if os.path.exists(shared_schema_path):
        shared_file_names = [
            f
            for f in os.listdir(shared_schema_path)
            if os.path.isfile(os.path.join(shared_schema_path, f))
        ]

    refs = {}
    for shared_schema_file in shared_file_names:
        with open(os.path.join(shared_schema_path, shared_schema_file)) as data_file:
            refs["shared/" + shared_schema_file] = json.load(data_file)

    return refs


def get_schemas() -> Tuple[Dict, Dict]:
    """
    Load the schema references, prepare metadata for each streams and return schema and metadata for the catalog.
    """
    schemas = {}
    field_metadata = {}

    refs = load_schema_references()
    for stream_name, stream_obj in STREAMS.items():
        schema_path = get_abs_path("schemas/{}.json".format(stream_name))
        with open(schema_path) as file:
            schema = json.load(file)

        schemas[stream_name] = schema
        schema = singer.resolve_schema_references(schema, refs)

        mdata = metadata.new()
        mdata = metadata.get_standard_metadata(
            schema=schema,
            key_properties=getattr(stream_obj, "key_properties"),
            valid_replication_keys=(getattr(stream_obj, "replication_keys") or []),
            replication_method=getattr(stream_obj, "replication_method"),
        )
        mdata = metadata.to_map(mdata)

        automatic_keys = getattr(stream_obj, "replication_keys") or []
        for field_name in schema.get("properties", {}).keys():
            if field_name in automatic_keys:
                mdata = metadata.write(
                    mdata, ("properties", field_name), "inclusion", "automatic"
                )

        parent_tap_stream_id = getattr(stream_obj, "parent", None)
        if parent_tap_stream_id:
            mdata = metadata.write(mdata, (), 'parent-tap-stream-id', parent_tap_stream_id)

        mdata = metadata.to_list(mdata)
        field_metadata[stream_name] = mdata

    return schemas, field_metadata

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_REGEX = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")
DATETIME_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(Z|[\+\-]\d{2}:\d{2}| UTC)?$"
)

def infer_type(value):
    if value is None:
        return ["null", "string"]

    if isinstance(value, bool):
        return ["null", "boolean"]

    if isinstance(value, int):
        return ["null", "integer"]

    if isinstance(value, float):
        return ["null", "number"]

    if isinstance(value, list):
        return ["null", "array"]

    if isinstance(value, dict):
        return ["null", "object"]

    if isinstance(value, str):
        # Only datetime gets format
        if DATETIME_REGEX.match(value):
            return {"type": ["null", "string"], "format": "date-time"}

        # Date-only (YYYY-MM-DD) → treat as plain string
        if DATE_REGEX.match(value):
            return ["null", "string"]

        # Time-only → plain string
        if TIME_REGEX.match(value):
            return ["null", "string"]

        return ["null", "string"]

    return ["null", "string"]

def get_dynamic_schema(client, config) -> Tuple[Dict, Dict]:
    schemas = {}
    field_metadata = {}

    raw_ids = config.get("form_ids", [])

    if isinstance(raw_ids, str):
        form_ids = ast.literal_eval(raw_ids)
    else:
        form_ids = raw_ids

    for form_id in form_ids:
        response = client.make_request(
            method="GET",
            endpoint=client.base_url.format(form_id=form_id),
            params={
                "page": 1,
                "include_attachments": "true"
            }
        )

        submissions = response.get("submissions", [])
        if not submissions:
            LOGGER.warning(f"No submissions found for form {form_id}. Skipping.")
            continue

        first_submission = submissions[0]
        data_obj = first_submission.get("data", {})

        data_properties = {}
        for key, value in data_obj.items():
            inferred = infer_type(value)
            if isinstance(inferred, dict):
                data_properties[key] = inferred
            else:
                data_properties[key] = {"type": inferred}

        schema = {
            "type": "object",
            "properties": {
                "id": {"type": ["null", "integer"]},
                "created_at": {"type": ["null", "string"], "format": "date-time"},
                "spam": {"type": ["null", "boolean"]},
                "data": {
                    "type": "object",
                    "properties": data_properties
                }
            }
        }
        table_name = form_id
        schemas[table_name] = schema
        mdata = metadata.new()
        mdata = metadata.get_standard_metadata(
            schema=schema,
            key_properties=["id"],
            valid_replication_keys=["created_at"],
            replication_method="INCREMENTAL"
        )

        mdata = metadata.to_map(mdata)
        mdata = metadata.write(
            mdata, ('properties', "created_at"), 'inclusion', 'automatic'
        )

        field_metadata[table_name] = metadata.to_list(mdata)

    return schemas, field_metadata
