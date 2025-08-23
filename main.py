import os
import sys
import time
import json
import argparse
import asyncio
from tkinter import Tk, filedialog
from telethon import TelegramClient

MB = 1024 * 1024
ME = "me"
CLEAR_PREV_LINE = "\033[F\033[K"
FAILED_JSON = 'failed.json'


async def upload(files, concurrency: int = 5) -> list[str]:
    print(f"total: {len(files)}")
    print("done : 0")

    semaphore = asyncio.Semaphore(concurrency)
    ongoing: list[list[str]] = []
    done_cnt = 0
    rendered_cnt = 0

    def get_ongoing_file_item(filepath) -> tuple[int, list[str]] | None:
        for idx, f in enumerate(ongoing):
            if f[0] == filepath:
                return (idx, f)
        return None

    def clear_ongoing():
        for _ in range(rendered_cnt):
            clear_prev_line()

    def render_ongoing_files():
        for f in ongoing:
            print(f[1])
        nonlocal rendered_cnt
        rendered_cnt = len(ongoing)

    async def upload_one(idx, filepath):
        """return filepath if failed """

        filename = os.path.split(filepath)[1]
        start, upload_bytes = time.time(), 0

        def callback(current, total):
            nonlocal start, upload_bytes
            end = time.time()
            cost = end - start
            start = end

            speed = (current - upload_bytes) / MB / cost

            upload_bytes = current
            tip = f"{filename[-50:]:>50.25} {current / MB:6.2f}/{total / MB:6.2f}M {(current / total) * 100:6.2f}% {speed:6.2f}M/s"
            f = get_ongoing_file_item(filepath)
            if f:
                f[1][1] = tip

            clear_ongoing()
            render_ongoing_files()

        async with semaphore:
            try:
                # if idx & 1 == 0:
                #     raise Exception('Simulated upload failure for testing purposes.')

                ongoing.append([filepath, ''])

                await client.send_file(
                    ME,
                    filepath,
                    caption=filename,
                    supports_streaming=True,
                    progress_callback=callback,
                    silient=True,
                )
            except Exception:
                return filepath
            finally:
                t = get_ongoing_file_item(filepath)
                if t:
                    del ongoing[t[0]]

    failed = []
    for task in asyncio.as_completed([upload_one(i, filepath) for i, filepath in enumerate(files)]):
        try:
            fp = await task
            if fp:
                failed.append(fp)
                continue
            done_cnt += 1

            clear_ongoing()
            clear_prev_line()

            print(f"done : {done_cnt}")
            render_ongoing_files()
        except Exception:
            pass
    return failed


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

    client = TelegramClient("upload", appid, apphash)
    client.start()
    with client:
        try:
            failed = client.loop.run_until_complete(upload(files, args.count))
            if failed:
                print(f"Failed to upload {len(failed)} files. See '{FAILED_JSON}' for details.")
                for f in failed:
                    print(os.path.split(f)[1])

                with open(FAILED_JSON, 'w') as f:
                    json.dump(failed, f, indent=2)
            else:
                if reupload:
                    os.remove(FAILED_JSON)
                    print(f"All files reuploaded successfully. '{FAILED_JSON}' was removed.")
        except Exception as e:
            print(f"An error occurred: {e}")

    if after:
        after()
