#   Copyright (C) <2024>  <Lee Shaw>
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License along
#   with this program; if not, write to the Free Software Foundation, Inc.,
#   51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

bl_info = {
    "name": "Maze Generator",
    "blender": (4, 1, 0),
    "category": "Object",
    "author": "Lee Shaw",
    "version": (0, 2, 1),
    "location": "View3D > Sidebar > Create",
    "description": "Generates a random maze mesh",
    "warning": "",
    "wiki_url": "https://github.com/lshawau/Blender-Maze-Generator/blob/main/README.md",
    "tracker_url": "https://github.com/lshawau/Blender-Maze-Generator/issues",
}

import bpy
import random
import bmesh
import time

#   Represents a single vertex in the maze grid.

#   Attributes:
#       row (int): Row index of the vertex in the grid.
#       col (int): Column index of the vertex.
#       direction (Vertex): Optional; points to another vertex to establish a path in the maze.

#   The `direction` attribute is used to trace the path from one vertex to another, forming the corridors of the maze.

class Vertex:
    def __init__(self, row, col):
        self.row = row # Row index of the vertex in the grid or graph
        self.col = col # Column index of the vertex in the grid or graph
        self.direction = None # Direction associated with the vertex


#   Blender operator to generate a maze. It handles user inputs, maze generation, and updates the 3D view.

class OBJECT_OT_GenerateMaze(bpy.types.Operator):
    bl_idname = "object.generate_maze"
    bl_label = "Generate Maze"
    bl_options = {'REGISTER', 'UNDO'}
    bl_description = "Generate a maze with customizable parameters"

#   Create adjustable properties for the user, accessible from the 3D Viewport's bottom left after initial maze generation. 
#   Dragging these values modifies the maze in real-time. later in the script we will integrate these properties into the Create Menu side panel, 
#   where changes will apply post 'Generate Maze' button press, benefiting users with slower PCs or when generating large, laggy mazes.

    random_seed: bpy.props.IntProperty(
        name="Random Seed", 
        default=0, 
        description="Seed value for random maze generation"
    )
    
    rows: bpy.props.IntProperty(
        name="Rows", 
        default=20, 
        min=1, 
        description="Number of rows in the maze grid"
    )

    columns: bpy.props.IntProperty(
        name="Columns", 
        default=20, 
        min=1, 
        description="Number of columns in the maze grid"
    )

    cell_size: bpy.props.IntProperty(
        name="Cell Size", 
        default=2, 
        min=1, 
        description="Size of each maze cell (XY)"
    )

    wall_height: bpy.props.FloatProperty(
        name="Wall Height", 
        default=2.4, 
        min=0.01, 
        description="Height of the maze walls"
    )

    iterations: bpy.props.IntProperty(
        name="Iterations", 
        default=5, 
        min=1, 
        description="Number of iterations for maze generation algorithm"
    )

    delete_islands: bpy.props.BoolProperty(
        name="Delete Islands", 
        default=True, 
        description="Whether to delete isolated areas of the maze"
    )

    island_wall_count: bpy.props.IntProperty(
        name="Island Wall Count", 
        default=6, 
        min=0, 
        description="Determines the quantity of walls that will be removed"
    )

    apply_solidify: bpy.props.BoolProperty(
        name="Apply Solidify", 
        default=True, 
        description="Whether to apply the solidify modifier to the maze walls"
    )

    apply_bevel: bpy.props.BoolProperty(
        name="Apply Bevel", 
        default=True, 
        description="Whether to apply the bevel modifier to the maze walls"
    )


#   Executes the maze generation process, updates the scene, and handles errors and performance timing.

#   This method coordinates the steps involved in generating a new maze, including initializing the grid, 
#   creating the maze structure, and applying necessary modifications. 
#   It also measures the execution time for performance tracking.

#   Parameters:
#       context (bpy.types.Context): The context in which the operator is executed, 
#       providing access to data and area of Blender being operated on.

#   Returns:
#       {'FINISHED'} if the maze generation completes successfully,
#       {'CANCELLED'} if an error occurs during the process.

