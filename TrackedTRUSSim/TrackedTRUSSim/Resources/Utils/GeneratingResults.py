import numpy as np
import pandas as pd
import os, sys
import open3d as o3d

def fidsToSTL(fids, outputPath, depth=5, width=5, showModel=True):
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(fids)
    pcd.estimate_normals()
    pcd.orient_normals_consistent_tangent_plane(100)
    poisson_mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=depth, width=width)
    o3d.visualization.draw_geometries([poisson_mesh])
    poisson_mesh = o3d.geometry.TriangleMesh.compute_triangle_normals(poisson_mesh)
    o3d.io.write_triangle_mesh(outputPath + "\\ProstateModel.stl", poisson_mesh)

def generateResults():

    participants = ["Colton"]

    resultsDir = "C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\TrialResults\\"
    groundtruthDir = "C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\Resources\\registered_zones\\"
    contentsOfDir = os.listdir(resultsDir)
    resultsDF = pd.DataFrame(columns=['Participant','Volume','Trial','TruePositive','TrueNegative',
                                       'FalsePositive','FalseNegative', 'Recall','Specificity',
                                       'Precision','DiceScore'])

    allFolders = []
    for f in contentsOfDir:
        if os.path.isdir(os.path.join(resultsDir,f)):
            allFolders.append(f)

    #Load in all 3 scans that we need
    trus1Path = os.path.join(groundtruthDir, "Patient_8", "TRUS.nrrd")
    trus1Volume = slicer.util.loadVolume(trus1Path)
    trus1Volume.SetName("TRUSVolume_1")

    trus2Path = os.path.join(groundtruthDir, "Patient_9", "TRUS.nrrd")
    trus2Volume = slicer.util.loadVolume(trus2Path)
    trus2Volume.SetName("TRUSVolume_2")

    trus3Path = os.path.join(groundtruthDir, "Patient_10", "TRUS.nrrd")
    trus3Volume = slicer.util.loadVolume(trus3Path)
    trus3Volume.SetName("TRUSVolume_3")

    allTrusNodes = [trus1Volume, trus2Volume, trus3Volume]

    #Generate the neccesary transform to move the open3d model to the volume
    trialTransform = slicer.util.loadTransform(os.path.join(resultsDir, 'open3dModelToReference.h5'))

    for participant in allFolders:
        currPath = os.path.join(resultsDir,participant)

        allTrialFolders = os.listdir(currPath)
        trialNamesSplit = np.array([f.split("_") for f in allTrialFolders])

        volumes = np.unique(trialNamesSplit[:,2])
        trials = np.unique(trialNamesSplit[:,4])

        i = 0

        for volume in volumes:

            gtModelPath = groundtruthDir + "Patient_{}".format(volume+7) + "\\GroundtruthModel.stl"

            #Load in the current volume
            vol = allTrusNodes[i]

            for trial in trials:

                #Generate a model
                resultsPath = os.path.join(resultsDir, "{}_Volume_{}_Trial_{}".format(participant,volume,trial))
                fids = np.load(os.path.join(resultsDir, "fiducials.npy"))
                fidsToSTL(fids, resultsPath)

                #Load the trial model and transform
                trialModelPath = resultsPath + "\\ProstateModel.stl"
                trialModel = slicer.util.loadModel(trialModelPath)
                trialModel.SetName("TrialModel")
                trialModel.SetAndObserveTransformNodeID(trialTransform.GetID())
                trialModel.HardenTransform()

                gtModel = slicer.util.loadModel(gtModelPath)
                gtModel.SetName("GroundTruthModel")

                A = arrayFromVolume(vol)

                # Generate the binary array for the trial model
                segTrial = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
                segTrial.SetName("TrialModelSegmentation")

                segLogTrial = slicer.modules.segmentations.logic()
                segTrial.SetReferenceImageGeometryParameterFromVolumeNode(vol)
                segLogTrial.ImportModelToSegmentationNode(trialModel, segTrial)
                segTrial.SetReferenceImageGeometryParameterFromVolumeNode(vol)

                LabelMapTrial = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
                LabelMapTrial.SetName("TrialModelSegmentation")
                segLogTrial.ExportVisibleSegmentsToLabelmapNode(segTrial, LabelMapTrial, vol)

                segTrialArray = slicer.util.arrayFromVolume(LabelMapTrial)

                # Generate the binary array for the groundtruth model
                segGT = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode')
                segGT.SetName("segModelSegmentation")

                segLogGT = slicer.modules.segmentations.logic()
                segGT.SetReferenceImageGeometryParameterFromVolumeNode(vol)
                segLogGT.ImportModelToSegmentationNode(gtModel, segGT)
                segGT.SetReferenceImageGeometryParameterFromVolumeNode(vol)

                LabelMapGT = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode')
                LabelMapGT.SetName("GTModelSegmentation")
                segLogGT.ExportVisibleSegmentsToLabelmapNode(segGT, LabelMapGT, vol)

                segGTArray = slicer.util.arrayFromVolume(LabelMapGT)

                # Get key stats for metrics
                true_pos = sum(sum(sum(np.logical_and(segGTArray == 1, segTrialArray == 1))))
                true_neg = sum(sum(sum(np.logical_and(segGTArray == 0, segTrialArray == 0))))
                false_pos = sum(sum(sum(np.logical_and(segGTArray == 1, segTrialArray == 0))))
                false_neg = sum(sum(sum(np.logical_and(segGTArray == 0, segTrialArray == 1))))

                recall = true_pos / (true_pos + false_neg)
                specificity = true_neg / (true_neg + false_pos)
                precision = true_pos / (true_pos + false_pos)

                intersection = sum(sum(sum(np.logical_and(segGTArray, segTrialArray))))

                dice_score = 2. * intersection.sum() / (segGTArray.sum() + segTrialArray.sum())

                resultsRow = [participant, volume, trial, true_pos, true_neg, false_pos, false_neg,
                              recall, specificity, precision,dice_score ]

                resultsDF.loc[0 if pd.isnull(df.index.max()) else df.index.max() + 1] = resultsRow

        i = i + 1

    resultsCSVPath = "C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\TrialResults\\results.csv"
    resultsDF.to_csv(resultsCSVPath)

    slicer.mrmlScene.RemoveNode(trus1Volume)
    slicer.mrmlScene.RemoveNode(trus2Volume)
    slicer.mrmlScene.RemoveNode(trus3Volume)
    slicer.mrmlScene.RemoveNode(trialTransform)


# trialModelPath = "C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\TrialResults\\1\\1_Volume_2_Trial_1\\mesh.stl"
# gtModelPath = "C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\Resources\\registered_zones\\Patient_9\\GroundtruthModel.stl"
# vol = getNode("TRUS")

self = slicer.mymod
self.generateResults()