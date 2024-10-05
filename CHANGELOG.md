# CHANGELOG

## [1.1.0] 2024-10-05
### Added:
- Added CHANGELOG file.
- Added #gplm_DSN.kicad_dbl file file for DSN connection usage
- Added create_update_setup.bat file for windows usage
- Added sqlite3.exe for windows usage
### Changed:
- The basic folder structure has been reorganized into two main sections: source code and documentation.
- The source code folder has been restructured with the following subdirectories: g_3dmodels, g_database, g_footprint, g_symbol and spice.
- The evnsetup.sh file has been renamed to create_update_setup.sh.
### Fixed:
- "CON" is a reserved filename in Windows, so all instances of "CON" have been changed to "CNN" (including symbols, CSV files, and the README file).
### ToDo:
- A section for Windows usage needs to be created in the README file, explaining the installation of the ODBC driver and the usage of the create_update_setup.bat file.
- The installation steps need to be reviewed and updated according to the new folder structure.---
