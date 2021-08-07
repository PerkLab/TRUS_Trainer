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

#######################################################
#Possible other method
#Based on this: https://slicer.readthedocs.io/en/latest/developer_guide/script_repository.html#save-a-series-of-images-from-a-slice-view

#Start by hiding intersecting volumes and slice view annotations
# Disable slice annotations immediately
sliceAnnotations = slicer.modules.DataProbeInstance.infoWidget.sliceAnnotations
sliceAnnotations.sliceViewAnnotationsEnabled=False
sliceAnnotations.updateSliceViewFromGUI()

#Hide the trajectory and biopsy location
BIOPSY_MODEL = "BiopsyModel"
biopsyModel = slicer.mrmlScene.GetFirstNodeByName(BIOPSY_MODEL)
biopsyDispNode = biopsyModel.GetDisplayNode()
biopsyDispNode.SliceIntersectionVisibilityOff()

#Hide the trajectory and biopsy location
BIOPSY_TRAJECTORY_MODEL = "BiopsyTrajectoryModel"
biopsyTrajectoryModel = slicer.mrmlScene.GetFirstNodeByName(BIOPSY_TRAJECTORY_MODEL)
biopsyTrajectoryDispNode = biopsyTrajectoryModel.GetDisplayNode()
biopsyTrajectoryDispNode.SliceIntersectionVisibilityOff()

#Create a new blank volume
nodeName = "MyNewVolume"
imageSize = [601, 717, 1]
voxelType=vtk.VTK_UNSIGNED_CHAR
imageOrigin = [0, 0, 0]
imageSpacing = [0.1220, 0.1220, 0.1220]
imageDirections = [[1,0,0], [0,1,0], [0,0,1]]
fillVoxelValue = 0

# Create an empty image volume, filled with fillVoxelValue
imageData = vtk.vtkImageData()
imageData.SetDimensions(imageSize)
imageData.AllocateScalars(voxelType, 1)
imageData.GetPointData().GetScalars().Fill(fillVoxelValue)

# Create volume node
volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", nodeName)
volumeNode.SetOrigin(imageOrigin)
volumeNode.SetSpacing(imageSpacing)
volumeNode.SetIJKToRASDirections(imageDirections)
volumeNode.SetAndObserveImageData(imageData)
volumeNode.CreateDefaultDisplayNodes()
volumeNode.CreateDefaultStorageNode()

# *** REALTIME *** #

import ScreenCapture
cap = ScreenCapture.ScreenCaptureLogic()
viewNodeID = 'vtkMRMLSliceNodeRed'
view = cap.viewFromNode(slicer.mrmlScene.GetNodeByID(viewNodeID))
im = qt.QPixmap.grabWidget(view).toImage()
width, height = im.width(), im.height()
img_np = np.array(im.constBits()).reshape(height, width, 4)
grayscale = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)


volumeNode.SetAndObserveImageData(sliceImageData)

#Convert QImage to numpy array
width, height = im.width(), im.height()
img_np = np.array(im.constBits()).reshape(height, width, 4)
grayscale = cv2.cvtColor(img_np, cv2.COLOR_BGR2GRAY)

#Convert directly from QImage to vtkImageData
#(Note this keeps it as 4 channel)
sliceImageData = vtk.vtkImageData()
slicer.qMRMLUtils().qImageToVtkImageData(im, sliceImageData)

# Create an empty image volume, filled with fillVoxelValue
# imageData = vtk.vtkImageData()
# imageData.SetDimensions(imageSize)
# imageData.AllocateScalars(voxelType, 1)
# imageData.GetPointData().GetScalars().Fill(fillVoxelValue)


###########################################################
#         GOAL: Read in an image as a volume.             #
###########################################################

import cv2
import numpy as np

#Specify the image filepath
path = "C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\Resources\\Utils\\example.png"
img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
reader = vtk.vtkPNGReader()
reader.SetFileName(path)
reader.Update()

#Create a new blank volume
nodeName = "MyNewVolume"
imageSize = [400, 400, 1]
voxelType=vtk.VTK_UNSIGNED_INT
imageOrigin = [0, 0, 0]
imageSpacing = [0.1220, 0.1220, 0.1220]
imageDirections = [[1,0,0], [0,1,0], [0,0,1]]
fillVoxelValue = 0

# Create an empty image volume, filled with fillVoxelValue
sampleData = vtk.vtkImageData()
sampleData.SetDimensions(imageSize)
sampleData.AllocateScalars(voxelType, 1)
sampleData.GetPointData().GetScalars().Fill(fillVoxelValue)

# Create volume node
volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", nodeName)
volumeNode.SetOrigin(imageOrigin)
volumeNode.SetSpacing(imageSpacing)
volumeNode.SetIJKToRASDirections(imageDirections)
volumeNode.SetAndObserveImageData(sampleData)
volumeNode.CreateDefaultDisplayNodes()
volumeNode.CreateDefaultStorageNode()

imageData = vtk.vtkImageData()
imageData.DeepCopy(reader.GetOutput())

volumeNode.SetAndObserveImageData(imageData)
