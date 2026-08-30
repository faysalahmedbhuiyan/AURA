import sqlite3

c = sqlite3.connect("../database/aura.db")
c.execute(
    "DELETE FROM sub_agents WHERE name != ? AND task_description LIKE ?",
    ("writing-clean-python-code-with-proper-er-033fc6", "writing clean Python code%"),
)
c.commit()
print("deleted:", c.total_changes)
c.close()