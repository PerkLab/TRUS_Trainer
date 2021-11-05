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
    sliceShape = sliceNode.GetDimensions()
    bounds = [0]*6
    volume.GetRASBounds(bounds)
    sliceNode.SetDimensions(*sliceShape)
    # sliceNode.SetFieldOfView(*sliceShape)
    imageReslice = redWidget.sliceLogic().GetBackgroundLayer().GetReslice()
    imageReslice.Update()
    imageData = imageReslice.GetOutputDataObject(0)
    array = vtk.util.numpy_support.vtk_to_numpy(imageData.GetPointData().GetScalars())
    print("Sliceshape: " + str(sliceShape))
    print("array shape: " + str(array.shape))
    npImage = array.reshape(sliceShape[1],sliceShape[0])
    return npImage

def createVolumeSlice(imageData, imageSpacing, nodeName="MyNewVolume"):
    print("Image data shape: " + str(imageData.shape))
    vtkGrayscale = numpy_support.numpy_to_vtk(imageData.flatten(order='C'), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)
    #Convert the image to vtkImageData object
    sliceImageData = vtk.vtkImageData()
    sliceImageData.SetDimensions(len(imageData[0]), len(imageData), 1)
    sliceImageData.SetOrigin(0.0, 0.0, 0.0)
    sliceImageData.GetPointData().SetScalars(vtkGrayscale)
    imageOrigin = [0, 0, 0]
    imageDirections = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    print("Slice image data: " + str(sliceImageData.GetDimensions()))
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

    position = numpy.random.rand(3) * 2 - 1
    position = [bounds[0] + bounds[1]-bounds[0] * position[0],
      bounds[2] + bounds[3]-bounds[2] * position[1],
      bounds[4] + bounds[5]-bounds[4] * position[2]]
    normal = numpy.random.rand(3) * 2 - 1
    normal = normal / numpy.linalg.norm(normal)
    transverse = numpy.cross(normal, [0,0,1])

    sliceRAS = sliceNode.GetSliceToRAS()
    numpyRAS = slicer.util.arrayFromVTKMatrix(sliceRAS)
    position = [numpyRAS[0,3], numpyRAS[1,3], numpyRAS[2,3]]
    position = [bounds[0] + bounds[1]-bounds[0] * position[0],
      bounds[2] + bounds[3]-bounds[2] * position[1],
      bounds[4] + bounds[5]-bounds[4] * position[2]]
    normal = [numpyRAS[0,2], numpyRAS[1,2], numpyRAS[2,2]]
    transverse = [numpyRAS[0, 0], numpyRAS[1, 0], numpyRAS[2, 0]]
    orientation = 0
    sliceNode.SetSliceToRASByNTP( normal[0], normal[1], normal[2],
      transverse[0], transverse[1], transverse[2],
      position[0], position[1], position[2],
      orientation)
###########################################################
#         Original example code (random slabs)            #
###########################################################

sliceShape = slicer.app.layoutManager().sliceWidget("Red").mrmlSliceNode().GetDimensions()[:2]
volume = slicer.util.GetNode('TRUS')


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

###########################################################
#         Step by step version         #
###########################################################

#Get the bounds of the volume
TRUSVolumeNode = getNode('TRUSVolume')
bounds = [0] * 6
TRUSVolumeNode.GetRASBounds(bounds)

#Get the matrix that defines the Image plane relative to the TRUS volume
ImageToProbe = getNode('ImageToProbe')
ImageToWorld = vtk.vtkGeneralTransform()
ImageToProbe.GetTransformToWorld(ImageToWorld)

#Set the settings for the vtkImageReslice driver
reslice = vtk.vtkImageReslice()
reslice.SetBackgroundColor(0, 0, 0, 0)
reslice.AutoCropOutputOff()
reslice.SetOptimization(1)
reslice.SetOutputOrigin( 0, 0, 0 )
reslice.SetOutputSpacing( 1, 1, 1)
reslice.SetOutputDimensionality( 3 )
reslice.GenerateStencilOutputOn()
reslice.SetResliceTransform(ImageToWorld)
reslice.SetOutputExtent(int(bounds[0]), int(bounds[1]), int(bounds[2]), int(bounds[3]), int(bounds[4]), int(bounds[5]))
reslice.SetInterpolationModeToNearestNeighbor()
reslice.SetInputData(TRUSVolumeNode.GetImageData())
reslice.Update()

