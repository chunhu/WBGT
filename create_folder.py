
import os

def Create_folder(foldername):
    try:
        os.stat(foldername)
    except:
        os.mkdir(foldername)