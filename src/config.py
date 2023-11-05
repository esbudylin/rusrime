import configparser

elements = configparser.RawConfigParser()

with open("elements.cfg", encoding="utf8") as f:
    elements.read_file(f)

xpath = dict(elements.items("XPATH"))

classes = dict(elements.items("CLASS"))

search_url = elements.get("URL", "subcorpus_url")
