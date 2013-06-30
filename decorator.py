#!/usr/bin/python
# coding: utf-8

# Desktop Decorator

from fractions import Fraction
from math import fabs
from numpy import asarray
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from Tkinter import Tk
import os

VERBOSE	= False

def main():

	import argparse

	parser = argparse.ArgumentParser(description='Generate display-optimised wallpaper images from a directory of wallpapers.', epilog='Which is how you do it.')

	cli_required = parser.add_argument_group('Required Arguments')
	cli_required.add_argument('directory', metavar='directory', type=str, help='directory to load images from')

	cli_output = parser.add_argument_group('Output Options')
	cli_output.add_argument('-x', '--width', metavar='width', type=int, help='change desired width of wallpapers (default: detect desktop resolution)')
	cli_output.add_argument('-y', '--height', metavar='height', type=int, help='change desired height of wallpapers (default: detect desktop resolution)')
	cli_output.add_argument('-u', '--upscale', action='store_const', const=True, default=False, help='allow images to be scaled up, rather than only down')

	cli_iproc = parser.add_argument_group('Image Processing Options')
	cli_iproc.add_argument('-m', '--mask', action='store_const', const=True, default=False, help='enable centre masking (forces feature detection to focus on edges)')
	cli_iproc.add_argument('-g', '--gradient-mask', action='store_const', const=True, default=False, help='use gradient centre masking (requires -m)')
	cli_iproc.add_argument('-t', '--threshold', metavar='threshold', type=int, default=166, choices=range(256), help='change the threshold for feature detection, must be between 0 and 255 (default: 166)')
	
	cli_other = parser.add_argument_group('Other Options')
	cli_other.add_argument('-v', '--verbose', action='store_const', const=True, default=False, help='show verbose (debug) output')
	cli_args = parser.parse_args()

	VERBOSE = cli_args.verbose

	# Detect desktop resolution via Tk if we don't have them specified
	if cli_args.width == None or cli_args.height == None:

		tk = Tk()
		cli_args.width = tk.winfo_screenwidth()
		cli_args.height = tk.winfo_screenheight()
		del tk

	target_ratio = Fraction(cli_args.width, cli_args.height)

	print 'Desktop Decorator'
	print '================='
	print 'Attempting to optimise wallpapers for a display at %sw @ %s...' % (cli_args.width, ratio_string(target_ratio))

	for (dirpath, dirnames, filenames) in os.walk(cli_args.directory):

		for name in filenames:

			if os.path.splitext(name)[-1][1:] in ['jpg', 'jpeg', 'png']:

				print '* Processing "%s"...' % os.path.splitext(name)[0]
				image = Image.open(os.path.join(dirpath, name))
				image = smart_crop(image, cli_args.width, cli_args.height, cli_args.upscale, cli_args.threshold, cli_args.mask, cli_args.gradient_mask)
				image.save('images/%s.%s' % (os.path.splitext(name)[0], os.path.splitext(name)[-1][1:]))

			else:

				print '* %s is being ignored...' % os.path.splitext(name)[0]

	print 'Done.'

