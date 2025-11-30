import asyncio
from server.uploader import upload_image_to_db, upload_video_to_db
asyncio.run(upload_image_to_db("test.png"))
asyncio.run(upload_video_to_db("test.mp4"))
