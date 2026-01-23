cmake_minimum_required(VERSION 3.16)
project(PythonOCC_Superbuild)

include(ExternalProject)

# Installation directory
set(INSTALL_DIR ${CMAKE_BINARY_DIR}/install CACHE PATH "Installation directory")
set(CMAKE_INSTALL_PREFIX ${INSTALL_DIR})

# 1. FreeType
ExternalProject_Add(freetype
    URL ${CMAKE_SOURCE_DIR}/src/3rdparty/freetype-2.13.2.tar.gz
    CMAKE_ARGS
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DCMAKE_BUILD_TYPE=Release
        -DBUILD_SHARED_LIBS=ON
        -DCMAKE_POLICY_VERSION_MINIMUM=3.5
    INSTALL_DIR ${INSTALL_DIR}
)

# 2. Tcl/Tk (Unix only for now, Windows uses vcpkg)
if(UNIX)
    # Tcl
    ExternalProject_Add(tcl
        URL ${CMAKE_SOURCE_DIR}/src/3rdparty/tcl8.6.13-src.tar.gz
        CONFIGURE_COMMAND <SOURCE_DIR>/unix/configure --prefix=<INSTALL_DIR> --enable-shared
        BUILD_COMMAND make
        INSTALL_COMMAND make install
        INSTALL_DIR ${INSTALL_DIR}
    )

    # Tk
    ExternalProject_Add(tk
        URL ${CMAKE_SOURCE_DIR}/src/3rdparty/tk8.6.13-src.tar.gz
        CONFIGURE_COMMAND <SOURCE_DIR>/unix/configure --prefix=<INSTALL_DIR> --enable-shared --with-tcl=<INSTALL_DIR>/lib
        BUILD_COMMAND make
        INSTALL_COMMAND make install
        DEPENDS tcl
        INSTALL_DIR ${INSTALL_DIR}
    )
    
    set(OCCT_TCL_ARGS 
        -DUSE_TCL=ON 
        -DUSE_TK=ON
        -D3RDPARTY_TCL_DIR=${INSTALL_DIR}
        -D3RDPARTY_TK_DIR=${INSTALL_DIR}
        -D3RDPARTY_TCL_INCLUDE_DIR=${INSTALL_DIR}/include
        -D3RDPARTY_TK_INCLUDE_DIR=${INSTALL_DIR}/include
        -D3RDPARTY_TCL_LIBRARY_DIR=${INSTALL_DIR}/lib
        -D3RDPARTY_TK_LIBRARY_DIR=${INSTALL_DIR}/lib
    )
    set(OCCT_DEPENDS freetype tcl tk)
else()
    # Windows assumes vcpkg or pre-installed
    set(OCCT_TCL_ARGS "")
    set(OCCT_DEPENDS freetype)
endif()

# 3. SWIG (Unix only, Windows uses vcpkg)
if(UNIX)
    ExternalProject_Add(swig
        URL ${CMAKE_SOURCE_DIR}/src/3rdparty/swig-4.2.1.tar.gz
        CONFIGURE_COMMAND <SOURCE_DIR>/configure --prefix=<INSTALL_DIR> --without-pcre
        BUILD_COMMAND make
        INSTALL_COMMAND make install
        INSTALL_DIR ${INSTALL_DIR}
    )
    list(APPEND OCCT_DEPENDS swig)
endif()

# 4. OCCT
ExternalProject_Add(occt
    SOURCE_DIR ${CMAKE_SOURCE_DIR}/src/occt
    CMAKE_ARGS
        -DCMAKE_INSTALL_PREFIX=<INSTALL_DIR>
        -DCMAKE_BUILD_TYPE=Release
        -DUSE_FREETYPE=ON
        -D3RDPARTY_FREETYPE_DIR=${INSTALL_DIR}
        -D3RDPARTY_FREETYPE_INCLUDE_DIR_freetype2=${INSTALL_DIR}/include/freetype2
        -D3RDPARTY_FREETYPE_LIBRARY_DIR=${INSTALL_DIR}/lib
        ${OCCT_TCL_ARGS}
        # Disable unused modules to speed up build
        -DBUILD_MODULE_Draw=OFF
        -DBUILD_MODULE_Viz=ON
        -DBUILD_MODULE_DataExchange=ON
        -DBUILD_MODULE_OCAF=ON
    DEPENDS ${OCCT_DEPENDS}
    INSTALL_DIR ${INSTALL_DIR}
)
