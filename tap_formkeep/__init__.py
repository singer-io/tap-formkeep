import sys
import json
import singer
from tap_formkeep.client import Client
from tap_formkeep.discover import discover
from tap_formkeep.sync import sync

LOGGER = singer.get_logger()

REQUIRED_CONFIG_KEYS = ['api_token', 'form_ids', 'start_date']

def do_discover(client, config):
    """
    Discover and emit the catalog to stdout
    """
    LOGGER.info("Starting discover")
    catalog = discover(client, config)
    json.dump(catalog.to_dict(), sys.stdout, indent=2)
    LOGGER.info("Finished discover")


@singer.utils.handle_top_exception(LOGGER)
def main():
    """
    Run the tap
    """
    parsed_args = singer.utils.parse_args(REQUIRED_CONFIG_KEYS)
    state = {}
    if parsed_args.state:
        state = parsed_args.state

    with Client(parsed_args.config) as client:
        if parsed_args.discover:
            do_discover(client, parsed_args.config)
        elif parsed_args.catalog:
            sync(
                client=client,
                config=parsed_args.config,
                catalog=parsed_args.catalog,
                state=state)


if __name__ == "__main__":
    main()

