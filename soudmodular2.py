__author__ = 'Srinivasan'

import pyaudio
import wave

import math
import struct
from math import cos, pi
import random

class Patcher:

    """
    Constructor takes in a dictionary of parameters:
    options = {'format': pyaudio format (pyaudio object),
                 'channels' : number of channels (int),
                 'sampling_rate' : sampling rate (int),
                 'save_file' : path to save output audio (string)
                 }
    """

    def __init__(self, user_dict):
        self.module = Module(user_dict['sampling_rate'])
        self.audio = pyaudio.PyAudio()
        self.format = user_dict.get('format', pyaudio.paInt16)
        self.stream = self.audio.open(format=self.format,
                                      channels=user_dict['channels'],
                                      rate=user_dict['sampling_rate'],
                                      input=False,
                                      output=True)

        filename = user_dict['save_file']
        self.file = wave.open(filename, 'w')		        # self.file : wave file

        self.file.setnchannels(user_dict['channels'])		# stereo
        self.file.setsampwidth(2)		                    # four bytes per sample
        self.file.setframerate(user_dict['sampling_rate'])

        self.range = self.set_range()


    def set_range(self):
        # https://people.csail.mit.edu/hubert/pyaudio/docs/#pyaudio.paInt16
        # Soundmodular currently only supports integer format
        audio_format_range_mapper = {
            16: [-128, 127],                # int8
            8: [-32768, 32767],             # int16
            2: [-2147483648, 2147483647]    # int32
        }

        try:
            return audio_format_range_mapper[self.format]
        except KeyError:
            print "Format must be int8, int16 or int32. See PyAudio docs"


    def to_master(self, block, L, R):

        # Hard Clip amplitude to fit in bit range to avoid overflow
        for k in range(0,len(block)):
            if block[k] > self.range[1]:
                block[k] = self.range[1]
            elif block[k] < self.range[0]:
                block[k] = self.range[0]

        str_out = self.module.pan_stereo(block, L, R)  # Returns a packed struct ready to write

        self.stream.write(str_out)              # Write to playback stream
        self.file.writeframes(str_out)          # Write to file


class Module:

    def __init__(self, sampling_rate):
        self.sampling_rate = sampling_rate

    # Utility Modules
    # Pans audio by applying different gains on left and right channels
    @staticmethod
    def pan_stereo(input_block, gain_left, gain_right):

        if gain_left > 1 or gain_left < 0 or gain_right > 1 or gain_right < 0:
            # print "Invalid Gain. Try between 0 and 1"
            raise ValueError("Invalid Gain. Try values between 0 and 1")

        x_stereo = [0 for n in range(0, 2*len(input_block))]

        for n in range(0,len(input_block)):
            x_stereo[2*n] = gain_left * input_block[n]
            x_stereo[2*n + 1] = gain_right * input_block[n]

        output_str = struct.pack('h'*2*len(input_block), *x_stereo)  # 'h' for 16 bits
        return output_str

    # Source Modules

    def wnoise(self, duration, decay, gain):
        """
        White noise generator

        :param duration: Duration in seconds
        :param decay: Logarithmic decay time in seconds
        :param gain: Initial gain
        :return: Stereo interleaved list
        """
        duration = int(duration* self.sampling_rate)
        decay_samples = int(decay * self.sampling_rate)
        a = math.log(0.01)/decay_samples

        values = range(-32768, 32767)
        out_block = [math.exp(a*n)*gain*random.choice(values) for n in range(0, duration)]

        return out_block

    