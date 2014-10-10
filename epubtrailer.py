#!/usr/bin/env python
#-*- coding:utf-8 -*-
"""

(C) 2014 Contributors to the Digital Publishing Toolkit

License: GPL3

This code has been developed as part of the [Digital Publishing Toolkit](http://digitalpublishingtoolkit.org).
with the support of Institute for [Network Cultures](http://networkcultures.org)
and [Creating 010](http://creating010.com).

"""

import sys, zipfile, os, shutil, glob, textwrap, struct
from os.path import join
from xml.etree import ElementTree as ET
from PIL import Image, ImageFont, ImageDraw
from images2gif import writeGif
import argparse


def decode_hexcolor (p):
	"#FFFFFF => (255, 255, 255)"
	if p.startswith("#"):
		p = p.lstrip("#")
	return struct.unpack('BBB',p.decode('hex'))


###############################
# Parse the arguments
###############################
parser = argparse.ArgumentParser(description='Make a gif-format book trailer from an epub')
parser.add_argument('epub', help='epub file')
parser.add_argument('-o', '--output', help='output file')
parser.add_argument('--width', type=int, default=720, help='Width (default: 720)')
parser.add_argument('--height', type=int, default=576, help='Width (default: 576)')
parser.add_argument('--duration', type=float, default=0.25, help='Base slide duration (Default: 0.25 secs)')
parser.add_argument('--backgroundcolor', default="#FFFFFF", help='Background color (default: #FFFFFF aka white)')
parser.add_argument('--textcolor', default="#000000", help='Text color (default: #000000 aka black)')
parser.add_argument('--font', help='Font to use (default: search epub for font, use first found)')
parser.add_argument('--fontratio', type=float, help='Used to compute font sizes (default is width/80)')
parser.add_argument('--padding', type=float, help='Used to position text (default is width/7)')
parser.add_argument('--wrapchars', default=20, type=int, help='Charwidth for text wrapping (default: 20)')
parser.add_argument('--valign', default="top", help='Vertical alignment for text, can be top (default), center, or bottom')


quality=100
args = parser.parse_args()

duration = args.duration # 0.25
W = args.width # 720
H = args.height # 576
titleDuration = 1
epubFont = 1
if args.fontratio:
	fontratio = args.fontratio
else:
	fontratio = int(W/80.0) # 6
bgColor = decode_hexcolor(args.backgroundcolor)
fontColor = decode_hexcolor(args.textcolor)
if args.padding:
	padding = args.padding
else:
	padding = int(W/7.0)
wrapchars = args.wrapchars
filename = args.epub
outfilename = args.output

###############################
# Make the Trailer
###############################
# copy file
copy = 'new-' + filename 
shutil.copy2(filename, 'new-' + filename)

# rename file with zip extension
if filename.endswith('.epub'):
	os.rename(copy, copy[:-4] + 'zip')
	zipname = copy[:-4] + 'zip'
	print "converted extension for " + str(zipname)
else:
	print "File is not an Epub"
	zipname = filename

# unzip ePub
fh = open(str(zipname), 'rb')
z = zipfile.ZipFile(fh)
for name in z.namelist():
    outpath = "temp"
    z.extract(name, outpath)
fh.close()

# remove copy
os.remove(zipname)

# find content.opf
lookfor = "content.opf"
for root, dirs, files in os.walk('temp'):
    print "searching", root
    if lookfor in files:
    	opfpath = join(root, lookfor)
        print "found: %s" % join(root, lookfor)
        break
        
def innerhtml (tag):
    return (tag.text or '') + ''.join(ET.tostring(e) for e in tag)

t = ET.parse(opfpath)

#Get Title
titletag = t.findall('.//{http://purl.org/dc/elements/1.1/}title')
title = titletag[0].text

# Get Authors
cap = t.findall('.//{http://purl.org/dc/elements/1.1/}creator')
authors = []
for tag in cap:
	inner = innerhtml(tag)
	authors.append(inner)
	
# Get Publisher
pubtag = t.findall('.//{http://purl.org/dc/elements/1.1/}publisher')
publisher = None
if pubtag: 
	publisher = pubtag[0].text

# Get Date
datetag = t.findall('.//{http://purl.org/dc/elements/1.1/}date')
date = None
if datetag: 
	date = datetag[0].text

# Show Metadata
if title:
	print "Title:", title
if authors:
	print "Authors:"
	for n in authors:
		print "  ",n
if publisher:
	print "Publisher:", publisher
if date:
	print "Date:", date

# create new directory
if not os.path.exists('new-pictures'):
    os.makedirs('new-pictures')

# Search for fonts

fonts = []
if args.font:
	fonts.append(args.font)

