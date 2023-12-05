from svgpathtools import svg2paths2, wsvg, parse_path, Path, Line
import xml.etree.ElementTree as ET
import re
import os

#from svgwrite.mixins import ViewBox
"""
This script reads a .svg and processess it to output the
necessary .png files.
"""
print('separating svg components from original svg...')

def translatePath (path, x, y):
    parse = re.split('[ ,]',path)
    string =''
    while parse:
        elem = parse.pop(0)
        if re.match('[A-Za-z]',elem):
            string += elem + ' '
        else:
            string += str(float(elem) + x) + ','
            string += str(float(parse.pop(0)) + y)
        if parse:
            string += ' '
    return string

# make sure that folder were svg components will be stored is empty
files = os.listdir('./components_svg')
for file in files:
    os.remove('./components_svg' + file)

# select figure in folder
svg_name = 'harry-potter.svg'

# open figure into svgFile and read into svgString
svgFile = open(svg_name,'r')
svgString = svgFile.read()
svgFile.close()

# remove section <defs> ... </defs> from svgString because it is not useful
svgString = re.sub('<defs.*>.*</defs>','<defs/>',svgString, flags=re.DOTALL)
svg_name = 'harry-potter_processed.svg'
newSvgFile = open(svg_name,'w')
newSvgFile.write(svgString)


# reads .svg as a tree element
tree = ET.parse(svg_name)
root = tree.getroot()
g_path_qty = []
# finds the final g tag elements and the qty of paths in each one
# this enumerator will be useful when working with svgpathtools
for g_tag in root.findall('.//{http://www.w3.org/2000/svg}g'):
    path_qty = len(g_tag.findall('{http://www.w3.org/2000/svg}path'))
    if path_qty > 0:
        g_path_qty.append(path_qty)

# reads the svg with svgpathtools
paths, attributes, svg_attributes = svg2paths2(svg_name)
# figure line stroke width of 5mm to guarantee the distance
strokeWidth = 5 * (float(svg_attributes['viewBox'].split()[2]) 
    / float(svg_attributes['width'][:-2]))
# extract some useful params
width_mm = float(svg_attributes['width'][:-2])
height_mm = float(svg_attributes['height'][:-2])
width_px = float(svg_attributes['viewBox'].split()[2])
height_px = float(svg_attributes['viewBox'].split()[3])

# increases path line width to be 5mm, rounds linecaps, 
# rounds linejoints, fills components with black
for attribute in attributes:
    # increases path line width to be 5mm
    try:
        attribute['style'] = re.sub('stroke-width:[0-9.]*', 
            'stroke-width:' + str(strokeWidth),attribute['style'])
    except:
        pass
    # rounds linecaps
    try:
        attribute['style'] = re.sub('stroke-linecap:[a-z]*', 
            'stroke-linecap:round',attribute['style'])
    except:
        pass
    # rounds linejoints
    try:
        attribute['style'] = re.sub('stroke-linejoin:[a-z]*', 
            'stroke-linejoin:round',attribute['style'])
    except:
        pass
    # removes linemiter limits because they do 
    # not make sense in round joints
    try:
        attribute['style'] = re.sub(';stroke-miterlimit:[0-9.]*;', 
            ';',attribute['style'])
    except:
        pass
    # fills with black
    try:
        attribute['style'] = re.sub('fill:[0-9a-z.#]*',
            'fill:black', attribute['style'])
    except:
        pass

# removes transform attributes and includes it on path tag lines
for i in range(0,len(paths)):
    try:
        translation = attributes[i].pop('transform')
        translation = translation[translation.find('(') + 1: translation.find(')')].split(',')
        paths[i] = parse_path(translatePath(paths[i].d(), float(translation[0]), float(translation[1])))
    except:
        continue

# separates components
components = []
for idx, qty in enumerate(g_path_qty):
    components.append([paths[0:qty], attributes[0:qty], svg_attributes])
    paths = paths[qty:]
    attributes = attributes[qty:]

# moves components to the superior left corner of svg and adjust viewbox
for idx, component in enumerate(components):
    # component[h]: paths if h=0; attributes if h=1, svg_attributes if h=2
    # component[0][p] is the component path
    # component[0][p][l] is the line "l" of path "p"
    # component[0][p][l][d] is the point "d" of line "l"
    x_min = 50000
    y_min = 50000
    x_max = -50000
    y_max = -50000
    # gets the min and max x and y in component 
    for path in component[0]:
        for line in path:
            for dot in line:
                if dot.real < x_min: x_min = dot.real
                if dot.real > x_max: x_max = dot.real
                if dot.imag < y_min: y_min = dot.imag
                if dot.imag > y_max: y_max = dot.imag

    # translates position so that it fits in square(0,0,X,Y)
    translation = [-x_min + strokeWidth/2, -y_min + strokeWidth/2]
    for path_idx in range(0, len(component[0])):
        #for i in range(0,len(paths)):
        try:
            component[0][path_idx] = parse_path(translatePath(component[0][path_idx].d(), float(translation[0]), float(translation[1])))
        except:
            continue
   
    # changes the viewBox and the size(in "mm") of svg
    comp_width_px = x_max+strokeWidth-x_min
    comp_height_px = y_max+strokeWidth-y_min
    components[idx][2]['width'] = comp_width_px * width_mm / width_px
    components[idx][2]['height'] = comp_height_px * height_mm / height_px
    components[idx][2]['viewBox'] = ' '.join(map(str,
        [0,0,comp_width_px,comp_height_px])) 
    # if this step be performed outside the loop it does not work
    # this is the only reason 
    wsvg(paths = components[idx][0], attributes = components[idx][1], 
        svg_attributes=components[idx][2], 
            filename='./components_svg/comp'+str(idx).zfill(3)+'.svg')

print('components separates with SUCCESS!')