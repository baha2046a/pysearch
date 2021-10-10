#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Ex.
CopyProgress('/path/to/SOURCE', '/path/to/DESTINATION')


I think this 'copy with overall progress' is very 'plastic' and can be easily adapted.
By default, it will RECURSIVELY copy the CONTENT of  'path/to/SOURCE' to 'path/to/DESTINATION/' keeping the directory tree.

Paying attention to comments, there are 4 main options that can be immediately change:

1 - The LOOK of the progress bar: see COLORS and the PAIR of STYLE lines in 'def getPERCECENTprogress'(inside and after the 'while' loop);

2 - The DESTINATION path: to get 'path/to/DESTINATION/SOURCE_NAME' as target, comment the 2nd 'DST =' definition on the top of the 'def CopyProgress(SOURCE, DESTINATION)' function;

3 - If you don't want to RECURSIVELY copy from sub-directories but just the files in the root source directory to the root of destination, you can use os.listdir() instead of os.walk(). Read the comments inside 'def CopyProgress(SOURCE, DESTINATION)' function to disable RECURSION. Be aware that the RECURSION changes(4x2) must be made in both os.walk() loops;

4 - Handling destination files: if you use this in a situation where the destination filename may already exist, by default, the file is skipped and the loop will jump to the next and so on. On the other way shutil.copy2(), by default, overwrites destination file if exists. Alternatively, you can handle files that exist by overwriting or renaming (according to current date and time). To do that read the comments after 'if os.path.exists(dstFILE): continue' both in the count bytes loop and the main loop. Be aware that the changes must match in both loops (as described in comments) or the progress function will not work properly.

