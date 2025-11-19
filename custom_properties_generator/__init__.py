bl_info = {
    "name": "CPG — Custom Property Generator",
    "author": "ChatGPT",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar (N) > CPG",
    "description": "Generate multiple custom properties with flexible naming and placement.",
    "category": "Object",
}

import bpy
from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import (
    IntProperty,
    StringProperty,
    BoolProperty,
    EnumProperty,
    FloatProperty,
)


# ---------- Helpers ----------

def zero_pad(n: int) -> str:
    return f"{n:03d}_"

def idprop_apply_ui(idblock, key, *, ptype, default=None, min_val=None, max_val=None, desc=None, subtype='NONE', soft_min=None, soft_max=None):
    """
    Create/update ID prop and apply UI metadata (Blender 4.x API).
    """
    # Create the raw property first if missing, falling back to a type-appropriate default
    if key not in idblock:
        if ptype == 'INT':
            idblock[key] = int(default if default is not None else 0)
        elif ptype == 'FLOAT':
            idblock[key] = float(default if default is not None else 0.0)
        elif ptype == 'BOOL':
            idblock[key] = bool(default if default is not None else False)
        elif ptype == 'STRING':
            idblock[key] = str(default if default is not None else "")
        else:
            idblock[key] = default

    # Ensure value type matches the chosen prop type
    try:
        if ptype == 'INT':
            idblock[key] = int(idblock.get(key, 0))
        elif ptype == 'FLOAT':
            idblock[key] = float(idblock.get(key, 0.0))
        elif ptype == 'BOOL':
            idblock[key] = bool(idblock.get(key, False))
        elif ptype == 'STRING':
            idblock[key] = str(idblock.get(key, ""))
    except Exception:
        pass

    # Apply UI metadata (works in 4.x via id_properties_ui(...).update_from_dict)
    try:
        ui = idblock.id_properties_ui(key)
        data = {}
        if desc is not None:
            data["description"] = desc
        if ptype in {"INT", "FLOAT"}:
            if min_val is not None: data["min"] = min_val
            if max_val is not None: data["max"] = max_val
            if soft_min is not None: data["soft_min"] = soft_min
            if soft_max is not None: data["soft_max"] = soft_max
            if default is not None: data["default"] = default
            if subtype is not None: data["subtype"] = subtype
        elif ptype in {"BOOL", "STRING"}:
            if default is not None: data["default"] = default
        if data:
            ui.update_from_dict(data)
    except Exception:
        # If API differs, silently continue (the property still exists).
        pass


def get_targets_for_object(obj):
    """
    Returns list of (identifier, name, description, idblock_list) dynamic options
    for placement based on the selected object's capabilities.
    """
    items = [("OBJECT", "Object Properties", "Place on the Object datablock")]
    # Object Data (if present)
    if getattr(obj, "data", None) is not None:
        items.append(("DATA", "Object Data Properties", "Place on the Object Data datablock"))

    # Materials (if mesh/curve/whatever uses materials)
    has_slots = hasattr(obj, "material_slots") and len(obj.material_slots) > 0
    if has_slots:
        items.append(("ACTIVE_MATERIAL", "Active Material", "Place on the active material only"))
        items.append(("ALL_MATERIALS", "All Materials", "Place on every assigned material slot that has a material"))

    return items


# ---------- Properties ----------

def target_items_callback(self, context):
    obj = context.active_object
    if obj is None:
        return [("OBJECT", "Object Properties", "Place on the Object datablock")]
    return get_targets_for_object(obj)