#   Raises:
#       Exception: If any step in the maze generation process fails, 
#       an error is reported through Blender's reporting system, and the exception is re-raised to halt further execution. 
#       This ensures that partial or incorrect maze generation does not occur.

    def execute(self, context):
    
        try:
            time_start = time.time()

            random.seed(self.random_seed)
        
            self.deselect_objects()
            self.delete_existing_maze()
            create_grid(self.rows, self.columns, self.cell_size, self.wall_height, self.iterations, self.delete_islands, self.island_wall_count, self.apply_solidify, self.apply_bevel)
        
            time_end = time.time()
            duration = time_end - time_start
            # Output to console
            print()
            print(f"Maze generation completed in {duration:.3f} seconds.")
            print()
            
        except Exception as e:
            self.report({'ERROR'}, f"An error occurred: {str(e)}")
            return {'CANCELLED'}    
        return {'FINISHED'}


#   Deselects all objects in the current Blender view layer.

#   This method ensures that no objects are selected in the scene before starting the maze generation,
#   preventing unintended transformations or deletions of unrelated objects during the maze creation process.
#   It is a crucial step to maintain a clean state in the Blender environment, especially before operations that modify the mesh data.

    def deselect_objects(self):
    
        try:
            for obj in bpy.context.view_layer.objects:
                obj.select_set(False)
                
        except Exception as e:
            self.report({'ERROR'}, f"Failed to deselect objects: {str(e)}")
            raise


#   Deletes the maze object named "Maze" from the current Blender view layer.

#   This method ensures that the prior maze is deleted before generating a new one to reduce clutter and prevent conflicts. 
#   It specifically targets an object named "Maze" and will not delete objects with different names.

    def delete_existing_maze(self):
    
        try:
            existing_maze = bpy.data.objects.get("Maze")
            if existing_maze:
                bpy.data.objects.remove(existing_maze, do_unlink=True)
                
        except Exception as e:
            self.report({'ERROR'}, f"Failed to delete existing maze: {str(e)}")
            raise


#   Generates the grid layout for the maze and initializes vertices, applying specified modifiers and settings.

#   This function sets up a grid of vertices based on the specified number of rows and columns. 
#   It initializes the maze structure by linking vertices according to the maze generation algorithm. 
#   The function also handles the application of Blender modifiers like solidify and bevel based on user inputs, 
#   and performs cleanup tasks like deleting isolated islands within the maze.

#   Parameters:
#       rows (int): Number of rows in the maze grid.
#       cols (int): Number of columns in the maze grid.
#       cell_size (int): Size of each cell in the maze (XY dimensions).
#       wall_height (float): Height of the maze walls.
#       iterations (int): Number of iterations for the maze generation algorithm.
#       delete_islands (bool): Flag to determine whether to remove isolated sections of the maze.
#       island_wall_count (int): Maximum number of walls an island can have before it is removed.
#       apply_solidify (bool): Flag to determine whether to apply the solidify modifier to the maze walls.
#       apply_bevel (bool): Flag to determine whether to apply the bevel modifier to the maze walls.

def create_grid(rows, cols, cell_size, wall_height, iterations, delete_islands, island_wall_count, apply_solidify, apply_bevel):

    try:
        time_start = time.time()

        vertices = [[Vertex(row, col) for col in range(cols)] for row in range(rows)]
        initialize_maze(vertices, rows, cols)
        
        mesh = bpy.data.meshes.new(name="Maze")
        obj = bpy.data.objects.new(name="Maze", object_data=mesh)
        bpy.context.collection.objects.link(obj)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        verts = [(col * cell_size, row * cell_size, 0) for row in range(rows) for col in range(cols)]
        mesh.from_pydata(verts, [], [])

        for _ in range(iterations):
            origin_row = random.randint(0, rows - 1)
            origin_col = random.randint(0, cols - 1)
            origin_vertex = vertices[origin_row][origin_col]
            neighbor_vertex = get_random_neighbor(vertices, origin_vertex, rows, cols)
            origin_vertex.direction = neighbor_vertex

        visualize_maze(mesh, vertices, rows, cols, cell_size)
        extrude_walls(obj, wall_height)
            
        if apply_solidify:
            apply_solidify_modifier(obj, apply_solidify)
            
        if delete_islands:
            delete_islands_with_up_to_n_faces(obj, delete_islands, island_wall_count)
            
        if apply_bevel:
            apply_bevel_modifier(obj, apply_bevel)
            
        apply_transform_and_cleanup(obj, wall_height)

        time_end = time.time()
        duration = time_end - time_start
        print()  
        print(f"Create grid completed in {duration:.3f} seconds.")
        print()
        
    except Exception as e:
        print(f"Error in create_grid: {str(e)}")
        raise