'''

import os
import shutil
import sys
import threading
import time

from PySide6.QtCore import Signal

progressCOLOR = '\033[38;5;33;48;5;236m' #BLUEgreyBG
finalCOLOR =  '\033[48;5;33m' #BLUEBG
# check the color codes below and paste above

###### COLORS #######
# WHITEblueBG = '\033[38;5;15;48;5;33m'
# BLUE = '\033[38;5;33m'
# BLUEBG  = '\033[48;5;33m'
# ORANGEBG = '\033[48;5;208m'
# BLUEgreyBG = '\033[38;5;33;48;5;236m'
# ORANGEgreyBG = '\033[38;5;208;48;5;236m' # = '\033[38;5;FOREGROUND;48;5;BACKGROUNDm' # ver 'https://i.stack.imgur.com/KTSQa.png' para 256 color codes
# INVERT = '\033[7m'
###### COLORS #######

BOLD    = '\033[1m'
UNDERLINE = '\033[4m'
CEND    = '\033[0m'

FilesLeft = 0

def FullFolderSize(path):
    TotalSize = 0
    if os.path.exists(path):# to be safely used # if FALSE returns 0
        for root, dirs, files in os.walk(path):
            for file in files:
                TotalSize += os.path.getsize(os.path.join(root, file))
    return TotalSize

def getPERCECENTprogress(source_path, destination_path, bytes_to_copy, txt_out: Signal):
    dstINIsize = FullFolderSize(destination_path)
    time.sleep(.25)
    print(" ")
    print((BOLD + UNDERLINE + "FROM:" + CEND + "   "), source_path)
    print((BOLD + UNDERLINE + "TO:" + CEND + "     "), destination_path)
    print(" ")
    if os.path.exists(destination_path):
        while bytes_to_copy != (FullFolderSize(destination_path)-dstINIsize):
            #sys.stdout.write('\r')
            percentagem = int((float((FullFolderSize(destination_path)-dstINIsize))/float(bytes_to_copy)) * 100)
            steps = int(percentagem/5)
            copiado = '{:,}'.format(int((FullFolderSize(destination_path)-dstINIsize)/1000000))# Should be 1024000 but this get's closer to the file manager report
            sizzz = '{:,}'.format(int(bytes_to_copy/1000000))
            txt_out.emit(("         {:s} / {:s} Mb  ".format(copiado, sizzz)) +  (BOLD + progressCOLOR + "{:20s}".format('|'*steps) + CEND) + ("  {:d}% ".format(percentagem)) + ("  {:d} ToGo ".format(FilesLeft))) #  STYLE 1 progress default #
            #BOLD# sys.stdout.write(BOLD + ("        {:s} / {:s} Mb  ".format(copiado, sizzz)) +  (progressCOLOR + "{:20s}".format('|'*steps) + CEND) + BOLD + ("  {:d}% ".format(percentagem)) + ("  {:d} ToGo ".format(FilesLeft))+ CEND) # STYLE 2 progress BOLD # 
            #classic B/W# sys.stdout.write(BOLD + ("        {:s} / {:s} Mb  ".format(copiado, sizzz)) +  ("|{:20s}|".format('|'*steps)) + ("  {:d}% ".format(percentagem)) + ("  {:d} ToGo ".format(FilesLeft))+ CEND) # STYLE 3 progress classic B/W #
            #sys.stdout.flush()
            time.sleep(.01)
        #sys.stdout.write('\r')
        #time.sleep(.05)
        #txt_out.emit(("         {:s} / {:s} Mb  ".format('{:,}'.format(int((FullFolderSize(destination_path)-dstINIsize)/1000000)), '{:,}'.format(int(bytes_to_copy/1000000)))) +  (BOLD + finalCOLOR + "{:20s}".format(' '*20) + CEND) + ("  {:d}% ".format( 100)) + ("  {:s}      ".format('    ')) + "\n") #  STYLE 1 progress default #
        #BOLD# sys.stdout.write(BOLD + ("        {:s} / {:s} Mb  ".format('{:,}'.format(int((FullFolderSize(destination_path)-dstINIsize)/1000000)), '{:,}'.format(int(bytes_to_copy/1000000)))) +  (finalCOLOR + "{:20s}".format(' '*20) + CEND) + BOLD + ("  {:d}% ".format( 100)) + ("  {:s}      ".format('    ')) + "\n" + CEND ) # STYLE 2 progress BOLD # 
        #classic B/W# sys.stdout.write(BOLD + ("        {:s} / {:s} Mb  ".format('{:,}'.format(int((FullFolderSize(destination_path)-dstINIsize)/1000000)), '{:,}'.format(int(bytes_to_copy/1000000)))) +  ("|{:20s}|".format('|'*20)) + ("  {:d}% ".format( 100)) + ("  {:s}      ".format('    ')) + "\n" + CEND ) # STYLE 3 progress classic B/W # 
        #sys.stdout.flush()


def CopyProgress(SOURCE, DESTINATION, txt_out: Signal):
    global FilesLeft
    DST = os.path.join(DESTINATION, os.path.basename(SOURCE))
    # <- the previous will copy the Source folder inside of the Destination folder. Result Target: path/to/Destination/SOURCE_NAME
    # -> UNCOMMENT the next (# DST = DESTINATION) to copy the CONTENT of Source to the Destination. Result Target: path/to/Destination
    DST = DESTINATION # UNCOMMENT this to specify the Destination as the target itself and not the root folder of the target 
    #
    if DST.startswith(SOURCE):
        print(" ")
        print(BOLD + UNDERLINE + 'Source folder can\'t be changed.' + CEND)
        print('Please check your target path...')
        print(" ")
        print(BOLD + '        CANCELED' + CEND)
        print(" ")
        exit()
    #count bytes to copy
    Bytes2copy = 0
    for root, dirs, files in os.walk(SOURCE): # USE for filename in os.listdir(SOURCE): # if you don't want RECURSION #
        dstDIR = root.replace(SOURCE, DST, 1) # USE dstDIR = DST # if you don't want RECURSION #
        for filename in files:                # USE if not os.path.isdir(os.path.join(SOURCE, filename)): # if you don't want RECURSION #
            dstFILE = os.path.join(dstDIR, filename)
            if os.path.exists(dstFILE): continue # must match the main loop (after "threading.Thread")
            #                                      To overwrite delete dstFILE first here so the progress works properly: ex. change continue to os.unlink(dstFILE)
            #                                      To rename new files adding date and time, instead of deleating and overwriting,
            #                                      comment 'if os.path.exists(dstFILE): continue'
            Bytes2copy += os.path.getsize(os.path.join(root, filename)) # USE os.path.getsize(os.path.join(SOURCE, filename)) # if you don't want RECURSION #
            FilesLeft += 1
    # <- count bytes to copy
    #
    # Treading to call the preogress
    threading.Thread(name='progresso', target=getPERCECENTprogress, args=(SOURCE, DST, Bytes2copy, txt_out)).start()
    # main loop
    for root, dirs, files in os.walk(SOURCE): # USE for filename in os.listdir(SOURCE): # if you don't want RECURSION #
        dstDIR = root.replace(SOURCE, DST, 1) # USE dstDIR = DST # if you don't want RECURSION #
        if not os.path.exists(dstDIR):
            os.makedirs(dstDIR)
        for filename in files:                # USE if not os.path.isdir(os.path.join(SOURCE, filename)): # if you don't want RECURSION #
            srcFILE = os.path.join(root, filename) # USE os.path.join(SOURCE, filename) # if you don't want RECURSION #
            dstFILE = os.path.join(dstDIR, filename)
            if os.path.exists(dstFILE): continue # MUST MATCH THE PREVIOUS count bytes loop 
            #   <- <-                              this jumps to the next file without copying this file, if destination file exists. 
            #                                      Comment to copy with rename or overwrite dstFILE
            #
            # RENAME part below
            head, tail = os.path.splitext(filename)
            count = -1
            year = int(time.strftime("%Y"))
            month = int(time.strftime("%m"))
            day = int(time.strftime("%d"))
            hour = int(time.strftime("%H"))
            minute = int(time.strftime("%M"))
            while os.path.exists(dstFILE):
                count += 1
                if count == 0:
                    dstFILE = os.path.join(dstDIR, '{:s}[{:d}.{:d}.{:d}]{:d}-{:d}{:s}'.format(head, year, month, day, hour, minute, tail))
                else:
                    dstFILE = os.path.join(dstDIR, '{:s}[{:d}.{:d}.{:d}]{:d}-{:d}[{:d}]{:s}'.format(head, year, month, day, hour, minute, count, tail))
            # END of RENAME part
            shutil.copy2(srcFILE, dstFILE)
            FilesLeft -= 1
            #

'''
Ex.
CopyProgress('/path/to/SOURCE', '/path/to/DESTINATION')
'''
