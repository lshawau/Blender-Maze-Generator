# Copyright (C) <2024>  <Lee Shaw>
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License along
#with this program; if not, write to the Free Software Foundation, Inc.,
#51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

bl_info = {
    "name": "Blender Maze Generator",
    "blender": (4, 1, 0),
    "category": "Object",
    "author": "Lee Shaw",
    "version": (0, 1),
    "location": "View3D > Sidebar > Create",
    "description": "Generates a random maze mesh",
    "warning": "",
    "wiki_url": "https://github.com/lshawau/Blender-Maze-Generator/blob/main/README.md",
    "tracker_url": "https://github.com/lshawau/Blender-Maze-Generator/issues",
}



import bpy
import bmesh
import random
dir(bpy.props)


class MESH_OT_generate_maze(bpy.types.Operator):
    """Generate a Random Maze"""
    bl_idname = "mesh.generate_maze"
    bl_label = "Generate Maze"
    bl_options = {'REGISTER', 'UNDO'}

    rows: bpy.props.IntProperty(
        name="Rows",
        description="Number of rows in the maze",
        default=20,
        min=1
    )
    cols: bpy.props.IntProperty(
        name="Columns",
        description="Number of columns in the maze",
        default=20,
        min=1
    )
    cell_size: bpy.props.FloatProperty(
        name="Cell Size",
        description="Size of each maze cell",
        default=40.0,
        min=0.1
    )
    wall_height: bpy.props.FloatProperty(
        name="Wall Height",
        description="Height of maze walls",
        default=2.4,
        min=0.1
    )
    
    def execute(self, context):
        rows = self.rows
        cols = self.cols
        cell_size = self.cell_size
        wall_height = self.wall_height

        # Delete existing maze if present
        existing_maze = bpy.data.objects.get("Maze")
        if existing_maze:
            bpy.data.objects.remove(existing_maze, do_unlink=True)

        def create_grid(rows, cols, cell_size):
            bpy.ops.mesh.primitive_grid_add(x_subdivisions=cols, y_subdivisions=rows, size=cell_size)
            grid_obj = bpy.context.object
            grid_obj.name = "Maze"  # Rename the object for easy identification
            return grid_obj
            
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.inset(thickness=cell_size / 2, depth=0)
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.edge_collapse()
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Randomly open up additional pathways
            for _ in range(rows * cols // 4):  # Adjust the ratio of open pathways as needed
                # Randomly select a cell
                row = random.randint(0, rows - 1)
                col = random.randint(0, cols - 1)

                # Select the edges around the cell
                bpy.context.view_layer.objects.active = grid_obj
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.mesh.select_non_manifold()

                # Randomly deselect one edge to open up a pathway
                bpy.ops.mesh.select_random(seed=random.randint(0, 100), action='DESELECT')

                # Collapse the selected edge to open up the pathway
                bpy.ops.mesh.delete(type='EDGE')

                bpy.ops.object.mode_set(mode='OBJECT')

            return grid_obj

        def remove_edges(grid_obj):
            bm = bmesh.new()
            bm.from_mesh(grid_obj.data)

            edges_to_remove = []

            for edge in bm.edges:
                if random.random() > 0.5:
                    edges_to_remove.append(edge)

            bmesh.ops.delete(bm, geom=edges_to_remove, context='EDGES')
            bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_edges], context='VERTS')

            bm.to_mesh(grid_obj.data)
            bm.free()

        def extrude_edges(grid_obj, wall_height):
            bpy.context.view_layer.objects.active = grid_obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, wall_height)})
            bpy.ops.object.mode_set(mode='OBJECT')
            
            # Add Solidify modifier
            solidify_modifier = grid_obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify_modifier.thickness = 0.15  # Set the thickness of the walls
            solidify_modifier.solidify_mode = 'NON_MANIFOLD'
            
            bpy.context.view_layer.objects.active = grid_obj
            bpy.ops.object.modifier_apply(modifier="Solidify")

        grid_obj = create_grid(rows, cols, cell_size)
        remove_edges(grid_obj)
        extrude_edges(grid_obj, wall_height)
        bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS', center='BOUNDS')
        
        return {'FINISHED'}

class VIEW3D_PT_maze_panel(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""
    bl_label = "Maze Generator"
    bl_idname = "VIEW3D_PT_maze_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Create'

    def draw(self, context):
        self.layout.label(text="Check bottom-left of viewport for adjustments.")
        layout = self.layout
        layout.operator("mesh.generate_maze")

def menu_func(self, context):
    self.layout.operator(MESH_OT_generate_maze.bl_idname)
    
classes = (
    MESH_OT_generate_maze,
    VIEW3D_PT_maze_panel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
