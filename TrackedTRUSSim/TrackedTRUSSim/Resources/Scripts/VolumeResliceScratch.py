'''
Script for generating a mask from the command line
'''

import cv2
import numpy as np
import slicer.util
from vtk.util.numpy_support import vtk_to_numpy
import ScreenCapture

from matplotlib import pyplot as plt
from vtk.util import numpy_support


###########################################################
#         Creating a volume from scratch.             #
###########################################################

import cv2
import numpy as np

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


###########################################################
#         Modified script                                 #
###########################################################

def newRedVol(volName):
    volume = slicer.util.getNode(volName)
    npImage = resliceRed(volume)
    # Create a new blank volume
    imageSpacing = [0.1220, 0.1220, 0.1220]
    createVolumeSlice(npImage, imageSpacing)
    cv2.imshow("TEST", npImage)

def resliceRed(volume):
    layoutManager = slicer.app.layoutManager()
    redWidget = layoutManager.sliceWidget("Red")
    sliceNode = redWidget.mrmlSliceNode()
    bounds = [0]*6
    volume.GetRASBounds(bounds)
    imageReslice = redWidget.sliceLogic().GetBackgroundLayer().GetReslice()
    imageData = imageReslice.GetOutputDataObject(0)
    array = vtk.util.numpy_support.vtk_to_numpy(imageData.GetPointData().GetScalars())
    sliceShape = sliceNode.GetDimensions()
    npImage = array.reshape(sliceShape[1],sliceShape[0])
    return npImage

def createVolumeSlice(imageData, imageSpacing, nodeName="MyNewVolume"):
    vtkGrayscale = numpy_support.numpy_to_vtk(imageData.flatten(order='C'), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
    #Convert the image to vtkImageData object
    sliceImageData = vtk.vtkImageData()
    # sliceImageData.SetScalarTypeToUnsignedChar()
    sliceImageData.SetDimensions(len(imageData[0]), len(imageData[1]), 1)
    sliceImageData.SetOrigin(0.0, 0.0, 0.0)
    # sliceImageData.SetSpacing(imageSpacing)
    sliceImageData.GetPointData().SetScalars(vtkGrayscale)
    imageOrigin = [0, 0, 0]
    imageDirections = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    # Create volume node
    volumeNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode", nodeName)
    volumeNode.SetOrigin(imageOrigin)
    volumeNode.SetSpacing(imageSpacing)
    volumeNode.SetIJKToRASDirections(imageDirections)
    volumeNode.SetAndObserveImageData(sliceImageData)
    volumeNode.CreateDefaultDisplayNodes()
    volumeNode.CreateDefaultStorageNode()

def imageFromNPData(npData):
    imageData, npData = newRedVol('TRUS')
    plt.imshow(npData, interpolation='nearest')
    plt.show()

    # position = numpy.random.rand(3) * 2 - 1
    # position = [bounds[0] + bounds[1]-bounds[0] * position[0],
    #   bounds[2] + bounds[3]-bounds[2] * position[1],
    #   bounds[4] + bounds[5]-bounds[4] * position[2]]
    # normal = numpy.random.rand(3) * 2 - 1
    # normal = normal / numpy.linalg.norm(normal)
    # transverse = numpy.cross(normal, [0,0,1])

    # sliceRAS = sliceNode.GetSliceToRAS()
    # numpyRAS = slicer.util.arrayFromVTKMatrix(sliceRAS)
    # position = [numpyRAS[0,3], numpyRAS[1,3], numpyRAS[2,3]]
    # normal = [numpyRAS[0,2], numpyRAS[1,2], numpyRAS[2,2]]
    # transverse = [numpyRAS[0, 0], numpyRAS[1, 0], numpyRAS[2, 0]]
    # orientation = 0
    # print()
    # sliceNode.SetSliceToRASByNTP( normal[0], normal[1], normal[2],
    #   transverse[0], transverse[1], transverse[2],
    #   position[0], position[1], position[2],
    #   orientation)
###########################################################
#         Original example code (random slabs)            #
###########################################################

def randomSlices(volume, sliceCount, sliceShape):
  layoutManager = slicer.app.layoutManager()
  redWidget = layoutManager.sliceWidget("Red")
  sliceNode = redWidget.mrmlSliceNode()
  sliceNode.SetDimensions(*sliceShape, 1)
  sliceNode.SetFieldOfView(*sliceShape, 1)
  bounds = [0]*6
  volume.GetRASBounds(bounds)
  imageReslice = redWidget.sliceLogic().GetBackgroundLayer().GetReslice()

  sliceSize = sliceShape[0] * sliceShape[1]
  X = numpy.zeros([sliceCount, sliceSize])

  for sliceIndex in range(sliceCount):
    position = numpy.random.rand(3) * 2 - 1
    position = [bounds[0] + bounds[1]-bounds[0] * position[0],
      bounds[2] + bounds[3]-bounds[2] * position[1],
      bounds[4] + bounds[5]-bounds[4] * position[2]]
    normal = numpy.random.rand(3) * 2 - 1
    normal = normal / numpy.linalg.norm(normal)
    transverse = numpy.cross(normal, [0,0,1])
    orientation = 0
    sliceNode.SetSliceToRASByNTP( normal[0], normal[1], normal[2],
      transverse[0], transverse[1], transverse[2],
      position[0], position[1], position[2],
      orientation)
    if sliceIndex % 100 == 0:
      slicer.app.processEvents()
    imageReslice.Update()
    imageData = imageReslice.GetOutputDataObject(0)
    array = vtk.util.numpy_support.vtk_to_numpy(imageData.GetPointData().GetScalars())
    X[sliceIndex] = array
  return X