import re

def is_numbered_event(block):
    for line in block.splitlines():
        if line.startswith("SUMMARY:"):
            return re.match(r"SUMMARY:UFC \d+", line) is not None
    return False

with open("UFC.ics", "r", encoding="utf-8") as f:
    data = f.read()

events = data.split("BEGIN:VEVENT")
header = events[0]
event_blocks = ["BEGIN:VEVENT" + e for e in events[1:]]

filtered = [e for e in event_blocks if is_numbered_event(e)]

with open("ufc-numbered.ics", "w", encoding="utf-8") as f:
    f.write(header)
    for e in filtered:
        f.write(e)