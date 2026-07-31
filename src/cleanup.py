import os

from . import config

class CLEANUP:
    def __init__(self,period):
        self.base_path = config.GOLLY_BASE
        self.period = str(period)
        self.rle_path = os.path.join(self.base_path, 'rles', self.period) + '/'
        self.pattern_path = os.path.join(self.base_path, 'ntzfind_patterns', self.period) + '/'
        if not os.path.exists(self.pattern_path):
            os.makedirs(self.pattern_path)
        if not os.path.exists(self.rle_path):
            os.makedirs(self.rle_path)
        self.gif_path = './gifs/'+str(self.period)+'/'
        self.patterns = {}

    def clear_files(self):
        self.clean_rles()
        self.clean_patterns()

    def clean_rles(self):
        print("Cleaning up rles...")
        rles = os.listdir(self.rle_path)
        for rle in rles:
            if rle.endswith('.rle'):
                print(f"Deleting {rle}")
                os.remove(self.rle_path + rle)

    def clean_patterns(self):
        print("Cleaning up patterns...")
        patterns = os.listdir(self.pattern_path)
        for pattern in patterns:
            if pattern.endswith('.lif'):
                print(f"Deleting {pattern}")
                os.remove(self.pattern_path + pattern)

    def get_gifs(self):
        # Get all the gifs from the gifs directory
        gif_files = []
        print("Getting gifs...")
        for file in os.listdir(self.gif_path):
            if file.endswith('.gif'):
                gif_files.append(file)
        return gif_files

    def import_patterns(self):
        import json
        with open("./data/"+self.period+"/patterns.json") as f:
            self.patterns = json.load(f)

    def select_patterns(self):
        self.import_patterns()

        import tkinter as tk
        from PIL import Image, ImageTk
        import os
        import glob

        def handle_user_choice(keep):
            global current_image_path
            apgcode = os.path.basename(current_image_path).replace('.gif', '')

            if not keep:
                # Delete gif from gifs directory
                os.remove(current_image_path)
                print(f"Deleted {current_image_path}")

                # Delete QR from qrs directory
                qr_path = current_image_path.replace('gifs', 'qrs')
                qr_path = qr_path.replace('.gif', '.png')
                os.remove(qr_path)
                print(f"Deleted {qr_path}")

            load_next_image()

        def load_next_image():
            global current_image_path
            nonlocal img_label, root
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

        # Display each pattern from the gifs directory
        # and ask the user if they want to keep it
        image_directory = self.gif_path
        image_paths = glob.glob(os.path.join(image_directory, '*.gif'))
        import random
        random.shuffle(image_paths)
        images_iter = iter(image_paths)

        keep_button = tk.Button(
                        root,
                        text="Keep Image",
                        command=lambda: handle_user_choice(True)
                        )
        keep_button.pack(side=tk.LEFT)

        delete_button = tk.Button(
                            root,
                            text="Delete Image",
                            command=lambda: handle_user_choice(False)
                            )
        delete_button.pack(side=tk.RIGHT)

        load_next_image()
        root.mainloop()

