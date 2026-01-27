cmake_minimum_required(VERSION 3.14)
project(GameEngineCore VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/include)

# Source files
set(SOURCES
    src/core/time_manager.cpp
    src/ecs/component.cpp
    src/physics/collision.cpp
    src/physics/collision_world.cpp
    src/rendering/animation.cpp
)

# Header files
set(HEADERS
    include/core/time_manager.h
    include/ecs/component.h
    include/physics/collision.h
    include/physics/collision_world.h
    include/rendering/animation.h
    include/rendering/sprite.h
)

# Create library
add_library(game_engine_core STATIC ${SOURCES} ${HEADERS})

target_include_directories(game_engine_core PUBLIC
    ${CMAKE_SOURCE_DIR}/include
)

# Optional: Create executable for testing
# add_executable(game_engine_test src/main.cpp)
# target_link_libraries(game_engine_test game_engine_core)
