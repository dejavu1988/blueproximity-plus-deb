#!/usr/bin/python           
""" To compute XCorrelation and time-freq distance of wav pair"""

import wave
import os
import audioop
import math
from scipy import signal, fftpack
import numpy

def getXCorrandDistFromWav(path0, path1):
    amps0, n0 = getSampleAmplitudes(path0)
    amps1, n1 = getSampleAmplitudes(path1)
    N = min(n0,n1)
    timeSignal0 = normalize(amps0, N)
    timeSignal1 = normalize(amps1, N)

    ccf = xcorr(timeSignal0, timeSignal1)
    maxCorr = max(ccf)
    timeDist = 1 - maxCorr
    
    freqSignal0 = normalize(harmonics(timeSignal0), 0)
    freqSignal1 = normalize(harmonics(timeSignal1), 0)

    freqSum = 0
    for i in range(0, len(freqSignal0)):
        diff = freqSignal0[i] - freqSignal1[i]
        freqSum += diff * diff
    freqDist = math.sqrt(freqSum)

    dist = math.sqrt(freqSum + timeDist*timeDist)
    return maxCorr, dist

def getSampleAmplitudes(path):
    wav = wave.open(path, 'rb')
    n = wav.getnframes()
    width = wav.getsampwidth()
    wavbuf = wav.readframes(n)
    amps = []
    for i in range(0,n):
        #print audioop.getsample(wavbuf,width,i)
        amps.append(float(audioop.getsample(wavbuf,width,i)))
    wav.close()
    return amps, n

def normalize(amps, n):
    """Normalize float list with the total average energy
    amps: list of floats, n: size assigned
    return normalized list of float"""
    size = 0
    if size == 0:
        size == len(amps)
    else:
        size = n
    sum_energy = 0
    for amp in amps:
        sum_energy += amp * amp
    avg_energy = math.sqrt(sum_energy)
    normalizedAmps = []
    for amp in amps:
        normalizedAmps.append(amp/avg_energy)
    return normalizedAmps

def harmonics(timeSignal):
    windowSize = len(timeSignal)
    tmpTimeSignal = []
    for i in range(0,windowSize):
        hamWindow = 0.54 - 0.46*math.cos(2*math.pi*i/windowSize)
        tmpTimeSignal.append(timeSignal[i] * hamWindow)
    ta = numpy.array(tmpTimeSignal)
    fullFFTList = fftpack.fft(ta)
    #vector_end = int(round(float(windowSize)/2))
    fftValues = []
    for complexVal in fullFFTList:
        fftValues.append(math.sqrt(complexVal.real**2 + complexVal.imag**2))
    return fftValues

def xcorr(sig1, sig2):
    n2 = len(sig2)
    sig2reverse = [0]*n2
    for i in range(0, n2):
        sig2reverse[i] = sig2[n2-1-i]
    ta0 = numpy.array(sig1)
    ta1 = numpy.array(sig2reverse)
    ccf = signal.fftconvolve(ta0, ta1, 'full')
    return ccf

if __name__ == "__main__":
    path0 = '0.wav'
    path1 = '1.wav'
    maxCorr, freqDist, dist = getXCorrandDistFromWav(path0, path1)
    print maxCorr, dist

