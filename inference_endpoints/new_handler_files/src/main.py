# filename='record.log',
import logging

from handler import EndpointHandler

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')

logger = logging.getLogger(__name__)

endpoint_handler = EndpointHandler("something")


def handler(event, context):
    result = endpoint_handler(event)
    logger.info(f"Received POST request with data: {event}")
    return result
