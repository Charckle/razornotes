import re

from app.main_page_module.models import Notes


TODO_TYPE = 2

_ITEM = re.compile(r"^- \[( |x|X)\] ?(.*)$")


class Todo:
    """A to-do is a note whose text is a markdown checklist, one item per line:
    "- [ ] milk" / "- [x] bread". Lines keep the order the items were created
    in; checked items are only moved to the bottom when displayed, so an
    unchecked item returns to its original place."""

    # Todo
    @staticmethod
    def parse(text):
        items = []
        for line in Notes.normalize_text(text).split("\n"):
            m = _ITEM.match(line)
            if m:
                items.append({"checked": m.group(1) != " ", "text": m.group(2)})

        return items

    # Todo
    @staticmethod
    def serialize(items):
        return "\n".join(f"- [{'x' if i['checked'] else ' '}] {i['text']}" for i in items)

    # Todo
    @staticmethod
    def clean(text):
        """Drops empty items and anything that is not an item line."""
        items = [i for i in Todo.parse(text) if i["text"].strip()]

        return Todo.serialize(items)

    # Todo
    @staticmethod
    def indexed(text):
        """Items with their position, unchecked first, as the view shows them."""
        items = [dict(i, index=n) for n, i in enumerate(Todo.parse(text))]

        return [i for i in items if not i["checked"]] + [i for i in items if i["checked"]]

    # Todo
    @staticmethod
    def progress(text):
        items = Todo.parse(text)

        return {"done": sum(1 for i in items if i["checked"]), "total": len(items)}

    # Todo
    @staticmethod
    def preview(text, n=100):
        open_items = [i["text"] for i in Todo.parse(text) if not i["checked"]]

        return " · ".join(open_items)[:n]

    # Todo
    @staticmethod
    def set_checked(text, index, checked):
        """Returns the new text, or None if the item does not exist."""
        items = Todo.parse(text)
        if not 0 <= index < len(items):
            return None
        items[index]["checked"] = bool(checked)

        return Todo.serialize(items)
