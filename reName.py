#!/usr/bin/env python
# coding=utf-8

import os, os.path

def rename_file(current_path, img_list):
    count = 0
    srcdir = os.getcwd()
    for file in img_list:
        if file[0] == '.':
            count += 1
            continue
        suffix = file_suffix(file)
        file = srcdir + current_path + file
        print file
        destfile = '%04d' % (count) + suffix
        destfile = srcdir + current_path + destfile
        os.rename(file, destfile)
        print destfile
        count += 1

#rename_file()
def file_suffix(path):
    return os.path.splitext(path)[1]

input_dir = raw_input('please input dir:')
current_path = '/%s/' % (input_dir)
img_list = os.listdir('.' + current_path)
#input_suffix = raw_input('please input suffix:')
#suffix = '.' + input_suffix
print 'input_dir : %s ' % input

#print 'input_suffix : %s ' % input

rename_file(current_path, img_list)