#   Initializes the maze using a depth-first search to set directions for each vertex.

def initialize_maze(vertices, rows, cols):
    
    try:
        time_start = time.time()

        visited = set()
        stack = [(0, 0)] # start from the top-left corner or any other starting point
        while stack:
            row, col = stack.pop()
            visited.add((row, col))
            neighbors = [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]
            random.shuffle(neighbors)
            for neighbor_row, neighbor_col in neighbors:
                if 0 <= neighbor_row < rows and 0 <= neighbor_col < cols and (neighbor_row, neighbor_col) not in visited:
                    vertices[row][col].direction = vertices[neighbor_row][neighbor_col]
                    stack.append((neighbor_row, neighbor_col))
                    visited.add((neighbor_row, neighbor_col))

        time_end = time.time()
        duration = time_end - time_start
        print()
        print(f"Initialize maze completed in {duration:.3f} seconds.")
        print()
                    
    except Exception as e:
        print(f"Error in initialize_maze: {str(e)}")
        raise


#   Selects a random neighboring vertex for the given vertex within the maze grid.

#   Parameters:
#       vertices (list): 2D list of Vertex objects representing the maze grid.
#       vertex (Vertex): The vertex for which a neighbor is to be found.
#       rows (int): Total number of rows in the maze grid.
#       cols (int): Total number of columns in the maze grid.

#   Returns:
#       Vertex: A randomly selected neighboring vertex that is within grid bounds and not previously visited.

#   This function checks the four possible directions (up, down, left, right) from the given vertex and selects one randomly.
    
def get_random_neighbor(vertices, vertex, rows, cols):
    
    try:
        time_start = time.time()

        neighbors = []
        if vertex.row > 0:
            neighbors.append(vertices[vertex.row - 1][vertex.col])
        if vertex.row < rows - 1:
            neighbors.append(vertices[vertex.row + 1][vertex.col])
        if vertex.col > 0:
            neighbors.append(vertices[vertex.row][vertex.col - 1])
        if vertex.col < cols - 1:
            neighbors.append(vertices[vertex.row][vertex.col + 1])
        return random.choice(neighbors)
    
        time_end = time.time()
        duration = time_end - time_start
        print()
        print(f"Get random neighbour completed in {duration:.3f} seconds.")
        print()
        
    except Exception as e:
        print(f"Error in get_random_neighbor: {str(e)}")
        raise


#   Creates edges between vertices in the mesh based on their directions to visualize the maze.

#   Parameters:
#       mesh (Mesh): The Blender mesh data block where the maze geometry is stored.
#       vertices (list): 2D list of Vertex objects representing the maze grid.
#       rows (int): Number of rows in the maze grid.
#       cols (int): Number of columns in the maze grid.
#       cell_size (float): The size of each cell in the maze.

#   This function iterates over each vertex and adds an edge to the mesh for each direction that is not None, effectively drawing the maze paths.

def visualize_maze(mesh, vertices, rows, cols, cell_size):

    try:
        time_start = time.time()

        edges = []
        for row in range(rows):
            for col in range(cols):
                vertex = vertices[row][col]
                if vertex.direction:
                    edges.append((row * cols + col, vertex.direction.row * cols + vertex.direction.col))
        mesh.edges.add(len(edges))
        mesh.edges.foreach_set("vertices", [v for e in edges for v in e])

        time_end = time.time()
        duration = time_end - time_start
        print()
        print(f"Visualize maze completed in {duration:.4f} seconds.")
        print()
        
    except Exception as e:
        print(f"Error in visualize_maze: {str(e)}")
        raise


#   Extrudes the maze's walls vertically to the specified height to create a 3D maze structure.