for root, subdirs, files in os.walk('temp'):
    for file in files:
        if os.path.splitext(file)[1].lower() in ('.otf', '.ttf'):
             fonts.append(os.path.join(root, file))
if len(fonts) == 0:
	# try for fonts in the working directory
	for root, subdirs, files in os.walk('.'):
	    for file in files:
	        if os.path.splitext(file)[1].lower() in ('.otf', '.ttf'):
	             fonts.append(os.path.join(root, file))
	             break
	    if len(fonts) > 0:
	    	break

def _bytes(x, encoding="latin-1"):
	""" imagemagick seems to want latin-1 bytes """
	if type(x) == unicode:
		return x.encode(encoding, errors='ignore')
	return x

def screen(text, seq, fontsize, frames, valign=args.valign):
	for x in range(0, frames):
		seqall = seq + '-' + str(x)
		image = Image.new("RGBA", (W,H), bgColor)
		if fonts:
			if epubFont:
				usr_font = ImageFont.truetype(fonts[0], fontsize)
		else:		
			usr_font = ImageFont.load_default() # ImageFont.truetype("resources/NotCourierSans.otf", fontsize)
		d_usr = ImageDraw.Draw(image)
		# align center
		lines = textwrap.wrap(text, width = wrapchars)

		# prefly to calculate total height
		text_height = 0
		for line in lines:
			w, h = d_usr.textsize(_bytes(text), usr_font)
			linebytes = line
			width, height = usr_font.getsize(_bytes(line))
			text_height += height

		if valign=="center":
			y_text = (H/2)-(text_height/2) # padding
		elif valign=="bottom":
			y_text = H-padding-text_height
		else:
			# TOP
			y_text = padding

		for line in lines:
			w, h = d_usr.textsize(_bytes(text), usr_font)
			linebytes = line
			width, height = usr_font.getsize(_bytes(line))
			# d_usr = d_usr.text(((W-w)/2,(H-h)/2), line, fontColor, font=usr_font)
			d_usr.text((padding, y_text), _bytes(line), fontColor, font=usr_font)
			y_text += height
		filename = 'new-pictures/' + seqall + '.jpeg'
		image.save(filename, 'jpeg', quality=quality)

# Create Screen for Title
screen(title, '00', int(fontratio * 6), titleDuration*8)	
# Create Screen for 'by'
screen('A book by', '01', int(fontratio * 2.8), titleDuration*4)
# Create Screens for Authors
i = 0
for name in authors:
	screen(name, '02-' + str(i), int(fontratio * 4), titleDuration*4)
	i = i + 1
if pubtag: 
	# Create Screens for "published by"
	screen('Published by', '03', int(fontratio * 2.8), titleDuration*4)
	# Create Screen for Publisher
	screen(publisher, '04', int(fontratio * 4), titleDuration*4)	

# Search for pictures
epubImages = []
for root, subdirs, files in os.walk('temp'):
    for file in files:
        if os.path.splitext(file)[1].lower() in ('.jpg', '.jpeg', '.png', '.gif', '.bmp'):
             epubImages.append(os.path.join(root, file))
             
# Convert and resize all Picz to Jpeg
i = 0
for picture in epubImages:
	background = Image.new("RGBA", (W,H), bgColor)
	image = Image.open(picture)
	image.thumbnail((W, H), Image.CUBIC)
	(w, h) = image.size
	background.paste(image, ((W-w)/2,(H-h)/2))
	pictitle = 'new-pictures/05-respic' + str(i) + '.jpeg'
	background.save(pictitle, quality=quality)
	i = i + 1

# add some black frames
for x in range(0, titleDuration):
	seq = '06-' + str(x)
	image = Image.new("RGBA", (W,H), bgColor)
	filename = 'new-pictures/' + seq + '-black.jpeg'
	image.save(filename, 'jpeg', quality=quality)
	
# create screen for date
if date: 
	screen('In your Public Library since ' + date, '07', int(fontratio * 3), titleDuration*4)	
	
# add some black frames
for x in range(0, titleDuration):
	seq = '08-' + str(x)
	image = Image.new("RGBA", (W,H), bgColor)
	filename = 'new-pictures/' + seq + '-black.jpeg'
	image.save(filename, 'jpeg', quality=quality)
	
# Make gif!!
images = [Image.open(image) for image in sorted(glob.glob("new-pictures/*.jpeg"))]

if outfilename == None:
	outfilename = 'trailer-' + title.replace("/", "").replace(" ", "_").strip() + '.gif'

writeGif(outfilename, images, duration=duration)

# Remove folders
shutil.rmtree('temp')
shutil.rmtree('new-pictures')  
 
