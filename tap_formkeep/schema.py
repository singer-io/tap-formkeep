import ast
import json
import os
import re
from typing import Dict, Tuple

import singer
from singer import metadata

from tap_formkeep.exceptions import formkeepBadRequestError, formkeepUnprocessableEntityError
from tap_formkeep.streams import STREAMS
from tap_formkeep.utils import sanitize_field_name

LOGGER = singer.get_logger()

DATE_REGEX = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_REGEX = re.compile(r"^\d{2}:\d{2}(:\d{2})?$")
DATETIME_REGEX = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(Z|[\+\-]\d{2}:\d{2}| UTC)?$"
)


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


def infer_type(value):
    if value is None:
        return {"type": ["null", "string"]}

    if isinstance(value, bool):
        return {"type": ["null", "boolean"]}

    if isinstance(value, int):
        return {"type": ["null", "integer"]}

    if isinstance(value, float):
        return {"type": ["null", "number"]}

    if isinstance(value, str):
        if DATETIME_REGEX.match(value) or DATE_REGEX.match(value):
            return {"type": ["null", "string"], "format": "date-time"}

        if TIME_REGEX.match(value):
            return {"type": ["null", "string"]}

        return {"type": ["null", "string"]}

    # --- Recursive dict ---
    if isinstance(value, dict):
        props = {
            k: infer_type(v)
            for k, v in value.items()
        }
        return {
            "type": ["null", "object"],
            "properties": props
        }

    # --- Recursive list ---
    if isinstance(value, list):
        if value:
            # infer type from first element
            item_type = infer_type(value[0])
        else:
            # empty list → unknown items
            item_type = {"type": ["null", "string"]}

        return {
            "type": ["null", "array"],
            "items": item_type
        }

    return {"type": ["null", "string"]}


def get_dynamic_schema(client, config):
    schemas = {}
    field_metadata = {}
    forms_without_submissions = []
    invalid_forms = []

    raw_ids = config.get("form_ids", "")
    raw_ids = [id.strip() for id in raw_ids.split(",")]

    if isinstance(raw_ids, str):
        form_ids = ast.literal_eval(raw_ids)
    else:
        form_ids = raw_ids

    for form_id in form_ids:
        try:
            response = client.make_request(
                method="GET",
                endpoint=client.base_url.format(form_id=form_id),
                params={"page": 1, "include_attachments": "true"},
            )
        except Exception as err:
            LOGGER.error(f"Error fetching submissions for form_id: {form_id}. Error: {str(err)}")
            invalid_forms.append(form_id)
            continue

        submissions = response.get("submissions", [])
        if not submissions:
            LOGGER.warning(f"No submissions found for form_id: {form_id}. Skipping schema inference for this form.")
            forms_without_submissions.append(form_id)
            continue

        first_submission = submissions[0]
        data_obj = first_submission.get("data", {})

        # Sanitize field names
        data_properties = {
            sanitize_field_name(k): infer_type(v)
            for k, v in data_obj.items()
        }

        schema = {
            "type": "object",
            "properties": {
                "id": {"type": ["null", "integer"]},
                "created_at": {"type": ["null", "string"], "format": "date-time"},
                "spam": {"type": ["null", "boolean"]},
                "data": {
                    "type": "object",
                    "properties": data_properties,
                },
            },
        }

        schemas[form_id] = schema

        # metadata
        mdata = metadata.new()
        mdata = metadata.get_standard_metadata(
            schema=schema,
            key_properties=["id"],
            valid_replication_keys=["created_at"],
            replication_method="INCREMENTAL",
        )
        mdata = metadata.to_map(mdata)
        mdata = metadata.write(
            mdata, ('properties', "created_at"), 'inclusion', 'automatic'
        )
        field_metadata[form_id] = metadata.to_list(mdata)

    if invalid_forms:
        error_message = f"Invalid forms detected: {', '.join(invalid_forms)}. Please check the configuration."
        LOGGER.error(error_message)
        raise formkeepBadRequestError(error_message)

    if len(forms_without_submissions) == len(form_ids):
        error_message = "No submissions found for any of the forms. Please check the configuration."
        LOGGER.error(error_message)
        raise formkeepUnprocessableEntityError(error_message)

    return schemas, field_metadata
