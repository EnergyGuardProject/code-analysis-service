import json, yaml
# ruleid: custom_python_file-never-closed
yaml.safe_dump({"a": 1}, open("config.yaml", "w"), sort_keys=False)
# ruleid: custom_python_file-never-closed
data = json.load(open("data.json", encoding="utf-8"))
# ok: custom_python_file-never-closed
with open("config.yaml", "w") as f:
    yaml.safe_dump({"a": 1}, f)
# ok: custom_python_file-never-closed
text = open("notes.txt").read()
