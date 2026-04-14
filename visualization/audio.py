import numpy
import pygame

# module-level tone cache: maps integer value -> pygame.Sound
_tone_cache = {}


def generate_tones(arr):
    global _tone_cache
    _tone_cache = {}

    # number of audio samples per second (CD quality)
    sample_rate = 44100

    # tone duration in seconds
    duration = 0.05

    # total number of audio samples for one tone
    num_samples = int(sample_rate * duration)

    min_val = min(arr)
    max_val = max(arr)
    # avoid division by zero if all values are identical
    if max_val == min_val:
        max_val = min_val + 1

    for value in set(arr):
        # map value linearly to a frequency between 200 Hz and 2000 Hz
        freq = 200 + (value - min_val) / (max_val - min_val) * 1800

        # create an array of sample indices: [0, 1, 2, ..., num_samples-1]
        t = numpy.arange(num_samples)

        # compute sine wave: sin(2 * pi * freq * t / sample_rate)
        wave = numpy.sin(2 * numpy.pi * freq * t / sample_rate)

        # scale floating-point values to 16-bit signed integer range [-32767, 32767]
        wave = (wave * 32767).astype(numpy.int16)

        # duplicate mono channel into stereo (two identical columns side by side)
        stereo = numpy.column_stack([wave, wave])

        # ensure memory layout is C-contiguous (required by pygame.sndarray.make_sound)
        stereo = numpy.ascontiguousarray(stereo)

        # create a pygame Sound object from the numpy array and store in cache
        _tone_cache[value] = pygame.sndarray.make_sound(stereo)


def play_tone(value):
    if value in _tone_cache:
        _tone_cache[value].play()
