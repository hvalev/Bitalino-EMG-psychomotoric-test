import bitalino
import numpy as np
import time
import random
import matplotlib.pyplot as plt
from threading import Thread
from statsmodels.nonparametric.smoothers_lowess import lowess
import peakutils.peak
import math

num_buzz_trig = 20
threshold = 0
trialData = []
trial = True

# Mac OS
# macAddress = "/dev/tty.BITalino-XX-XX-DevB"
# Windows
macAddress = "20:17:09:18:58:60"
device = bitalino.BITalino(macAddress)

#generate breaks randomly between the different buzzer pulses
def generatePauses(number):
    fib = range(number)
    nums = []
    for num in fib:
        #nums.append(random.uniform(2, 5)) -> a little more stressful test!
        nums.append(random.uniform(3, 6))
    return nums


def dataAcquisition():
    global trial 
    global trialData
    global threshold
    time.sleep(1)
    
    srate = 1000
    nframes = 100

    device.start(srate, [0])
    try:
        while trial:        
            data = device.read(nframes)            
            if np.mean(data[:, 1]) < 1: break    
            EMG = data[:, -1]            
            envelope = np.mean(abs(np.diff(EMG)))            
            #disable writing to datastructure if just initialized
            if(len(trialData) > 0):
                idx = len(trialData) - 1
                #check if timestamp has been written -> disallow two peaks within the same trial frame
                if(trialData[idx][1] == 0 and threshold < envelope):
                    trialData[idx][1] = time.time()
    finally:
        print("STOP")
        device.stop()
        device.close()


def triggerBuzzer():
    global trial 
    global trialData
    global num_buzz_trig
    print("The following trial will measure your psychomotoric response.")
    print("Please activate your muscle as soon as you hear the buzz.")
    time.sleep(10)
    print("5")
    time.sleep(1)
    print("4")
    time.sleep(1)
    print("3")
    time.sleep(1)
    print("2")
    time.sleep(1)
    print("1")
    time.sleep(1)
    print("START")
    pauses = generatePauses(num_buzz_trig)
    for pause in pauses:
        time.sleep(pause)
        trialData.append([time.time(),0])
        device.trigger([0, 1])
        time.sleep(0.2)
        device.trigger([0, 0])
    #final pause, to give room for the last assessment before killing both threads
    time.sleep(5)
    trial = False
    pass

def calibrateSensor():
    global threshold
    print("In order to calibrate the sensor to the muscle you will be using we require you")
    print("to activate that muscle three times during an interval of 10 seconds")
    time.sleep(10)
    srate = 1000
    nframes = 100
    #threshold = 5
    d = []
    device.start(srate, [0])
    try:
        cal_start = time.time()
        while(True):
            now = time.time()
            print("It has been {0} seconds".format(round(now - cal_start),1))
            
            data = device.read(nframes)
            d.extend(data[:,5])
            
            #break loop after 10 seconds
            if((now - cal_start) > 10):
                break
            
    finally:
        converted = []
        for val in d:
            converted.append(transformData(val))
        t = range(len(d))
        filtered = lowess(np.abs(converted), t, is_sorted=True, frac=0.025, it=0)
        plt.plot(filtered[:,1])
        plt.show()
        
        baseline = np.mean(filtered[:,1])
        max_val = np.max(filtered[:,1])
        threshold = (baseline+max_val)/2
        indexes = peakutils.peak.indexes(np.array(filtered[:,1]),
                                         threshold, min_dist=50)
        peaks = []
        for index in indexes:
            peaks.append(filtered[:,1][index])
            
        print('Peaks are: %s' % (indexes))
        print('Peak values are: %s' % (peaks))
        print('Baseline is : %s' % (baseline))
        print('Threshold is : %s' % (threshold))
        
        #we have exactly 3 peaks -> good & don't close socket
        if(len(peaks) == 3):
            device.stop()
            return True   
    device.stop()
    device.close()
    return False
            

def transformData(ADC):
    VCC = 3.3
    G_emg = 1000
    n = 10
    return (((ADC/math.pow(2,n)-0.5)*VCC)/G_emg)*1000

def validateResults():
    global trialData
    for instance in trialData:
        if(instance[1] == 0 or instance[0] == 0):
            return False
    return True

def drawCharts():
    global trialData
    parsed = []
    for e in trialData:
        parsed.append(e[1]-e[0])
    plt.plot(parsed)
    plt.show()
    
    
    fig = plt.figure()
    ax = fig.add_subplot(1,1,1)
    
    x_points = []
    means = []
    std_dev = []
    mins = []
    maxes = []
    upper_boundry = []
    lower_boundry = []
    
    x_points = [0]
    means.append(np.mean(parsed))
    std_dev.append(np.std(parsed))
    mins.append(np.min(parsed))
    maxes.append(np.max(parsed))
    upper_boundry.append(means[0] - mins[0])
    lower_boundry.append(maxes[0] - means[0])
    
    ax.plot()
    ya = ax.get_xaxis()
    ya.set_ticklabels([])
    
    plt.errorbar(x_points, means, [upper_boundry, lower_boundry], fmt='.k', ecolor='blue', lw=5)
    plt.errorbar(x_points, means, std_dev, fmt='ok', ecolor='red', lw=5)
    print("The blue line describes the distribution of values obtained from the trial, also depicting the maximum and minimum")
    print("The red line describes the standard deviation")
    print("The black dot is the mean of all the values")
    if(np.mean(parsed) > 0.7):
        print("You are psychomotorically retarded")
    pass


def main():
    if(calibrateSensor()):
        print("Calibration successful")
        #thread one deals with continuous data acquision
        t1 = Thread(target = dataAcquisition)
        #thread two controls the experiment and triggers the buzzer
        t2 = Thread(target = triggerBuzzer)
        t1.setDaemon(True)
        t2.setDaemon(True)
        t1.start()
        t2.start()
        #rejoin threads to execute drawCharts sequentially
        t1.join()
        t2.join()
        if(validateResults()):
            drawCharts()
        else:
            print("Trial unsucessfull, you may have missed to react to the buzzer")
    else:
        print("Calibration unsuccessfull, please analyze data")
    

if __name__ == "__main__":
    main()
    
    