def extrude_walls(obj, wall_height):
    try:
        time_start = time.time()

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={"value": (0, 0, wall_height)})
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type='VERT')          
        bpy.ops.object.mode_set(mode='OBJECT')
        remove_non_manifold_vertices(obj)

        time_end = time.time()
        duration = time_end - time_start
        print()
        print(f"Extrude walls completed in {duration:.3f} seconds.")
        print()
   
    except Exception as e:
        print(f"Error in extrude_walls: {str(e)}")
        raise        


#   Applies a solidify modifier to the maze object if enabled, enhancing the wall thickness.

def apply_solidify_modifier(obj, apply_solidify):
    try:
        if  apply_solidify:

            start_time = time.time()

            solidify_modifier = obj.modifiers.new(name="Solidify", type='SOLIDIFY')
            solidify_modifier.thickness = 0.15
            solidify_modifier.solidify_mode = 'NON_MANIFOLD'
            solidify_modifier.offset = 0
            bpy.ops.object.modifier_apply(modifier="Solidify")

            end_time = time.time()
            duration = end_time - start_time
            print()
            print(f"Solidify modifier applied in {duration:.3f} seconds.")
            print()

    except Exception as e:
        print(f"Error in apply_solidify_modifier: {str(e)}")
        raise   


#   Applies a bevel modifier to the maze object if enabled, smoothing the edges of the maze walls.

def apply_bevel_modifier(obj, apply_bevel):
    
    try:
        if apply_bevel:
            start_time = time.time()

            bevel_modifier = obj.modifiers.new(name="Bevel", type='BEVEL')
            bevel_modifier.width = .02
            bevel_modifier.segments = 4
            bpy.ops.object.modifier_apply(modifier="Bevel")

            end_time = time.time()
            duration = end_time - start_time
            print()
            print(f"Bevel modifier applied in {duration:.3f} seconds.")
            print()

    except Exception as e:
        print(f"Error in apply_bevel_modifier: {str(e)}")
        raise           


#    Cleans up non-manifold vertices from the maze mesh to ensure mesh integrity, 
#    particularly by removing leftover vertices that do not form part of the maze walls.

#    During the maze generation process, especially after extruding the maze walls, 
#    some vertices may remain that are not connected to any significant edges or faces. 
#    These vertices can form non-functional edges when extruded, 
#    which do not contribute to the maze structure and may interfere with both the visual and functional aspects of the maze. 
#    This function identifies and removes such vertices to maintain a clean and usable mesh.

#    Parameters:
#        obj (bpy.types.Object): The Blender object whose mesh will be inspected and cleaned.

#    Process:
#        1. Switches the object to 'EDIT' mode to allow direct manipulation of the mesh.
#        2. Utilizes Blender's bmesh module to access and modify the mesh data directly.
#        3. Identifies non-manifold vertices using Blender's selection tools.
#        4. Removes these vertices to prevent the formation of unwanted edges and to ensure a manifold geometry.
#        5. Returns the object to 'OBJECT' mode after cleaning is complete.

#    Note:
#        This function modifies the mesh data directly and should be used with caution. 
#        Ensure that the object is not involved in any other operations during this process to avoid conflicts.

def remove_non_manifold_vertices(obj):
    
    try:
        start_time = time.time()

        # Switch to edit mode
        bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        # Deselect all elements first
        bpy.ops.mesh.select_all(action='DESELECT')

        isolated_edges = [edge for edge in bm.edges if len(edge.verts[0].link_edges) == 1 and len(edge.verts[1].link_edges) == 1]
        for edge in isolated_edges:
            edge.select = True
        bpy.ops.mesh.delete(type='EDGE')
        bmesh.update_edit_mesh(mesh)
        
        bpy.ops.object.mode_set(mode='OBJECT')

        end_time = time.time()
        duration = end_time - start_time
        print()
        print(f"Non-manifold vertices removed in {duration:.3f} seconds. ")
        print()

    except Exception as e:
        print(f"Error in remove_non_manifold_vertices: {str(e)}")
        raise        


#    Allows the user to remove small isolated sections (islands) of the maze based on the specified face count threshold.

#    This function identifies and deletes isolated sections of the maze that have up to a specified number of walls (faces). 
#    It is useful for simplifying the maze or ensuring that all parts of the maze are accessible by removing smaller, 
#    disconnected sections. This operation is optional and can be enabled or disabled based on user preference.

