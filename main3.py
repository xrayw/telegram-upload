
import os
import sys
import time
import json
import signal
import argparse
import asyncio
from tkinter import Tk, filedialog
from telethon import TelegramClient
from fastupload import upload_file
from tg_upload_client import TelegramUploadClient
from util import gen_tags

MB = 1024 * 1024
ME = "me"
DELETE_CUR_LINE = '\033[1M'
CLEAR_CUR_LINE = '\033[K'
CLEAR_PREV_LINE = "\033[F\033[K"
FAILED_JSON = 'failed.json'
UPLOADED = set()


async def upload(files, concurrency: int = 5):
    print(f"total: {len(files)}")
    print("done : 0")

    ongoing: list[list[str]] = []
    rendered_cnt = 0

    def get_ongoing_file_item(filepath) -> tuple[int, list[str]] | None:
        for idx, f in enumerate(ongoing):
            if f[0] == filepath:
                return (idx, f)

    def clear_ongoing():
        for _ in range(rendered_cnt):
            clear_prev_line()

    def render_ongoing_files():
        for f in ongoing:
            print(f[1])
        nonlocal rendered_cnt
        rendered_cnt = len(ongoing)

    async def upload_one(idx, filepath):
        filename = os.path.split(filepath)[1]
        upload_bytes = 0

        def callback(part_size, total):
            nonlocal upload_bytes
            upload_bytes += part_size
            print(f'\033[K {upload_bytes / MB:.2f}-{total / MB:.2f} M {upload_bytes / total * 100:6.2f}%', end='\r')

        with open(filepath, 'rb') as f:
            # tgfile = await upload_file(client, f, callback)
            tgfile = await client.upload_file2(f, part_size_kb=512, file_name=filename, progress_callback=callback)
            # tgfile.name = filename
            await client.send_file(ME, tgfile, caption=gen_tags(os.path.splitext(filename)[0]), supports_streaming=True, silient=True)

    for p in files:
        await upload_one(0, p)
        UPLOADED.add(p)

        print('\033[A\033[2M', end='')
        print(f"done : {len(UPLOADED)}")

def clear_prev_line():
    sys.stdout.write(CLEAR_PREV_LINE)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload files to Telegram using Telethon.")
    parser.add_argument('-c', '--count', type=int, default=5, help='Number of concurrent uploads (default: 5)')
    args = parser.parse_args()

    after = None
    if not os.path.exists(".tg_cache"):
        appid = input("  Please input the appid:")
        apphash = input("Please input the apphash:")

        def saveid():
            with open(".tg_cache", "w") as f:
                json.dump({"appid": appid, "apphash": apphash}, f)
            print("Saved appid and apphash to .tg_cache")

        after = saveid
    else:
        with open(".tg_cache", "r") as f:
            data = json.loads(f.read())
            appid = data.get("appid")
            apphash = data.get("apphash")

    files = None
    if os.path.exists(FAILED_JSON):
        try:
            with open(FAILED_JSON, 'r') as f:
                failed = json.load(f)
                if failed:
                    yn = input('Do you want continue to upload failed files? (y/n):').strip().lower()
                    if yn == 'y':
                        files = failed
                    else:
                        print(f'You need to delete `{FAILED_JSON}` first.')
                        exit(0)
        except Exception:
            pass

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    reupload = True if files else False
    if not reupload:
        try:
            files = filedialog.askopenfilenames(parent=root)
        finally:
            root.destroy()
        root.update()

    if not files:
        print("No files selected.")
        exit(1)

    def handle(*args):
        exit(0)

    signal.signal(signal.SIGINT, handle)

    # client = TelegramClient("upload", appid, apphash)
    client = TelegramUploadClient("upload", appid, apphash, concurrent=args.count)
    client.start()
    try:
        with client:
            client.loop.run_until_complete(upload(files, args.count))
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        failed = set(files) - UPLOADED
        if failed:
            print(f"Failed to upload {len(failed)} files. See '{FAILED_JSON}' for details.")
            for f in failed:
                print(os.path.split(f)[1])

            with open(FAILED_JSON, 'w') as f:
                json.dump(list(failed), f, indent=2)
        else:
            if reupload:
                os.remove(FAILED_JSON)
                print(f"All files reuploaded successfully. '{FAILED_JSON}' was removed.")

    if after:
        after()
