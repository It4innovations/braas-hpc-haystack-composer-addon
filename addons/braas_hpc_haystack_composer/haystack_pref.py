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
import subprocess
import importlib
import sys
import os

ADDON_NAME = 'braas_hpc_haystack_composer'

#######################HayStackPreferences#########################################
class HayStackPreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_NAME

    haystack_remote: bpy.props.BoolProperty(
        default=False
    ) # type: ignore

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        box.label(text='Remote/Local:')
        col = box.column()
        col.prop(self, 'haystack_remote')        
       

def ctx_preferences():
    try:
        return bpy.context.preferences
    except AttributeError:
        return bpy.context.user_preferences

def preferences() -> HayStackPreferences:
    return ctx_preferences().addons[ADDON_NAME].preferences

def register():
    bpy.utils.register_class(HayStackPreferences)

def unregister():
    bpy.utils.unregister_class(HayStackPreferences)
