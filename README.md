**Replace the sequential upload to concurrent upload. and only use one connection at a time**

And most of them come from https://github.com/Nekmo/telegram-upload/blob/master/telegram_upload/client/telegram_upload_client.py

I simplified it, only kept the upload function, and made some optimizations.

___

Old (**sequential**):
<img width="1934" height="1430" alt="image" src="https://github.com/user-attachments/assets/3ffc48e1-9ec8-46d4-81d7-806a8ec7bf5f" />
___
New (**concurrent**):
<img width="2656" height="1430" alt="image" src="https://github.com/user-attachments/assets/673e1c23-9e9d-4a68-aa32-121a79bb7022" />




---
#### Feature:
1. Support GUI file batch selection
2. Support re-upload after failure
3. Support Concurrent-Upload (Fast speed)


#### Upload
> uv run main.py

#### concurrent upload
> uv run concurrent_upload.py
