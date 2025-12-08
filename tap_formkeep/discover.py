import singer
from singer import metadata
from singer.catalog import Catalog, CatalogEntry, Schema
from tap_formkeep.schema import get_dynamic_schema

LOGGER = singer.get_logger()


def discover(client, config) -> Catalog:
    """
    Dynamically discover all forms from formkeep and build the catalog.
    """
    dynamic_schemas, dynamic_field_metadata = get_dynamic_schema(client, config)
    catalog = Catalog([])

    for stream_name, schema_dict in dynamic_schemas.items():
        try:
            schema = Schema.from_dict(schema_dict)
            mdata = dynamic_field_metadata[stream_name]
        except Exception as err:
            LOGGER.error(err)
            LOGGER.error("stream_name: {}".format(stream_name))
            LOGGER.error("type schema_dict: {}".format(type(schema_dict)))
            raise err

        key_properties = metadata.to_map(mdata).get((), {}).get("table-key-properties")

        catalog.streams.append(
            CatalogEntry(
                stream=stream_name,
                tap_stream_id=stream_name,
                key_properties=key_properties,
                schema=schema,
                metadata=mdata,
            )
        )

    return catalog
