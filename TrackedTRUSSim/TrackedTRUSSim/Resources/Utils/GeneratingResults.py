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

            
