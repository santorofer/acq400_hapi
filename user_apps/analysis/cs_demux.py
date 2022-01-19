#!/usr/bin/env python

"""
A python script to demux the data from the cs system.

The data is supposed to come out in the following way:

CH01 .. CH02 .. CH03 .. CH04 .. INDEX .. FACET .. SAM COUNT .. usec COUNT
short   short   short   short   long     long     long          long

Usage:
Linux:
python cs_demux.py --data_file="/home/sean/PROJECTS/workspace/acq400_hapi-1/user_apps/
                                    acq400/acq1001_068/000001/0000"
Windows:
python .\cs_demux.py --plot_facets=4 --data_file="C:/acq2106_112/000001/0000"
"""


import numpy as np
import matplotlib.pyplot as plt
import argparse


# Sample in u32
# <ACQ420    ><QEN         ><AGG        >
# <AI12><AI34><FACET><INDEX><AGSAM><USEC>

SPS = 12      # shorts per sample
LPS = 6       # longs per sample
ESS = 4       # EVENT signature length in samples
ESL = LPS*ESS # ES length in LW

IX_AI0102 = 0
IX_AI0304 = 1
IX_FACET  = 2
IX_INDEX  = 3
IX_AGSAM  = 4
IX_USEC   = 5

PREV_INDEX = LPS-IX_INDEX   # look back to INDEX in previous sample
NEXT_INDEX = ESL+IX_INDEX   # look forward to next INDEX from beginning of ES

def isES(d):
    return d[0] == 0xaa55f154 and d[1] == 0xaa55f154 and d[2] == 0xaa55f15f and d[3] == 0xaa55f15f

