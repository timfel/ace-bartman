if(DEFINED AMIGA_GCC_PREFIX)
       include(bebbo-toolchain.cmake)
else()
       if(NOT WIN32)
              message(FATAL_ERROR "Bartman's toolchain works only on Windows. Define AMIGA_GCC_PREFIX to point to Bebbo's toolchain")
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

set(RESOURCES resources/for.plt)

if(NOT DEFINED WAR1GUS_DATA)
       message(FATAL_ERROR "Point WAR1GUS_DATA to the data directory of war1gus")
endif()

set(CONVERSION_TOOLS
        ${PROJECT_BINARY_DIR}/Rgb2Amiga
        ${PROJECT_BINARY_DIR}/tileset_conv
        ${PROJECT_BINARY_DIR}/bitmap_conv
        ${PROJECT_BINARY_DIR}/palette_conv)

add_custom_command(OUTPUT ${CONVERSION_TOOLS}
                   COMMAND ${CMAKE_COMMAND} -S ${PROJECT_SOURCE_DIR}/deps/rgb2amiga -B ${PROJECT_BINARY_DIR}/rgb2amiga_build
                   COMMAND ${CMAKE_COMMAND} --build ${PROJECT_BINARY_DIR}/rgb2amiga_build
                   COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/rgb2amiga/bin/debug/Rgb2Amiga ${PROJECT_BINARY_DIR}/Rgb2Amiga
                   COMMAND ${CMAKE_COMMAND} -S ${PROJECT_SOURCE_DIR}/deps/ACE/tools -B ${PROJECT_BINARY_DIR}/ace_tools_build
                   COMMAND ${CMAKE_COMMAND} --build ${PROJECT_BINARY_DIR}/ace_tools_build
                   COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/ACE/tools/bin/tileset_conv ${PROJECT_BINARY_DIR}/tileset_conv
                   COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/ACE/tools/bin/bitmap_conv ${PROJECT_BINARY_DIR}/bitmap_conv
                   COMMAND ${CMAKE_COMMAND} -E copy ${PROJECT_SOURCE_DIR}/deps/ACE/tools/bin/palette_conv ${PROJECT_BINARY_DIR}/palette_conv
                   COMMENT "Building tools"
                   VERBATIM)

add_custom_command(OUTPUT ${RESOURCES}
                   DEPENDS ${CONVERSION_TOOLS}
                   COMMAND python3
                   ARGS ${PROJECT_SOURCE_DIR}/extract_data.py --data ${WAR1GUS_DATA} --output ${RESOURCES} --prefix ${PROJECT_BINARY_DIR}
                   COMMENT "Converting graphics"
                   WORKING_DIRECTORY ${PROJECT_BINARY_DIR}
                   MAIN_DEPENDENCY ${PROJECT_SOURCE_DIR}/extract_data.py
                   VERBATIM)

set(SOURCES ${C_SOURCES} ${HEADERS} ${RESOURCES})

include(target-definition.cmake)
