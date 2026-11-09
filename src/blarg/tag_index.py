"""A grouped index of successfully rendered Markdown pages."""

from urllib.parse import quote

from markupsafe import Markup, escape


def write_tag_index(source, target, template, pages):
    destination = target / "tags" / "index.html"
    if destination.exists():
        return

    groups = {}
    # Main permits flat-name overwrites. Only the last successful output owns tags.
    outputs = {output: (page, output, metadata) for page, output, metadata in pages}
    for page, output, metadata in sorted(
        outputs.values(), key=lambda entry: entry[0].relative_to(source).as_posix()
    ):
        if not isinstance(metadata, dict):
            continue
        tags = metadata.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        if not isinstance(tags, list):
            continue
        tags = {tag.strip() for tag in tags if isinstance(tag, str) and tag.strip()}
        title = metadata.get("title")
        if not isinstance(title, str) or not title.strip():
            title = page.stem
        link = "../" + quote(output.parent.relative_to(target).as_posix()) + "/"
        for tag in tags:
            groups.setdefault(tag, []).append((link, title))

    if not groups:
        return
    body = ""
    for tag in sorted(groups):
        body += f"<h2>{escape(tag)}</h2><ul>"
        for link, title in groups[tag]:
            body += f'<li><a href="{escape(link)}">{escape(title)}</a></li>'
        body += "</ul>"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        template.render(body=Markup(body), frontmatter={"title": "Tags"}),
        encoding="utf-8",
    )