def find_zero_index(args):
    # This function finds the first 0xaa55f154 short value in the data and then
    # uses its position to check the index before this event sample and the
    # index after this event sample and checks the latter is one greater
    # than the former. If the values do not increment then go to the next
    # event sample and repeat.

    
    for pos, lvnu in enumerate(args.data32):
        if isES(args.data32[pos:pos+ESL]):
            # Check current index
            first_es_position = pos
            break

    print("DEBUG: first_es_position {}".format(first_es_position))
    # loop over all the event samples. Look at the "index" value before and
    # after and check they have incremented.
    next_es = args.transient_length*LPS + ESL
    
    for pos, lvnu in enumerate(args.data32[first_es_position:]):
        if pos > 0 and pos % next_es == 0:
            if not isES(args.data32[pos:pos+ESL]):
                print("ERROR: expected ES at {}".format(pos))
                exit(1)
            print("DEBUG: counter {} samples {}".format(pos, pos//LPS))            
            if args.isNewIndex(args.data32[pos - PREV_INDEX], args.data32[pos + NEXT_INDEX]):
                return pos

    print("ERROR: we do not want to be here")
    exit(1)


def extract_bursts(args, zero_index):
    burst32 = args.transient_length*LPS
    burst16 = args.transient_length*SPS
    burst_es = args.transient_length*LPS + ESL
    data = []

    print("extract_bursts() {}, {}, {}".format(zero_index+ESL, len(args.data32), burst_es))
    first_time = True
    for bxx in range(zero_index+ESL, len(args.data32), burst_es):        
        b32 = bxx + 2
        b16 = bxx * 2
        if first_time:
            for ic in range(0, 4):
                data.append(args.data16[b16:b16+burst16:SPS])
                b16 += 1
            for ic in range(0, 4):
                data.append(args.data32[b32:b32+burst32:LPS])
                b32 +=1
            #print(data)
            first_time = False
        else:
            for ic in range(0, 4):
                data[ic] = np.concatenate((data[ic], args.data16[b16:b16+burst16:SPS]))
                b16 += 1
            for ic in range(0, 4):
                data[ic+4] = np.concatenate((data[ic+4], args.data32[b32:b32+burst32:LPS]))
                b32 +=1
    
    if args.msb_direct:
        tmp = np.bitwise_and(data[4], 0x80000000)
        data.append(np.logical_and(tmp, tmp))
        tmp = np.bitwise_and(data[5], 0x80000000)
        data.append(np.logical_and(tmp, tmp))
        
        data[4] = np.bitwise_and(data[4], 0x7fffffff)        
        data[5] = np.bitwise_and(data[5], 0x7fffffff)
         
    for ic, ch in enumerate(data):
        print("{} {}".format(ic, ch.shape))
    return data
        
def save_data(args, data):
    np.tofile("test_file", data)
    return None


def plot_data(args, data):
    # plot all the data in order (not stacked)

    axes = [
        "Demuxed channels from acq1001" + " rev2 with embedded DI2,DI4" if args.msb_direct else "",
        "CH01 \n (Sampled \n FACET)",
        "CH02 \n (Sampled \n INDEX)",
        "CH03 \n (Sampled \n Sine Wave)",
        "CH04 \n (Sampled \n DI2)",
        "FACET \n (u32)",
        "INDEX \n (u32)",
        "Sample Count\n (u32)",
        "usec Count\n (u32)",
        "DI2\n (bool)",
        "DI4\n (bool)"    
    ]

    nsp = 8 if not args.msb_direct else 10
    f, plots = plt.subplots(nsp, 1)
    plots[0].set_title(axes[0])

    for sp in range(0,nsp):
        if args.plot_facets != -1:
            plen = args.transient_length*args.plot_facets
            try:
                # Plot ((number of facets) * (rtm len)) - 1 from each channel
                #plots[sp].plot(data[sp:args.plot_facets * args.transient_length * 8 - 1:8])
                plots[sp].plot(data[sp][:plen])
            except:
                print("Not enough facets to plot")
                plots[sp].plot(data[sp])
        else:
            plots[sp].plot(data[sp])

        plots[sp].set(ylabel=axes[sp+1], xlabel="Samples")
    plt.show()
    return None

def plot_data_msb_direct(args, data):
    # plot all the data in order (not stacked)

    axes = ["Demuxed channels from acq1001",
    "CH01 \n (Sampled \n FACET)",
    "CH02 \n (Sampled \n INDEX)",
    "CH03 \n (Sampled \n Sine Wave)",
    "CH04 \n (Sampled \n Sine Wave)",

    "FACET",
    "INDEX",
    "Sample Count",
    "usec Count",
    "DI2\n",
    "DI4\n",
    ]

    f, plots = plt.subplots(8, 1)
    plots[0].set_title(axes[0])

    for sp in range(0,8):
        if args.plot_facets != -1:
            try:
                slice = data[sp:args.plot_facets * args.transient_length * 8 - 1:8]
                # Plot ((number of facets) * (rtm len)) - 1 from each channel
                plots[sp].plot()
            except:
                print("Data exception met. Plotting all data instead.")
                plots[sp].plot(data[sp:-1:8])
        else:
            plots[sp].plot(data[sp:-1:8])

        plots[sp].set(ylabel=axes[sp+1], xlabel=axes[-1])
    plt.show()
    return None

def isNewIndex_default(w1, w2):
    return w1+1 == w2

def isNewIndex_msb_direct(w1, w2):
    return (w1&0x7fffffff)+1 == (w2&0x7fffffff)

def run_main():
    parser = argparse.ArgumentParser(description='cs demux')
    parser.add_argument('--plot', default=1, type=int, help="Plot data")
    parser.add_argument('--plot_facets', default=-1, type=int, help="No of facets"
                                                                    "to plot")
    parser.add_argument('--save', default=0, type=int, help="Save data")
    parser.add_argument('--transient_length', default=8192, type=int, help='transient length')
    parser.add_argument("--data_file", default="./shot_data", type=str, help="Name of"
                                                                    "data file")
    parser.add_argument("--msb_direct", default=0, type=int, help="new msb_direct feature, d2/d4 embedded in count d31")
    args = parser.parse_args()
    args.isNewIndex = isNewIndex_msb_direct if args.msb_direct else isNewIndex_default
    
    args.data32 = np.fromfile(args.data_file, dtype=np.uint32)
    args.data16 = np.fromfile(args.data_file, dtype=np.int16)

    data = extract_bursts(args, find_zero_index(args))
    if args.plot == 1:
            plot_data(args, data)
    if args.save == 1:
        save_data(args, data)

if __name__ == '__main__':
    run_main()
