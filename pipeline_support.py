"""Small shared durability and Moodle policy helpers (standard library only)."""
import os
import re
import tempfile
from pathlib import Path

def atomic_write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(text)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def excluded_resource(resource):
    if resource.get("kind", "").lower() in {"skip", "quiz", "grade", "grades", "exam", "assignment"}:
        return True
    # A reviewed teaching file can have "exam" in its title. Never override
    # Moodle activity/grade URLs or an explicit assessment kind.
    url = str(resource.get("url", ""))
    if re.search(r"/mod/(?:quiz|assign)/|/grade/", url, re.I):
        return True
    if resource.get("reviewed_teaching_material") is True:
        return False
    value = url + " " + str(resource.get("title", ""))
    return bool(re.search(r"/mod/(?:quiz|assign)/|/grade/|\b(?:quizzes|quiz|grades|gradebook|exam|submission)\b", value, re.I))
