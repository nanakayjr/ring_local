def save_clip(frames, output_path, fps):
    if not frames:
        return

    try:
        import ffmpeg
        import numpy as np
    except Exception:
        # If ffmpeg or numpy are not available, log and return silently; callers
        # should handle the absence of an output file.
        try:
            import logging
            _LOGGER = logging.getLogger(__name__)
            _LOGGER.exception("ffmpeg or numpy not available; cannot save clip %s", output_path)
        except Exception:
            pass
        return

    height, width, _ = frames[0].shape
    process = (
        ffmpeg
        .input('pipe:', format='rawvideo', pix_fmt='bgr24', s=f'{width}x{height}', r=fps)
        .output(output_path, pix_fmt='yuv420p')
        .overwrite_output()
        .run_async(pipe_stdin=True)
    )

    for frame in frames:
        process.stdin.write(frame.astype(np.uint8).tobytes())

    process.stdin.close()
    process.wait()
