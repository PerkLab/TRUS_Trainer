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
from datetime import datetime
from glob import glob
from pathlib import Path

#
# TrackedTRUSSim
#

#TODO
#Change to cylinders to 1cm or 5mm in mask

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


#Reimplementation of the vtkMRMLScriptedModuleNode


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
      if self.moduleWidget.confirmExit():

        slicer.app.quit()
        return True
      else:
        event.ignore()
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

    #Get the path to module resources
    self.moduleDirPath = slicer.modules.trackedtrussim.path.replace("TrackedTRUSSim.py","")

    #Set scene in MRML widgets
    uiWidget.setMRMLScene(slicer.mrmlScene)

    #Create logic class
    self.logic = TrackedTRUSSimLogic()

    #Connect UI
    self.ui.userComboBox.currentIndexChanged.connect(self.onUserComboBoxChanged)
    self.ui.createUserButton.connect('clicked(bool)', self.createNewUserDialog)
    self.ui.loadBiopsyButton.connect('clicked(bool)', self.onLoadBiopsyButton)
    self.ui.biopsyDepthSlider.connect('valueChanged(double)', self.onMoveBiopsy)
    self.ui.customUIButton.connect('toggled(bool)', self.onCustomUIToggled)
    self.ui.fireBiopsyButton.connect('clicked(bool)', self.onFireBiopsyClicked)
    # self.ui.showZonesCheckbox.connect('stateChanged(int)', self.onShowZonesChecked)
    # self.ui.showBiopsyCheckbox.connect('stateChanged(int)', self.onShowBiopsyChecked)
    # self.ui.showModelsCheckbox.connect('stateChanged(int)', self.onShowModelsChecked)
    # self.ui.loadCaseButton.connect('clicked(bool)', self.onLoadCase)
    self.ui.saveBiopsyButton.connect('clicked(bool)', self.saveBiopsy)

    self.eventFilter = MainWidgetEventFilter(self)
    slicer.util.mainWindow().installEventFilter(self.eventFilter)

    #Populate the users combobox with all folder names in UserData
    self.updateUsersComboBox()

    #Open base models / transforms
    self.logic.setupParameterNode()

    #Setup icons
    self.placeIcons()

    #Ensure that all checkbox states

  def placeIcons(self):

    #Settings
    settingsIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/Settings.png')
    self.ui.customUIButton.setIcon(settingsIcon)

    #User
    userIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/User.png')
    self.ui.userCollapsibleButton.setIcon(userIcon)

    #Plus
    addUserIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/AddUser.png')
    self.ui.createUserButton.setIcon(addUserIcon)

    #Save
    saveFileIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/Save.png')
    self.ui.saveBiopsyButton.setIcon(saveFileIcon)

    ########
    #New case section

    #Case Number Label
    numberIcon = qt.QPixmap(self.moduleDirPath + '/Resources/Icons/Pound.png')
    self.ui.poundLabel.setPixmap(numberIcon)

    #Play Button
    playIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/Play.png')
    self.ui.playPauseButton.setIcon(playIcon)

    #Stop Button
    stopIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/Stop.png')
    self.ui.stopButton.setIcon(stopIcon)

    #Biopsy Depth Label
    measurementIcon = qt.QPixmap(self.moduleDirPath + '/Resources/Icons/Measure.png')
    self.ui.biopsyDepthLabel.setPixmap(measurementIcon)

    #Stop Button
    fireBiopsyIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/Place.png')
    self.ui.fireBiopsyButton.setIcon(fireBiopsyIcon)

    ########
    #New case section

    #Load Biopsy Button
    loadBiopsyIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/Review.png')
    self.ui.loadBiopsyButton.setIcon(loadBiopsyIcon)

    ########
    #View Control Section

    #View Toggle Button 1
    loadBiopsyIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/VisibilityOn.png')
    self.ui.viewToggleButton_1.setIcon(loadBiopsyIcon)

    #View Toggle Button 2
    self.ui.viewToggleButton_2.setIcon(loadBiopsyIcon)

    #View Toggle Button 3
    self.ui.viewToggleButton_3.setIcon(loadBiopsyIcon)

    ########

    #New Biopsy Tab Icon
    newBiopsyIcon = qt.QIcon(self.moduleDirPath + '/Resources/Icons/NewFile.png')
    self.ui.tab.setWindowIcon(newBiopsyIcon) ##

  def createNewUserDialog(self):

    #Create the basic window components
    self.userWidget = qt.QDialog()
    self.userWidget.setModal(True)
    self.userFrame = qt.QFrame(self.userWidget)
    self.userFrame.setStyleSheet(slicer.util.mainWindow().styleSheet)
    self.userWidget.setWindowTitle('Create New Username')
    popupGeometry = qt.QRect()
    mainWindow = slicer.util.mainWindow()

    #Adjust the geometry of the window if the main window is available as reference
    if mainWindow:
      windowWidth = mainWindow.width * 0.35
      windowHeight = mainWindow.height * 0.1
      popupGeometry.setWidth(windowWidth)
      popupGeometry.setHeight(windowHeight)
      self.userWidget.setGeometry(popupGeometry)
      self.userFrame.setGeometry(popupGeometry)
      self.userWidget.move(mainWindow.width / 2.0 - windowWidth,
                           mainWindow.height / 2 - windowHeight)
    userDialogLayout = qt.QVBoxLayout()
    userDialogLayout.setContentsMargins(12, 4, 4, 4)
    userDialogLayout.setSpacing(4)

    userDialogButtonLayout = qt.QFormLayout()
    userDialogButtonLayout.setContentsMargins(12, 4, 4, 4)
    userDialogButtonLayout.setSpacing(4)

    self.usernameLineEdit = qt.QLineEdit()
    userDialogButtonLayout.addRow(self.usernameLineEdit)

    self.createNewUsernameButton = qt.QPushButton("Create New Username")
    userDialogButtonLayout.addRow(self.createNewUsernameButton)

    self.createNewUsernameButton.connect('clicked(bool)', self.onNewUserCreatedButton)

    userDialogLayout.addLayout(userDialogButtonLayout)
    self.userFrame.setLayout(userDialogLayout)

    self.userWidget.open()
    self.userWidget.visible = True

  def onNewUserCreatedButton(self):

    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)
    newUserPath = os.path.join(moduleDir, "Resources", "UserData", self.usernameLineEdit.text)

    Path(newUserPath).mkdir(parents=True, exist_ok=True)

    #Close the dialog
    self.userWidget.close()
    self.userWidget.visible = False

    #Repopulate the user combobox
    self.updateUsersComboBox()


  def updateUsersComboBox(self):

    #Get the names of all user folders
    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)
    userDataPath = os.path.join(moduleDir, "Resources", "UserData")
    allUsers = [f.name for f in os.scandir(userDataPath) if f.is_dir()]

    #Clear the combo box and add all the newly found names
    self.ui.userComboBox.clear()
    for user in allUsers:
      self.ui.userComboBox.addItem(user)

    self.updateBiopsyComboBox()


  def updateBiopsyComboBox(self):

    #Get the names of all user folders
    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)
    userPath = os.path.join(moduleDir, "Resources", "UserData", self.ui.userComboBox.currentText)
    allBiopsies = [f.name for f in os.scandir(userPath)]

    #Clear the combo box and add all the newly found names
    self.ui.loadBiopsyComboBox.clear()
    for biopsy in allBiopsies:
      self.ui.loadBiopsyComboBox.addItem(biopsy)

  def onCustomUIToggled(self, toggled):

    self.setSlicerInterfaceVisible(not toggled)

    if toggled:
      styleFile = self.resourcePath("TrackedTRUSSim.qss")
      f = qt.QFile(styleFile)
      f.open(qt.QFile.ReadOnly | qt.QFile.Text)
      ts = qt.QTextStream(f)
      stylesheet = ts.readAll()
      slicer.util.mainWindow().setStyleSheet(stylesheet)
    else:
      slicer.util.mainWindow().setStyleSheet("")

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

  def onCaseComboBoxChanged(self):

    # get current case
    case = self.ui.caseComboBox.currentIndex

    # load the appropriate transforms
    self.logic.setupCase(case)

  def onUserComboBoxChanged(self):
    self.updateBiopsyComboBox()

  def onLoadBiopsyButton(self):
    self.logic.loadScene(self.ui.loadBiopsyComboBox.currentText, self.ui.userComboBox.currentText)

  def onLoadCase(self):
    self.logic.setupCase(self.ui.caseComboBox.currentIndex)

    self.onShowZonesChecked()

  def onShowModelsChecked(self):
    pass

  def onShowBiopsyChecked(self):
    pass

  def saveBiopsy(self):
    self.logic.saveScene(self.ui.biopsyNameLineEdit.text, self.ui.userComboBox.currentText)

    #update load biopsy combo box
    self.updateBiopsyComboBox()

  def onMoveBiopsy(self):

    #Get the current location of the slider
    sliderVal = self.ui.biopsyDepthSlider.value
    print("Slider value: " + str(sliderVal))

    self.logic.moveBiopsy(sliderVal)

  def onFireBiopsyClicked(self):

    self.logic.fireBiopsyNeedle()

    self.ui.biopsyDepthSlider.value = 0


  def onShowZonesChecked(self):

    showZonesState = self.ui.showZonesCheckbox.checked

    self.logic.changeZoneVisibility(showZonesState)

  def confirmExit(self):
    msgBox = qt.QMessageBox()
    msgBox.setStyleSheet(slicer.util.mainWindow().styleSheet)
    msgBox.setWindowTitle("Confirm exit")
    msgBox.setText("Are you sure you want to exit?")
    discardButton = msgBox.addButton("Exit", qt.QMessageBox.DestructiveRole)
    cancelButton = msgBox.addButton("Cancel", qt.QMessageBox.RejectRole)
    msgBox.setModal(True)
    msgBox.exec()

    if msgBox.clickedButton() == discardButton:
      return True
    else:
      return False


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
  BIOPSYTRAJECTORY_TO_PROBEMODEL = "BiopsyTrajectoryToProbeModel"
  BIOPSYMODEL_TO_BIOPSYTRAJECTORY = "BiopsyModelToBiopsyTrajectory"

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
  BIOPSY_TRAJECTORY_MODEL = "BiopsyTrajectoryModel"

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

    self.caseLoaded = False
    self.currCaseNumber = -1


  def saveScene(self, filename, currentUser):

    filename = filename + ".mrml"

    #only save the scene if a case is loaded
    if self.caseLoaded:

      #Create filename
      # date = datetime.now().strftime("%m%d%y_%H%M%S")
      # filename = "TRUSSimulator_Case{}_{}.mrml".format(self.currCaseNumber, date)

      #Append to current directory
      moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)
      biopsySavePath = os.path.join(moduleDir, "Resources", "UserData", currentUser, filename)

      print("save path: " + biopsySavePath)

      #save the scene to file
      slicer.util.saveScene(biopsySavePath)


  def loadScene(self, filename, currentUser):

    print("filename: " + filename)

    # Append to current directory
    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)
    biopsySavePath = os.path.join(moduleDir, "Resources", "UserData", currentUser, filename)

    print("biopsySavePath: " + biopsySavePath)

    # save the scene to file
    slicer.util.loadScene(biopsySavePath)

  #Redefine createParameterNode method.
  #This method is used to create a parameter node that will not be saved with the scene, and will
  #contain models / data that is shared across all cases within our module.
  def createParameterNode(self):

    node = ScriptedLoadableModuleLogic.createParameterNode(self)
    node.SetSaveWithScene(False) #Ensure that the parameter node is not saved with the scene
    return node


  #createCaseNode()
  #Used to store references to case specific data nodes, and is saved with the scene. This enables us to use the save / load
  #Slicer functions to save / load cases for the simulator, without saving unchanged data like models and static transforms
  def createCaseNode(self):

    node = slicer.mrmlScene.CreateNodeByClass('vtkMRMLScriptedModuleNode')
    node.UnRegister(None)
    node.SetAttribute('CaseNode', self.moduleName)
    node.SetSaveWithScene(True) #Save the parameter node with the scene
    node.SetName(self.moduleName + "_case")
    return node


  def getParameterNode(self):

    parameterNode = slicer.mrmlScene.GetSingletonNode(self.moduleName, "vtkMRMLScriptedModuleNode")
    if parameterNode:
      # After close scene, ModuleName attribute may be removed, restore it now
      if parameterNode.GetAttribute("ModuleName") != self.moduleName:
        parameterNode.SetAttribute("ModuleName", self.moduleName)
      return parameterNode

    parameterNode = slicer.mrmlScene.AddNode(self.createParameterNode())
    return parameterNode


  def getCaseNode(self):

    if self.caseLoaded:
      numberOfScriptedModuleNodes =  slicer.mrmlScene.GetNumberOfNodesByClass("vtkMRMLScriptedModuleNode")
      for nodeIndex in range(numberOfScriptedModuleNodes):
        node  = slicer.mrmlScene.GetNthNodeByClass( nodeIndex, "vtkMRMLScriptedModuleNode" )
        if node.GetName() == self.moduleName + "_case":
          return node

    else:
      # no parameter node was found for this module, therefore we add a new one now
      caseNode = slicer.mrmlScene.AddNode(self.createCaseNode())
      self.caseLoaded = True
      return caseNode


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
    BiopsyModelToBiopsyTrajectory = parameterNode.GetNodeReference(self.BIOPSYMODEL_TO_BIOPSYTRAJECTORY)

    #Get the raw transform
    rawTransform = BiopsyModelToBiopsyTrajectory.GetMatrixTransformToParent()

    rawTransform.SetElement(2, 3, biopsyDepth)

    BiopsyModelToBiopsyTrajectory.SetMatrixTransformToParent(rawTransform)

    # transformStr = str(slicer.util.arrayFromTransformMatrix(BiopsyModelToBiopsyTrajectory))


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
    caseNode = self.getCaseNode()

    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)

    #Get relevant models / transforms
    BiopsyModelToBiopsyTrajectory = parameterNode.GetNodeReference(self.BIOPSYMODEL_TO_BIOPSYTRAJECTORY)
    biopsyTransformRolesNode = caseNode.GetParameter(self.BIOPSY_TRANSFORM_ROLES)

    # print("biopsy transform roles node: " + str(biopsyTransformRolesNode))

    #Load all previous biopsy names
    biopsyTransformRoles = []
    if biopsyTransformRolesNode is not '':
      biopsyTransformRoles = json.loads(biopsyTransformRolesNode)

    # print("biopsyTransformRoles: " + str(biopsyTransformRoles))

    #Name the current one
    currBiopsyRole = "BiopsyModelToReference_" + str(len(biopsyTransformRoles))

    #Get a copy of the current biopsy transform
    biopsyModelToReferenceTransform = vtk.vtkMatrix4x4()
    BiopsyModelToBiopsyTrajectory.GetMatrixTransformToWorld(biopsyModelToReferenceTransform)

    #Add a duplicate transform to the scene
    biopsyModelToReferenceNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", currBiopsyRole)
    biopsyModelToReferenceNode.SetMatrixTransformToParent(biopsyModelToReferenceTransform)
    caseNode.SetNodeReferenceID(currBiopsyRole, biopsyModelToReferenceNode.GetID())

    #Create a biopsy cylinder and add it to the new transform
    biopsyModelPath = os.path.join(moduleDir, "Resources", "models", "BiopsyModel.vtk")
    biopsyModel =  slicer.util.loadModel(biopsyModelPath)
    biopsyModel.SetName("BiopsyModel_" + str(len(biopsyTransformRoles)))

    biopsyModel.SetAndObserveTransformNodeID(biopsyModelToReferenceNode.GetID())

    #Change the colour
    biopsyDispNode = biopsyModel.GetDisplayNode()
    biopsyDispNode.SetColor(1,0.5,0)
    biopsyDispNode.SliceIntersectionVisibilityOn()
    biopsyDispNode.SetSliceIntersectionOpacity(0.8)

    #Update the list of transform IDs
    biopsyTransformRoles = biopsyTransformRoles + [currBiopsyRole]
    biopsyTransformRoles = json.dumps(biopsyTransformRoles)
    caseNode.SetParameter(self.BIOPSY_TRANSFORM_ROLES, biopsyTransformRoles)

    biopsyTransformRolesNode = caseNode.GetParameter(self.BIOPSY_TRANSFORM_ROLES)

    # print("new biopsyTRansformRoles" + biopsyTransformRoles)
    # print("New transform roles node: " + str(biopsyTransformRoles))

    #Reset the value of BiopsyModelToBiopsyTrajectory after saving it
    self.moveBiopsy(0)

  def changeZoneVisibility(self, showZonesState):

    #Get the parameter node
    caseNode = self.getCaseNode()

    #Get the node for the segmentation
    zoneSegmentationNode = caseNode.GetNodeReference(self.ZONE_SEGMENTATION)

    #Get the display node and change the visibility
    zoneSegmentationDisplayNode = zoneSegmentationNode.GetDisplayNode()
    zoneSegmentationDisplayNode.SetVisibility(showZonesState)

  def visualizeBiopsies(self):
    '''
    This method will ensure that all transforms with the name "BiopsyModelToReference_X" are added to
    BiopsyModelToBiopsyTrajectory, as well as add a biopsy model to any that don't already have one.
    '''

    #Establish the location of the biopsy model file
    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)
    biopsyModelPath = os.path.join(moduleDir, "Resources", "models", "BiopsyModel.vtk")

    #Get the parameter node
    parameterNode = self.getParameterNode()
    caseNode = self.getCaseNode()

    #Get parameter containing all the role IDs
    biopsyTransformRolesNode = caseNode.GetParameter(self.BIOPSY_TRANSFORM_ROLES)

    print(str(biopsyTransformRolesNode))

    #If there are no biopsy transforms exit the function
    if biopsyTransformRolesNode is '':
      return

    #Read the list of biopsy transform roles
    biopsyTransformRoles = json.loads(biopsyTransformRolesNode)

    #Go through each biopsy transform role
    for idx, biopsyRole in enumerate(biopsyTransformRoles):

      #Get the transform for each biopsy role
      biopsyModelToReferenceNode = parameterNode.GetNodeReference(biopsyRole)

      #If the parent node isn't BiopsyModelToBiopsyTrajectory, change it
      # if biopsyModelToReferenceNode.GetParentTransformNode().GetName() is not "BiopsyModelToBiopsyTrajectory":
      #   biopsyModelToReferenceNode.SetAndObserveTransformNodeID(BiopsyModelToBiopsyTrajectory.GetID())

      #Check whether the biopsy model already exists
      biopsyModelName = "BiopsyModel_{}".format(idx)

      if slicer.mrmlScene.GetNodesByName(biopsyModelName).GetNumberOfItems() == 0:

        # Create a biopsy cylinder and add it to the new transform
        biopsyModel = slicer.util.loadModel(biopsyModelPath)
        biopsyModel.SetName(biopsyModelName)

        biopsyModel.SetAndObserveTransformNodeID(biopsyModelToReferenceNode.GetID())

        # Change the colour
        biopsyDispNode = biopsyModel.GetDisplayNode()
        biopsyDispNode.SetColor(0, 0.5, 0)


  def setupParameterNode(self):
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
    boxModel.GetDisplayNode().SetOpacity(0.1)
    boxModel.GetDisplayNode().SetColor(0,0,1)
    boxModel.SetSaveWithScene(False)

    cylinderModel = parameterNode.GetNodeReference(self.CYLINDER_MODEL)
    cylinderModelPath = os.path.join(moduleDir, "Resources", "models", "CylinderModel.vtk")
    if cylinderModel is None:
      cylinderModel =  slicer.util.loadModel(cylinderModelPath)
      cylinderModel.SetName(self.CYLINDER_MODEL)
      parameterNode.SetNodeReferenceID(self.CYLINDER_MODEL, cylinderModel.GetID())

    cylinderToBox = parameterNode.GetNodeReference(self.CYLINDER_TO_BOX)
    cylinderModel.SetAndObserveTransformNodeID(cylinderToBox.GetID())
    cylinderModel.GetDisplayNode().SetOpacity(0.1)
    cylinderModel.SetSaveWithScene(False)

    probeModel = parameterNode.GetNodeReference(self.PROBE_MODEL)
    probeModelPath = os.path.join(moduleDir, "Resources", "models", "ProbeModel.stl")
    if probeModel is None:
      probeModel =  slicer.util.loadModel(probeModelPath)
      probeModel.SetName(self.PROBE_MODEL)
      parameterNode.SetNodeReferenceID(self.PROBE_MODEL, probeModel.GetID())

    probeToBox = parameterNode.GetNodeReference(self.PROBEMODEL_TO_PROBETIP)
    probeModel.SetAndObserveTransformNodeID(probeToBox.GetID())
    probeModel.SetSaveWithScene(False)

    USMaskVolume = parameterNode.GetNodeReference(self.MASK_VOLUME)
    USMaskVolumePath = os.path.join(moduleDir, "Resources", "models", "USMask.png")
    if USMaskVolume is None:
      USMaskVolume =  slicer.util.loadVolume(USMaskVolumePath)
      USMaskVolume.SetName(self.MASK_VOLUME)
      parameterNode.SetNodeReferenceID(self.MASK_VOLUME, USMaskVolume.GetID())

    USMaskToProbeModel = parameterNode.GetNodeReference(self.USMASK_TO_PROBEMODEL)
    USMaskVolume.SetAndObserveTransformNodeID(USMaskToProbeModel.GetID())
    USMaskVolume.SetSaveWithScene(False)

    #Get the US Mask display node
    usDispNode = USMaskVolume.GetDisplayNode()
    usDispNode.SetLowerThreshold(10)
    usDispNode.SetUpperThreshold(600)

    #Load in the biopsy model
    biopsyModel = parameterNode.GetNodeReference(self.BIOPSY_MODEL)
    biopsyModelPath = os.path.join(moduleDir, "Resources", "models", "BiopsyModel.vtk")
    if biopsyModel is None:
      biopsyModel =  slicer.util.loadModel(biopsyModelPath)
      biopsyModel.SetName(self.BIOPSY_MODEL)
      parameterNode.SetNodeReferenceID(self.BIOPSY_MODEL, biopsyModel.GetID())

    BiopsyModelToBiopsyTrajectory = parameterNode.GetNodeReference(self.BIOPSYMODEL_TO_BIOPSYTRAJECTORY)
    biopsyModel.SetAndObserveTransformNodeID(BiopsyModelToBiopsyTrajectory.GetID())
    biopsyModel.SetSaveWithScene(False)

    #Show the intersection between the biopsy and the red slice
    biopsyDispNode = biopsyModel.GetDisplayNode()
    biopsyDispNode.SliceIntersectionVisibilityOn()
    biopsyDispNode.SetColor(1,0,0)

    #Load in the biopsy trajectory model
    biopsyTrajectoryModel = parameterNode.GetNodeReference(self.BIOPSY_TRAJECTORY_MODEL)
    biopsyTrajectoryModelPath = os.path.join(moduleDir, "Resources", "models", "BiopsyTrajectoryModel.stl")
    if biopsyTrajectoryModel is None:
      biopsyTrajectoryModel =  slicer.util.loadModel(biopsyTrajectoryModelPath)
      biopsyTrajectoryModel.SetName(self.BIOPSY_TRAJECTORY_MODEL)
      parameterNode.SetNodeReferenceID(self.BIOPSY_TRAJECTORY_MODEL, biopsyTrajectoryModel.GetID())

    BiopsyTrajectoryToProbeModel = parameterNode.GetNodeReference(self.BIOPSYTRAJECTORY_TO_PROBEMODEL)
    biopsyTrajectoryModel.SetAndObserveTransformNodeID(BiopsyTrajectoryToProbeModel.GetID())
    biopsyTrajectoryModel.SetSaveWithScene(False)

    #Show the intersection between the biopsy and the red slice
    biopsyTrajectoryDispNode = biopsyTrajectoryModel.GetDisplayNode()
    biopsyTrajectoryDispNode.SliceIntersectionVisibilityOn()
    biopsyTrajectoryDispNode.SetSliceIntersectionOpacity(0.8)
    biopsyTrajectoryDispNode.SetColor(0,1,0)

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
      referenceToRas.SetSaveWithScene(False)

    boxModelToReference = parameterNode.GetNodeReference(self.BOXMODEL_TO_REFERENCE)
    if boxModelToReference is None:
      boxModelToReferencePath = os.path.join(moduleDir, "Resources", "transforms", "BoxModelToReference.h5")
      boxModelToReference = slicer.util.loadTransform(boxModelToReferencePath)
      parameterNode.SetNodeReferenceID(self.BOXMODEL_TO_REFERENCE, boxModelToReference.GetID())
      boxModelToReference.SetSaveWithScene(False)
    boxModelToReference.SetAndObserveTransformNodeID(referenceToRas.GetID())

    cylinderToBox = parameterNode.GetNodeReference(self.CYLINDER_TO_BOX)
    if cylinderToBox is None:
      cylinderToBoxPath = os.path.join(moduleDir, "Resources", "transforms", "CylinderToBox.h5")
      cylinderToBox = slicer.util.loadTransform(cylinderToBoxPath)
      parameterNode.SetNodeReferenceID(self.CYLINDER_TO_BOX, cylinderToBox.GetID())
      cylinderToBox.SetSaveWithScene(False)
    cylinderToBox.SetAndObserveTransformNodeID(boxModelToReference.GetID())

    phantomToReference = parameterNode.GetNodeReference(self.PHANTOM_TO_REFERENCE)
    if phantomToReference is None:
      phantomToReferencePath = os.path.join(moduleDir, "Resources", "transforms", "PhantomToReference.h5")
      phantomToReference = slicer.util.loadTransform(phantomToReferencePath)
      parameterNode.SetNodeReferenceID(self.PHANTOM_TO_REFERENCE, phantomToReference.GetID())
      phantomToReference.SetSaveWithScene(False)
    phantomToReference.SetAndObserveTransformNodeID(referenceToRas.GetID())

    probeToPhantom = parameterNode.GetNodeReference(self.PROBE_TO_PHANTOM)
    if probeToPhantom is None:
      probeToPhantomPath = os.path.join(moduleDir, "Resources", "transforms", "ProbeToPhantom.h5")
      probeToPhantom = slicer.util.loadTransform(probeToPhantomPath)
      parameterNode.SetNodeReferenceID(self.PROBE_TO_PHANTOM, probeToPhantom.GetID())
      probeToPhantom.SetSaveWithScene(False)
    probeToPhantom.SetAndObserveTransformNodeID(phantomToReference.GetID())

    probeTipToProbe = parameterNode.GetNodeReference(self.PROBETIP_TO_PROBE)
    if probeTipToProbe is None:
      probeTipToProbePath = os.path.join(moduleDir, "Resources", "transforms", "ProbeTipToProbe.h5")
      probeTipToProbe = slicer.util.loadTransform(probeTipToProbePath)
      parameterNode.SetNodeReferenceID(self.PROBETIP_TO_PROBE, probeTipToProbe.GetID())
      probeTipToProbe.SetSaveWithScene(False)
    probeTipToProbe.SetAndObserveTransformNodeID(probeToPhantom.GetID())

    probeModelToProbeTip = parameterNode.GetNodeReference(self.PROBEMODEL_TO_PROBETIP)
    if probeModelToProbeTip is None:
      probeModelToProbeTipPath = os.path.join(moduleDir, "Resources", "transforms", "ProbeModelToProbeTip.h5")
      probeModelToProbeTip = slicer.util.loadTransform(probeModelToProbeTipPath)
      parameterNode.SetNodeReferenceID(self.PROBEMODEL_TO_PROBETIP, probeModelToProbeTip.GetID())
      probeModelToProbeTip.SetSaveWithScene(False)
    probeModelToProbeTip.SetAndObserveTransformNodeID(probeTipToProbe.GetID())

    USMaskToProbeModel = parameterNode.GetNodeReference(self.USMASK_TO_PROBEMODEL)
    if USMaskToProbeModel is None:
      USMaskToProbeModelPath = os.path.join(moduleDir, "Resources", "transforms", "USMaskToProbeModel.h5")
      USMaskToProbeModel = slicer.util.loadTransform(USMaskToProbeModelPath)
      parameterNode.SetNodeReferenceID(self.USMASK_TO_PROBEMODEL, USMaskToProbeModel.GetID())
      USMaskToProbeModel.SetSaveWithScene(False)
    USMaskToProbeModel.SetAndObserveTransformNodeID(probeModelToProbeTip.GetID())

    BiopsyTrajectoryToProbeModel = parameterNode.GetNodeReference(self.BIOPSYTRAJECTORY_TO_PROBEMODEL)
    if BiopsyTrajectoryToProbeModel is None:
      BiopsyTrajectoryToProbeModelPath = os.path.join(moduleDir, "Resources", "transforms", "BiopsyTrajectoryToProbeModel.h5")
      BiopsyTrajectoryToProbeModel = slicer.util.loadTransform(BiopsyTrajectoryToProbeModelPath)
      parameterNode.SetNodeReferenceID(self.BIOPSYTRAJECTORY_TO_PROBEMODEL, BiopsyTrajectoryToProbeModel.GetID())
      BiopsyTrajectoryToProbeModel.SetSaveWithScene(False)
    BiopsyTrajectoryToProbeModel.SetAndObserveTransformNodeID(probeModelToProbeTip.GetID())

    BiopsyModelToBiopsyTrajectory = parameterNode.GetNodeReference(self.BIOPSYMODEL_TO_BIOPSYTRAJECTORY)
    if BiopsyModelToBiopsyTrajectory is None:
      BiopsyModelToBiopsyTrajectoryPath = os.path.join(moduleDir, "Resources", "transforms", "BiopsyModelToBiopsyTrajectory.h5")
      BiopsyModelToBiopsyTrajectory = slicer.util.loadTransform(BiopsyModelToBiopsyTrajectoryPath)
      parameterNode.SetNodeReferenceID(self.BIOPSYMODEL_TO_BIOPSYTRAJECTORY, BiopsyModelToBiopsyTrajectory.GetID())
      BiopsyModelToBiopsyTrajectory.SetSaveWithScene(False)
    BiopsyModelToBiopsyTrajectory.SetAndObserveTransformNodeID(BiopsyTrajectoryToProbeModel.GetID())

    #Add the transforms that are generated by the PLUS config file
    pointerToPhantom = parameterNode.GetNodeReference(self.POINTER_TO_PHANTOM)
    if pointerToPhantom is None:
      pointerToPhantom = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLinearTransformNode", self.POINTER_TO_PHANTOM)
      parameterNode.SetNodeReferenceID(self.POINTER_TO_PHANTOM, pointerToPhantom.GetID())
      pointerToPhantom.SetSaveWithScene(False)
    pointerToPhantom.SetAndObserveTransformNodeID(phantomToReference.GetID())

    pointerTipToPointer = parameterNode.GetNodeReference(self.POINTERTIP_TO_POINTER)
    if pointerTipToPointer is None:
      pointerTipToPointerPath = os.path.join(moduleDir, "Resources", "transforms", "PointerTipToPointer.h5")
      pointerTipToPointer = slicer.util.loadTransform(pointerTipToPointerPath)
      parameterNode.SetNodeReferenceID(self.POINTERTIP_TO_POINTER, pointerTipToPointer.GetID())
      pointerTipToPointer.SetSaveWithScene(False)
    pointerTipToPointer.SetAndObserveTransformNodeID(pointerToPhantom.GetID())


  def setupCase(self, case):

    self.currCaseNumber = case

    parameterNode = self.getParameterNode()
    caseNode = self.getCaseNode()

    print("casenode: ")

    moduleDir = os.path.dirname(slicer.modules.trackedtrussim.path)

    #Load TRUSToCylinder transform
    trusToCylinder = caseNode.GetNodeReference(self.TRUS_TO_CYLINDER)
    if trusToCylinder != None:
      slicer.mrmlScene.RemoveNode(trusToCylinder)
    trusToCylinderPath = os.path.join(moduleDir, "Resources", 'registered_zones', 'Patient_' + str(case), 'TRUSToCylinder.h5')
    trusToCylinder = slicer.util.loadTransform(trusToCylinderPath)
    trusToCylinder.SetName(self.TRUS_TO_CYLINDER)
    caseNode.SetNodeReferenceID(self.TRUS_TO_CYLINDER, trusToCylinder.GetID())

    #Add TRUSToCylinder into hierarchy
    cylinderToBox = parameterNode.GetNodeReference(self.CYLINDER_TO_BOX)
    trusToCylinder.SetAndObserveTransformNodeID(cylinderToBox.GetID())

    #Load the TRUS volume
    trusVolume = caseNode.GetNodeReference(self.TRUS_VOLUME)
    if trusVolume != None:
      slicer.mrmlScene.RemoveNode(trusVolume)
    trusPath = os.path.join(moduleDir, "Resources", "registered_zones", "Patient_" + str(case), "TRUS.nrrd")
    trusVolume = slicer.util.loadVolume(trusPath)
    trusVolume.SetName(self.TRUS_VOLUME)
    caseNode.SetNodeReferenceID(self.TRUS_VOLUME, trusVolume.GetID())

    trusVolume.SetAndObserveTransformNodeID(trusToCylinder.GetID())

    #load zone segmentation
    seg = caseNode.GetNodeReference(self.ZONE_SEGMENTATION)
    if seg != None:
      slicer.mrmlScene.RemoveNode(seg)
    zone_path = os.path.join(moduleDir, "Resources", 'registered_zones', 'Patient_' + str(case), 'Zones.seg.nrrd')
    zoneNode = slicer.util.loadLabelVolume(zone_path)

    #Setup segmentation
    labelmapVolumeNode = zoneNode
    seg = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', self.ZONE_SEGMENTATION)
    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapVolumeNode, seg)
    seg.CreateClosedSurfaceRepresentation()
    slicer.mrmlScene.RemoveNode(labelmapVolumeNode)
    segDisplay = seg.GetDisplayNode()
    segDisplay.SetVisibility(False)
    segDisplay.SetOpacity(0.3)
    caseNode.SetNodeReferenceID(self.ZONE_SEGMENTATION, seg.GetID())

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
