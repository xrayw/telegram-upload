import os
import time
import json
from telethon import TelegramClient
from pathlib import Path
from tkinter import Tk, filedialog

MB = 1024 * 1024
ME = "me"


async def upload(files):
    print()
    for i, filepath in enumerate(files):
        path = Path(filepath)
        filename = path.name
        start, upload_bytes = time.time(), 0

        def callback(current, total):
            nonlocal start, upload_bytes
            end = time.time()
            cost = end - start
            start = end

            speed = (current - upload_bytes) / MB / cost

            upload_bytes = current

            print(f"\033[K {i:4}:{len(files)} {filename[-50:]:>50.50} {total/MB:6.2f}M {(current / total) * 100:6.2f}% {speed:6.2f}M/s", end="\r")

        await client.send_file(
            ME,
            filepath,
            caption=filename,
            supports_streaming=True,
            progress_callback=callback,
            silient=True,
            part_size=MB * 20,
        )
        print()



if __name__ == "__main__":
    HOME_DIR = os.path.expanduser("~")

    after = None
    if not os.path.exists(HOME_DIR + '/.tg_cache'):
        appid =   input("  Please input the appid:")
        apphash = input("Please input the apphash:")

        def saveid():
            with open(HOME_DIR + '/.tg_cache', 'w') as f:
                json.dump({'appid': appid, 'apphash': apphash}, f)
            print("Saved appid and apphash to ~/.tg_cache")

        after = saveid
    else:
        with open(HOME_DIR + '/.tg_cache', 'r') as f:
            data = json.loads(f.read())
            appid = data.get('appid')
            apphash = data.get('apphash')

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        files = filedialog.askopenfilenames(parent=root)
    finally:
        root.destroy()
    root.update()

    if not files:
        print("No files selected.")
        exit(1)

    client = TelegramClient("upload", appid, apphash)
    client.start()
    with client:
        client.loop.run_until_complete(upload(files))

    if after:
        after()