#    Parameters:
#        obj (bpy.types.Object): The Blender object representing the maze where islands are to be removed.
#        delete_islands (bool): A flag to determine whether island deletion should be performed. If False, the function will exit without making changes.
#        island_wall_count (int): The maximum number of walls (faces) an island can have before it is considered for deletion. Only islands with this number of faces or fewer will be deleted.

#    Note:
#        This function operates in 'EDIT' mode to directly manipulate the mesh data of the provided object. It assumes that the object's mesh is well-formed and that the 'obj' parameter correctly references a Blender object with mesh data.

def delete_islands_with_up_to_n_faces(obj, delete_islands, island_wall_count):
    
    try:
        time_start = time.time()

        if delete_islands:    
            # Switch to edit mode
            bpy.ops.object.mode_set(mode='EDIT')

            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)
            bm.faces.ensure_lookup_table()

            # Deselect all elements first
            bpy.ops.mesh.select_all(action='DESELECT')

            # Get all islands (disconnected mesh elements)
            bm.verts.ensure_lookup_table()
            islands = []
            visited = set()

            for vert in bm.verts:
                if vert not in visited:
                    stack = [vert]
                    island = set()
                    while stack:
                        v = stack.pop()
                        if v not in visited:
                            visited.add(v)
                            island.add(v)
                            for edge in v.link_edges:
                                for v2 in edge.verts:
                                    if v2 not in visited:
                                        stack.append(v2)
                    islands.append(island)

            for island in islands:
                faces = [face for face in bm.faces if all(vert in island for vert in face.verts)]
                if len(faces) <= island_wall_count:
                    for face in faces:
                        face.select = True

            bmesh.update_edit_mesh(mesh)
            bpy.ops.mesh.delete(type='FACE')
            bpy.ops.object.mode_set(mode='OBJECT')

            time_end = time.time()
            duration = time_end - time_start
            print()
            print(f"Islands with {island_wall_count} faces removed in {duration:.3f} seconds.")
            print()

    except Exception as e:
        print(f"Error in delete_islands_with_up_to_n_faces: {str(e)}")
        raise


#   Applies transformations to the maze object and sets its origin for consistent scaling and manipulation.

def apply_transform_and_cleanup(obj, wall_height):
    try:
        time_start = time.time()

        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
        bpy.ops.object.origin_set(type='GEOMETRY_ORIGIN', center='MEDIAN')
        obj.location.z = wall_height / 2
        bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)

        time_end = time.time()
        duration = time_end - time_start
        print()
        print(f"Transform and cleanup completed in {duration:.3f} seconds.")
        print()

    except Exception as e:
        print(f"Error in apply_transform_and_cleanup: {str(e)}")
        raise


#   UI panel for the 3D Viewport that provides a user interface to control maze generation parameters.

class VIEW3D_PT_CreateMazeMenu(bpy.types.Panel):
    bl_label = "Maze Generator"
    bl_idname = "VIEW3D_PT_CreateMazeMenu"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Create'
    bl_description = "Generate a maze with customizable parameters"
    
#   Draws the UI elements for controlling maze generation within the 3D Viewport's Create menu.

#   This method populates the panel with interactive controls that allow users to:
#       - Initiate maze generation via a button.
#       - Adjust key maze parameters such as size, complexity, and modifiers in real-time.
#       - Each control is linked to a property that influences the maze generation algorithm when the 'Generate Maze' button is pressed.

#   The layout is organized to provide a user-friendly interface, with parameters grouped logically to guide the user through the setup process.

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        layout.operator("object.generate_maze", text="Generate Maze", icon= 'CUBE')
        row = layout.row()
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "random_seed")
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "rows")
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "columns")
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "cell_size")
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "wall_height")
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "iterations")
        row = layout.row()
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "delete_islands")
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "island_wall_count")
        row = layout.row()
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "apply_solidify")
        layout.prop(bpy.context.window_manager.operator_properties_last("object.generate_maze"), "apply_bevel")


classes = (OBJECT_OT_GenerateMaze, VIEW3D_PT_CreateMazeMenu)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