#Get the reslice point data
resliceOutput_ptData = reslice.GetOutput().GetPointData()

def mergeVolumes(self, volumeList):
    # Get bounds of final volume
    bounds = np.zeros((len(volumeList), 6))
    for i in range(len(volumeList)):
        volumeList[i].GetSliceBounds(bounds[i, :], None)
    min = bounds.min(0)
    max = bounds.max(0)
    volumeBounds_ROI = np.array([min[0], max[1], min[2], max[3], min[4], max[5]])
    outputSpacing = 0.4
    roiDim = np.zeros(3)
    for i in range(3):
        roiDim[i] = (volumeBounds_ROI[i * 2 + 1] - volumeBounds_ROI[i * 2]) / outputSpacing;
    roiDim = np.ceil(roiDim).astype('uint16')
    out = slicer.util.getFirstNodeByName('Stitched-Output')
    if not out or not out.GetName() == 'Stitched-Output':
        out = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLScalarVolumeNode', 'Stitched-Output')
    out.SetOrigin(volumeBounds_ROI[0], volumeBounds_ROI[2], volumeBounds_ROI[4])
    out.SetSpacing([outputSpacing] * 3)
    # Create accumulator image initialized to 0 to populate with final max values
    maxImage = vtk.vtkImageData()
    maxImage.SetOrigin(0,0,0)
    maxImage.SetSpacing(1, 1, 1)
    maxImage.SetExtent(0, roiDim[0], 0, roiDim[1], 0, roiDim[2])
    maxImage.AllocateScalars(vtk.VTK_UNSIGNED_CHAR,0)
    # for each volume, resample into output space
    # will need to do for each frame in sequence as well
    for i in range(len(volumeList)):
        n = volumeList[i]
        # Get transforms for input and output volumes
        inputIJK2RASMatrix = vtk.vtkMatrix4x4()
        n.GetIJKToRASMatrix(inputIJK2RASMatrix)
        referenceRAS2IJKMatrix = vtk.vtkMatrix4x4()
        out.GetRASToIJKMatrix(referenceRAS2IJKMatrix)
        inputRAS2RASTransform = vtk.vtkGeneralTransform()
        if n.GetTransformNodeID():
            slicer.mrmlScene.GetNodeByID(n.GetTransformNodeID()).GetTransformToWorld(inputRAS2RASTransform)
        # Create resample transform from reference volume to input
        resampleTransform = vtk.vtkGeneralTransform()
        resampleTransform.Identity()
        resampleTransform.PostMultiply()
        resampleTransform.Concatenate(inputIJK2RASMatrix)
        resampleTransform.Concatenate(inputRAS2RASTransform)
        resampleTransform.Concatenate(referenceRAS2IJKMatrix)
        resampleTransform.Inverse()
        # Resample the image to the output space using transform
        resampler = vtk.vtkImageReslice()
        resampler.SetInputConnection(n.GetImageDataConnection())
        resampler.SetOutputOrigin(0, 0, 0)
        resampler.SetOutputSpacing(1, 1, 1)
        resampler.SetOutputExtent(0, roiDim[0], 0, roiDim[1], 0, roiDim[2])
        resampler.SetResliceTransform(resampleTransform)
        resampler.SetInterpolationModeToCubic()
        resampler.SetOutputScalarType(vtk.VTK_UNSIGNED_CHAR)
        resampler.Update()
        # Take maximum value
        mathFilter = vtk.vtkImageMathematics()
        mathFilter.SetOperationToMax()
        mathFilter.SetInput1Data(maxImage)
        mathFilter.SetInput2Data(resampler.GetOutput())
        mathFilter.Update()
        maxImage.DeepCopy(mathFilter.GetOutput())
    # Set output volume
    out.SetAndObserveImageData(maxImage)