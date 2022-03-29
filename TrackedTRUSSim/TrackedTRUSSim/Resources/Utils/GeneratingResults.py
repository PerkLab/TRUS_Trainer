import numpy as np
import pandas as pd
import os, sys

def fidsToSTL(fids, outputPath, depth=5, width=5, showModel=True):
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(fids)
    pcd.estimate_normals()
    pcd.orient_normals_consistent_tangent_plane(100)
    poisson_mesh, _ = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=depth, width=width)
    o3d.visualization.draw_geometries([poisson_mesh])
    poisson_mesh = o3d.geometry.TriangleMesh.compute_triangle_normals(poisson_mesh)
    o3d.io.write_triangle_mesh(outputPath + "\\mesh.stl", poisson_mesh)

participants = ["Colton"]

resultsDir = "C:\\repos\\TRUS_Trainer\\TrackedTRUSSim\\TrackedTRUSSim\\TrialResults\\"
contentsOfDir = os.listdir(resultsDir)
allResults = pd.DataFrame(columns=['Participant','Volume','Trial',''])

allFolders = []
for f in contentsOfDir:
    if os.path.isdir(os.path.join(resultsDir,f)):
        allFolders.append(f)

for participant in allFolders:
    currPath = os.path.join(resultsDir,participant)

    allTrialFolders = os.listdir(currPath)
    trialNamesSplit = np.array([f.split("_") for f in allTrialFolders])

    volumes = np.unique(trialNamesSplit[:,2])
    trials = np.unique(trialNamesSplit[:,4])

    for volume in volumes:

        for trial in trials:

            resultsPath = os.path.join(resultsDir, "{}_Volume_{}_Trial_{}".format(participant,volume,trial))
            print(resultsPath)

            fids = np.load(os.path.join(resultsDir, "fiducials.npy"))

            fidsToSTL(fids, resultsPath)

            
