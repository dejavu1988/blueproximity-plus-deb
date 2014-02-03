#! /usr/bin/python

import pyaudio
import wave
import threading
from log import Logging

TAG = 'AUDIO'

class AudioScan(threading.Thread):
    def __init__(self, logging, path='.'):
        threading.Thread.__init__(self)
        self.FILEPATH = path
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 44100
        self.RECORD_SECONDS = 10
        self.WAVE_OUTPUT_FILENAME = "0.wav"
        self.log = logging

    def run(self): 
        self.log.log(TAG,'Audio scan started')
        p = pyaudio.PyAudio()

        stream = p.open(format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.RATE,
                input=True,
                frames_per_buffer=self.CHUNK)
        self.log.log(TAG,'Audio stream started')
        #print("* recording")

        frames = []

        for i in range(0, int(self.RATE / self.CHUNK * self.RECORD_SECONDS)):
            data = stream.read(self.CHUNK)
            frames.append(data)

        #print("* done recording")

        stream.stop_stream()
        stream.close()
        p.terminate()
        self.log.log(TAG,'Audio stream terminated')

        wf = wave.open(self.FILEPATH+'/'+self.WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(self.CHANNELS)
        wf.setsampwidth(p.get_sample_size(self.FORMAT))
        wf.setframerate(self.RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        self.log.log(TAG,'Audio scan ended, wave dumped')

if __name__ == "__main__":
    AudioScan().start()