class CPG_Props(PropertyGroup):
    count: IntProperty(
        name="Count",
        description="How many properties to create",
        default=1,
        min=1,
    )

    prop_type: EnumProperty(
        name="Type",
        description="Custom property data type",
        items=[
            ("INT", "Integer", "Integer custom property"),
            ("FLOAT", "Float", "Float custom property"),
            ("BOOL", "Boolean", "Boolean custom property"),
            ("STRING", "String", "String custom property"),
        ],
        default="INT",
    )

    # Type-specific UI controls
    int_default: IntProperty(name="Default", default=0)
    int_min: IntProperty(name="Min", default=0)
    int_max: IntProperty(name="Max", default=100)

    float_default: FloatProperty(name="Default", default=0.0)
    float_min: FloatProperty(name="Min", default=0.0)
    float_max: FloatProperty(name="Max", default=1.0)
    float_soft_min: FloatProperty(name="Soft Min", default=0.0)
    float_soft_max: FloatProperty(name="Soft Max", default=1.0)
    float_subtype: EnumProperty(
        name="Subtype",
        description="UI hint for float",
        items=[
            ('NONE', "None", ""),
            ('PERCENTAGE', "Percentage", ""),
            ('FACTOR', "Factor", ""),
            ('ANGLE', "Angle", ""),
            ('TIME', "Time", ""),
            ('DISTANCE', "Distance", ""),
        ],
        default='NONE',
    )

    bool_default: BoolProperty(name="Default", default=False)

    string_default: StringProperty(name="Default", default="")
    string_description: StringProperty(name="Description", default="", description="Tooltip/description")

    # Naming
    base_name: StringProperty(
        name="Name",
        description="Base name used for the properties (numbers/prefix/suffix will be applied around this)",
        default="prop",
    )
    free_prefix: StringProperty(name="Prefix", description="Optional free-text prefix", default="")
    free_suffix: StringProperty(name="Suffix", description="Optional free-text suffix", default="")

    auto_increment: BoolProperty(
        name="Auto Increment (001_, 002_, ...)",
        description="Automatically add a three-digit running number",
        default=False,
    )
    increment_start_from: IntProperty(
        name="Start From",
        description='If blank/0 → starts at 1 (formats as "001_")',
        default=0,
        min=0,
    )
    increment_as_prefix: BoolProperty(
        name="Number as Prefix",
        description="When enabled, numbering goes before the base name (e.g. 001_name)",
        default=True,
    )

    # Placement
    placement: EnumProperty(
        name="Place In",
        description="Where to create the properties",
        items=target_items_callback,
    )

    overwrite_existing: BoolProperty(
        name="Overwrite Existing",
        description="If a property with the same name exists, overwrite its value/UI",
        default=True,
    )


# ---------- Operator ----------

class CPG_OT_Generate(Operator):
    bl_idname = "cpg.generate"
    bl_label = "Generate Custom Properties"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.cpg_props
        obj = context.active_object

        if obj is None:
            self.report({'ERROR'}, "No active object selected.")
            return {'CANCELLED'}

        # resolve targets based on placement
        idblocks = []

        if props.placement == "OBJECT":
            idblocks = [obj]
        elif props.placement == "DATA":
            if getattr(obj, "data", None) is None:
                self.report({'ERROR'}, "Selected object has no Data block.")
                return {'CANCELLED'}
            idblocks = [obj.data]
        elif props.placement == "ACTIVE_MATERIAL":
            mat = obj.active_material
            if mat is None:
                self.report({'ERROR'}, "Active material not found on object.")
                return {'CANCELLED'}
            idblocks = [mat]
        elif props.placement == "ALL_MATERIALS":
            mats = [slot.material for slot in obj.material_slots if slot.material is not None]
            if not mats:
                self.report({'ERROR'}, "No materials on object.")
                return {'CANCELLED'}
            # de-duplicate
            idblocks = list({m.name: m for m in mats}.values())
        else:
            idblocks = [obj]

        # increment starting index
        idx = props.increment_start_from if props.increment_start_from > 0 else 1

        for i in range(props.count):
            # Build the property name
            num = zero_pad(idx) if props.auto_increment else ""
            if props.increment_as_prefix:
                name_parts = [props.free_prefix, num, props.base_name, props.free_suffix]
            else:
                name_parts = [props.free_prefix, props.base_name, num, props.free_suffix]

            # Clean empty parts & join
            prop_name = "".join(p for p in name_parts if p)

            # Ensure prop name is non-empty
            if not prop_name:
                self.report({'ERROR'}, "Resulting property name is empty. Please set Name/Prefix/Suffix.")
                return {'CANCELLED'}

            # Determine default & UI values based on type
            ptype = props.prop_type
            default = None
            min_val = None
            max_val = None
            soft_min = None
            soft_max = None
            subtype = 'NONE'
            desc = props.string_description.strip() if props.string_description else ""

            if ptype == 'INT':
                default = int(props.int_default)
                min_val = int(props.int_min)
                max_val = int(props.int_max)
                # guard if min > max
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
            elif ptype == 'FLOAT':
                default = float(props.float_default)
                min_val = float(props.float_min)
                max_val = float(props.float_max)
                soft_min = float(props.float_soft_min)
                soft_max = float(props.float_soft_max)
                subtype = props.float_subtype
                # fix ranges if needed
                if min_val > max_val:
                    min_val, max_val = max_val, min_val
                if soft_min > soft_max:
                    soft_min, soft_max = soft_max, soft_min
            elif ptype == 'BOOL':
                default = bool(props.bool_default)
            elif ptype == 'STRING':
                default = str(props.string_default)

            # Apply to each target idblock
            for idb in idblocks:
                if prop_name in idb and not props.overwrite_existing:
                    # skip existing if not overwriting
                    continue

                idprop_apply_ui(
                    idb,
                    prop_name,
                    ptype=ptype,
                    default=default,
                    min_val=min_val,
                    max_val=max_val,
                    desc=desc if desc else None,
                    subtype=subtype,
                    soft_min=soft_min,
                    soft_max=soft_max,
                )

            idx += 1

        self.report({'INFO'}, f"Created {props.count} custom propertie(s) on {len(idblocks)} target(s).")
        return {'FINISHED'}


