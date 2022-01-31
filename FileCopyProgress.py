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
import threading
import time

from PySide6.QtCore import Signal

from TextOut import TextOut

progressCOLOR = '\033[38;5;33;48;5;236m'  # BLUEgreyBG
finalCOLOR = '\033[48;5;33m'  # BLUEBG
# check the color codes below and paste above

# ##### COLORS ####### WHITEblueBG = '\033[38;5;15;48;5;33m' BLUE = '\033[38;5;33m' BLUEBG  = '\033[48;5;33m'
# ORANGEBG = '\033[48;5;208m' BLUEgreyBG = '\033[38;5;33;48;5;236m' ORANGEgreyBG = '\033[38;5;208;48;5;236m' # =
# '\033[38;5;FOREGROUND;48;5;BACKGROUNDm' # ver 'https://i.stack.imgur.com/KTSQa.png' para 256 color codes INVERT =
# '\033[7m' ##### COLORS #######

BOLD = '\033[1m'
UNDERLINE = '\033[4m'
CEND = '\033[0m'

FilesLeft = 0


def FullFolderSize(path):
    total_size = 0
    if os.path.exists(path):  # to be safely used # if FALSE returns 0
        for root, dirs, files in os.walk(path):
            for file in files:
                total_size += os.path.getsize(os.path.join(root, file))
    return total_size


def output_progress(source_path, destination_path, bytes_to_copy, txt_out: Signal = None):
    dst_in_size = FullFolderSize(destination_path)
    time.sleep(.25)

    print(" ")
    print((BOLD + UNDERLINE + "FROM:" + CEND + "   "), source_path)
    print((BOLD + UNDERLINE + "TO:" + CEND + "     "), destination_path)
    print(" ")

    # if os.path.exists(destination_path):
    total_size = int(bytes_to_copy / 1000000)
    TextOut.out_progress_max(total_size)
    total_lab = '{:,}'.format(total_size)

    while bytes_to_copy != (FullFolderSize(destination_path) - dst_in_size):
        current_size = int((FullFolderSize(destination_path) - dst_in_size) / 1000000)
        TextOut.out_progress(current_size)

        if txt_out is not None:
            percent_lab = int(
                (float((FullFolderSize(destination_path) - dst_in_size)) / float(bytes_to_copy)) * 100)
            steps = int(percent_lab / 5)
            current_lab = '{:,}'.format(current_size)
            txt_out.emit(("{:s} / {:s} Mb  ".format(current_lab, total_lab)) + (
                "{:20s}".format('|' * steps)) + (
                             "  {:d}% ".format(percent_lab)) + (
                             "  {:d} Remain ".format(FilesLeft)))
        time.sleep(.01)

    TextOut.out_progress(total_size)


def CopyProgress(source_path, dst, txt_out: Signal = None, allow_same_name=False):
    global FilesLeft

    if dst.startswith(source_path):
        print(" ")
        print(BOLD + UNDERLINE + 'Source folder can\'t be changed.' + CEND)
        print('Please check your target path...')
        print(" ")
        return

    # count bytes to copy
    bytes2copy = 0
    for root, dirs, files in os.walk(source_path):
        # USE for filename in os.listdir(SOURCE): # if you don't want RECURSION #
        dst_dir = root.replace(source_path, dst, 1)  # USE dstDIR = DST # if you don't want RECURSION #
        for filename in files:  # USE if not os.path.isdir(os.path.join(SOURCE, filename)): # if you don't want
            # RECURSION #
            dst_file = os.path.join(dst_dir, filename)
            if os.path.exists(dst_file) and not allow_same_name:
                continue
            bytes2copy += os.path.getsize(os.path.join(root, filename))
            # USE os.path.getsize(os.path.join(SOURCE, filename)) # if you don't want RECURSION #
            FilesLeft += 1

    # Treading to call the progress
    threading.Thread(name='progress', target=output_progress, args=(source_path, dst, bytes2copy, txt_out)).start()
    # main loop
    for root, dirs, files in os.walk(source_path):
        dst_dir = root.replace(source_path, dst, 1)
        if not os.path.exists(dst_dir):
            os.makedirs(dst_dir)
        for filename in files:  # USE if not os.path.isdir(os.path.join(SOURCE, filename)): # if you don't want
            # RECURSION #
            src_file = os.path.join(root, filename)  # USE os.path.join(SOURCE, filename) # if you don't want
            # RECURSION #
            dst_file = os.path.join(dst_dir, filename)
            if os.path.exists(dst_file) and not allow_same_name:
                continue
            head, tail = os.path.splitext(filename)
            count = -1
            year = int(time.strftime("%Y"))
            month = int(time.strftime("%m"))
            day = int(time.strftime("%d"))
            hour = int(time.strftime("%H"))
            minute = int(time.strftime("%M"))
            while os.path.exists(dst_file):
                count += 1
                if count == 0:
                    dst_file = os.path.join(dst_dir,
                                            '{:s}[{:d}.{:d}.{:d}]{:d}-{:d}{:s}'.format(head, year, month, day, hour,
                                                                                       minute, tail))
                else:
                    dst_file = os.path.join(dst_dir,
                                            '{:s}[{:d}.{:d}.{:d}]{:d}-{:d}[{:d}]{:s}'.format(head, year, month, day,
                                                                                             hour, minute, count, tail))
            # END of RENAME part
            shutil.copy2(src_file, dst_file)
            FilesLeft -= 1
            #


'''
Ex.
CopyProgress('/path/to/SOURCE', '/path/to/DESTINATION')
'''
