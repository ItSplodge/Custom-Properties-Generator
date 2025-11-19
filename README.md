# Custom Property Generator (CPG)

This repository contains the CPG Blender add-on. The add-on lives inside the package directory `custom_properties_generator`, which you can distribute directly or zip for Blender's add-on installer.

## Installing

1. Zip the `custom_properties_generator` directory (select the folder itself, not just its contents).
2. In Blender, open *Edit ➜ Preferences ➜ Add-ons*.
3. Click *Install…* and choose the zipped archive.
4. Enable **CPG — Custom Property Generator** from the add-on list.

## Development Notes

- `custom_properties_generator/__init__.py` defines the add-on's operators, panel, and registration functions.
- Update the `bl_info` dictionary when you bump version numbers or adjust Blender compatibility.
