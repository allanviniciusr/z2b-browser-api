from fastapi import APIRouter, Response
import os

router = APIRouter()

# Favicon simples em base64
FAVICON_DATA = b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff\xcc\x00/\xff'

@router.get("/favicon.ico")
async def favicon():
    return Response(content=FAVICON_DATA, media_type="image/x-icon") 