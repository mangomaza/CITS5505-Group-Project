from wtforms.validators import ValidationError


def detect_image_type(header):
    if header.startswith(b'\xff\xd8\xff'):
        return 'jpeg'
    if header.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if header.startswith((b'GIF87a', b'GIF89a')):
        return 'gif'
    if header.startswith(b'RIFF') and header[8:12] == b'WEBP':
        return 'webp'
    return None


def validate_image_upload(upload, *, max_bytes, allowed_types,
                          oversize_message, invalid_message):
    """Size + magic-byte check for an uploaded image field.

    Returns silently if upload is empty. Raises ValidationError otherwise.
    Always restores the stream position so the route can re-read it.
    """
    if upload is None or not getattr(upload, 'filename', ''):
        return

    stream = upload.stream
    start = stream.tell()
    stream.seek(0, 2)
    size = stream.tell()
    stream.seek(0)

    try:
        if size > max_bytes:
            raise ValidationError(oversize_message)

        header = stream.read(512)
        stream.seek(0)
        image_type = detect_image_type(header)
        mimetype = (upload.mimetype or '').lower()
        if image_type not in allowed_types or not mimetype.startswith('image/'):
            raise ValidationError(invalid_message)
    finally:
        stream.seek(start)
