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

set(RESOURCES resources)

if(NOT DEFINED WAR1GUS_DATA)
       message(FATAL_ERROR "Point WAR1GUS_DATA to the data directory of war1gus")
endif()

add_custom_command(OUTPUT ${RESOURCES}
                   COMMAND python3
                   ARGS ${PROJECT_SOURCE_DIR}/extract_data.py --data ${WAR1GUS_DATA} --output ${RESOURCES} --prefix ${TOOLCHAIN_PATH}
                   COMMENT "Converting graphics"
                   WORKING_DIRECTORY ${PROJECT_BINARY_DIR}
                   VERBATIM)

set(SOURCES ${C_SOURCES} ${HEADERS} ${RESOURCES})

include(target-definition.cmake)
