import numpy as np
import cv2
import math

def generateFanMask(outerRad, innerRad, FOV, imageHeight, imageWidth, center=None):
    if center is None:  # use the middle of the image
        center = (int(imageWidth / 2), int(imageHeight / 2))
    #Generate a grid of pixels of the image size specified
    Y, X = np.ogrid[:imageHeight, :imageWidth]
    distFromCenter = np.sqrt((X - center[0]) ** 2 + (Y - center[1]) ** 2)
    radsFromMidline = np.zeros((imageHeight, imageWidth))
    #Generate a "donut" mask
    mask =np.logical_and(distFromCenter < outerRad, distFromCenter > innerRad)
    for y in range(imageHeight):
        for x in range(imageWidth):
            if mask[y][x]:
                radsFromMidline[y][x] = angle_between([y-center[1],x-center[0]],[-1,0])
    #Select a particular fraction of the "donut"
    mask_2 = np.logical_and(mask, radsFromMidline < math.radians(FOV/2))
    #Return the resulting mask
    return mask_2

def unit_vector(vector):
    """ Returns the unit vector of the vector.  """
    return vector / np.linalg.norm(vector)

def angle_between(v1, v2):
    """ Returns the angle in radians between vectors 'v1' and 'v2'
        Taken from here: https://stackoverflow.com/questions/2827393/
                         angles-between-two-n-dimensional-vectors-in-
                         python/13849249#13849249
    """
    v1_u = unit_vector(v1)
    v2_u = unit_vector(v2)
    return np.arccos(np.clip(np.dot(v1_u, v2_u), -1.0, 1.0))

def addNeedleTrajectory(oldMask, center, innerRadius):
    '''
    The ratio between the inner radius and the location of the needle trajectory is
    3:1 in the original probe (ie. it is a probe with a radius of 12mm and the needle is 3mm above that).
    '''
    #Define how long the dashes should be
    dashLen = 10
    dashThickness = 1
    #Define the columns of interest once, since this does not change.
    trajCol = int(center[0] + (innerRadius / 3) * 5)
    cols = list(range(trajCol-dashThickness, trajCol+dashThickness))
    #Go through rows of interest
    for i in range(oldMask.shape[0]):
        #Check whether 5 goes into i an even or odd number of times; only proceed if its odd.
        if math.floor(i/dashLen) % 2:
            #Go through colums of interest
            for j in cols:
                #only colour pixels within the fan
                if oldMask[i,j] > 0:
                    oldMask[i,j] = 0
    return oldMask

imageHeight = 448
imageWidth = 848
FOV = 120
innerRadius = 70
outerRadius = 402
center = (int(imageWidth / 2), int(imageHeight))

mask = generateFanMask(outerRadius, innerRadius, FOV, imageHeight, imageWidth, center)
mask_int = mask.astype(np.uint8) * 255

cv2.imshow("MASK", mask_int)

# maskWithTraj = addNeedleTrajectory(mask_int, center, innerRadius)
# cv2.imshow("MASK", maskWithTraj)
# cv2.waitKey(0)

print(len(mask))
print(len(mask[0]))
cv2.imwrite("C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\Resources\\Utils\\US_Mask_2.png", mask_int)

outputFileName = "US_Mask_2.png"
#
cv2.imshow(outputFileName, mask_int)
cv2.imwrite(outputFileName, mask_int)
cv2.waitKey(0)

self = slicer.mymod
self.loadVolume()

self.getSeg(self.scan,i)

self.polyDataToModel()

import pyvista as pv
pts = slicer.util.arrayFromModelPoints(getNode('Prostate'))
cloud = pv.PolyData(pts)
volume = cloud.delaunay_3d(alpha=5)
shell = volume.extract_geometry()
shell.SetLines(None)
mod = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
mod.SetAndObservePolyData(shell)

n = getNode("ImageToProbe")
mat = n.GetMatrixTransformToParent()
a = slicer.util.arrayFromTransformMatrix(n)
rs = a[0:3,0:3]
import numpy as np
[ss,vv,dd] = np.linalg.svd(rs)
rot = rs/vv
scale = [0.12,0.12,0.12]
rs_new = rot*scale
a[0:3,0:3] = rs_new
a