import golly as g
import os

# Base paths inside the local Golly install
BASE_GOLLY_DIR = os.environ.get('GOLLY_DIR', "/Volumes/Macintosh HD/Users/winston/devel/golly-4.3-mac")
PATTERNS_BASE = os.path.join(BASE_GOLLY_DIR, "Scripts", "Python", "ntzfind_patterns")
RLES_BASE = os.path.join(BASE_GOLLY_DIR, "Scripts", "Python", "rles")

# Auto-select a period directory so the user doesn't have to specify one
available_periods = [d.name for d in os.scandir(PATTERNS_BASE) if d.is_dir()]
if not available_periods:
    raise RuntimeError(f"No period directories found under {PATTERNS_BASE}")

numeric_periods = sorted([int(p) for p in available_periods if p.isdigit()])
if numeric_periods:
    selected_period = str(numeric_periods[-1])
else:
    selected_period = sorted(available_periods)[-1]

directory_path = os.path.join(PATTERNS_BASE, selected_period)
rles_dir = os.path.join(RLES_BASE, selected_period)
os.makedirs(rles_dir, exist_ok=True)

filenames = [
    f for f in os.listdir(directory_path)
    if os.path.isfile(os.path.join(directory_path, f)) and f.lower().endswith('.lif')
]

def get_rule(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
        if len(lines) > 1:
            return lines[1].lstrip('#').strip()
    return None

for index, file in enumerate(sorted(filenames), start=1):
    full = os.path.join(directory_path, file)
    g.open(full)
    rule = get_rule(full)
    print(full)
    if rule:
        g.setrule(rule)
    g.save(os.path.join(rles_dir, f"pattern{index}.rle"), "rle")
    g.update()