# TODO: Move smart_crop and find_image_centroid into a library
def smart_crop(target_image, target_width, target_height, allow_upscale=False, colour_threshold=166,
				use_mask=False, use_mask_gradient=False):

	# Detect target aspect ratio, and current image's aspect ratio
	target_aspect_ratio = Fraction(target_width, target_height)
	existing_aspect_ratio = Fraction(target_image.size[0], target_image.size[1])

	# Debug log of aspect ratio and width
	log('%sw @ %s' % (target_image.size[0], ratio_string(existing_aspect_ratio)))

	# If the aspect ratios match, we can get away with just scaling
	if target_aspect_ratio == existing_aspect_ratio:

		log('Image does not need cropping...')

		# If the image is the same size as we want, we can just output it as-is
		if target_image.size[0] == target_width and target_image.size[1] == target_height:
			
			log('Image is correct size...')

		# Otherwise, if we're allowed to upscale it, or if it's bigger than we need, scale it using
		# the best algorithm we have access to
		elif allow_upscale == True or target_image.size[0] > target_width and target_image.size[1] > target_height:

			log('Image being resized...')
			target_image = target_image.resize((target_width, target_height), Image.ANTIALIAS)

		# Smaller image, but told not to upscale
		else:

			log('Image accepted as-is...')

		return target_image

	# If we need to update the image
	else:

		log('Image sizes differ by %s pixels horizontally, and %s pixels vertically.' % (int(fabs(target_image.size[0] - target_width)), int(fabs(target_image.size[1] - target_height))))

		resize_width = target_width
		resize_height = target_height
		resize_ratio_width = float(resize_width) / float(target_image.size[0])
		resize_ratio_height = float(resize_height) / float(target_image.size[1])

		if resize_ratio_width >= resize_ratio_height:
			resize_height = int(float(target_image.size[1]) * resize_ratio_width)
		else:
			resize_width = int(float(target_image.size[0]) * resize_ratio_height)

		log('Resizing to %sx%s (%s)...' % (resize_width, resize_height, ratio_string(Fraction(resize_width, resize_height))))
		target_image = target_image.resize([resize_width, resize_height], Image.ANTIALIAS)

		image_centroid = find_image_centroid(target_image, colour_threshold, use_mask, use_mask_gradient)

		log('Centroid detected at %s, %s.' % (image_centroid[0], image_centroid[1]))

		# Best crop based on detected centroid
		optimal_crop = [
			int(image_centroid[0] - target_width  / 2),	# Left
			int(image_centroid[1] - target_height / 2),	# Top
			int(image_centroid[0] + target_width  / 2),	# Right
			int(image_centroid[1] + target_height / 2)	# Bottom
		]

		log(optimal_crop)

		# Offsets for crop - if the crop is out of bounds, we adjust it here
		optimal_crop_offset_x = 0
		optimal_crop_offset_y = 0

		# TODO: This is a terrible block. Yuuuck. There must be a way to add/subtract from multi-dimensional arrays in one go?
		if (optimal_crop[0] < 0):
			optimal_crop_offset_x = 0 - optimal_crop[0]
		if (optimal_crop[1] < 0):
			optimal_crop_offset_y = 0 - optimal_crop[1]
		if (optimal_crop[2] > resize_width):
			optimal_crop_offset_x = resize_width - optimal_crop[2]
		if (optimal_crop[3] > resize_height):
			optimal_crop_offset_y = resize_height - optimal_crop[3]

		optimal_crop[0] = optimal_crop[0] + optimal_crop_offset_x
		optimal_crop[1] = optimal_crop[1] + optimal_crop_offset_y
		optimal_crop[2] = optimal_crop[2] + optimal_crop_offset_x
		optimal_crop[3] = optimal_crop[3] + optimal_crop_offset_y

		log(optimal_crop)

		# Crop the target image to the dimensions we specified
		target_image = target_image.crop(optimal_crop)
		return target_image

def find_image_centroid(target_image, colour_threshold=166, use_mask=False, use_mask_gradient=False):

	log('Converting image to greyscale, and detecting edges...')
	edge_detected_image = ImageOps.invert(target_image.copy().filter(ImageFilter.FIND_EDGES))

	# If we're using a mask (to try to direct detection to the edges of the image)
	if use_mask == True:

		# Gradient mask affects detection less, but is more "fair".
		if use_mask_gradient == True:
			mask = Image.new('L', (1,511))
			for y in range(511):
				mask.putpixel((0, 510-y), 254-int(fabs(254-y)))
			mask = mask.resize(target_image.size, Image.NEAREST)

		# Our normal mask is just a rectangle taking up twice the difference between the two image sizes
		elif use_mask_gradient == False:
			mask = Image.new('L', target_image.size)
			drawmask = ImageDraw.Draw(mask)
			drawmask.rectangle(
				[
					(fabs(target_image.size[0] - target_width)*2, fabs(target_image.size[1] - target_height)*2),
					(edge_detected_image.size[0] - fabs(target_image.size[0] - target_width)*2, edge_detected_image.size[1] - fabs(target_image.size[1] - target_height)*2)
				],
				fill=(255)
			)
			del drawmask

		# Overlaying the mask
		draw = ImageDraw.Draw(edge_detected_image)
		draw.bitmap([0,0], mask)
		del draw

	# Convert to greyscale, and apply a hard threshold to weed out less stark contrast
	edge_detected_image = ImageOps.invert(edge_detected_image).convert("L").point(lambda i: i > colour_threshold and 255 or 0)

	# Centroid logic contributed by Ben Stewart
	log('Finding centroid...')

	# Sum of colours in image
	image_sum = sum([sum(row) for row in asarray(edge_detected_image)])

	weighted_rows = sum([y * sum(row) for y, row in enumerate(asarray(edge_detected_image))])
	centroid_y = weighted_rows / image_sum

	weighted_cols = sum([sum([x * val for x, val in enumerate(row)]) for row in asarray(edge_detected_image)])
	centroid_x = weighted_cols / image_sum

	return (centroid_x, centroid_y)

def ratio_string(ratio):
	return str(ratio).replace('/', 'x')

def log(message):
	if VERBOSE == True:
		print '* [DEBUG]', message


if __name__ == "__main__":
	main()