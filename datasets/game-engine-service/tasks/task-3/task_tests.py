"""
Collision Layers Task Tests

Tests for verifying correct implementation of collision layer filtering in the
game engine's physics system.
"""

import pytest
import re


def read_file_content(filepath: str) -> str:
    """Read and return the contents of a source file."""
    with open(filepath, 'r') as f:
        return f.read()


class TestCollisionMaskBidirectionalCheck:
    """Tests for the canCollideWith function implementing bidirectional layer checks."""

    def test_can_collide_with_checks_both_directions(self):
        """
        Verifies that canCollideWith performs a bidirectional collision check by
        examining whether both thisCanHitOther and otherCanHitThis conditions are
        evaluated and combined with a logical AND operation.
        """
        content = read_file_content('project/src/physics/collision.cpp')
        
        function_match = re.search(
            r'bool\s+CollisionMask::canCollideWith\s*\([^)]*\)\s*const\s*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "canCollideWith function not found"
        
        function_body = function_match.group(1)
        
        has_other_can_hit_this = re.search(
            r'hasLayer\s*\(\s*other\.collidesWith\s*,\s*layer\s*\)',
            function_body
        )
        assert has_other_can_hit_this is not None, \
            "Missing reverse direction check: hasLayer(other.collidesWith, layer)"

    def test_can_collide_with_returns_and_of_both_checks(self):
        """
        Ensures the canCollideWith function returns the logical AND of both
        directional checks rather than just one direction.
        """
        content = read_file_content('project/src/physics/collision.cpp')
        
        function_match = re.search(
            r'bool\s+CollisionMask::canCollideWith\s*\([^)]*\)\s*const\s*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "canCollideWith function not found"
        
        function_body = function_match.group(1)
        
        has_and_return = re.search(
            r'return\s+[^;]*&&[^;]*;',
            function_body
        )
        assert has_and_return is not None, \
            "Return statement must use && to combine both directional checks"


class TestDetectCollisionsLayerFiltering:
    """Tests for collision layer filtering in the detectCollisions function."""

    def test_detect_collisions_checks_layer_masks(self):
        """
        Validates that detectCollisions retrieves collision masks from both
        colliders before adding a collision to the results.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'std::vector<CollisionInfo>\s+CollisionWorld::detectCollisions\s*\(\s*\)\s*const\s*\{(.*?)^\}',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert function_match is not None, "detectCollisions function not found"
        
        function_body = function_match.group(1)
        
        gets_mask_a = re.search(r'\.collider\.getCollisionMask\s*\(\s*\)', function_body)
        assert gets_mask_a is not None, \
            "detectCollisions must retrieve collision masks from colliders"

    def test_detect_collisions_calls_can_collide_with(self):
        """
        Confirms that detectCollisions invokes canCollideWith to determine
        whether two overlapping colliders should actually register a collision.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'std::vector<CollisionInfo>\s+CollisionWorld::detectCollisions\s*\(\s*\)\s*const\s*\{(.*?)^\}',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert function_match is not None, "detectCollisions function not found"
        
        function_body = function_match.group(1)
        
        calls_can_collide = re.search(r'canCollideWith\s*\(', function_body)
        assert calls_can_collide is not None, \
            "detectCollisions must call canCollideWith to filter collisions by layer"

    def test_detect_collisions_skips_incompatible_layers(self):
        """
        Verifies that detectCollisions contains logic to skip collision pairs
        where the layer masks are incompatible.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'std::vector<CollisionInfo>\s+CollisionWorld::detectCollisions\s*\(\s*\)\s*const\s*\{(.*?)^\}',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert function_match is not None, "detectCollisions function not found"
        
        function_body = function_match.group(1)
        
        has_skip_logic = re.search(
            r'if\s*\(\s*!.*canCollideWith.*\)\s*\{?\s*continue',
            function_body,
            re.DOTALL
        )
        assert has_skip_logic is not None, \
            "detectCollisions must skip pairs that fail canCollideWith check"


class TestQueryAABBLayerFiltering:
    """Tests for layer filtering in the queryAABB function."""

    def test_query_aabb_with_filter_checks_layer(self):
        """
        Ensures that the queryAABB overload accepting a layerFilter parameter
        actually uses that filter to check each collider's layer.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'std::vector<EntityID>\s+CollisionWorld::queryAABB\s*\(\s*const\s+AABB\s*&\s*bounds\s*,\s*CollisionLayer\s+layerFilter\s*\)\s*const\s*\{(.*?)^\}',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert function_match is not None, "queryAABB with layerFilter not found"
        
        function_body = function_match.group(1)
        
        uses_has_layer = re.search(r'hasLayer\s*\(\s*layerFilter', function_body)
        assert uses_has_layer is not None, \
            "queryAABB must use hasLayer with layerFilter parameter"

    def test_query_aabb_with_filter_conditionally_adds_entities(self):
        """
        Confirms that queryAABB with a layer filter only adds entities to results
        when they pass the layer check.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'std::vector<EntityID>\s+CollisionWorld::queryAABB\s*\(\s*const\s+AABB\s*&\s*bounds\s*,\s*CollisionLayer\s+layerFilter\s*\)\s*const\s*\{(.*?)^\}',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert function_match is not None, "queryAABB with layerFilter not found"
        
        function_body = function_match.group(1)
        
        has_conditional_push = re.search(
            r'if\s*\(\s*hasLayer\s*\([^)]*\([^)]*\)[^)]*\)\s*\)\s*\{?\s*results\.push_back',
            function_body,
            re.DOTALL
        )
        assert has_conditional_push is not None, \
            "queryAABB must conditionally add entities based on layer filter"

    def test_query_aabb_filter_uses_collider_layer(self):
        """
        Validates that the layer filter check in queryAABB retrieves each
        collider's layer via getLayer() for comparison.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'std::vector<EntityID>\s+CollisionWorld::queryAABB\s*\(\s*const\s+AABB\s*&\s*bounds\s*,\s*CollisionLayer\s+layerFilter\s*\)\s*const\s*\{(.*?)^\}',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert function_match is not None, "queryAABB with layerFilter not found"
        
        function_body = function_match.group(1)
        
        gets_collider_layer = re.search(r'\.collider\.getLayer\s*\(\s*\)', function_body)
        assert gets_collider_layer is not None, \
            "queryAABB must get each collider's layer for filtering"
