# Core
import time
import datetime

# Third-party
import feedparser
import logging
import requests_cache
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


# Cache session settings
cached_session = requests_cache.CachedSession(
    name="hour-cache",
    expire_after=datetime.timedelta(hours=1),
    backend="memory",
    old_data_on_error=True,
)
cached_session.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=5, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504]
        )
    ),
)


def get_rss_feed_content(url, offset=0, limit=6, exclude_items_in=None):
    """
    Get the entries from an RSS feed

    Inspired by https://github.com/canonical-webteam/get-feeds/,
    minus Django-specific stuff.
    """

    logger = logging.getLogger(__name__)
    end = limit + offset if limit is not None else None

    try:
        response = cached_request(url)
    except Exception as request_error:
        logger.warning(
            "Attempt to get feed failed: {}".format(str(request_error))
        )
        return False

    try:
        feed_data = feedparser.parse(response.text)
        if not feed_data.feed:
            logger.warning("No valid feed data found at {}".format(url))
            return False
        content = feed_data.entries
    except Exception as parse_error:
        logger.warning(
            "Failed to parse feed from {}: {}".format(url, str(parse_error))
        )
        return False

    if exclude_items_in:
        exclude_ids = [item["guid"] for item in exclude_items_in]
        content = [item for item in content if item["guid"] not in exclude_ids]

    content = content[offset:end]

    for item in content:
        updated_time = time.mktime(item["updated_parsed"])
        item["updated_datetime"] = datetime.datetime.fromtimestamp(
            updated_time
        )

    return content


def cached_request(url):
    """
    Retrieve the response from the requests cache.
    If the cache has expired then it will attempt to update the cache.
    If it gets an error, it will use the cached response, if it exists.
    """

    response = cached_session.get(url, timeout=3)

    response.raise_for_status()

    return response
