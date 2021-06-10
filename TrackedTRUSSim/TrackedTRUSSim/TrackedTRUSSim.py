import json
import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

import ScreenCapture
import numpy as np
from vtk.util.numpy_support import vtk_to_numpy
from Resources.Utils import GenerateFanMask
#
# TrackedTRUSSim
#

class TrackedTRUSSim(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "TrackedTRUSSim"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["Examples"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["John Doe (AnyWare Corp.)"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#TrackedTRUSSim">module documentation</a>.
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""


#
# TrackedTRUSSimWidget
#

class MainWidgetEventFilter(qt.QWidget):

  def __init__(self, moduleWidget):
    qt.QWidget.__init__(self)
    self.moduleWidget = moduleWidget

  def eventFilter(self, object, event):

    if self.moduleWidget.getSlicerInterfaceVisible():
      return False

    if event.type() == qt.QEvent.Close:
      #TODO: self.moduleWidget.confirmExit() 
      slicer.app.quit()
      return True

    return False


class TrackedTRUSSimWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  #Set names as class wide constants.
  IMAGE_TO_PROBE = "ImageToProbe"
  PROBE_TO_REFERENCE = "ProbeToReference"
  PROBEMODEL_TO_PROBE = 'ProbeModelToProbe'
  ROTATED_TO_PROBEMODEL = "RotatedToProbeModel"

  def __init__(self, parent=None):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.__init__(self, parent)


  def setup(self):
    """
    Called when the user opens the module the first time and the widget is initialized.
    """
    ScriptedLoadableModuleWidget.setup(self)

    # Load widget from .ui file (created by Qt Designer).
    # Additional widgets can be instantiated manually and added to self.layout.
    uiWidget = slicer.util.loadUI(self.resourcePath('UI/TrackedTRUSSim.ui'))
    self.layout.addWidget(uiWidget)
    self.ui = slicer.util.childWidgetVariables(uiWidget)

    #Set scene in MRML widgets
    uiWidget.setMRMLScene(slicer.mrmlScene)

    #Create logic class
    self.logic = TrackedTRUSSimLogic()
    self.logic.setup()

    #Connect UI
    self.ui.patientComboBox.currentIndexChanged.connect(self.onPatientComboBoxChanged)
    self.ui.biopsyDepthSlider.connect('sliderMoved(double)', self.onMoveBiopsy)
    self.ui.customUIButton.connect('toggled(bool)', self.onCustomUIToggled)
    self.ui.fireBiopsyButton.connect('clicked(bool)', self.onFireBiopsyClicked)
    # self.ui.Zones.connect('toggled(bool)', self.showZones)

    self.eventFilter = MainWidgetEventFilter(self)
    slicer.util.mainWindow().installEventFilter(self.eventFilter)

  def onCustomUIToggled(self, toggled):
    self.setSlicerInterfaceVisible(not toggled)
    print(toggled)

  def getSlicerInterfaceVisible(self):
    return not self.ui.customUIButton.checked

  def setSlicerInterfaceVisible(self, visible):

    slicer.util.setToolbarsVisible(visible)
    slicer.util.setApplicationLogoVisible(visible)
    slicer.util.setModuleHelpSectionVisible(visible)
    slicer.util.setModulePanelTitleVisible(visible)
    slicer.util.setDataProbeVisible(visible)
    slicer.util.setStatusBarVisible(visible)
    slicer.util.setMenuBarsVisible(visible)

  def onPatientComboBoxChanged(self):

    # get current patient
    patient = self.ui.patientComboBox.currentIndex

    # load the appropriate transforms
    self.logic.setupPatient(patient)

  def onMoveBiopsy(self):

    #Get the current location of the slider
    sliderVal = self.ui.biopsyDepthSlider.value

    self.logic.moveBiopsy(sliderVal)

  def onFireBiopsyClicked(self):

    self.logic.fireBiopsyNeedle()

    self.ui.biopsyDepthSlider.value = 0


#
# TrackedTRUSSimLogic
#

class TrackedTRUSSimLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  # Transform names
  REFERENCE_TO_RAS = "ReferenceToRAS"
  BOXMODEL_TO_REFERENCE = "BoxModelToReference"
  CYLINDER_TO_BOX = "CylinderToBox"
  TRUS_TO_CYLINDER = "TRUSToCylinder"
  PHANTOM_TO_REFERENCE = "PhantomToReference"
  PROBE_TO_PHANTOM = "ProbeToPhantom"
  PROBETIP_TO_PROBE = "ProbeTipToProbe"
  PROBEMODEL_TO_PROBETIP = "ProbeModelToProbeTip"
  USMASK_TO_PROBEMODEL = "USMaskToProbeModel"
  BIOPSYMODEL_TO_PROBEMODEL = "BiopsyModelToProbeModel"

  #PLUS related transforms
  POINTER_TO_PHANTOM = "PointerToPhantom"
  POINTERTIP_TO_POINTER = "PointerTipToPointer"

  #Model names
  PROBE_MODEL = "ProbeModel"
  BOX_MODEL = "BoxModel"
  CYLINDER_MODEL = "CylinderModel"
  TRUS_VOLUME = "TRUSVolume"
  ZONE_SEGMENTATION = "ZoneSegmentation"
  BIOPSY_MODEL = "BiopsyModel"

  #Volume names
  MASK_VOLUME = "MaskVolume"

  #OpenIGTLink PLUS connection
  CONFIG_FILE = "PlusDeviceSet_Server_Optitrak.xml"
  CONFIG_TEXT_NODE = "ConfigTextNode"
  PLUS_SERVER_NODE = "PlusServer"
  PLUS_SERVER_LAUNCHER_NODE = "PlusServerLauncher"

  #Various other node names
  BIOPSY_TRANSFORM_ROLES = "BiopsyTransformRoles"


  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)


  #custom layout to show 3D view and yellow slice
  def splitSliceViewer(self):

    customLayout = """
    <layout type="horizontal" split="true">
      <item>
       <view class="vtkMRMLViewNode" singletontag="1">
         <property name="viewlabel" action="default">1</property>
       </view>
      </item>
      <item>
       <view class="vtkMRMLSliceNode" singletontag="Red">
        <property name="orientation" action="default">Saggital</property>
        <property name="viewlabel" action="default">Y</property>
        <property name="viewcolor" action="default">#EDD54C</property>
       </view>
      </item>
    </layout>
    """

    # Built-in layout IDs are all below 100, so you can choose any large random number
    # for your custom layout ID.
    customLayoutId = 501

    layoutManager = slicer.app.layoutManager()
    layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(customLayoutId, customLayout)

    # Switch to the new custom layout
    layoutManager.setLayout(customLayoutId)


  def maskSlice(self):

    #Use screencap module logic to get slice view
    screenCapLogic = ScreenCapture.ScreenCaptureLogic()
    view = screenCapLogic.viewFromNode(slicer.util.getNode('vtkMRMLSliceNodeRed'))
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

    cv2.imshow("MASK", mask_int)
    cv2.imwrite("C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\Resources\\Utils\\US_Mask.png", mask)

    npImage[~mask] = [0,0,0]

    cv2.imshow("TEST", npImage)


  def moveBiopsy(self, biopsyDepth):

    #Get the parameter node and transform node
    parameterNode = self.getParameterNode()
    biopsyModelToProbeModel = parameterNode.GetNodeReference(self.BIOPSYMODEL_TO_PROBEMODEL)

    #Get the raw transform
    rawTransform = biopsyModelToProbeModel.GetMatrixTransformToParent()

    rawTransform.SetElement(2, 3, 269 + biopsyDepth)

    biopsyModelToProbeModel.SetMatrixTransformToParent(rawTransform)

    # transformStr = str(slicer.util.arrayFromTransformMatrix(biopsyModelToProbeModel))


  def fireBiopsyNeedle(self):
    '''
    When the biopsy needle is fired, the following occurs:
    1. The current value of the BiopsyNeedleToProbeModel transform is saved.
    2. The BiopsyNeedleToProbeModel transform, biopsy model and slider are moved back
        to their default locations.
    3. A label updated indicating that the biopsy was taken.
    '''

    #Get the parameter node
    parameterNode = self.getParameterNode()

    #Get relevant models / transforms
    biopsyModelToProbeModel = parameterNode.GetNodeReference(self.BIOPSYMODEL_TO_PROBEMODEL)
    biopsyTransformRolesNode = parameterNode.GetParameter(self.BIOPSY_TRANSFORM_ROLES)

    print(str(biopsyTransformRolesNode))

    #Load all previous biopsy names
    biopsyTransformRoles = []
    if biopsyTransformRolesNode is not '':
      biopsyTransformRoles = json.loads(biopsyTransformRolesNode)

    #Name the current one
    currBiopsyRole = "btr_" + str(len(biopsyTransformRoles))

    #Get a copy of the current biopsy transform
    transformCopy = biopsyModelToProbeModel.GetMatrixTransformToParent()

    #Add a duplicate transform to the scene
    biopsyTransformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", currBiopsyRole)
    biopsyTransformNode.SetMatrixTransformToParent(transformCopy)
    parameterNode.SetNodeReferenceID(currBiopsyRole, biopsyTransformNode.GetID())

    #Update the list of transform IDs
    biopsyTransformRoles = biopsyTransformRoles + [currBiopsyRole]
    biopsyTransformRoles = json.dumps(biopsyTransformRoles)
    parameterNode.SetParameter(self.BIOPSY_TRANSFORM_ROLES, biopsyTransformRoles)

    #Reset the value of biopsyModelToProbeModel after saving it
    self.moveBiopsy(0)


  def setup(self):
    """
    Setup the slicer scene.
    """

    #Get the current directory
    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)

    self.setupTransformHierarchy()
    self.splitSliceViewer()
    self.setupPlusServer()

    #Get the parameter node
    parameterNode = self.getParameterNode()

    #Create models

    boxModel = parameterNode.GetNodeReference(self.BOX_MODEL)
    boxModelPath = os.path.join(moduleDir, "Resources", "models", "BoxModel.vtk")
    if boxModel is None:
      boxModel =  slicer.util.loadModel(boxModelPath)
      boxModel.SetName(self.BOX_MODEL)
      parameterNode.SetNodeReferenceID(self.BOX_MODEL, boxModel.GetID())

    boxModelToReference = parameterNode.GetNodeReference(self.BOXMODEL_TO_REFERENCE)
    boxModel.SetAndObserveTransformNodeID(boxModelToReference.GetID())
    boxModel.GetDisplayNode().SetOpacity(0.5)
    boxModel.GetDisplayNode().SetColor(0,0,1)

    cylinderModel = parameterNode.GetNodeReference(self.CYLINDER_MODEL)
    cylinderModelPath = os.path.join(moduleDir, "Resources", "models", "CylinderModel.vtk")
    if cylinderModel is None:
      cylinderModel =  slicer.util.loadModel(cylinderModelPath)
      cylinderModel.SetName(self.CYLINDER_MODEL)
      parameterNode.SetNodeReferenceID(self.CYLINDER_MODEL, cylinderModel.GetID())

    cylinderToBox = parameterNode.GetNodeReference(self.CYLINDER_TO_BOX)
    cylinderModel.SetAndObserveTransformNodeID(cylinderToBox.GetID())
    cylinderModel.GetDisplayNode().SetOpacity(0.5)
    boxModel.GetDisplayNode().SetColor(0,0,1)

    probeModel = parameterNode.GetNodeReference(self.PROBE_MODEL)
    probeModelPath = os.path.join(moduleDir, "Resources", "models", "ProbeModel.stl")
    if probeModel is None:
      probeModel =  slicer.util.loadModel(probeModelPath)
      probeModel.SetName(self.PROBE_MODEL)
      parameterNode.SetNodeReferenceID(self.PROBE_MODEL, probeModel.GetID())

    probeToBox = parameterNode.GetNodeReference(self.PROBEMODEL_TO_PROBETIP)
    probeModel.SetAndObserveTransformNodeID(probeToBox.GetID())

    USMaskVolume = parameterNode.GetNodeReference(self.MASK_VOLUME)
    USMaskVolumePath = os.path.join(moduleDir, "Resources", "models", "USMask.png")
    if USMaskVolume is None:
      USMaskVolume =  slicer.util.loadVolume(USMaskVolumePath)
      USMaskVolume.SetName(self.MASK_VOLUME)
      parameterNode.SetNodeReferenceID(self.MASK_VOLUME, USMaskVolume.GetID())

    USMaskToProbeModel = parameterNode.GetNodeReference(self.USMASK_TO_PROBEMODEL)
    USMaskVolume.SetAndObserveTransformNodeID(USMaskToProbeModel.GetID())

    #Get the US Mask display node
    usDispNode = USMaskVolume.GetDisplayNode()
    usDispNode.SetLowerThreshold(10)
    usDispNode.SetUpperThreshold(600)

    biopsyModel = parameterNode.GetNodeReference(self.BIOPSY_MODEL)
    biopsyModelPath = os.path.join(moduleDir, "Resources", "models", "BiopsyModel.vtk")
    if biopsyModel is None:
      biopsyModel =  slicer.util.loadModel(biopsyModelPath)
      biopsyModel.SetName(self.BIOPSY_MODEL)
      parameterNode.SetNodeReferenceID(self.BIOPSY_MODEL, biopsyModel.GetID())

    biopsyModelToProbeModel = parameterNode.GetNodeReference(self.BIOPSYMODEL_TO_PROBEMODEL)
    biopsyModel.SetAndObserveTransformNodeID(biopsyModelToProbeModel.GetID())

    #Show the intersection between the biopsy and the red slice
    biopsyDispNode = biopsyModel.GetDisplayNode()
    biopsyDispNode.SliceIntersectionVisibilityOn()

  def setupResliceDriver(self):
    """
    Drive yellow slice based on position of pointer tip
    """
    parameterNode = self.getParameterNode()

    #Get the reslice logic class and yellow slice node
    resliceLogic = slicer.modules.volumereslicedriver.logic()
    sliceNode = slicer.app.layoutManager().sliceWidget("Red").mrmlSliceNode()

    #Set the mask as the driver and set the mode to transverse
    usMaskVolume = parameterNode.GetNodeReference(self.MASK_VOLUME)
    resliceLogic.SetDriverForSlice(usMaskVolume.GetID(), sliceNode)
    resliceLogic.SetModeForSlice(resliceLogic.MODE_TRANSVERSE, sliceNode)

    # resliceLogic.SetDriverForSlice()

  def setupTransformHierarchy(self):
    """
    Setup the transform nodes in the scene in if they don't exist yet
    """

    parameterNode = self.getParameterNode()

    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)

    referenceToRas = parameterNode.GetNodeReference(self.REFERENCE_TO_RAS)
    if referenceToRas is None:
      referenceToRas = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.REFERENCE_TO_RAS)
      parameterNode.SetNodeReferenceID(self.REFERENCE_TO_RAS, referenceToRas.GetID())

    boxModelToReference = parameterNode.GetNodeReference(self.BOXMODEL_TO_REFERENCE)
    if boxModelToReference is None:
      boxModelToReferencePath = os.path.join(moduleDir, "Resources", "transforms", "BoxModelToReference.h5")
      boxModelToReference = slicer.util.loadTransform(boxModelToReferencePath)
      parameterNode.SetNodeReferenceID(self.BOXMODEL_TO_REFERENCE, boxModelToReference.GetID())
    boxModelToReference.SetAndObserveTransformNodeID(referenceToRas.GetID())

    cylinderToBox = parameterNode.GetNodeReference(self.CYLINDER_TO_BOX)
    if cylinderToBox is None:
      cylinderToBoxPath = os.path.join(moduleDir, "Resources", "transforms", "CylinderToBox.h5")
      cylinderToBox = slicer.util.loadTransform(cylinderToBoxPath)
      parameterNode.SetNodeReferenceID(self.CYLINDER_TO_BOX, cylinderToBox.GetID())
    cylinderToBox.SetAndObserveTransformNodeID(boxModelToReference.GetID())

    phantomToReference = parameterNode.GetNodeReference(self.PHANTOM_TO_REFERENCE)
    if phantomToReference is None:
      phantomToReferencePath = os.path.join(moduleDir, "Resources", "transforms", "PhantomToReference.h5")
      phantomToReference = slicer.util.loadTransform(phantomToReferencePath)
      parameterNode.SetNodeReferenceID(self.PHANTOM_TO_REFERENCE, phantomToReference.GetID())
    phantomToReference.SetAndObserveTransformNodeID(referenceToRas.GetID())

    probeToPhantom = parameterNode.GetNodeReference(self.PROBE_TO_PHANTOM)
    if probeToPhantom is None:
      probeToPhantomPath = os.path.join(moduleDir, "Resources", "transforms", "ProbeToPhantom.h5")
      probeToPhantom = slicer.util.loadTransform(probeToPhantomPath)
      parameterNode.SetNodeReferenceID(self.PROBE_TO_PHANTOM, probeToPhantom.GetID())
    probeToPhantom.SetAndObserveTransformNodeID(phantomToReference.GetID())

    probeTipToProbe = parameterNode.GetNodeReference(self.PROBETIP_TO_PROBE)
    if probeTipToProbe is None:
      probeTipToProbePath = os.path.join(moduleDir, "Resources", "transforms", "ProbeTipToProbe.h5")
      probeTipToProbe = slicer.util.loadTransform(probeTipToProbePath)
      parameterNode.SetNodeReferenceID(self.PROBETIP_TO_PROBE, probeTipToProbe.GetID())
    probeTipToProbe.SetAndObserveTransformNodeID(probeToPhantom.GetID())

    probeModelToProbeTip = parameterNode.GetNodeReference(self.PROBEMODEL_TO_PROBETIP)
    if probeModelToProbeTip is None:
      probeModelToProbeTipPath = os.path.join(moduleDir, "Resources", "transforms", "ProbeModelToProbeTip.h5")
      probeModelToProbeTip = slicer.util.loadTransform(probeModelToProbeTipPath)
      parameterNode.SetNodeReferenceID(self.PROBEMODEL_TO_PROBETIP, probeModelToProbeTip.GetID())
    probeModelToProbeTip.SetAndObserveTransformNodeID(probeTipToProbe.GetID())

    USMaskToProbeModel = parameterNode.GetNodeReference(self.USMASK_TO_PROBEMODEL)
    if USMaskToProbeModel is None:
      USMaskToProbeModelPath = os.path.join(moduleDir, "Resources", "transforms", "USMaskToProbeModel.h5")
      USMaskToProbeModel = slicer.util.loadTransform(USMaskToProbeModelPath)
      parameterNode.SetNodeReferenceID(self.USMASK_TO_PROBEMODEL, USMaskToProbeModel.GetID())
    USMaskToProbeModel.SetAndObserveTransformNodeID(probeModelToProbeTip.GetID())

    BiopsyModelToProbeModel = parameterNode.GetNodeReference(self.BIOPSYMODEL_TO_PROBEMODEL)
    if BiopsyModelToProbeModel is None:
      BiopsyModelToProbeModelPath = os.path.join(moduleDir, "Resources", "transforms", "BiopsyModelToProbeModel.h5")
      BiopsyModelToProbeModel = slicer.util.loadTransform(BiopsyModelToProbeModelPath)
      parameterNode.SetNodeReferenceID(self.BIOPSYMODEL_TO_PROBEMODEL, BiopsyModelToProbeModel.GetID())
    BiopsyModelToProbeModel.SetAndObserveTransformNodeID(probeModelToProbeTip.GetID())

    #Add the transforms that are generated by the PLUS config file
    pointerToPhantom = parameterNode.GetNodeReference(self.POINTER_TO_PHANTOM)
    if pointerToPhantom is None:
      pointerToPhantom = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.POINTER_TO_PHANTOM)
      parameterNode.SetNodeReferenceID(self.POINTER_TO_PHANTOM, pointerToPhantom.GetID())
    pointerToPhantom.SetAndObserveTransformNodeID(phantomToReference.GetID())

    pointerTipToPointer = parameterNode.GetNodeReference(self.POINTERTIP_TO_POINTER)
    if pointerTipToPointer is None:
      pointerTipToPointerPath = os.path.join(moduleDir, "Resources", "transforms", "PointerTipToPointer.h5")
      pointerTipToPointer = slicer.util.loadTransform(pointerTipToPointerPath)
      parameterNode.SetNodeReferenceID(self.POINTERTIP_TO_POINTER, pointerTipToPointer.GetID())
    pointerTipToPointer.SetAndObserveTransformNodeID(pointerToPhantom.GetID())


  def setupPatient(self, patient):

    parameterNode = self.getParameterNode()

    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)

    #Load TRUSToCylinder transform
    trusToCylinder = parameterNode.GetNodeReference(self.TRUS_TO_CYLINDER)
    if trusToCylinder != None:
      slicer.mrmlScene.RemoveNode(trusToCylinder)
    trusToCylinderPath = os.path.join(moduleDir, "Resources", 'registered_zones', 'Patient_' + str(patient), 'TRUSToCylinder.h5')
    trusToCylinder = slicer.util.loadTransform(trusToCylinderPath)
    trusToCylinder.SetName(self.TRUS_TO_CYLINDER)
    parameterNode.SetNodeReferenceID(self.TRUS_TO_CYLINDER, trusToCylinder.GetID())

    #Add TRUSToCylinder into hierarchy
    cylinderToBox = parameterNode.GetNodeReference(self.CYLINDER_TO_BOX)
    trusToCylinder.SetAndObserveTransformNodeID(cylinderToBox.GetID())

    #Load the TRUS volume
    trusVolume = parameterNode.GetNodeReference(self.TRUS_VOLUME)
    if trusVolume != None:
      slicer.mrmlScene.RemoveNode(trusVolume)
    trusPath = os.path.join(moduleDir, "Resources", "registered_zones", "Patient_" + str(patient), "TRUS.nrrd")
    trusVolume = slicer.util.loadVolume(trusPath)
    trusVolume.SetName(self.TRUS_VOLUME)
    parameterNode.SetNodeReferenceID(self.TRUS_VOLUME, trusVolume.GetID())

    trusVolume.SetAndObserveTransformNodeID(trusToCylinder.GetID())

    #load zone segmentation
    seg = parameterNode.GetNodeReference(self.ZONE_SEGMENTATION)
    if seg != None:
      slicer.mrmlScene.RemoveNode(seg)
    zone_path = os.path.join(moduleDir, "Resources", 'registered_zones', 'Patient_' + str(patient), 'Zones.seg.nrrd')
    zoneNode = slicer.util.loadLabelVolume(zone_path)

    #Setup segmentation
    labelmapVolumeNode = zoneNode
    seg = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', self.ZONE_SEGMENTATION)
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, seg)
    seg.CreateClosedSurfaceRepresentation()
    slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
    segDisplay = seg.GetDisplayNode()
    segDisplay.SetVisibility(False)
    parameterNode.SetNodeReferenceID(self.ZONE_SEGMENTATION, seg.GetID())

    seg.SetAndObserveTransformNodeID(trusToCylinder.GetID())

    #Set the foreground and background of the red slice
    layoutManager = slicer.app.layoutManager()
    compositeNode = layoutManager.sliceWidget("Red").sliceLogic().GetSliceCompositeNode()
    usMaskVolume = parameterNode.GetNodeReference(self.MASK_VOLUME)
    compositeNode.SetBackgroundVolumeID(usMaskVolume.GetID())
    compositeNode.SetForegroundVolumeID(trusVolume.GetID())

    #Set the opacity to strictly show the foreground
    compositeNode.SetForegroundOpacity(1)

    self.setupResliceDriver()

    #Get the US Mask display node
    usMaskVolume = parameterNode.GetNodeReference(self.MASK_VOLUME)
    usDispNode = usMaskVolume.GetDisplayNode()

    #Apply a threshold that gets rid of the US fan but keeps the outline
    usDispNode.ApplyThresholdOn()
    usDispNode.SetLowerThreshold(50)
    usDispNode.SetUpperThreshold(600)

    #Recenter the red slice on the new content
    layoutManager.sliceWidget("Red").sliceLogic().FitSliceToAll()


  def setupPlusServer(self):
    """
    Creates PLUS server and OpenIGTLink connection if it doesn't exist already.
    """
    parameterNode = self.getParameterNode()

    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)
    configFullpath = os.path.join(moduleDir, "Resources", "plus", self.CONFIG_FILE)

    configTextNode = parameterNode.GetNodeReference(self.CONFIG_TEXT_NODE)
    if configTextNode is None:
      configTextNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTextNode", self.CONFIG_TEXT_NODE)
      configTextNode.SaveWithSceneOff()                                                             #What does this do?
      configTextNode.SetForceCreateStorageNode(slicer.vtkMRMLTextNode.CreateStorageNodeAlways)
      parameterNode.SetNodeReferenceID(self.CONFIG_TEXT_NODE, configTextNode.GetID())
    if not configTextNode.GetStorageNode():
      configTextNode.AddDefaultStorageNode()
    configTextStorageNode = configTextNode.GetStorageNode()
    configTextStorageNode.SaveWithSceneOff()
    configTextStorageNode.SetFileName(configFullpath)
    configTextStorageNode.ReadData(configTextNode)

    plusServerNode = parameterNode.GetNodeReference(self.PLUS_SERVER_NODE)
    if not plusServerNode:
      plusServerNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlusServerNode", self.PLUS_SERVER_NODE)
      plusServerNode.SaveWithSceneOff()
      parameterNode.SetNodeReferenceID(self.PLUS_SERVER_NODE, plusServerNode.GetID())
    plusServerNode.SetAndObserveConfigNode(configTextNode)

    plusServerLauncherNode = parameterNode.GetNodeReference(self.PLUS_SERVER_LAUNCHER_NODE)
    if not plusServerLauncherNode:
      plusServerLauncherNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLPlusServerLauncherNode", self.PLUS_SERVER_LAUNCHER_NODE)
      plusServerLauncherNode.SaveWithSceneOff()

    if plusServerLauncherNode.GetNodeReferenceID('plusServerRef') != plusServerNode.GetID():
      plusServerLauncherNode.AddAndObserveServerNode(plusServerNode)

#
# TrackedTRUSSimTest
#


class TrackedTRUSSimTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_TrackedTRUSSim1()

  def test_TrackedTRUSSim1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('TrackedTRUSSim1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = TrackedTRUSSimLogic()

    # Test algorithm with non-inverted threshold
    logic.process(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.process(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
