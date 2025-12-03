#####################################################################################################################
# Copyright(C) 2011-2025 IT4Innovations National Supercomputing Center, VSB - Technical University of Ostrava
#
# This program is free software : you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
#####################################################################################################################

import bpy

from bpy.types import NodeTree, Node, NodeSocket, Panel, Operator, PropertyGroup, UIList, Object, Material, Scene
from bpy.utils import register_class, unregister_class
from nodeitems_utils import NodeCategory, NodeItem, register_node_categories, unregister_node_categories
from bpy.props import (StringProperty, FloatProperty, FloatVectorProperty, IntProperty, BoolProperty, EnumProperty, PointerProperty, CollectionProperty, IntVectorProperty)

from mathutils import Matrix

from pathlib import Path
import os
import platform
import re

from . import haystack_pref
##################################
# Timer for Auto Code Generation
##################################

def auto_generate_timer():
    """Timer function to automatically generate code for selected node"""
    for area in bpy.context.screen.areas:
        if area.type == 'NODE_EDITOR':
            for space in area.spaces:
                if space.type == 'NODE_EDITOR' and space.tree_type == 'HayStackComposerTreeType':
                    tree = space.edit_tree
                    if tree and hasattr(tree, 'auto_generate_code') and tree.auto_generate_code:
                        active_node = tree.nodes.active
                        if active_node and hasattr(active_node, 'auto_generate_node_code'):
                            try:
                                active_node.auto_generate_node_code(bpy.context)
                            except Exception as e:
                                print(f"Auto-generate error: {str(e)}")
                        
                        # Return interval based on FPS setting
                        return 1.0 / tree.auto_generate_code_fps
    
    # Check again in 0.5 seconds if no active tree found
    return 0.5

#####################################################################################################################

# Define a custom node tree type
class HayStackComposerNodeTree(NodeTree):
    bl_idname = 'HayStackComposerTreeType'
    bl_label = 'HayStack Composer'
    bl_icon = 'NODETREE'

    auto_generate_code_fps: IntProperty(  # type: ignore
        name="Auto Generate Code FPS",
        min=1,
        max=30,
        default=10,
        description="Set FPS for auto-generating code when enabled"
    )

    def _update_auto_generate_code(self, context):
        """Start or stop the timer when auto-generate is toggled"""
        if self.auto_generate_code:
            # Start timer if not already running
            if not bpy.app.timers.is_registered(auto_generate_timer):
                bpy.app.timers.register(auto_generate_timer, first_interval=0.1)
        else:
            # Stop timer
            if bpy.app.timers.is_registered(auto_generate_timer):
                bpy.app.timers.unregister(auto_generate_timer)
    
    auto_generate_code: BoolProperty(  # type: ignore
        name="Auto Generate Code",
        default=False,
        description="Automatically generate code when selected node values change",
        update=_update_auto_generate_code
    )        

    def generate_command_code(self):
        """Generate executable command code from the node tree"""
        code_lines = []
        
        # Find render node
        render_node = None
        for node in self.nodes:
            if node.bl_idname == 'HayStackRenderBRAASHPCNodeType' or node.bl_idname == 'HayStackRenderViewerNodeType' or node.bl_idname == 'HayStackRenderViewerQTNodeType' or node.bl_idname == 'HayStackRenderOfflineNodeType':
                render_node = node
                break

        if render_node is None:
            raise ValueError("No Render node found in the node tree.")
        
        code_lines.append("")
        code_lines.append(render_node.get_file_path())
        
        code_lines.extend(self._generate_node_code(render_node, set()))
        # code_lines.extend(render_node.generate_code())
        code_lines.append("")
        
        final_command = " ".join(code_lines)
        
        # Create or get text block
        text_name = f"{self.name}_command_tree.cmd"
        if text_name in bpy.data.texts:
            text = bpy.data.texts[text_name]
            text.clear()
        else:
            text = bpy.data.texts.new(text_name)
        
        text.write(final_command)

        return text_name
    
    def _generate_node_code(self, node, visited):
        """Recursively generate command for a node and its dependencies"""
        if node in visited or not hasattr(node, 'generate_code'):
            return []
        
        visited.add(node)
        code_lines = []
        
        # Generate command for input nodes first
        for input_socket in node.inputs:
            if input_socket.is_linked:
                for link in input_socket.links:
                    from_node = link.from_node
                    code_lines.extend(self._generate_node_code(from_node, visited))
        
        # Generate code for this node
        code_lines.extend(node.generate_code())
        # code_lines.append("")
        
        return code_lines

# Define a custom node socket type
class HayStackCommandSocket(NodeSocket):
    bl_idname = 'HayStackCommandSocketType'
    bl_label = 'HayStack Data Node Socket'

    # Optional: Tooltip for the socket
    def draw(self, context, layout, node, text):
        layout.label(text=text)  # Draw the socket label

    # Optional: Template drawing (for more complex layouts)
    def draw_color(self, context, node):
        return (1.0, 0.4, 0.216, 1.0)  # Define the color of the socket

