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

foreach(i RANGE 1 12 1)
        list(APPEND MAPS resources/maps/human${i}.map)
endforeach()

foreach(i RANGE 1 12 1)
        list(APPEND MAPS resources/maps/orc${i}.map)
endforeach()

set(RESOURCES resources/forest_tileset.plt)

if(NOT DEFINED WAR1GUS_DATA)
       message(FATAL_ERROR "Point WAR1GUS_DATA to the data directory of war1gus")
endif()

add_custom_command(OUTPUT ${RESOURCES}
                   COMMAND python3
                   ARGS convert_images.py --data ${WAR1GUS_DATA} --output resources --prefix ${TOOLCHAIN_PATH}
                   COMMENT "Converting graphics"
                   WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
                   VERBATIM)

add_custom_command(OUTPUT ${MAPS}
                   COMMAND python3
                   ARGS convert_maps.py --data ${WAR1GUS_DATA} --output resources
                   WORKING_DIRECTORY ${PROJECT_SOURCE_DIR}
                   COMMENT "Converting maps"
                   SOURCES convert_maps.py
                   VERBATIM)

set(SOURCES ${C_SOURCES} ${HEADERS} ${MAPS} ${RESOURCES})

include(target-definition.cmake)

add_custom_command(
        TARGET ${PROJECT_EXECUTABLE} POST_BUILD
	COMMAND ${CMAKE_COMMAND} ARGS -E create_symlink ${PROJECT_SOURCE_DIR}/resources ${PROJECT_BINARY_DIR}/resources
)
