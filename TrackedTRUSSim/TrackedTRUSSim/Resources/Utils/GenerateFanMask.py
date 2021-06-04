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

# imageHeight = 400
# imageWidth = 400
# FOV = 140
# innerRadius = 40
# outerRadius = 210
# center = (int(imageWidth / 2), int(imageHeight / 4)*3)
#
# mask = generateFanMask(outerRadius, innerRadius, FOV, imageHeight, imageWidth, center)
# mask_int = mask.astype(np.uint8) * 255
#
# cv2.imshow("MASK", mask_int)
# cv2.imwrite("C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\Resources\\Utils\\US_Mask.png", mask_int)
#
# outputFileName = "US_Mask.png"
# #
# cv2.imshow(outputFileName, mask_int)
# cv2.imwrite(outputFileName, mask_int)
# cv2.waitKey(0)



