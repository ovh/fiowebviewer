import sys
import os
# this path have to point to fiowebviewer package
sys.path.insert(0,"/path/where/you/installed/fiowebviewer/fiowebviewer")
# this path have to point to config file
os.environ['FIOWEBVIEWER_SETTINGS'] = '/path/where/you/installed/fiowebviewer/config.cfg'

from fiowebviewer import application
