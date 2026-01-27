# Game Engine Service

A C++ game engine implementation featuring core systems for animation, physics, rendering, and entity management.

## Tech Stack

- **Language**: C++
- **Build System**: CMake
- **Containerization**: Docker

## Project Structure

```
game-engine-service/
├── project/
│   ├── include/
│   │   ├── core/           # Time management, engine core
│   │   ├── ecs/            # Entity Component System
│   │   ├── physics/        # Collision detection & physics
│   │   └── rendering/      # Sprites, animations, rendering
│   └── src/
│       ├── core/           # Core implementations
│       ├── ecs/            # ECS implementations
│       ├── physics/        # Physics implementations
│       └── rendering/      # Rendering implementations
├── tests/                  # Test suites
└── tasks/                  # Evaluation tasks
```

## Features

- Entity Component System (ECS) architecture
- Animation blending with easing functions
- Collision detection with layer filtering
- Spatial partitioning (Quadtree)
- Sprite batching for render optimization
- Fixed timestep physics with interpolation
- Memory pooling for performance
- Event system for decoupled communication
- Component serialization

## Getting Started

### Prerequisites

- C++ compiler with C++17 support
- CMake 3.16+
- Docker (optional)

### Building

```bash
docker-compose build
```

### Running Tests

```bash
./run_tests.sh
```
