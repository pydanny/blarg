"""Opt-in RSS 2.0 for successfully built posts."""

from datetime import datetime, timezone
from email.utils import format_datetime
from string import hexdigits
from urllib.parse import quote, unquote, urlsplit, urlunsplit
from xml.etree import ElementTree as ET


def _xml_text(value):
    return "".join(
        c
        for c in value
        if c in "\t\n\r"
        or 0x20 <= ord(c) <= 0xD7FF
        or 0xE000 <= ord(c) <= 0xFFFD
        or 0x10000 <= ord(c) <= 0x10FFFF
    )


def validate_options(site_url, feed_title):
    """Validate before the builder removes or writes any output."""
    if (
        not isinstance(feed_title, str)
        or not feed_title.strip()
        or _xml_text(feed_title) != feed_title
    ):
        raise ValueError("feed_title must be nonblank XML text")
    if site_url is None:
        return None
    error = "site_url must be an absolute HTTP(S) URL without credentials, query or fragment"
    if (
        not isinstance(site_url, str)
        or any(c.isspace() or ord(c) < 32 for c in site_url)
        or "\\" in site_url
    ):
        raise ValueError(error)
    try:
        parts = urlsplit(site_url)
        port = parts.port
        host = parts.hostname
    except ValueError:
        raise ValueError(error) from None
    if (
        parts.scheme not in {"http", "https"}
        or not host
        or parts.username is not None
        or parts.password is not None
        or "?" in site_url
        or "#" in site_url
    ):
        raise ValueError(error)
    if any(segment in {".", ".."} for segment in unquote(parts.path).split("/")):
        raise ValueError(error)
    # Preserve valid escapes: decoding %2F would change the deployed path.
    for index, char in enumerate(parts.path):
        if char == "%" and (
            len(parts.path[index + 1 : index + 3]) != 2
            or any(c not in hexdigits for c in parts.path[index + 1 : index + 3])
        ):
            raise ValueError(error)
    # Normalize international hostnames and escape literal path characters once.
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError:
        raise ValueError(error) from None
    if any(c in host for c in '/%<>"{}|^`') or _xml_text(site_url) != site_url:
        raise ValueError(error)
    if ":" in host:
        host = "[" + host + "]"
    authority = host + (f":{port}" if port is not None else "")
    path = quote(parts.path, safe="/%").rstrip("/") + "/"
    return urlunsplit((parts.scheme, authority, path, "", ""))


def _date(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        return None
    try:
        return value.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        return None


def write_feed(source, target, site_url, feed_title, pages):
    if site_url is None:
        return
    root = ET.Element("rss", version="2.0")
    channel = ET.SubElement(root, "channel")
    for tag, value in [
        ("title", feed_title),
        ("link", site_url),
        ("description", feed_title),
    ]:
        ET.SubElement(channel, tag).text = value
    outputs = {output: (page, metadata) for page, output, metadata in pages}
    entries = []
    for output, (page, metadata) in outputs.items():
        relative = page.relative_to(source)
        if len(relative.parts) < 2 or relative.parts[0] not in {"blog", "posts"}:
            continue
        metadata = metadata if isinstance(metadata, dict) else {}
        if metadata.get("published") is False:
            continue
        title = metadata.get("title")
        if not isinstance(title, str) or not title.strip():
            title = page.stem
        date = _date(metadata.get("date"))
        link = (
            site_url
            + quote(output.parent.relative_to(target).as_posix(), safe="/")
            + "/"
        )
        entries.append((date, link, _xml_text(title)))
    entries.sort(key=lambda entry: entry[1])
    entries.sort(
        key=lambda entry: (
            entry[0] is not None,
            entry[0] or datetime.min.replace(tzinfo=timezone.utc),
        ),
        reverse=True,
    )
    for date, link, title in entries:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = link
        ET.SubElement(item, "guid", isPermaLink="true").text = link
        if date is not None:
            ET.SubElement(item, "pubDate").text = format_datetime(date, usegmt=True)
    ET.ElementTree(root).write(
        target / "rss.xml", encoding="utf-8", xml_declaration=True
    )
