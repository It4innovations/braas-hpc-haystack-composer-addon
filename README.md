# BRaaS-HPC-HayStack Composer

A Blender addon that provides a node-based visual interface for composing and generating [HayStack](https://github.com/ingowald/haystack) rendering commands. This addon enables users to create complex scientific visualization workflows through an intuitive node editor.

## Overview

**BRaaS-HPC-HayStack Composer** is a Blender addon developed by IT4Innovations National Supercomputing Center for creating [HayStack](https://github.com/ingowald/haystack) rendering pipelines. It allows users to visually compose rendering commands through a node-based interface, supporting various data formats including unstructured meshes, volumes, point clouds, and more.

The addon generates executable command-line instructions that can be run locally or on remote HPC clusters via the BRaaS-HPC infrastructure.

## Features

- **Visual Node-Based Workflow**: Create rendering pipelines by connecting nodes in Blender's node editor
- **Multiple Data Loaders**: Support for various scientific data formats (UMesh, OBJ, Mini, Spheres, NanoVDB, RAW volumes, etc.)
- **Render Backends**: Multiple rendering targets including BRaaS-HPC, hsViewer, hsViewerQT, and offline rendering
- **Auto-Generate Code**: Automatically generate command-line code as you modify node parameters
- **Remote/Local Support**: Work with both local files and remote HPC filesystem paths
- **Transfer Function Editor**: Create and manage volume transfer functions using Blender's material nodes
- **Camera Control**: Integrated camera setup with Blender camera objects

## Requirements

- **Blender**: Version 4.5.0 or higher
- **Optional**: BRaaS-HPC addon for remote cluster execution

## Installation

1. Download or clone the addon to your local machine
2. Open Blender
3. Go to `Edit` → `Preferences` → `Add-ons`
4. Click `Install...` button
5. Navigate to the addon folder and select the folder or zip file
6. Enable the addon by checking the box next to "BRaaS-HPC-HayStackComposer"

## How to Use

### Getting Started

1. **Open Node Editor**:
   - In Blender, switch any area to `Node Editor` (Shift+F3)
   - From the node editor header, select `HayStack Composer` from the tree type dropdown

2. **Access the Panel**:
   - In the Node Editor, press `N` to open the sidebar
   - Navigate to the `HAYSTACK` tab to find the composer panel

### Creating a Basic Rendering Pipeline

#### Step 1: Add Data Loader Nodes
- Press `Shift+A` in the node editor
- Navigate to `Add` → `DataLoader` category
- Select a data loader node (e.g., `UMesh`, `OBJ`, `RAWVolume`, etc.)
- Configure the file path to your data file

#### Step 2: Add Scene Nodes (Optional)
- Add a `Camera` node from the `Scene` category
- Configure camera position, view direction, and field of view
- Add a `TransferFunction` node for volume rendering
- Create and configure a material for the transfer function

#### Step 3: Add Property Nodes (Optional)
- Add a `Properties` node to configure rendering parameters:
  - Number of frames
  - Paths per pixel (sampling rate)
  - Default radius for primitives
  - Merge options
- Add an `OutputImage` node to specify output path and resolution

#### Step 4: Add Render Output Node
- Add a render node from the `Output` category:
  - **hsBlender(BRaaS-HPC)**: Render on remote HPC cluster
  - **hsViewer**: Interactive local viewer
  - **hsViewerQT**: Qt-based interactive viewer
  - **hsOffline**: Offline batch rendering

#### Step 5: Connect Nodes
- Connect data loader outputs to the render node input
- Connect camera and other scene nodes to the render node
- The render node can accept multiple inputs (up to 100 connections)

#### Step 6: Generate Command
- Click `Generate Tree Code` button in the HAYSTACK panel
- The generated command will be saved in a Blender text block
- Access it from the Text Editor in Blender

### Auto-Generate Mode

Enable automatic code generation for real-time feedback:

1. In the HAYSTACK panel, check `Auto Generate Node Code`
2. Adjust the FPS slider to control update frequency (1-30 FPS)
3. Select any node in the tree
4. As you modify node parameters, code is automatically generated
5. The generated code appears in a text block named `{TreeName}_command_node.cmd`

### Working with Remote Files

If you have the BRaaS-HPC addon installed:

1. Go to `Edit` → `Preferences` → `Add-ons`
2. Find `BRaaS-HPC-HayStackComposer` settings
3. Enable `Remote/Local` toggle for remote file access
4. In the Node Editor sidebar, use the `Remote` panel to browse remote filesystems
5. Navigate directories and select files directly from the HPC cluster

## GUI Components

### Node Editor Interface

**HAYSTACK Panel** (Sidebar → HAYSTACK tab):
- **Generate Tree Code**: Creates full command from entire node tree
- **Auto Generate Node Code FPS**: Sets refresh rate for auto-generation
- **Auto Generate Node Code**: Toggle automatic code generation
- **Generate Node Code**: Generate code for currently selected node only
- **Active Node**: Displays currently selected node name

**Remote Panel** (when remote mode enabled):
- **Remote path**: Current path on remote filesystem
- **File browser**: Navigate and select files from HPC cluster

### Node Categories

#### DataLoader Nodes
- **UMesh**: Unstructured mesh files (.umesh)
- **OBJ**: Wavefront OBJ mesh files
- **Mini**: Mini mesh format files
- **Spheres**: Raw sphere data with configurable format and radius
- **TSTri**: Tim Sandstrom triangle files
- **NanoVDB**: NanoVDB volume files with optional spacing
- **RAWVolume**: Raw volume data with format, dimensions, and channels
- **Boxes**: Raw box primitive data
- **Cylinders**: Raw cylinder primitive data
- **SpatiallyPartitionedUMesh**: Spatially partitioned unstructured meshes

#### Scene Nodes
- **Camera**: Define camera position, view direction, up vector, and field of view
- **TransferFunction**: Volume transfer function using Blender materials

#### Property Nodes
- **Properties**: Configure rendering parameters
  - Num. frames: Accumulation frames
  - Paths per pixel: Sampling rate
  - Merge umeshes: Merge multiple unstructured meshes
  - Default Radius: Default sphere/cylinder radius
  - Measure: Enable performance measurement
  - ndg: Number of data groups
  - dpr: Data groups per rank
  - Head node: Enable head node creation
- **Output Image**: Specify output filename, directory, and resolution

#### Output Nodes
- **hsBlender(BRaaS-HPC)**: Render on HPC cluster with hostname and port
- **hsViewer**: Interactive viewer
- **hsViewerQT**: Qt-based interactive viewer
- **hsOffline**: Offline rendering

### Node Socket Types

- **Orange sockets**: HayStack command/data flow connections

## Example Workflow

### Volume Rendering Example

1. Add `RAWVolume` node
   - Set file path to your .raw volume file
   - Configure format (e.g., float)
   - Set dimensions (e.g., 512, 512, 512)
   - Set channels (e.g., 1)

2. Add `Camera` node
   - Set camera position (vp)
   - Set view direction (vi)
   - Adjust field of view (fovy)

3. Add `TransferFunction` node
   - Click "Create Material" to generate a transfer function material
   - Edit the color ramp and opacity curve in the material editor
   - Specify output .xf filename

4. Add `OutputImage` node
   - Set output filename (e.g., "render.png")
   - Set output directory
   - Set resolution (e.g., 1920, 1080)

5. Add `Properties` node
   - Set paths per pixel (e.g., 16 for better quality)
   - Set num. frames for accumulation

6. Add `hsViewer` or `hsBlender(BRaaS-HPC)` node
   - Set executable path
   - For BRaaS-HPC: configure hostname and port

7. Connect all nodes to the render node input

8. Click "Generate Tree Code" to create the command

## Generated Command Structure

The addon generates command-line arguments that follow this general structure:

```
<executable_path> <data_files> --camera <vp> <vi> <vu> -fovy <angle> -xf <transfer_function> -o <output_path> -res <width> <height> --num-frames <frames> --paths-per-pixel <spp> [additional_options]
```

# License
This software is licensed under the terms of the [GNU General Public License](https://github.com/It4innovations/braas-hpc/blob/main/LICENSE).


# Acknowledgement
This work was supported by the Ministry of Education, Youth and Sports of the Czech Republic through the e-INFRA CZ (ID:90254).
