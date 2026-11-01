"""Procedural scene sounds: synthesis, WAV cache and silent fallback.

No real Ursina here: playback is checked with a fake Audio class, and a fake
ursina without Audio must make every call a silent no-op.
"""
import sys
import wave
from types import ModuleType

import pytest

from bloxorz.gui.scene import sounds

EFFECTS = [name for name in sounds.RECIPES if name != "music"]


@pytest.mark.parametrize("name", EFFECTS)
def test_effect_is_normalised_and_fades_out(name):
    samples = sounds.render(name)
    seconds, _recipe = sounds.RECIPES[name]

    assert len(samples) == int(seconds * sounds.RATE)
    assert max(abs(v) for v in samples) == pytest.approx(0.95)
    # The last sample is silent, so the clip ends without a click.
    assert samples[-1] == 0


def test_music_loops_without_a_seam():
    samples = sounds.render("music")

    assert max(abs(v) for v in samples) == pytest.approx(0.95)
    assert abs(samples[-1] - samples[0]) < 0.02


def test_sound_file_writes_a_mono_wav_once(monkeypatch, tmp_path):
    monkeypatch.setattr(sounds, "CACHE_DIR", tmp_path)

    path = sounds.sound_file("select")
    first_write = path.stat().st_mtime_ns

    with wave.open(str(path)) as clip:
        assert clip.getnchannels() == 1
        assert clip.getframerate() == sounds.RATE
        assert clip.getnframes() == int(sounds.RECIPES["select"][0] * sounds.RATE)
    assert sounds.sound_file("select") == path
    assert path.stat().st_mtime_ns == first_write
    assert not list(tmp_path.glob("*.tmp"))


class FakeAudio:
    volume_multiplier = 0.5
    made = []

    def __init__(self, clip, **kwargs):
        self.clip = clip
        self.kwargs = kwargs
        self.played = 0
        self.stopped = 0
        FakeAudio.made.append(self)

    def play(self):
        self.played += 1

    def stop(self):
        self.stopped += 1


@pytest.fixture
def fake_audio(monkeypatch, tmp_path):
    FakeAudio.made = []
    ursina = ModuleType("ursina")
    ursina.Audio = FakeAudio
    ursina.invoke = lambda function, *args, delay=0: function(*args)
    monkeypatch.setitem(sys.modules, "ursina", ursina)
    monkeypatch.setattr(sounds, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(sounds, "_clips", {})
    monkeypatch.setattr(sounds, "_music", None)
    monkeypatch.setattr(sounds, "_music_requested", False)
    monkeypatch.setattr(sounds, "_enabled", True)
    return FakeAudio


def test_play_reuses_one_clip_per_sound(fake_audio):
    sounds.play("land")
    sounds.play("land", volume=0.5, pitch=1.2)

    assert len(fake_audio.made) == 1
    clip = fake_audio.made[0]
    assert clip.played == 2
    assert clip.volume == pytest.approx(sounds.SFX_VOLUME * 0.5)
    assert clip.pitch == 1.2
    # Ursina's default master volume halves everything; sounds lifts it.
    assert fake_audio.volume_multiplier == 1.0


def test_music_starts_once_and_follows_mute(fake_audio):
    sounds.preload()  # build the music file so start_music needs no thread
    sounds.start_music()
    sounds.start_music()

    music = [audio for audio in fake_audio.made if audio.kwargs.get("loop")]
    assert len(music) == 1
    assert music[0].played == 1

    sounds.set_enabled(False)
    sounds.play("win")
    assert music[0].stopped == 1
    assert not [audio for audio in fake_audio.made if not audio.kwargs.get("loop")]

    sounds.set_enabled(True)
    assert music[0].played == 2


def test_everything_is_silent_without_ursina_audio(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "ursina", ModuleType("ursina"))
    monkeypatch.setattr(sounds, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(sounds, "_music_requested", False)

    sounds.play("land")
    sounds.start_music()
    sounds.preload()

    assert not list(tmp_path.iterdir())  # nothing synthesised or written


def test_a_broken_audio_backend_never_breaks_the_game(fake_audio, monkeypatch):
    def broken(*_args, **_kwargs):
        raise OSError("no sound card")

    sounds.preload()
    monkeypatch.setattr(fake_audio, "__init__", broken)

    sounds.play("crack")  # must not raise
    sounds.start_music()


def test_music_gives_up_when_the_file_is_never_built(fake_audio, monkeypatch):
    monkeypatch.setattr(sounds.threading, "Thread", lambda **_kwargs: type(
        "NoThread", (), {"start": lambda self: None})())

    sounds.start_music()  # polls a bounded number of times, then stops

    assert not fake_audio.made
