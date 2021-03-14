if(DEFINED AMIGA_GCC_PREFIX)
       include(bebbo-toolchain.cmake)
else()
       if(NOT WIN32)
              message(FATAL_ERROR "Bartman's toolchain works only on Windows. Define AMIGA_GCC_PREFIX to point to Bebbo's toolchain")
       else()
              set(USE_WIN32 1)
       endif()
       include(bartman-toolchain.cmake)
endif()

cmake_minimum_required(VERSION 3.16)
project(orcsvsmen)

add_subdirectory(deps/ACE ace)
include_directories(deps/ACE/include)

include_directories(
        ${PROJECT_SOURCE_DIR}/src
)

set(C_SOURCES src/main.c
              src/bob_new.c
              src/game.c)

set(HEADERS src/game.h
            src/bob_new.h)

set(RESOURCES
        ${PROJECT_BINARY_DIR}/resources/imgs/for.plt
        ${PROJECT_BINARY_DIR}/resources/imgs/swa.plt
        ${PROJECT_BINARY_DIR}/resources/imgs/dun.plt)

if(NOT DEFINED WAR1_DATA)
       if (EXISTS ${PROJECT_SOURCE_DIR}/DATA.WAR)
              set(WAR1_DATA ${PROJECT_SOURCE_DIR})
       else()
              message(FATAL_ERROR "Point WAR1_DATA to the data directory of Warcraft 1, War1gus, or place DATA.WAR in the source directory of this project.")
       endif()
endif()

file(MAKE_DIRECTORY ${PROJECT_BINARY_DIR}/tools)
if(USE_WIN32)
       set(CONVERSION_TOOLS
              ${PROJECT_BINARY_DIR}/Rgb2Amiga.exe
              ${PROJECT_BINARY_DIR}/tileset_conv.exe
              ${PROJECT_BINARY_DIR}/bitmap_conv.exe
              ${PROJECT_BINARY_DIR}/palette_conv.exe)
       # just download prebuilt rgb2amiga on windows, it's annoying to have to build imagemagick
       execute_process(
                     COMMAND ${CMAKE_COMMAND} -S ${PROJECT_SOURCE_DIR}/deps/ACE/tools -B ${PROJECT_BINARY_DIR}/ace_tools_build
                     COMMAND_ECHO STDOUT)
       if(NOT EXISTS ${PROJECT_BINARY_DIR}/rgb2amiga.zip)
              file(
                     DOWNLOAD https://github.com/timfel/rgb2amiga/releases/download/windows-binaries/rgb2amiga.zip
                     ${PROJECT_BINARY_DIR}/rgb2amiga.zip
                     SHOW_PROGRESS)
       endif()
       if(NOT EXISTS ${PROJECT_BINARY_DIR}/rgb2amiga)
              file(ARCHIVE_EXTRACT INPUT ${PROJECT_BINARY_DIR}/rgb2amiga.zip)
       endif()
       if(NOT EXISTS ${PROJECT_BINARY_DIR}/tools/Rgb2Amiga.exe)
              file(GLOB RGB2AMIGABINARIES ${PROJECT_BINARY_DIR}/rgb2amiga/*)
              file(COPY ${RGB2AMIGABINARIES} DESTINATION ${PROJECT_BINARY_DIR}/tools/)
       endif()
       add_custom_command(OUTPUT ${CONVERSION_TOOLS}
                     COMMAND ${CMAKE_COMMAND} --build ${PROJECT_BINARY_DIR}/ace_tools_build
                     COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/ACE/tools/bin/Debug/tileset_conv.exe ${PROJECT_BINARY_DIR}/tools/tileset_conv.exe
                     COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/ACE/tools/bin/Debug/bitmap_conv.exe ${PROJECT_BINARY_DIR}/tools/bitmap_conv.exe
                     COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/ACE/tools/bin/Debug/palette_conv.exe ${PROJECT_BINARY_DIR}/tools/palette_conv.exe
                     COMMENT "Building tools"
                     VERBATIM)
else()
       # build submodules on linux
       set(CONVERSION_TOOLS
              ${PROJECT_BINARY_DIR}/Rgb2Amiga
              ${PROJECT_BINARY_DIR}/tileset_conv
              ${PROJECT_BINARY_DIR}/bitmap_conv
              ${PROJECT_BINARY_DIR}/palette_conv)
       execute_process(COMMAND ${CMAKE_COMMAND} -S ${PROJECT_SOURCE_DIR}/deps/rgb2amiga -B ${PROJECT_SOURCE_DIR}/deps/rgb2amiga
                     COMMAND ${CMAKE_COMMAND} -S ${PROJECT_SOURCE_DIR}/deps/ACE/tools -B ${PROJECT_BINARY_DIR}/ace_tools_build
                     COMMAND_ECHO STDOUT)
       
       add_custom_command(OUTPUT ${CONVERSION_TOOLS}
              COMMAND ${CMAKE_COMMAND} --build ${PROJECT_SOURCE_DIR}/deps/rgb2amiga
              COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/rgb2amiga/bin/debug/Rgb2Amiga ${PROJECT_BINARY_DIR}/tools/Rgb2Amiga
              COMMAND ${CMAKE_COMMAND} --build ${PROJECT_BINARY_DIR}/ace_tools_build
              COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/ACE/tools/bin/tileset_conv ${PROJECT_BINARY_DIR}/tools/tileset_conv
              COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/ACE/tools/bin/bitmap_conv ${PROJECT_BINARY_DIR}/tools/bitmap_conv
              COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/ACE/tools/bin/palette_conv ${PROJECT_BINARY_DIR}/tools/palette_conv
              COMMENT "Building tools"
              VERBATIM)
endif()

add_custom_command(OUTPUT ${RESOURCES}
                   DEPENDS ${CONVERSION_TOOLS}
                   COMMAND python3 ${PROJECT_SOURCE_DIR}/extract_data.py --data ${WAR1_DATA} --output resources --prefix ${PROJECT_BINARY_DIR}/tools
                   COMMENT "Converting graphics"
                   WORKING_DIRECTORY ${PROJECT_BINARY_DIR}
                   VERBATIM)

set(SOURCES ${C_SOURCES} ${HEADERS} ${RESOURCES})

include(target-definition.cmake)
