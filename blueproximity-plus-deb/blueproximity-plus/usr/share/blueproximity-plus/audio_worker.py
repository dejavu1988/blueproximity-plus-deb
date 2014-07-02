#! /usr/bin/python

import pyaudio
import wave
import os
import threading
from log import *

TAG = 'AUDIO'

class AudioScan(threading.Thread):
    def __init__(self, log_queue, log_lock, path='.'):
        threading.Thread.__init__(self)
        self.FILEPATH = path
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.RECORD_SECONDS = 10
        self.WAVE_OUTPUT_FILENAME = "0.wav"
        self.log_queue = log_queue
        self.log_lock = log_lock

    def run(self): 
        self.log(TAG,'Audio scan started')
        p = pyaudio.PyAudio()

        stream = p.open(format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK)
        self.log(TAG,'Audio stream started')
        #print("* recording")

        frames = []

        for i in range(0, int(self.RATE / self.CHUNK * self.RECORD_SECONDS)):
            data = stream.read(self.CHUNK)
            frames.append(data)

        #print("* done recording")

        stream.stop_stream()
        stream.close()
        p.terminate()
        self.log(TAG,'Audio stream terminated')

        wf = wave.open(os.path.join(self.FILEPATH, self.WAVE_OUTPUT_FILENAME), 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        self.log(TAG,'Audio scan ended, wave dumped')

    def log(self, tag, msg):
        log(self.log_queue, self.log_lock, tag, msg)


if __name__ == "__main__":
    AudioScan().start()
