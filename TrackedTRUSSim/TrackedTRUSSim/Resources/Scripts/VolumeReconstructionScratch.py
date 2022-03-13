'''
Script for generating a mask from the command line
'''

import cv2
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy
import ScreenCapture

#Use screencap module logic to get slice view
screenCapLogic = ScreenCapture.ScreenCaptureLogic()
view = screenCapLogic.viewFromNode(slicer.util.getNode('vtkMRMLSliceNodeYellow'))
view.forceRender()

#Apply vtkWindowToImageFilter
rw = view.renderWindow()
wti = vtk.vtkWindowToImageFilter()

wti.SetInput(rw)
wti.Update()

capturedImage = wti.GetOutput()
cols, rows, _ = capturedImage.GetDimensions()
print("columns: " + str(cols))
print("rows: " + str(rows))
sc = capturedImage.GetPointData().GetScalars()
npImage = vtk_to_numpy(sc)
npImage = npImage.reshape(rows, cols, -1)
npImage = np.flipud(npImage)

cv2.imshow("TEST", npImage)

imageHeight = 60
imageWidth = 40
FOV = 120
innerRadius = 8
outerRadius = 30

mask = generateFanMask(outerRadius, innerRadius, FOV, imageHeight, imageWidth)
mask_int = mask.astype(np.uint8) * 255

cv2.imshow("MASK", mask_int)
cv2.imwrite("C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\Resources\\Utils\\US_Mask.png", mask)

npImage[~mask] = [0,0,0]

cv2.imshow("TEST", npImage)