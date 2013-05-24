#!/usr/bin/python
# coding: utf-8

# Desktop Decorator

from PIL import Image
from fractions import Fraction
import os

for (dirpath, dirnames, filenames) in os.walk(os.path.expanduser('~/Dropbox/Photos/Wallpapers/')):
	for name in filenames:
		if os.path.splitext(name)[-1][1:] in ['jpg', 'jpeg', 'png']:
			image = Image.open(os.path.join(dirpath, name))
			ratio = Fraction(image.size[0],image.size[1])
			print '%s - %sw @ %s' % (os.path.splitext(name)[0], image.size[0], str(ratio).replace('/', 'x'))
			#print os.path.join(dirpath, name)