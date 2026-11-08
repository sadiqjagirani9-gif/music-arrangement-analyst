from __future__ import annotations

from contextlib import contextmanager

from backend.capture.models import CaptureDevice


class CaptureBackendUnavailable(RuntimeError):
    pass


class WindowsAudioBackend:
    """SoundCard/WASAPI loopback first, sounddevice input fallback."""

    def list_devices(self) -> list[CaptureDevice]:
        devices = self._soundcard_devices()
        known = {device.name.casefold() for device in devices}
        devices.extend(device for device in self._sounddevice_devices() if device.name.casefold() not in known)
        return devices

    @staticmethod
    def _soundcard_devices() -> list[CaptureDevice]:
        try:
            import soundcard as sc
        except (ImportError, OSError):
            return []
        try:
            default_speaker = sc.default_speaker()
            default_id = str(default_speaker.id) if default_speaker else ""
            microphones = sc.all_microphones(include_loopback=True)
        except RuntimeError:
            return []
        result = []
        for microphone in microphones:
            loopback = bool(getattr(microphone, "isloopback", False)) or "loopback" in microphone.name.casefold()
            result.append(CaptureDevice(
                id=f"soundcard:{microphone.id}", name=microphone.name,
                backend="soundcard_wasapi", kind="output_loopback" if loopback else "input",
                is_loopback=loopback, is_default=loopback and str(microphone.id) == default_id,
            ))
        return result

    @staticmethod
    def _sounddevice_devices() -> list[CaptureDevice]:
        try:
            import sounddevice as sd
        except (ImportError, OSError):
            return []
        result = []
        try:
            default_input = sd.default.device[0]
            for index, info in enumerate(sd.query_devices()):
                channels = int(info.get("max_input_channels") or 0)
                if channels:
                    result.append(CaptureDevice(
                        id=f"sounddevice:{index}", name=str(info["name"]), backend="sounddevice",
                        kind="input", is_loopback=False, is_default=index == default_input,
                        max_channels=min(2, channels),
                    ))
        except (sd.PortAudioError, ValueError):
            return []
        return result

    @contextmanager
    def open_stream(self, device_id: str, sample_rate: int, channels: int, blocksize: int):
        if device_id.startswith("soundcard:"):
            import soundcard as sc
            raw_id = device_id.removeprefix("soundcard:")
            microphone = next((item for item in sc.all_microphones(include_loopback=True) if str(item.id) == raw_id), None)
            if microphone is None:
                raise CaptureBackendUnavailable("所选 WASAPI 设备已断开，请重新选择")
            with microphone.recorder(samplerate=sample_rate, channels=channels, blocksize=blocksize) as recorder:
                yield lambda frames: recorder.record(numframes=frames)
            return
        if device_id.startswith("sounddevice:"):
            import sounddevice as sd
            index = int(device_id.removeprefix("sounddevice:"))
            with sd.InputStream(device=index, samplerate=sample_rate, channels=channels, dtype="float32", blocksize=blocksize) as stream:
                def read(frames: int):
                    data, _overflowed = stream.read(frames)
                    return data
                yield read
            return
        raise CaptureBackendUnavailable("未知音频设备")