# ---------- Panel ----------

class CPG_PT_Panel(Panel):
    bl_label = "CPG"
    bl_idname = "CPG_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CPG"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def draw(self, context):
        layout = self.layout
        props = context.scene.cpg_props
        obj = context.active_object

        col = layout.column(align=True)
        col.label(text=f"Active: {obj.name}", icon='OBJECT_DATA')
        col.prop(props, "count")

        layout.separator(factor=0.5)

        col = layout.column(align=True)
        col.prop(props, "prop_type")

        # Type-sensitive UI
        box = layout.box()
        if props.prop_type == 'INT':
            row = box.row(align=True)
            row.prop(props, "int_default")
            row = box.row(align=True)
            row.prop(props, "int_min")
            row.prop(props, "int_max")
        elif props.prop_type == 'FLOAT':
            row = box.row(align=True)
            row.prop(props, "float_default")
            row.prop(props, "float_subtype")
            row = box.row(align=True)
            row.prop(props, "float_min")
            row.prop(props, "float_max")
            row = box.row(align=True)
            row.prop(props, "float_soft_min")
            row.prop(props, "float_soft_max")
        elif props.prop_type == 'BOOL':
            box.prop(props, "bool_default")
        elif props.prop_type == 'STRING':
            box.prop(props, "string_default")
            box.prop(props, "string_description")

        layout.separator(factor=0.5)

        name_box = layout.box()
        name_box.prop(props, "base_name")
        row = name_box.row(align=True)
        row.prop(props, "free_prefix")
        row.prop(props, "free_suffix")
        name_box.prop(props, "auto_increment")
        if props.auto_increment:
            row = name_box.row(align=True)
            row.prop(props, "increment_start_from")
            row.prop(props, "increment_as_prefix")

        layout.separator(factor=0.5)

        # Placement (dynamic)
        place_box = layout.box()
        place_box.prop(props, "placement")
        place_box.prop(props, "overwrite_existing")

        layout.separator(factor=0.5)

        col = layout.column()
        col.operator("cpg.generate", text="Generate", icon='CHECKMARK')


# ---------- Registration ----------

classes = (
    CPG_Props,
    CPG_OT_Generate,
    CPG_PT_Panel,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.cpg_props = bpy.props.PointerProperty(type=CPG_Props)

def unregister():
    del bpy.types.Scene.cpg_props
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
