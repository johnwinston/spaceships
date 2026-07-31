import os
import re
import qrcode
import json
import random
import imageio

from . import config
from . import shipurl

def random_color():
    r = random.randint(0, 255)
    g = random.randint(0, 255)
    b = random.randint(0, 255)
    return "#{:02x}{:02x}{:02x}".format(r, g, b)

class RLE2APGCODE:
    def __init__(self,lifelib,period):
        self.period = period
        self.rle_path = os.path.join(config.GOLLY_BASE, 'rles/', str(period))
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
            rule = match.group(1).lower().replace('/','')
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
        if not os.path.exists('./qrs/'+self.period):
            os.makedirs('./qrs/'+self.period)

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

    def run(self):
        if len(os.listdir(self.rle_path)) == 0:
            print("No rle files found. Run automons.py in Golly")
            return False

        for filename in os.listdir(self.rle_path):
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
            self.patterns[filename]["rle"] = rle
            self.patterns[filename]["rule"] = rule
            self.patterns[filename]["apgcode"] = apgcode
            # QR codes point at the web player; catagolue kept for reference
            self.patterns[filename]["url"] = shipurl.player_url(
                apgcode=apgcode, rule=rule)
            self.patterns[filename]["catagolue"] = shipurl.catagolue_url(
                apgcode, rule)

            self.make_gif_and_qr(pattern, apgcode, rule, self.patterns[filename]["url"], filename[:-4])
            self.cleanup_shared_objects()

        if not os.path.exists('./data/' + self.period):
            os.makedirs('./data/' + self.period)
        with open('./data/' + self.period + '/patterns.json', 'w') as json_file:
            json.dump(self.patterns, json_file, indent=4)

        return self.patterns
