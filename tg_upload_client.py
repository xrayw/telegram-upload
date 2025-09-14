import asyncio
import hashlib
import os
from typing import Optional

from telethon import TelegramClient, custom, helpers, hints, utils
from telethon.crypto import AES
from telethon.tl import functions, types, TLRequest


class TelegramUploadClient(TelegramClient):

    def __init__(self, *args, concurrent: int = 5, **kwargs):
        self.concurrent = concurrent
        self.upload_semaphore = asyncio.Semaphore(concurrent)
        super().__init__(*args, **kwargs)

    async def upload_file2(
            self: 'TelegramUploadClient',
            file: 'hints.FileLike',
            *,
            part_size_kb: float = None,
            file_name: str = None,
            key: bytes = None,
            iv: bytes = None,
            progress_callback: 'hints.ProgressCallback' = None
    ) -> 'types.TypeInputFile':
        if isinstance(file, (types.InputFile, types.InputFileBig)):
            return file  # Already uploaded

        async with helpers._FileStream(file) as stream:
            file_size = stream.file_size

            if not part_size_kb:
                part_size_kb = utils.get_appropriated_part_size(file_size)

            if part_size_kb > 512:
                raise ValueError('The part size must be less or equal to 512KB')

            part_size = int(part_size_kb * 1024)
            if part_size % 1024 != 0:
                raise ValueError(
                    'The part size must be evenly divisible by 1024')

            file_id = helpers.generate_random_long()
            if not file_name:
                file_name = stream.name or str(file_id)

            if not os.path.splitext(file_name)[-1]:
                file_name += utils._get_extension(stream)

            # Determine whether the file is too big (over 10MB) or not
            # Telegram does make a distinction between smaller or larger files
            is_big = file_size > 10 * 1024 * 1024
            hash_md5 = hashlib.md5()

            part_count = (file_size + part_size - 1) // part_size
            # self._log[__name__].info('Uploading file of %d bytes in %d chunks of %d',
            #                         file_size, part_count, part_size)

            pos = 0
            tasks = []
            for part_index in range(part_count):
                # Read the file by in chunks of size part_size
                part = await helpers._maybe_await(stream.read(part_size))

                if not isinstance(part, bytes):
                    raise TypeError(
                        'file descriptor returned {}, not bytes (you must '
                        'open the file in bytes mode)'.format(type(part)))

                # `file_size` could be wrong in which case `part` may not be
                # `part_size` before reaching the end.
                if len(part) != part_size and part_index < part_count - 1:
                    raise ValueError(
                        'read less than {} before reaching the end; either '
                        '`file_size` or `read` are wrong'.format(part_size))

                pos += len(part)

                # Encryption part if needed
                if key and iv:
                    part = AES.encrypt_ige(part, key, iv)

                if not is_big:
                    # Bit odd that MD5 is only needed for small files and not
                    # big ones with more chance for corruption, but that's
                    # what Telegram wants.
                    hash_md5.update(part)

                # The SavePartRequest is different depending on whether
                # the file is too large or not (over or less than 10MB)
                if is_big:
                    request = functions.upload.SaveBigFilePartRequest(
                        file_id, part_index, part_count, part)
                else:
                    request = functions.upload.SaveFilePartRequest(
                        file_id, part_index, part)
                await self.upload_semaphore.acquire()
                t = self.loop.create_task(
                    self._send_file_part(request, part_index, part_count, len(part), file_size, progress_callback),
                    name=f"telegram-upload-file-{part_index}"
                )
                tasks.append(t)
            # Wait for all tasks to finish
            await asyncio.wait(tasks)
        if is_big:
            return types.InputFileBig(file_id, part_count, file_name)
        else:
            return custom.InputSizedFile(
                file_id, part_count, file_name, md5=hash_md5, size=file_size
            )

    async def _send_file_part(self, request: TLRequest, part_index: int, part_count: int, part_size: int, file_size: int,
                              progress_callback: Optional['hints.ProgressCallback'] = None) -> None:
        try:
            result = await self(request)
            if result:
                self._log[__name__].debug('Uploaded %d/%d',
                                          part_index + 1, part_count)
            if progress_callback:
                await helpers._maybe_await(progress_callback(part_size, file_size))
            else:
                raise RuntimeError(
                    'Failed to upload file part {}.'.format(part_index))
        finally:
            self.upload_semaphore.release()