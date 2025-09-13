import os
import sys
import json
import re
import random
from pathlib import Path
from subprocess import PIPE, Popen
from typing import Optional, Union, List

import numpy as np


def get_repo_root() -> Path:
    # repo_root = automons/ (two parents up from this file)
    return Path(__file__).resolve().parent.parent


class AutoNtzfind:
    """Generate random rules, run ntzfind, and write Life 1.05 pattern files."""

    def __init__(self, iterations: int, period: Union[int, str], repo_root: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else get_repo_root()
        self.iterations = int(iterations)
        self.period_int = int(period)
        self.period_str = f"p{self.period_int}"

        # Write patterns into repo-local directory so downstream steps can access them outside Golly
        self.patterns_dir = self.repo_root / "patterns" / str(self.period_int)
        self.patterns_dir.mkdir(parents=True, exist_ok=True)

        # Parameters for rule generation
        self.numbers = list(np.linspace(1, 7, 7, dtype=int))
        self.letters = [
            ["c", "e"],
            ["c", "e", "k", "a", "i", "n"],
            ["c", "e", "k", "a", "i", "n", "y", "q", "j", "r"],
            ["c", "e", "k", "a", "i", "n", "y", "q", "j", "r", "t", "w", "z"],
            ["c", "e", "k", "a", "i", "n", "y", "q", "j", "r"],
            ["c", "e", "k", "a", "i", "n"],
            ["c", "e"],
        ]

    def _generate_sub_rule(self) -> str:
        rule = ""
        for num in random.sample(self.numbers, random.randrange(1, 8)):
            rule += str(num)
            number_of_letters = random.randrange(1, len(self.letters[num - 1]))
            for letter in random.sample(self.letters[num - 1], number_of_letters):
                rule += letter
        return rule

    def _generate_rule(self) -> str:
        return f"b{self._generate_sub_rule()}/s{self._generate_sub_rule()}"

    def _run_ntzfind_once(self, rule: str, index: int) -> bool:
        i = 0
        result = False
        output: list[str] = []

        ntzfind_path = str(self.repo_root / "submodules" / "ntzfind" / "ntzfind")
        process = Popen(
            [ntzfind_path, rule, "w6", self.period_str, "k1", "v", "l200"],
            shell=False,
            stdout=PIPE,
        )

        while True:
            line = process.stdout.readline().decode("utf-8")
            if not line:
                break
            output.append(line)
            if "Starting search" in output[i]:
                start = i + 2
            elif "CPU time" in output[i]:
                start = i + 1
            elif "Length" in output[i]:
                end = i
            elif "0 spaceships" in output[i]:
                output.clear()
                break
            elif "Spaceship found" in output[i]:
                if end - start < 13 or end - start > 18:
                    output.clear()
                    break

                # Reconstruct initial phase from space-time diagram lines.
                # ntzfind outputs successive generations as rows, each horizontally shifted.
                raw_rows = [output[start + k].rstrip("\n").rstrip() for k in range(end - start)]

                # Determine leftmost live cell per row and use a robust shift estimate
                left_indices = []
                for row in raw_rows:
                    try:
                        idx = row.index('o')
                    except ValueError:
                        idx = None
                    left_indices.append(idx)

                # Compute per-row shift relative to first row having a live cell
                base_idx = None
                base_row = 0
                for r, idx in enumerate(left_indices):
                    if idx is not None:
                        base_idx = idx
                        base_row = r
                        break
                # If no live cells found (shouldn't happen), fall back to raw rows
                if base_idx is None:
                    aligned = [row.replace('o', '*') for row in raw_rows]
                else:
                    # Estimate typical shift per generation using median of consecutive diffs
                    diffs = []
                    for r in range(base_row + 1, len(left_indices)):
                        if left_indices[r] is not None and left_indices[r - 1] is not None:
                            diffs.append(left_indices[r] - left_indices[r - 1])
                    shift_per_gen = 0
                    if diffs:
                        diffs_sorted = sorted(diffs)
                        shift_per_gen = diffs_sorted[len(diffs_sorted) // 2]

                    # Align all rows back to generation base_row by compensating horizontal drift
                    # and OR rows together to get a single initial-phase pattern
                    # Build a sufficiently wide buffer
                    max_len = max(len(r) for r in raw_rows) + (len(raw_rows) * abs(shift_per_gen) if shift_per_gen else 0)
                    acc = [False] * max_len
                    for r, row in enumerate(raw_rows):
                        if not row:
                            continue
                        # Determine shift for this row relative to base
                        if left_indices[r] is not None:
                            relative_shift = (left_indices[r] - base_idx) - ((r - base_row) * shift_per_gen)
                        else:
                            relative_shift = 0
                        # Place this row into accumulator shifted left by relative_shift
                        for c, ch in enumerate(row):
                            if ch == 'o':
                                pos = c - relative_shift
                                if 0 <= pos < max_len:
                                    acc[pos] = True or acc[pos]
                    # Convert accumulator to a tight set of rows by taking max across small vertical window
                    # Since we OR'ed all rows into one, just emit a single row across acc
                    # But to keep visual, emit a compact bounding box of acc as a single row
                    # Convert acc boolean list to string
                    if any(acc):
                        left = next(i for i, v in enumerate(acc) if v)
                        right = len(acc) - 1 - next(i for i, v in enumerate(reversed(acc)) if v)
                        merged_row = ''.join('*' if acc[i] else '.' for i in range(left, right + 1))
                        aligned = [merged_row]
                    else:
                        aligned = ['']

                lif_path = self.patterns_dir / f"pattern{index + 1}.lif"
                with lif_path.open("w", encoding="utf-8") as f:
                    f.write("#Life 1.05\n")
                    f.write(f"#{rule}\n")
                    f.write(f"#Period {self.period_str}\n")
                    for row in aligned:
                        f.write(row + "\n")
                        print(row)
                output.clear()
                print("")
                result = True
                break
            i += 1

        return result

    def run(self) -> None:
        successes = 0
        while successes < self.iterations:
            rule = self._generate_rule()
            if self._run_ntzfind_once(rule, successes):
                successes += 1


class GollyBatch:
    """
    Generate a Golly-compatible script that converts Life 1.05 patterns (from repo) to RLEs.
    You still need to run this inside Golly due to the golly Python API.
    """

    def __init__(self, period: Union[int, str], repo_root: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else get_repo_root()
        self.period = str(period)

        self.patterns_dir = self.repo_root / "patterns" / self.period
        self.rles_dir = self.repo_root / "rles" / self.period
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        self.rles_dir.mkdir(parents=True, exist_ok=True)

    def generate_golly_script(self) -> Path:
        script_path = self.repo_root / "tmp" / f"automons_golly_{self.period}.py"
        script_path.parent.mkdir(parents=True, exist_ok=True)

        content = f"""
import golly as g
import os

PATTERNS_DIR = r"{self.patterns_dir.as_posix()}" + "/"
RLES_DIR = r"{self.rles_dir.as_posix()}" + "/"

filenames = [f for f in os.listdir(PATTERNS_DIR) if os.path.isfile(os.path.join(PATTERNS_DIR, f))]

def get_rule(filename):
    with open(filename, 'r') as file:
        lines = file.readlines()
        if len(lines) > 1:
            return lines[1].lstrip('#').strip()
    return None

i = 0
for file in filenames:
    i += 1
    full = PATTERNS_DIR + file
    g.open(full)
    rule = get_rule(full)
    if rule:
        g.setrule(rule)
    g.save(RLES_DIR + "pattern" + str(i) + ".rle", "rle")
    g.update()
""".strip()

        script_path.write_text(content, encoding="utf-8")
        return script_path


class Rle2Apgcode:
    def __init__(self, lifelib_module, period: Union[int, str], repo_root: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else get_repo_root()
        self.period = str(period)
        self.rles_dir = self.repo_root / "rles" / self.period
        self.life_rle_dir = self.repo_root / "legendary"
        self.pythlib_path = self.repo_root / "submodules" / "lifelib" / "pythlib"
        self.catagolue_url = "https://catagolue.hatsya.com/object/"
        self.patterns: dict[str, dict] = {}
        self.lifelib = lifelib_module
        self.rule_cache = ""
        self.lt = None
        self.data_dir = self.repo_root / "data" / self.period
        self.patterns_json_path = self.data_dir / "patterns.json"

        if self.period == "life":
            self.rles_dir = self.life_rle_dir

    def _random_color(self) -> str:
        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _extract_data(self, rle: str):
        match = re.search(r"rule = ([^ \n]+)", rle)
        if not match:
            raise ValueError("Could not find 'rule =' in RLE header")
        raw_rule = match.group(1).lower()
        # Normalize input to lifelib format (b..s.. without slash)
        normalized = self.lifelib.genera.sanirule(raw_rule, drop_history=True)
        # Canonicalize using isotropic.str2tab which raises NonCanonicalError with canonical form
        try:
            self.lifelib.genera.isotropic.str2tab(normalized)
            canonical_rule = normalized
        except Exception as e:
            text = str(e)
            if "non-canonical version of" in text:
                canonical_rule = text.split(" of ")[-1]
            else:
                # Fallback to normalized if unexpected exception
                canonical_rule = normalized
        if canonical_rule != self.rule_cache:
            print(f"Loading lifelib ruleset: {canonical_rule}")
            self.lt = self.lifelib.load_rules(canonical_rule).lifetree(n_layers=1)
            self.rule_cache = canonical_rule

        pattern = self.lt.pattern(rle)
        apgcode = pattern.apgcode
        return pattern, apgcode, self.rule_cache

    def _make_gif_and_qr(self, pattern, apgcode: str, rule: str, url: str, filename_stem: str) -> None:
        from PIL import Image  # ensure pillow available at runtime
        import qrcode

        gifs_dir = self.repo_root / "gifs" / self.period
        qrs_dir = self.repo_root / "qrs" / self.period
        gifs_dir.mkdir(parents=True, exist_ok=True)
        qrs_dir.mkdir(parents=True, exist_ok=True)

        if self.period == "life":
            pattern.make_gif(hue=self._random_color(), filename=str(gifs_dir / f"{filename_stem}.gif"))
        else:
            pattern.make_gif(hue=self._random_color(), filename=str(gifs_dir / f"{apgcode}.gif"))

        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=10, border=4)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image()
        img = img.resize((450, 450))
        if self.period == "life":
            img.save(qrs_dir / f"{filename_stem}.png")
        else:
            img.save(qrs_dir / f"{apgcode}.png")

    def _cleanup_shared_objects(self) -> None:
        try:
            if not os.path.isdir(self.pythlib_path):
                return
            for filename in os.listdir(self.pythlib_path):
                if filename.endswith(".so"):
                    try:
                        os.remove(self.pythlib_path / filename)
                    except FileNotFoundError:
                        pass
        except Exception:
            # Non-fatal; proceed even if cleanup cannot run
            pass

    def _load_existing_patterns(self) -> None:
        if self.patterns_json_path.exists():
            try:
                with open(self.patterns_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.patterns.update(data)
            except Exception:
                pass

    def _flush_patterns(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.patterns_json_path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as json_file:
            json.dump(self.patterns, json_file, indent=4)
        os.replace(tmp_path, self.patterns_json_path)

    def run(self) -> dict:
        if not self.rles_dir.exists() or len(os.listdir(self.rles_dir)) == 0:
            print("No rle files found. Run the Golly conversion step to create RLEs.")
            return {}

        # Load any existing results to allow incremental updates
        self._load_existing_patterns()

        for filename in os.listdir(self.rles_dir):
            if not filename.endswith(".rle"):
                continue
            self.patterns.setdefault(filename, {})
            self.patterns[filename].update({
                "rle": self.patterns[filename].get("rle", ""),
                "rule": self.patterns[filename].get("rule", ""),
                "apgcode": self.patterns[filename].get("apgcode", ""),
                "url": self.patterns[filename].get("url", ""),
                "status": "pending",
            })
            self._flush_patterns()

            file_path = self.rles_dir / filename
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                rle = f.read()

            try:
                # Indicate we may spend time compiling a shared object
                self.patterns[filename]["status"] = "compiling"
                self._flush_patterns()
                result = self._extract_data(rle)
            except Exception as e:
                print(f"Failed to extract for {filename}: {e}")
                self.patterns[filename]["error"] = str(e)
                self.patterns[filename]["status"] = "error"
                self._flush_patterns()
                continue
            pattern, apgcode, rule = result
            self.patterns[filename]["rle"] = rle
            self.patterns[filename]["rule"] = rule
            self.patterns[filename]["apgcode"] = apgcode
            self.patterns[filename]["url"] = self.catagolue_url + apgcode + "/" + rule
            self.patterns[filename]["status"] = "ok"
            self._flush_patterns()

            self._make_gif_and_qr(pattern, apgcode, rule, self.patterns[filename]["url"], file_path.stem)
            self._cleanup_shared_objects()

        return self.patterns


class Cleanup:
    def __init__(self, period: Union[int, str], repo_root: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else get_repo_root()
        self.period = str(period)
        self.rles_dir = self.repo_root / "rles" / self.period
        self.patterns_dir = self.repo_root / "patterns" / self.period
        self.gifs_dir = self.repo_root / "gifs" / self.period

        self.rles_dir.mkdir(parents=True, exist_ok=True)
        self.patterns_dir.mkdir(parents=True, exist_ok=True)
        self.gifs_dir.mkdir(parents=True, exist_ok=True)

        self.patterns: dict = {}

    def clear_files(self) -> None:
        self._clean_dir(self.rles_dir, ".rle", label="rles")
        self._clean_dir(self.patterns_dir, ".lif", label="patterns")

    def _clean_dir(self, directory: Path, suffix: str, label: str) -> None:
        print(f"Cleaning up {label}...")
        for name in os.listdir(directory):
            if name.endswith(suffix):
                print(f"Deleting {name}")
                try:
                    os.remove(directory / name)
                except FileNotFoundError:
                    pass

    def import_patterns(self) -> None:
        data_path = self.repo_root / "data" / self.period / "patterns.json"
        if data_path.exists():
            with open(data_path, "r", encoding="utf-8") as f:
                self.patterns = json.load(f)

    def select_patterns(self) -> None:
        self.import_patterns()
        import tkinter as tk
        from PIL import Image, ImageTk
        import glob

        def handle_user_choice(keep: bool):
            nonlocal images_iter
            global current_image_path
            apgcode = Path(current_image_path).name.replace(".gif", "")

            if not keep:
                os.remove(current_image_path)
                print(f"Deleted {current_image_path}")
                qr_path = current_image_path.replace("gifs", "qrs").replace(".gif", ".png")
                if os.path.exists(qr_path):
                    os.remove(qr_path)
                    print(f"Deleted {qr_path}")
            load_next_image()

        def load_next_image():
            nonlocal img_label, root, images_iter
            global current_image_path
            try:
                current_image_path = next(images_iter)
                img = Image.open(current_image_path)
                img = img.resize((500, 500), Image.Resampling.LANCZOS)
                tk_img = ImageTk.PhotoImage(img)
                img_label.configure(image=tk_img)
                img_label.image = tk_img
                root.title(current_image_path)
            except StopIteration:
                root.destroy()

        root = tk.Tk()
        img_label = tk.Label(root)
        img_label.pack()

        image_directory = self.gifs_dir
        image_paths = glob.glob(str(image_directory / "*.gif"))
        random.shuffle(image_paths)
        images_iter = iter(image_paths)

        keep_button = tk.Button(root, text="Keep Image", command=lambda: handle_user_choice(True))
        keep_button.pack(side=tk.LEFT)
        delete_button = tk.Button(root, text="Delete Image", command=lambda: handle_user_choice(False))
        delete_button.pack(side=tk.RIGHT)

        load_next_image()
        root.mainloop()


## removed Lif2Rle: we will generate RLEs via Golly as originally intended


class Combine:
    def __init__(self, period: Union[int, str], repo_root: Optional[Path] = None) -> None:
        self.repo_root = Path(repo_root) if repo_root is not None else get_repo_root()
        self.period = str(period)
        self.patterns: dict = {}

        self.patterns_path = self.repo_root / "data" / self.period / "patterns.json"
        self.font_path = self.repo_root / "fonts" / "FUTURE" / "future.ttf"

        self.template_path = self.repo_root / "card_backgrounds" / "template.png"
        self.common_path = self.repo_root / "card_backgrounds" / "common"
        self.uncommon_path = self.repo_root / "card_backgrounds" / "uncommon"
        self.rare_path = self.repo_root / "card_backgrounds" / "rare"
        self.legendary_path = self.repo_root / "card_backgrounds" / "legendary"

        self.common_text = "a common\nspaceship"
        self.uncommon_text = "an uncommon\n    spaceship"
        self.rare_text = "   a rare\nspaceship"
        self.legendary_text = "a legendary\n   spaceship"
        self.golden_text = " the golden\n      glider"
        self.golden_front_path = self.repo_root / "card_backgrounds" / "golden.png"

        for p in [self.common_path, self.uncommon_path, self.rare_path, self.legendary_path]:
            p.mkdir(parents=True, exist_ok=True)

        if self.period == "4":
            self.rarity_path = self.common_path / "common_"
            self.text = self.common_text
            self.front_path = self.repo_root / "card_backgrounds" / "common.png"
            self.desc_position = (285, 915)
            self.desc_font_size = 48
        elif self.period == "5":
            self.rarity_path = self.uncommon_path / "uncommon_"
            self.text = self.uncommon_text
            self.front_path = self.repo_root / "card_backgrounds" / "uncommon.png"
            self.desc_position = (240, 915)
            self.desc_font_size = 48
        elif self.period == "6":
            self.rarity_path = self.rare_path / "rare_"
            self.text = self.rare_text
            self.front_path = self.repo_root / "card_backgrounds" / "rare.png"
            self.desc_position = (285, 915)
            self.desc_font_size = 48
        else:
            self.rarity_path = self.legendary_path / "legendary_"
            self.text = self.legendary_text
            self.front_path = self.repo_root / "card_backgrounds" / "legendary.png"
            self.desc_position = (245, 915)
            self.desc_font_size = 48

        self.back_path = self.repo_root / "card_backgrounds" / "back.png"
        self.card_fronts_path = self.repo_root / "card_fronts" / self.period
        self.card_backs_path = self.repo_root / "card_backs" / self.period
        self.ships_path = self.repo_root / "gifs" / self.period
        self.qrs_path = self.repo_root / "qrs" / self.period
        self.card_fronts_path.mkdir(parents=True, exist_ok=True)
        self.card_backs_path.mkdir(parents=True, exist_ok=True)
        self.ships_path.mkdir(parents=True, exist_ok=True)
        self.qrs_path.mkdir(parents=True, exist_ok=True)

        self.gif_scale_factor_x = 1.39
        self.gif_scale_factor_y = 1.39
        self.qr_scale_factor_x = 0.36
        self.qr_scale_factor_y = 0.36
        self.name_font_size = 55
        self.name_position = (185, 194)
        self.ship_position = (195, 344)
        self.qr_position = (66, 141)
        self.name_center_position = (145, 75)
        self.text_color = (0, 0, 0)

    def _load_patterns(self):
        try:
            with open(self.patterns_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            print("Error loading patterns.json")
            return None

    def run(self) -> None:
        self.patterns = self._load_patterns()
        if self.patterns is None:
            return
        self._merge_ships_with_card_front()
        self._merge_qr_codes_with_card_back()
        self._merge_card_front_with_template()
        self._merge_card_back_with_template()

    def _get_ships(self):
        return [f for f in os.listdir(self.ships_path) if f.endswith(".gif")]

    def _get_qrs(self):
        return [f for f in os.listdir(self.qrs_path) if f.endswith(".png")]

    def _get_card_fronts(self):
        return [f for f in os.listdir(self.card_fronts_path) if f.endswith(".png")]

    def _get_card_backs(self):
        return [f for f in os.listdir(self.card_backs_path) if f.endswith(".png")]

    def _merge_card_back_with_template(self):
        from PIL import Image

        template_image = Image.open(self.template_path)
        x_offset = 3300 - 150 - 750
        y_offset = 375
        i = 0
        page = 1
        for card_back in self._get_card_backs():
            if i % 4 == 0 and i != 0:
                y_offset += 1087
                x_offset = 3300 - 150 - 750
            if i % 16 == 0 and i != 0:
                template_image.save(str(self.rarity_path) + f"back_{page}.png")
                page += 1
                template_image = Image.open(self.template_path)
                y_offset = 375
            back_image = Image.open(self.card_backs_path / card_back)
            back_image = back_image.crop((21, 0, 279, 400))
            back_image = back_image.crop((0, 0, 249, 400))
            back_image = back_image.crop((0, 21, 249, 400))
            back_image = back_image.crop((0, 0, 249, 362))
            width, height = back_image.size
            width = width + 3
            height = height + 1
            back_image = back_image.resize((int(width * 3), int(height * 3)))
            template_image.paste(back_image, (x_offset, y_offset), back_image)
            x_offset -= 750
            i += 1
        template_image.save(str(self.rarity_path) + f"back_{page}.png")

    def _merge_card_front_with_template(self):
        from PIL import Image

        template_image = Image.open(self.template_path)
        x_offset = 150
        y_offset = 375
        i = 0
        page = 1
        for card_front in self._get_card_fronts():
            if i % 4 == 0 and i != 0:
                y_offset += 1087
                x_offset = 150
            if i % 16 == 0 and i != 0:
                template_image.save(str(self.rarity_path) + f"front_{page}.png")
                page += 1
                template_image = Image.open(self.template_path)
                y_offset = 375
            front_image = Image.open(self.card_fronts_path / card_front)
            width, height = front_image.size
            width = width - 63
            height = height - 63
            front_image = front_image.crop((63, 63, width, height))
            template_width = 750
            template_height = 1088
            front_image = front_image.resize((int(template_width), int(template_height)))
            template_image.paste(front_image, (x_offset, y_offset), front_image)
            x_offset += 750
            i += 1
        template_image.save(str(self.rarity_path) + f"front_{page}.png")

    def _merge_qr_codes_with_card_back(self):
        from PIL import Image

        for qr_code in self._get_qrs():
            back_image = Image.open(self.back_path)
            qr_code_image = Image.open(self.qrs_path / qr_code)
            width, height = qr_code_image.size
            scaled_width = int(width * self.qr_scale_factor_x)
            scaled_height = int(height * self.qr_scale_factor_y)
            qr_code_image = qr_code_image.resize((scaled_width, scaled_height))
            qr_code_image = qr_code_image.convert("RGBA")
            back_image.paste(qr_code_image, self.qr_position, qr_code_image)
            back_image.save(self.card_backs_path / (qr_code[:-4] + ".png"))

    def _merge_ships_with_card_front(self):
        from PIL import Image, ImageDraw, ImageFont
        from unique_names_generator import get_random_name

        for ship in self._get_ships():
            if ship == "glider.gif":
                front_image = Image.open(self.golden_front_path)
            else:
                front_image = Image.open(self.front_path)
            ship_image = Image.open(self.ships_path / ship)

            width, height = ship_image.size
            scaled_width = int(width * self.gif_scale_factor_x)
            scaled_height = int(height * self.gif_scale_factor_y)
            ship_image = ship_image.resize((scaled_width, scaled_height))
            ship_image = ship_image.convert("RGBA")
            front_image.paste(ship_image, self.ship_position, ship_image)

            draw = ImageDraw.Draw(front_image)
            font = ImageFont.truetype(str(self.font_path), self.name_font_size)
            if self.period == "life":
                name = ship[:-4].replace("_", " ")
            else:
                name = get_random_name()
                while len(name) >= 11:
                    name = get_random_name()
            draw.text(self.name_position, name, font=font, fill=self.text_color)

            draw = ImageDraw.Draw(front_image)
            font = ImageFont.truetype(str(self.font_path), self.desc_font_size)
            if ship == "glider.gif":
                draw.text(self.desc_position, self.golden_text, font=font, fill=self.text_color)
            else:
                draw.text(self.desc_position, self.text, font=font, fill=self.text_color)
            front_image.save(self.card_fronts_path / (ship[:-4] + ".png"))


def _print_header() -> None:
    print("Automons unified pipeline")


def main(argv: Optional[List[str]] = None) -> int:
    import argparse
    from submodules import lifelib

    argv = argv if argv is not None else sys.argv[1:]
    parser = argparse.ArgumentParser(description="Unified Automons pipeline")
    sub = parser.add_subparsers(dest="command", required=True)

    p_find = sub.add_parser("find", help="Run ntzfind to generate Life 1.05 patterns (.lif)")
    p_find.add_argument("period", type=int)
    p_find.add_argument("iterations", type=int)

    p_golly = sub.add_parser(
        "golly-script",
        help="Generate a Golly script to convert patterns (.lif) to RLEs; run it inside Golly",
    )
    p_golly.add_argument("period", type=int)

    p_rle = sub.add_parser("rle2apgcode", help="Convert RLEs to GIFs, QR codes, and patterns.json")
    p_rle.add_argument("period", type=str)


    p_clean = sub.add_parser("clean", help="Delete generated .lif and .rle files for a period")
    p_clean.add_argument("period", type=int)

    p_select = sub.add_parser("select", help="Manually curate generated GIFs/QRs via a simple GUI")
    p_select.add_argument("period", type=str)

    p_combine = sub.add_parser("combine", help="Compose card fronts/backs and sheet pages from GIFs/QRs")
    p_combine.add_argument("period", type=str)

    p_all = sub.add_parser(
        "all",
        help=(
            "Run the end-to-end pipeline (ntzfind -> golly-script generation -> rle2apgcode -> combine). "
            "You still need to execute the generated Golly script manually in Golly between steps."
        ),
    )
    p_all.add_argument("period", type=int)
    p_all.add_argument("iterations", type=int)

    args = parser.parse_args(argv)
    repo_root = get_repo_root()
    _print_header()

    if args.command == "find":
        Cleanup(args.period, repo_root).clear_files()
        AutoNtzfind(args.iterations, args.period, repo_root).run()
        return 0

    if args.command == "golly-script":
        script_path = GollyBatch(args.period, repo_root).generate_golly_script()
        print(f"Generated Golly script: {script_path}")
        print("Open Golly, run this script to convert .lif patterns to .rle files.")
        return 0

    if args.command == "rle2apgcode":
        Rle2Apgcode(lifelib, args.period, repo_root).run()
        return 0


    if args.command == "clean":
        Cleanup(args.period, repo_root).clear_files()
        return 0

    if args.command == "select":
        Cleanup(args.period, repo_root).select_patterns()
        return 0

    if args.command == "combine":
        Combine(args.period, repo_root).run()
        return 0

    if args.command == "all":
        Cleanup(args.period, repo_root).clear_files()
        AutoNtzfind(args.iterations, args.period, repo_root).run()
        script_path = GollyBatch(args.period, repo_root).generate_golly_script()
        print(f"Generated Golly script: {script_path}")
        print("Open Golly and run the script before continuing. Then re-run: python -m src.pipeline rle2apgcode {args.period}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())


