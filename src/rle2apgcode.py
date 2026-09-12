import os
import re
import qrcode
import json
import random
import imageio

from . import config
from . import ruletable
from . import shipurl

def random_color():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return "#{:02x}{:02x}{:02x}".format(r, g, b)

class RLE2APGCODE:
    def __init__(self,lifelib,period):
        self.period = str(period)
        self.rle_path = os.path.join(config.PIPELINE_BASE, 'rles/', str(period))
        self.life_rle_path = './legendary/'
        self.pythlib_path = './submodules/lifelib/pythlib/'
        self.patterns = {}
        self.lifelib=lifelib
        self.rule = ''
        self.lt = None
        if period == 'life':
            self.rle_path = self.life_rle_path

    def return_node(self):
        return {
                  "rle" : "",
                  "rule" : "",
                  "apgcode" : "",
                  "url" : "",
                  "catagolue" : ""
               }

    def extract_data(self, rle):
        try:
            match = re.search(r'rule = ([^ \n]+)', rle)
            # lifelib insists on canonical Hensel form; searched rules
            # arrive with clauses in random order.
            rule = ruletable.canonical_rule(match.group(1), self.lifelib)
            rle = re.sub(r'rule = [^ \n]+', 'rule = ' + rule, rle)
            if rule != self.rule:
                self.lt = self.lifelib.load_rules(rule).lifetree(n_layers=1)
                self.rule = rule

            pattern = self.lt.pattern(rle)
            apgcode = pattern.apgcode
        except Exception as e:
            print(e)
            return None
        return pattern, apgcode, rule

    def make_gif_and_qr(self, pattern, apgcode, rule, url, filename):
        if not os.path.exists('./gifs/'+self.period):
            os.makedirs('./gifs/'+self.period)

        if self.period == 'life':
            gif = pattern.make_gif(
                hue=random_color(),
                filename='./gifs/'+self.period+'/'+filename+'.gif'
                )
        else:
            gif = pattern.make_gif(
                    hue=random_color(),
                    filename='./gifs/'+self.period+'/'+apgcode+'.gif'
                    )

        self.make_qr(apgcode, url, filename)

    def make_qr(self, apgcode, url, filename):
        if not os.path.exists('./qrs/'+self.period):
            os.makedirs('./qrs/'+self.period)

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
            )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image()
        img = img.resize((450,450))
        if self.period == 'life':
            img.save('./qrs/' + self.period + '/' + filename + '.png')
        else:
            img.save('./qrs/' + self.period + '/' + apgcode + '.png')

    def cleanup_shared_objects(self):
        for filename in os.listdir(self.pythlib_path):
            if filename.endswith(".so"):
                os.remove(os.path.join(self.pythlib_path, filename))

    def run(self, files=None, make_gifs=True, out_path=None,
            cleanup_each=True):
        """Process RLEs into patterns.json entries.

        files: subset of filenames to process (default: the whole
        directory) so a driver can split a period across workers.
        make_gifs: GIF rendering costs minutes per ship and only matters
        when gifs are the NFT artwork; QR PNGs are always written.
        cleanup_each: the historical behaviour deleted every compiled .so
        after every pattern, recompiling each ship from cold and breaking
        concurrent workers; pass False and clean once per batch instead.
        out_path: where to write the JSON (default: the period's
        patterns.json; workers write part files a driver merges).
        """
        if files is None:
            files = sorted(os.listdir(self.rle_path))
        if len(files) == 0:
            print("No rle files found. Run automons.py in Golly")
            return False

        for filename in files:
            self.patterns[filename] = self.return_node()

            file_path = os.path.join(self.rle_path, filename)
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                rle = f.read()

            try:
                pattern, apgcode, rule = self.extract_data(rle)
            except Exception as e:
                print(e)
                continue
            if pattern is None:
                continue
            # store with the canonical rule header (the player and
            # catalog builder treat the canonical form as identity)
            self.patterns[filename]["rle"] = re.sub(
                r'rule = [^ \n]+', 'rule = ' + rule, rle)
            self.patterns[filename]["rule"] = rule
            self.patterns[filename]["apgcode"] = apgcode
            # QR codes point at the web player; catagolue kept for reference
            self.patterns[filename]["url"] = shipurl.player_url(
                apgcode=apgcode, rule=rule)
            self.patterns[filename]["catagolue"] = shipurl.catagolue_url(
                apgcode, rule)

            if make_gifs:
                self.make_gif_and_qr(
                    pattern, apgcode, rule,
                    self.patterns[filename]["url"], filename[:-4])
            else:
                self.make_qr(apgcode, self.patterns[filename]["url"],
                             filename[:-4])
            if cleanup_each:
                self.cleanup_shared_objects()

        if out_path is None:
            if not os.path.exists('./data/' + self.period):
                os.makedirs('./data/' + self.period)
            out_path = './data/' + self.period + '/patterns.json'
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w') as json_file:
            json.dump(self.patterns, json_file, indent=4)

        return self.patterns
