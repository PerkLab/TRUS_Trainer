import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin

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

    #Connect UI
    self.ui.patientComboBox.currentIndexChanged.connect(self.make_scene)
    self.ui.customUIButton.connect('toggled(bool)', self.onCustomUIToggled)   
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

  def make_scene(self):

    # set up slicer scene
    slicer.mrmlScene.Clear()
    patient = self.ui.patientComboBox.currentIndex

    #Load the scene for the current patient
    scene = self.resourcePath('scene'+ str(patient) + '.mrb')
    slicer.util.loadScene(scene)

    TRUSVolume = slicer.mrmlScene.GetFirstNodeByName("TRUS")
    ProbeModel = slicer.mrmlScene.GetFirstNodeByName("USProbe")
    BoxModel = slicer.mrmlScene.GetFirstNodeByName("BoxModel")
    CylinderModel = slicer.mrmlScene.GetFirstNodeByName("CylinderModel")
    zoneNode = slicer.mrmlScene.GetFirstNodeByName("Segmentation")
    self.splitSliceViewer()  # get the yellow slice

    #load TRUS
    if TRUSVolume is None:
      US_path = self.resourcePath('registered_zones/Patient_' + str(patient) + '/TRUS.nrrd')
      TRUSVolume = slicer.util.loadVolume(US_path)
      print(TRUSVolume)
    #load probe
    if ProbeModel is None:
      probe_path = self.resourcePath('ProbeModel.stl')
      ProbeModel = slicer.util.loadModel(probe_path)
    #load zone segmentation
    if zoneNode is None:
      zone_path = self.resourcePath('registered_zones/Patient_' + str(patient) + '/Zones.seg.nrrd')
      zoneNode = slicer.util.loadLabelVolume(zone_path)
    #load box model
    if BoxModel is None:
      box_path = self.resourcePath('BoxModel.vtk')
      BoxModel = slicer.util.loadModel(box_path)
    # load cylinder model
    if CylinderModel is None:
      cylinder_path = self.resourcePath('CylinderModel.vtk')
      CylinderModel = slicer.util.loadModel(cylinder_path)

    #Setup segmentation
    labelmapVolumeNode = zoneNode
    seg = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, seg)
    seg.CreateClosedSurfaceRepresentation()
    slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
    segDisplay = seg.GetDisplayNode()
    segDisplay.SetVisibility(False)

    # create and name all transforms
    BoxModelToRAS = slicer.mrmlScene.GetFirstNodeByName("BoxModelToRAS")
    CylinderToBox = slicer.mrmlScene.GetFirstNodeByName("CylinderToBox")
    TRUSToCylinder = slicer.mrmlScene.GetFirstNodeByName("TRUSToCylinder")
    PhantomToBoxModel = slicer.mrmlScene.GetFirstNodeByName("PhantomToBoxModel")
    ProbeToPhantom = slicer.mrmlScene.GetFirstNodeByName("ProbeToPhantom")
    ProbeTipToProbe = slicer.mrmlScene.GetFirstNodeByName("ProbeTipToProbe")
    ProbeModelToProbeTip = slicer.mrmlScene.GetFirstNodeByName("ProbeModelToProbeTip")

    # Create hierarchy for phantom visualization
    TRUSVolume.SetAndObserveTransformNodeID(TRUSToCylinder.GetID())
    zoneNode.SetAndObserveTransformNodeID(TRUSToCylinder.GetID())
    CylinderModel.SetAndObserveTransformNodeID(CylinderToBox.GetID())
    TRUSToCylinder.SetAndObserveTransformNodeID(CylinderToBox.GetID())
    BoxModel.SetAndObserveTransformNodeID(BoxModelToRAS.GetID())
    CylinderToBox.SetAndObserveTransformNodeID(BoxModelToRAS.GetID())

    #Create hierarchy for probe visualization
    ProbeModel.SetAndObserveTransformNodeID(ProbeModelToProbeTip.GetID())
    ProbeModelToProbeTip.SetAndObserveTransformNodeID(ProbeTipToProbe.GetID())
    ProbeTipToProbe.SetAndObserveTransformNodeID(ProbeToPhantom.GetID())
    ProbeToPhantom.SetAndObserveTransformNodeID(PhantomToBoxModel.GetID())

    # Clean up extra camera nodes
    for i in range(3):
      camera = slicer.mrmlScene.GetFirstNodeByClass('vtkMRMLCameraNode')
      slicer.mrmlScene.RemoveNode(camera)

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
       <view class="vtkMRMLSliceNode" singletontag="Yellow">
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

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)


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
