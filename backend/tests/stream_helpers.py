"""Shared fakes for streaming tests: ffprobe results and ffmpeg launchers."""

HEVC_PROBE = {
    "format": {"format_name": "matroska,webm"},
    "streams": [{"codec_type": "video", "codec_name": "hevc"}],
}
H264_PROBE = {
    "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
    "streams": [{"codec_type": "video", "codec_name": "h264"}],
}


class FakeProcess:
    """Minimal stand-in for a subprocess.Popen, controllable from tests."""

    def __init__(self, alive=True):
        self._alive = alive
        self.terminated = 0
        self.killed = 0
        self.waited = 0

    def poll(self):
        return None if self._alive else 1

    def terminate(self):
        self.terminated += 1
        self._alive = False

    def kill(self):
        self.killed += 1
        self._alive = False

    def wait(self, timeout=None):
        self.waited += 1
        return 1


def make_fake_launch(segment_count=2):
    """Return a launcher that writes a playlist + segments synchronously.

    Mirrors real ffmpeg output: the playlist references segments relative
    to the playlist's own directory.
    """

    def _launch(input_path, work_dir):
        segments_dir = work_dir / "segments"
        segments_dir.mkdir(exist_ok=True)
        for i in range(segment_count):
            (segments_dir / f"segment_{i:05d}.ts").write_bytes(b"ts-data")
        lines = ["#EXTM3U", "#EXT-X-VERSION:3", "#EXT-X-TARGETDURATION:6", "#EXT-X-MEDIA-SEQUENCE:0"]
        for i in range(segment_count):
            lines.append("#EXTINF:6.000000,")
            lines.append(f"segment_{i:05d}.ts")
        lines.append("#EXT-X-ENDLIST")
        (work_dir / "index.m3u8").write_text("\n".join(lines) + "\n")
        return FakeProcess()

    return _launch