# Node
class HayStackBaseNode(Node):
    bl_idname = 'HayStackBaseNodeType'
    bl_label = 'BaseNode'
    bl_description = 'BaseNode'

    def init(self, context):
        self.width = 200 # Optionally adjust the default width of the node
        self.initNode(context)

    def update(self):
        pass

    def initNode(self, context):
        pass

    def generate_code(self):
        """Override in subclasses to generate command line code"""
        return []

    def get_file_path(self):
        if haystack_pref.preferences().haystack_remote:
            return str(self.file_path_remote)
        else:
            return str(bpy.path.abspath(self.file_path))
        
    def draw_file_path(self, layout):
        row = layout.column(align=True)
        if haystack_pref.preferences().haystack_remote:
            row.prop(self, "file_path_remote")
        else:
            row.prop(self, "file_path")

    def get_dir_path(self):
        if haystack_pref.preferences().haystack_remote:
            return str(self.dir_path_remote)
        else:
            return str(bpy.path.abspath(self.dir_path))
        
    def draw_dir_path(self, layout):
        row = layout.column(align=True)
        if haystack_pref.preferences().haystack_remote:
            row.prop(self, "dir_path_remote")
        else:
            row.prop(self, "dir_path")

    def generate_code_interactive(self, auto_gen_enabled=False):
        """Override in subclasses to generate command line code interactively"""
        code_lines = []
        return code_lines

    def auto_generate_node_code(self, context):
        """Callback to auto-generate code when properties change"""
        # Get the node tree
        if not hasattr(self, 'id_data'):
            return
        
        tree = self.id_data
        if not tree or not hasattr(tree, 'auto_generate_code'):
            return
        
        # Only proceed if auto-generate is enabled and this node is active
        if not tree.auto_generate_code:
            return
        
        # Check if this node is the active node in any node editor
        for area in context.screen.areas:
            if area.type == 'NODE_EDITOR':
                for space in area.spaces:
                    if space.type == 'NODE_EDITOR' and space.tree_type == 'HayStackComposerTreeType':
                        if space.edit_tree == tree and space.edit_tree.nodes.active == self:
                            node = self

                            # Generate code for the selected node
                            code_lines = []
                            
                            try:
                                node_code = node.generate_code_interactive(auto_gen_enabled=True)
                                code_lines.extend(node_code)
                            except Exception as e:
                                self.report({'ERROR'}, f"Error generating code: {str(e)}")
                                return {'CANCELLED'}
                            
                            code = "\n".join(code_lines)
                            
                            # Create or get text block
                            text_name = f"{tree.name}_command_node.cmd"
                            if text_name in bpy.data.texts:
                                text = bpy.data.texts[text_name]
                                text.clear()
                            else:
                                text = bpy.data.texts.new(text_name)
                            
                            text.write(code)                            

                            return


# def update_property(self, context):
#     self.update()

######################################################PANEL######################################################################
# def haystack_update_remote_files(self, context):
#     print(context.scene.haystack_remote_path)
#     #bpy.ops.haystack.update_remote_files()

class HAYSTACK_OT_GenerateCodeNode(Operator):
    """Generate code for selected node only"""
    bl_idname = "haystack_composer.generate_code_node"
    bl_label = "Generate Node Code"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        space = context.space_data
        if space.type != 'NODE_EDITOR' or space.tree_type != 'HayStackComposerTreeType':
            return False
        tree = space.edit_tree
        return tree and tree.nodes.active is not None
    
    def execute(self, context):
        tree = context.space_data.edit_tree
        if not tree:
            self.report({'ERROR'}, "No active node tree")
            return {'CANCELLED'}
        
        node = tree.nodes.active
        if not node:
            self.report({'ERROR'}, "No active node selected")
            return {'CANCELLED'}
        
        # Check if node has generate_code method
        if not hasattr(node, 'generate_code'):
            self.report({'ERROR'}, f"Node '{node.name}' does not support code generation")
            return {'CANCELLED'}
        
        # Generate code for the selected node
        code_lines = []
        
        try:
            node_code = node.generate_code_interactive(auto_gen_enabled=True)
            code_lines.extend(node_code)
        except Exception as e:
            self.report({'ERROR'}, f"Error generating code: {str(e)}")
            return {'CANCELLED'}
        
        code = "\n".join(code_lines)
        
        # Create or get text block
        text_name = f"{tree.name}_command_node.cmd"
        if text_name in bpy.data.texts:
            text = bpy.data.texts[text_name]
            text.clear()
        else:
            text = bpy.data.texts.new(text_name)
        
        text.write(code)
        
        self.report({'INFO'}, f"Generated code for node '{node.name}' in text block '{text_name}'")
        return {'FINISHED'}

class HAYSTACK_OT_update_remote_files(Operator):
    bl_idname = 'haystack_composer.update_remote_files'
    bl_label = 'Update remote files'

    name : StringProperty(        
        default="/"
        ) # type: ignore
    
    is_directory : BoolProperty(
        default=True
        ) # type: ignore

    active_node: None     

    def execute(self, context):
        pref = haystack_pref.preferences()

        if self.is_directory:
            context.scene.haystack_remote_list.clear()
            context.scene.haystack_remote_list_index = -1

            if self.name == "..":
                if context.scene.haystack_remote_path[len(context.scene.haystack_remote_path) - 1] == "/":
                    context.scene.haystack_remote_path = os.path.dirname(context.scene.haystack_remote_path)

                context.scene.haystack_remote_path = os.path.dirname(context.scene.haystack_remote_path)
                context.scene.haystack_remote_path = str(context.scene.haystack_remote_path) + "/"
            else:
                divider = "/"
                if context.scene.haystack_remote_path[len(context.scene.haystack_remote_path) - 1] == "/":
                    divider = ""

                context.scene.haystack_remote_path = str(context.scene.haystack_remote_path) + divider + str(self.name)

            item = context.scene.haystack_remote_list.add()
            item.Name = ".."
            item.is_directory = True

            # Check BRaaS HPC addon
            try:
                import braas_hpc

                pref = braas_hpc.raas_pref.preferences()
                preset = pref.cluster_presets[bpy.context.scene.raas_cluster_presets_index]
                ssh_server_name = braas_hpc.raas_config.GetServerFromType(preset.cluster_name.upper())    

            except ImportError:
                self.report({'ERROR'}, "BRAAS HPC addon not found. Please install and enable it.")
                return {'CANCELLED'}                         

            #folders
            try:
                remote_file_list = braas_hpc.raas_connection.ssh_command_sync(ssh_server_name, " ls -p " + context.scene.haystack_remote_path + " | grep -e /", preset)
                lines = remote_file_list.split('\n')

                for line in lines:
                    if len(line) > 0:
                        item = context.scene.haystack_remote_list.add()
                        item.Name = line
                        item.is_directory = True
            except:
                pass

            #files
            try:
                remote_file_list = braas_hpc.raas_connection.ssh_command_sync(ssh_server_name, " ls -p " + context.scene.haystack_remote_path + " | grep -v /", preset)
                lines = remote_file_list.split('\n')

                for line in lines:
                    if len(line) > 0:
                        item = context.scene.haystack_remote_list.add()
                        item.Name = line
                        item.is_directory = False

            except:
                pass

            try:
                if context.active_node is not None and isinstance(context.active_node, HayStackBaseNode) and pref.haystack_remote:
                    context.active_node.dir_path_remote = str(context.scene.haystack_remote_path)
            except:
                pass 

        else:
            try:
                if context.active_node is not None and isinstance(context.active_node, HayStackBaseNode) and pref.haystack_remote:
                    context.active_node.file_path_remote = str(context.scene.haystack_remote_path) + str(self.name)
            except:
                pass           

        return {"FINISHED"}
    
class HAYSTACK_PG_remote_files(PropertyGroup):
    Name : StringProperty(
        name="Name"
        ) # type: ignore
    
    is_directory : BoolProperty(
        default=False
        ) # type: ignore    
    
class HAYSTACK_UL_remote_files(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname):
        #row = layout.row()
        #row.label(text=item.Name)
        op = layout.operator("haystack.update_remote_files", text=item.Name, icon='FILE_FOLDER' if item.is_directory else 'FILE_BLEND')
        op.name = item.Name
        op.is_directory = item.is_directory

class HAYSTACK_PT_remote_file_path_node(Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Node"
    bl_label = "Remote"   

    @classmethod
    def poll(cls, context):
        pref = haystack_pref.preferences()        
        return context.active_node is not None and isinstance(context.active_node, HayStackBaseNode) and pref.haystack_remote

    def draw(self, context):
        layout = self.layout
        #node = context.active_node    

        col = layout.column()
        col.prop(context.scene, "haystack_remote_path")
        col.operator("haystack.update_remote_files")
        col.template_list("HAYSTACK_UL_remote_files", "", context.scene, "haystack_remote_list", context.scene, "haystack_remote_list_index")


class HAYSTACK_PT_ComposerPanel(Panel):
    """HAYSTACK Composer panel in Node Editor"""
    bl_label = "HAYSTACK Composer"
    bl_idname = "HAYSTACK_PT_composer_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "HAYSTACK"
    
    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'NODE_EDITOR' and space.tree_type == 'HayStackComposerTreeType'
    
    def draw(self, context):
        layout = self.layout
        tree = context.space_data.edit_tree
        
        # Code generation buttons
        layout.operator(HAYSTACK_OT_GenerateCodeTree.bl_idname, icon='FILE_SCRIPT')

        box = layout.box()
        
        active_node = tree.nodes.active if tree else None

        if active_node:
            box.label(text=f"Active Node: {active_node.name}")
        else:
            box.label(text="No Active Node")

        col = box.column()
        # Auto-generate checkbox
        if tree:
            #box.separator()            
            col.prop(tree, "auto_generate_code_fps", text="Auto Generate Node Code FPS")
            col.prop(tree, "auto_generate_code", text="Auto Generate Node Code")

        col.separator()
        col.operator(HAYSTACK_OT_GenerateCodeNode.bl_idname, icon='NODE')        

##################################################LOADING###################################################################    
# UMesh
class HayStackLoadUMeshNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadUMeshNodeType'
    bl_label = 'UMesh'
    bl_description = 'a umesh file of unstructured mesh data'

    file_path: StringProperty(
        name="File",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore          
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')        
    
    def generate_code(self):
        command = []
        command.append(self.get_file_path())
        return command

    def draw_buttons(self, context, layout):        
         self.draw_file_path(layout)

# OBJ
class HayStackLoadOBJNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadOBJNodeType'
    bl_label = 'OBJ'
    bl_description = 'a OBJ file of mesh data'

    file_path: StringProperty(
        name="File",
        subtype="FILE_PATH",        
        default="",
        #update = update_property
    ) # type: ignore

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore          
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')        
    
    def generate_code(self):
        command = []
        command.append(self.get_file_path())
        return command

    def draw_buttons(self, context, layout):        
         self.draw_file_path(layout)

    
# Mini
class HayStackLoadMiniNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadMiniNodeType'
    bl_label = 'Mini'
    bl_description = 'a mini file of mesh data'

    file_path: StringProperty(
        name="File",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore      
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')        
    
    def generate_code(self):
        command = []
        command.append(self.get_file_path())
        return command

    def draw_buttons(self, context, layout):        
         self.draw_file_path(layout)


#spheres://1@/cluster/priya/105000.p4:format=xyzi:radius=1
# Spheres
class HayStackLoadSpheresNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadSpheresNodeType'
    bl_label = 'Spheres'
    bl_description = 'a file of raw spheres'

    num_parts: IntProperty(
        name="Parts",
        default=1,
        #update = update_property
    ) # type: ignore 

    file_path: StringProperty(
        name="File",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore    

    format_items = [
        ('XYZ', "xyz", "Format without type specifier"),
        ('XYZF', "xyzf", "Format with floating point"),
        ('XYZI', "xyzi", "Format with integer"),        
    ]

    format: EnumProperty(
        name="Format",
        description="Choose the format",
        items=format_items,
        default='XYZ',
        #update = update_property
    ) # type: ignore

    radius: FloatProperty(
        name="Radius",
        default=1,
        #update = update_property
    ) # type: ignore     
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')                
    
    def generate_code(self):
        command = []
        command.append("spheres://")
        command.append(str(self.num_parts))
        command.append("@")
        command.append(self.get_file_path())
        command.append(":format=")
        command.append(str(self.format.lower()))
        command.append(":radius=")
        command.append(str(self.radius))
        return command
        
    def draw_buttons(self, context, layout):
        # layout.use_property_split = True
        # layout.use_property_decorate = False  # No animation.

        self.draw_file_path(layout)
        
        row = layout.column(align=True)
        row.prop(self, "num_parts")
        row.prop(self, "format")
        row.prop(self, "radius")


# TSTri
class HayStackLoadTSTriNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadTSTriNodeType'
    bl_label = 'TSTri'
    bl_description = 'Tim Sandstrom type .tri files'
    
    file_path: StringProperty(
        name="File",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore          
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')        
    
    def generate_code(self):
        command = []
        command.append("ts.tri://")
        command.append(self.get_file_path())
        return command

    def draw_buttons(self, context, layout):
        self.draw_file_path(layout)

# NanoVDB
class HayStackLoadNanoVDBNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadNanoVDBNodeType'
    bl_label = 'NanoVDB'
    bl_description = 'NanoVDB files'
    
    file_path: StringProperty(
        name="File",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore

    spacing: FloatVectorProperty(
        name="Spacing",
        size=3,
        subtype='XYZ_LENGTH',
        default=(1, 1, 1),
        #update = update_property
    ) # type: ignore

    spacingEnable: BoolProperty(
        name="Spacing",
        default=False,
        #update = update_property
    ) # type: ignore                
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')        
    
    def generate_code(self):
        command = []
        command.append("nvdb://")
        command.append(self.get_file_path())
        
        if self.spacingEnable:
            command.append(":spacing=")
            command.append(str(self.spacing[0]))
            command.append(",")
            command.append(str(self.spacing[1]))
            command.append(",")
            command.append(str(self.spacing[2]))
        
        return command

    def draw_buttons(self, context, layout):
        self.draw_file_path(layout)

        row = layout.column(align=True)
        row.prop(self, "spacingEnable")
        if self.spacingEnable:
            row.prop(self, "spacing")

#raw://4@/home/wald/models/magnetic-512-volume/magnetic-512-volume.raw:format=float:dims=512,512,512
# RAWVolume
class HayStackLoadRAWVolumeNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadRAWVolumeNodeType'
    bl_label = 'RAWVolume'
    bl_description = 'a file of raw volume'
    
    num_parts: IntProperty(
        name="Parts",
        default=1,
        #update = update_property
    ) # type: ignore 

    file_path: StringProperty(
        name="File",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore           

    format_items = [
        ('UINT8', "uint8", "Format uint8"),
        ('BYTE', "byte", "Format byte"),
        ('FLOAT', "float", "Format float"),
        ('F', "f", "Format float"),
        ('UINT16', "uint16", "Format uint16"),
    ]

    format: EnumProperty(
        name="Format",
        description="Choose the format",
        items=format_items,
        default='FLOAT',
        #update = update_property
    ) # type: ignore

    dims: IntVectorProperty(
        name="Dims",
        size=3,
        subtype='XYZ_LENGTH',
        default=(1, 1, 1),
        #update = update_property
    ) # type: ignore

    channels: IntProperty(
        name="Channels",
        default=1,
        #update = update_property
    ) # type: ignore

    extractEnable: BoolProperty(
        name="Extract",
        default=False,
        #update = update_property
    ) # type: ignore   

    extract: IntVectorProperty(
        name="Extract",
        size=3,
        subtype='XYZ_LENGTH',
        default=(0, 0, 0),
        #update = update_property
    ) # type: ignore

    isoValueEnable: BoolProperty(
        name="IsoValue",
        default=False,
        #update = update_property
    ) # type: ignore    

    isoValue: FloatProperty(
        name="IsoValue",
        default=1,
        #update = update_property
    ) # type: ignore    

       
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')
        self.width = 200 # Optionally adjust the default width of the node        
    
    def generate_code(self):
        command = []
        command.append("raw://")
        command.append(str(self.num_parts))
        command.append("@")
        command.append(self.get_file_path())
        command.append(":format=")
        command.append(str(self.format.lower()))
        command.append(":dims=")
        command.append(str(self.dims[0]))
        command.append(",")
        command.append(str(self.dims[1]))
        command.append(",")
        command.append(str(self.dims[2]))
        command.append(":channels=")
        command.append(str(self.channels))
        
        if self.extractEnable:
            command.append(":extract=")
            command.append(str(self.extract[0]))
            command.append(",")
            command.append(str(self.extract[1]))
            command.append(",")
            command.append(str(self.extract[2]))
            
        if self.isoValueEnable:
            command.append(":isoValue=")
            command.append(str(self.isoValue))
        
        return command
        
    def draw_buttons(self, context, layout):
        # layout.use_property_split = True
        # layout.use_property_decorate = False  # No animation.

        self.draw_file_path(layout)

        row = layout.column(align=True)
        row.prop(self, "num_parts")        
        row.prop(self, "format")
        row.prop(self, "dims")
        row.prop(self, "channels") 
   
        row.prop(self, "extractEnable")
        if self.extractEnable:
            row.prop(self, "extract")

        row.prop(self, "isoValueEnable")
        if self.isoValueEnable:
            row.prop(self, "isoValue")

# Boxes
class HayStackLoadBoxesNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadBoxesNodeType'
    bl_label = 'Boxes'
    bl_description = 'a file of raw boxes'
    
    file_path: StringProperty(
        name="File",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore    

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore      
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')        
    
    def generate_code(self):
        command = []
        command.append("boxes://")
        command.append(self.get_file_path())
        return command

    def draw_buttons(self, context, layout):
        self.draw_file_path(layout)

# Cylinders
class HayStackLoadCylindersNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadCylindersNodeType'
    bl_label = 'Cylinders'
    bl_description = 'a file of raw cylinders'
    
    file_path: StringProperty(
        name="File",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore    

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore      
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')        
    
    def generate_code(self):
        command = []
        command.append("cylinders://")
        command.append(self.get_file_path())
        return command

    def draw_buttons(self, context, layout):
        self.draw_file_path(layout)

# SpatiallyPartitionedUMesh
class HayStackLoadSpatiallyPartitionedUMeshNode(HayStackBaseNode):
    bl_idname = 'HayStackLoadSpatiallyPartitionedUMeshNodeType'
    bl_label = 'SpatiallyPartitionedUMesh'
    bl_description = 'spatially partitioned umeshes'
    
    file_path: StringProperty(
        name="File",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore    

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore      
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')        
    
    def generate_code(self):
        command = []
        command.append("spumesh://")
        command.append(self.get_file_path())
        return command

    def draw_buttons(self, context, layout):
        self.draw_file_path(layout)

##################################################Scene###################################################################
def camera_poll(self, object):
    return object.type == 'CAMERA'
    
#--camera 33.7268 519.912 545.901 499.61 166.807 -72.1014 0 1 0 -fovy 60
#   fromCL.camera.vp.x = std::stof(av[++i]);
#   fromCL.camera.vp.y = std::stof(av[++i]);
#   fromCL.camera.vp.z = std::stof(av[++i]);
#   fromCL.camera.vi.x = std::stof(av[++i]);
#   fromCL.camera.vi.y = std::stof(av[++i]);
#   fromCL.camera.vi.z = std::stof(av[++i]);
#   fromCL.camera.vu.x = std::stof(av[++i]);
#   fromCL.camera.vu.y = std::stof(av[++i]);
#   fromCL.camera.vu.z = std::stof(av[++i]);

#   fromCL.camera.fovy = std::stof(av[++i]);
# Camera
class HayStackCameraNode(HayStackBaseNode):
    bl_idname = 'HayStackCameraNodeType'
    bl_label = 'Camera'
    bl_description = 'Camera'

    # Define the PointerProperty for selecting camera objects
    camera_object: PointerProperty(
        name="Camera",
        type=Object,
        poll=camera_poll,
        #update = update_property
    ) # type: ignore

    vp: FloatVectorProperty(
        name="vp",
        size=3,
        subtype='XYZ',
        default=(0.0, 0.0, 0.0),
        #update = update_property
    ) # type: ignore

    vi: FloatVectorProperty(
        name="vi",
        size=3,
        subtype='XYZ',
        default=(0.0, 0.0, 0.0),
        #update = update_property
    ) # type: ignore    

    vu: FloatVectorProperty(
        name="vu",
        size=3,
        subtype='XYZ',
        default=(0.0, 1.0, 0.0),
        #update = update_property
    ) # type: ignore   

    fovy: FloatProperty(
        name="fovy",
        default=60.0,
        #update = update_property
    ) # type: ignore
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')        
        self.width = 200 # Optionally adjust the default width of the node
            
    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "camera_object")

        box = layout.box()
        col = box.column()
        col.prop(self, "vp", text="vp")
        col.prop(self, "vi", text="vi")
        col.prop(self, "vu", text="vu")
        col = layout.column()
        col.prop(self, "fovy", text="fovy")

    def generate_code(self):
        command = []
        command.append("--camera")
        command.append(str(self.vp[0]))
        command.append(str(self.vp[1]))
        command.append(str(self.vp[2]))
        command.append(str(self.vi[0]))
        command.append(str(self.vi[1]))
        command.append(str(self.vi[2]))
        command.append(str(self.vu[0]))
        command.append(str(self.vu[1]))
        command.append(str(self.vu[2]))
        command.append("-fovy")
        command.append(str(round(self.fovy, 3)))
        return command


#TransferFunction
class HAYSTACK_OT_tf_create_material(Operator):
    bl_idname = 'haystack_composer.tf_create_material'
    bl_label = 'Create Material'

    def execute(self, context):        
        # Create a new material
        material = bpy.data.materials.new(name="TFMaterial")
        material.use_nodes = True
        nodes = material.node_tree.nodes

        # Clear default nodes
        for node in nodes:
            nodes.remove(node)

        # Create Color Ramp node
        color_ramp = nodes.new(type="ShaderNodeValToRGB")
        color_ramp.location = (0, 200)

        # Create Float Curve node
        float_curve = nodes.new(type="ShaderNodeFloatCurve")
        float_curve.location = (200, 200)

        # Create Value node for DomainX
        value_domain_x = nodes.new(type="ShaderNodeValue")
        value_domain_x.location = (-200, 0)
        value_domain_x.name = "DomainX"
        value_domain_x.label = "DomainX"
        value_domain_x.outputs[0].default_value = 0.0

        # Create Value node for DomainY
        value_domain_y = nodes.new(type="ShaderNodeValue")
        value_domain_y.location = (-200, -200)
        value_domain_y.name = "DomainY"
        value_domain_y.label = "DomainY"
        value_domain_y.outputs[0].default_value = 1.0

        # Create Value node for Base Density
        value_base_density = nodes.new(type="ShaderNodeValue")
        value_base_density.location = (-400, 0)
        value_base_density.name = "Base Density"
        value_base_density.label = "Base Density"
        value_base_density.outputs[0].default_value = 1.0

        context.node.material = material
        context.node.file_path = material.name + ".xf"
        context.node.file_path_remote = material.name + ".xf"

        return {"FINISHED"}

class HayStackTransferFunctionNode(HayStackBaseNode):
    bl_idname = 'HayStackTransferFunctionNodeType'
    bl_label = 'TransferFunction'
    bl_description = 'TransferFunction'

    # Define the PointerProperty for selecting camera objects
    material: PointerProperty(
        name="Material",
        type=Material,
        #update = update_property
    ) # type: ignore

    file_path: StringProperty(
        name="XF",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore

    file_path_remote: StringProperty(
        name="File",
        default="",
        #update = update_property
    ) # type: ignore      
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')
        self.width = 200
            
    def draw_buttons(self, context, layout):
        self.draw_file_path(layout)

        col = layout.column()
        col.prop(self, "material")        
        col.operator("haystack_composer.tf_create_material")

    def generate_code(self):
        command = []
        # bpy.context.scene.haystack.server_settings.mat_volume = self.material
        command.append("-xf")
        command.append(self.get_file_path())
        return command

##################################################Utility###################################################################
# class HayStackMerge2Node(HayStackBaseNode):
#     bl_idname = 'HayStackMerge2NodeType'
#     bl_label = 'Merge2'
#     bl_description = 'Merge2'
   
#     def init(self, context):
#         self.inputs.new('HayStackCommandSocketType', 'Data 1')
#         self.inputs.new('HayStackCommandSocketType', 'Data 2')
#         self.outputs.new('HayStackCommandSocketType', 'Command')
        
#     def updateNode(self):
#         self.output_data = str(self.inputs['Data 1'].value) + " " + str(self.inputs['Data 2'].value)

# class HayStackMerge4Node(HayStackBaseNode):
#     bl_idname = 'HayStackMerge4NodeType'
#     bl_label = 'Merge4'
#     bl_description = 'Merge4'
   
#     def init(self, context):
#         self.inputs.new('HayStackCommandSocketType', 'Data 1')
#         self.inputs.new('HayStackCommandSocketType', 'Data 2')
#         self.inputs.new('HayStackCommandSocketType', 'Data 3')
#         self.inputs.new('HayStackCommandSocketType', 'Data 4')
#         self.outputs.new('HayStackCommandSocketType', 'Command')
        
#     def updateNode(self):
#         self.output_data = str(self.inputs['Data 1'].value) + " " + str(self.inputs['Data 2'].value)  + " " + \
#             str(self.inputs['Data 3'].value) + " " + str(self.inputs['Data 4'].value)
        
##########################################Output#################################################
class HayStackOutputImageNode(HayStackBaseNode):
    bl_idname = 'HayStackOutputImageNodeType'
    bl_label = 'Output Image'
    bl_description = 'HayStack Output Image'

    image_file_name: StringProperty(
        name="Name",
        default="output.png",
        subtype="FILE_NAME",
        #update = update_property
    ) # type: ignore

    dir_path: StringProperty(
        name="Path",
        default="",
        subtype="DIR_PATH",        
        #update = update_property
    ) # type: ignore

    dir_path_remote: StringProperty(
        name="Path",
        default="",
        #update = update_property
    ) # type: ignore        

    resolution: IntVectorProperty(
        name="Resolution",
        size=2,
        subtype='XYZ',
        default=(800, 600),
        #update = update_property
    ) # type: ignore            
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')  
    
    def generate_code(self):
        command = []
        command.append("-o")
        command.append(self.get_dir_path())
        command.append("/")
        command.append(str(self.image_file_name))
        command.append("-res")
        command.append(str(self.resolution[0]))
        command.append(str(self.resolution[1]))
        return command

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "image_file_name")

        self.draw_dir_path(layout)

        col = layout.column()
        col.prop(self, "resolution")                
##################################################Render###################################################################
def replace_drive_substrings(input_string):
    if platform.system() == 'Windows':
        ## pattern @
        pattern1 = r"@([a-zA-Z]):"
        def repl_func1(match):
            return f"@{match.group(1)}$"        
        result_string = re.sub(pattern1, repl_func1, input_string)

        ## pattern /
        pattern2 = r"/([a-zA-Z]):"
        def repl_func2(match):
            return f"/{match.group(1)}$"        
        result_string = re.sub(pattern2, repl_func2, result_string)
        
        return result_string
    else:
        return input_string
        
class HayStackRenderBaseNode(HayStackBaseNode):
    bl_idname = 'HayStackRenderBaseNodeType'
    bl_label = 'RenderBase'
    bl_description = 'HayStack Render'
    
    file_path: StringProperty(
        name="Path",
        default="",
        subtype="FILE_PATH",        
        #update = update_property
    ) # type: ignore

    file_path_remote: StringProperty(
        name="Path",
        default="",
        #update = update_property
    ) # type: ignore        
    
    def initNode(self, context):
        self.inputs.new('HayStackCommandSocketType', 'Commands').link_limit = 100

    def generate_code(self):
        command = []
        # command.append(self.get_file_path())
        return command

    def draw_buttons(self, context, layout):
        self.draw_file_path(layout)  

class HayStackRenderBRAASHPCNode(HayStackRenderBaseNode):
    """BRAAS HPC rendering output node"""
    bl_idname = 'HayStackRenderBRAASHPCNodeType'
    bl_label = 'hsBlender(BRaaS-HPC)'
    bl_description = 'HayStack Render BRAAS HPC'
    
    hostname: StringProperty(
        name="Hostname",
        default="localhost",
        description="Server hostname or IP address",
        #update = update_property
    ) # type: ignore
    
    port: IntProperty(
        name="Port",
        default=7000,
        min=1,
        max=65535,
        description="Server port number",
        #update = update_property
    ) # type: ignore
    
    def generate_code(self):
        """Generate BRAAS HPC render loop code"""
        command = []
        # command.append(self.get_file_path())

        # Port
        port = self.port

        if hasattr(bpy.context.scene, "braas_hpc_renderengine"):
            server_settings = bpy.context.scene.braas_hpc_renderengine.server_settings
            port = server_settings.braas_hpc_renderengine_port
        
        command.append("-server")
        command.append(str(self.hostname))
        command.append("-port")
        command.append(str(port))
        
        return command

class HayStackRenderViewerNode(HayStackRenderBaseNode):
    bl_idname = 'HayStackRenderViewerNodeType'
    bl_label = 'hsViewer'
    bl_description = 'HayStack Render hsViewer'
    
class HayStackRenderViewerQTNode(HayStackRenderBaseNode):
    bl_idname = 'HayStackRenderViewerQTNodeType'
    bl_label = 'hsViewerQT'
    bl_description = 'HayStack Render hsViewerQT'

class HayStackRenderOfflineNode(HayStackRenderBaseNode):
    bl_idname = 'HayStackRenderOfflineNodeType'
    bl_label = 'hsOffline'
    bl_description = 'HayStack Render hsOffline'

##################################################Property###################################################################    
class HayStackPropertiesNode(HayStackBaseNode):
    bl_idname = 'HayStackPropertiesNodeType'
    bl_label = 'Properties'
    bl_description = 'HayStack Properties'


    # } else if (arg == "--num-frames") {
    #   fromCL.numFramesAccum = std::stoi(av[++i]);
    num_frames: IntProperty(
        name="Num. frames",
        default=1024,
        #update = update_property
    ) # type: ignore  

    # } else if (arg == "-spp" || arg == "-ppp" || arg == "--paths-per-pixel") {
    #   fromCL.spp = std::stoi(av[++i]);
    paths_per_pixel: IntProperty(
        name="Paths per pixel",
        default=1,
        #update = update_property
    ) # type: ignore     
    # } else if (arg == "-mum" || arg == "--merge-unstructured-meshes" || arg == "--merge-umeshes") {
    #   fromCL.mergeUnstructuredMeshes = true; 
    # } else if (arg == "--no-mum") {
    #   fromCL.mergeUnstructuredMeshes = false;
    merge_umeshes: BoolProperty(
        name="Merge umeshes",
        default=False,
        #update = update_property
    ) # type: ignore       
    # } else if (arg == "--default-radius") {
    #   loader.defaultRadius = std::stof(av[++i]);
    default_radius: FloatProperty(
        name="Default Radius",
        default=0.1,
        #update = update_property,
    ) # type: ignore      
    # } else if (arg == "--measure") {
    #   fromCL.measure = true;
    measure: BoolProperty(
        name="Measure",
        default=False,
        #update = update_property
    ) # type: ignore      
    # } else if (arg == "-o") {
    #   fromCL.outFileName = av[++i];
    # } else if (arg == "--camera") {
    #   fromCL.camera.vp.x = std::stof(av[++i]);
    #   fromCL.camera.vp.y = std::stof(av[++i]);
    #   fromCL.camera.vp.z = std::stof(av[++i]);
    #   fromCL.camera.vi.x = std::stof(av[++i]);
    #   fromCL.camera.vi.y = std::stof(av[++i]);
    #   fromCL.camera.vi.z = std::stof(av[++i]);
    #   fromCL.camera.vu.x = std::stof(av[++i]);
    #   fromCL.camera.vu.y = std::stof(av[++i]);
    #   fromCL.camera.vu.z = std::stof(av[++i]);
    # } else if (arg == "-fovy") {
    #   fromCL.camera.fovy = std::stof(av[++i]);
    # } else if (arg == "-xf") {
    #   fromCL.xfFileName = av[++i];
    # } else if (arg == "-res") {
    #   fromCL.fbSize.x = std::stoi(av[++i]);
    #   fromCL.fbSize.y = std::stoi(av[++i]);
    # } else if (arg == "-ndg") {
    #   fromCL.ndg = std::stoi(av[++i]);
    ndg: IntProperty(
        name="ndg",
        description="Num data groups",
        default=1,
        #update = update_property
    ) # type: ignore     
    # } else if (arg == "-dpr") {
    #   fromCL.dpr = std::stoi(av[++i]);
    dpr: IntProperty(
        name="dpr",
        description="Data groups per rank",
        default=0,
        #update = update_property
    ) # type: ignore
    # } else if (arg == "-nhn" || arg == "--no-head-node") {
    #   fromCL.createHeadNode = false; 
    # } else if (arg == "-hn" || arg == "-chn" ||
    #            arg == "--head-node" || arg == "--create-head-node") {
    #   fromCL.createHeadNode = true; 
    create_head_node: BoolProperty(
        name="Head node",
        default=False,
        #update = update_property
    ) # type: ignore           
    
    def initNode(self, context):
        self.outputs.new('HayStackCommandSocketType', 'Command')
    
    def generate_code(self):
        command = []
        command.append("--num-frames")
        command.append(str(self.num_frames))
        command.append("--paths-per-pixel")
        command.append(str(self.paths_per_pixel))
        command.append("--default-radius")
        command.append(str(round(self.default_radius, 7)))
        command.append("-ndg")
        command.append(str(self.ndg))
        command.append("-dpr")
        command.append(str(self.dpr))
        
        if self.merge_umeshes:
            command.append("--merge-umeshes")
        else:
            command.append("--no-mum")

        if self.measure:
            command.append("--measure")

        if self.create_head_node:
            command.append("--create-head-node")
        
        return command

    def draw_buttons(self, context, layout):
        col = layout.column()
        col.prop(self, "num_frames")
        col.prop(self, "paths_per_pixel")
        col.prop(self, "merge_umeshes")
        col.prop(self, "default_radius")
        col.prop(self, "measure")
        col.prop(self, "ndg")
        col.prop(self, "dpr")
        col.prop(self, "create_head_node")
##################################################OPERATOR###################################################################
class HAYSTACK_OT_GenerateCodeTree(Operator):
    """Generate Command Line from node tree"""
    bl_idname = "haystack_composer.generate_code_tree"
    bl_label = "Generate Tree Code"
    bl_options = {'REGISTER', 'UNDO'}
    
    @classmethod
    def poll(cls, context):
        space = context.space_data
        return space.type == 'NODE_EDITOR' and space.tree_type == 'HayStackComposerTreeType'
    
    def execute(self, context):
        tree = context.space_data.edit_tree
        if not tree:
            self.report({'ERROR'}, "No active node tree")
            return {'CANCELLED'}
        
        text_name = tree.generate_command_code()
        self.report({'INFO'}, f"Generated code in text block '{text_name}'")
        
        return {'FINISHED'}

##################################################CATEGORY###################################################################    
# Define a new node category
class HayStackComposerNodeCategory(NodeCategory):
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'HayStackComposerTreeType' 

# List of node categories in a tuple (identifier, name, description, items)
haystack_node_categories = [
    HayStackComposerNodeCategory("HAYSTACK_DATALOADER_NODES", "DataLoader", items=[
        NodeItem("HayStackLoadUMeshNodeType"),
        NodeItem("HayStackLoadOBJNodeType"),
        NodeItem("HayStackLoadMiniNodeType"),
        NodeItem("HayStackLoadSpheresNodeType"),
        NodeItem("HayStackLoadTSTriNodeType"),
        NodeItem("HayStackLoadNanoVDBNodeType"),
        NodeItem("HayStackLoadRAWVolumeNodeType"),        
        NodeItem("HayStackLoadBoxesNodeType"),
        NodeItem("HayStackLoadCylindersNodeType"),
        NodeItem("HayStackLoadSpatiallyPartitionedUMeshNodeType"),
    ]),

    HayStackComposerNodeCategory("HAYSTACK_SCENE_NODES", "Scene", items=[
        NodeItem("HayStackCameraNodeType"),
        NodeItem("HayStackTransferFunctionNodeType"),        
    ]),

    # HayStackUtilityCategory("HAYSTACK_UTILITY_NODES", "Utility", items=[
    #     NodeItem("HayStackMerge2NodeType"),
    #     NodeItem("HayStackMerge4NodeType"),
    # ]),
    
    HayStackComposerNodeCategory("HAYSTACK_PROPERTY_NODES", "Property", items=[
        NodeItem("HayStackPropertiesNodeType"),
        NodeItem("HayStackOutputImageNodeType"),
    ]),

    HayStackComposerNodeCategory("HAYSTACK_OUTPUT_NODES", "Output", items=[
        NodeItem("HayStackRenderBRAASHPCNodeType"),
        NodeItem("HayStackRenderViewerNodeType"),
        NodeItem("HayStackRenderViewerQTNodeType"),
        NodeItem("HayStackRenderOfflineNodeType"),        
    ]),    

    # HayStackComposerNodeCategory("HAYSTACK_RENDER_NODES", "Render", items=[
    # ]),    
]

#####################################################################################################################    

# Registering
classes = [
    HayStackComposerNodeTree, 
    HayStackCommandSocket,
    HayStackBaseNode,

    #Loading
    HayStackLoadUMeshNode,
    HayStackLoadOBJNode,
    HayStackLoadMiniNode,
    HayStackLoadSpheresNode,
    HayStackLoadTSTriNode,
    HayStackLoadNanoVDBNode,
    HayStackLoadRAWVolumeNode,
    HayStackLoadBoxesNode,
    HayStackLoadCylindersNode,
    HayStackLoadSpatiallyPartitionedUMeshNode,

    #Render
    HayStackRenderBRAASHPCNode,
    HayStackRenderViewerNode,
    HayStackRenderViewerQTNode,
    HayStackRenderOfflineNode,

    #Property
    HayStackPropertiesNode,

    #Utility
    # HayStackMerge2Node,
    # HayStackMerge4Node,

    #Scene
    HayStackCameraNode,
    HayStackTransferFunctionNode,

    #Output
    HayStackOutputImageNode,

    #Other
    HAYSTACK_OT_update_remote_files,
    HAYSTACK_PG_remote_files,
    HAYSTACK_UL_remote_files,
    HAYSTACK_PT_remote_file_path_node,
    HAYSTACK_OT_tf_create_material,
    HAYSTACK_OT_GenerateCodeTree,
    HAYSTACK_OT_GenerateCodeNode,
    HAYSTACK_PT_ComposerPanel,
    ]

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    Scene.haystack_tree = PointerProperty(type=HayStackComposerNodeTree)

    # Register the node categories
    register_node_categories("HAYSTACK_CATEGORIES", haystack_node_categories)

    Scene.haystack_remote_list = CollectionProperty(type=HAYSTACK_PG_remote_files)
    Scene.haystack_remote_list_index = IntProperty(default=-1)
    Scene.haystack_remote_path = StringProperty(name="Remote path", default="/")

def unregister():
    # Unregister the node categories first
    unregister_node_categories("HAYSTACK_CATEGORIES")

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del Scene.haystack_tree

    del Scene.haystack_remote_list
    del Scene.haystack_remote_list_index    
    del Scene.haystack_remote_path
