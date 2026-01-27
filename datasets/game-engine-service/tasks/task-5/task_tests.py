"""
Entity Hierarchy Task Tests

Tests for verifying correct implementation of parent-child entity hierarchy
in the game engine's ECS and collision systems.
"""

import re
import pytest


def read_file_content(filepath: str) -> str:
    """Read and return the contents of a source file."""
    with open(filepath, 'r') as f:
        return f.read()


class TestHierarchyComponentDeclaration:
    """Tests for HierarchyComponent class declaration in component.h."""

    def test_hierarchy_component_class_declared(self):
        """
        Verifies that HierarchyComponent class is declared in the header file
        as a new component type for managing parent-child relationships.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        has_class = re.search(
            r'class\s+HierarchyComponent\s*:\s*public\s+ComponentBase\s*<\s*HierarchyComponent\s*>',
            content
        )
        assert has_class is not None, \
            "HierarchyComponent class must be declared inheriting from ComponentBase<HierarchyComponent>"

    def test_hierarchy_has_parent_field(self):
        """
        Confirms HierarchyComponent has a parent_ member field of type EntityID
        to store the parent entity reference.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        class_match = re.search(
            r'class\s+HierarchyComponent[^{]*\{(.*?)\};',
            content,
            re.DOTALL
        )
        assert class_match is not None, "HierarchyComponent class not found"
        
        class_body = class_match.group(1)
        has_parent_field = re.search(r'EntityID\s+parent_', class_body)
        assert has_parent_field is not None, \
            "HierarchyComponent must have parent_ field of type EntityID"

    def test_hierarchy_has_children_vector(self):
        """
        Validates that HierarchyComponent has a children_ member as a vector
        of EntityID to store references to child entities.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        class_match = re.search(
            r'class\s+HierarchyComponent[^{]*\{(.*?)\};',
            content,
            re.DOTALL
        )
        assert class_match is not None, "HierarchyComponent class not found"
        
        class_body = class_match.group(1)
        has_children_vector = re.search(
            r'std::vector\s*<\s*EntityID\s*>\s+children_',
            class_body
        )
        assert has_children_vector is not None, \
            "HierarchyComponent must have children_ field as vector<EntityID>"


class TestHierarchyComponentMethods:
    """Tests for HierarchyComponent method implementations in component.cpp."""

    def test_hierarchy_get_parent_method(self):
        """
        Verifies that HierarchyComponent has a getParent method that returns
        the parent EntityID stored in the component.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        has_get_parent = re.search(
            r'EntityID\s+HierarchyComponent::getParent\s*\(\s*\)\s*const',
            content
        )
        assert has_get_parent is not None, \
            "HierarchyComponent must have getParent() method returning EntityID"

    def test_hierarchy_set_parent_method(self):
        """
        Confirms HierarchyComponent has a setParent method that accepts an
        EntityID parameter to update the parent relationship.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        has_set_parent = re.search(
            r'void\s+HierarchyComponent::setParent\s*\(\s*EntityID',
            content
        )
        assert has_set_parent is not None, \
            "HierarchyComponent must have setParent(EntityID) method"

    def test_hierarchy_add_child_method(self):
        """
        Validates that HierarchyComponent has an addChild method that adds
        a child EntityID to the children vector.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'void\s+HierarchyComponent::addChild\s*\(\s*EntityID[^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "addChild method not found"
        
        function_body = function_match.group(1)
        uses_push_back = 'push_back' in function_body or 'emplace_back' in function_body
        assert uses_push_back, \
            "addChild must use push_back or emplace_back to add child to vector"

    def test_hierarchy_remove_child_method(self):
        """
        Ensures HierarchyComponent has a removeChild method that removes a
        child from the children vector using proper removal technique.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'void\s+HierarchyComponent::removeChild\s*\(\s*EntityID[^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "removeChild method not found"
        
        function_body = function_match.group(1)
        uses_remove = 'remove' in function_body or 'erase' in function_body
        assert uses_remove, \
            "removeChild must use std::remove or erase to remove child from vector"

    def test_hierarchy_has_parent_check(self):
        """
        Verifies HierarchyComponent has a hasParent method that returns true
        when the entity has a valid parent (parent_ != 0).
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'bool\s+HierarchyComponent::hasParent\s*\(\s*\)\s*const[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "hasParent method not found"
        
        function_body = function_match.group(1)
        checks_parent = 'parent_' in function_body and ('!= 0' in function_body or '> 0' in function_body or '!=' in function_body)
        assert checks_parent, \
            "hasParent must check if parent_ is not zero"


class TestCollisionWorldHierarchy:
    """Tests for hierarchy support in CollisionWorld."""

    def test_collision_world_has_parent_map(self):
        """
        Validates that CollisionWorld declares a parentMap_ member to store
        entity parent relationships as an unordered_map.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        
        has_parent_map = re.search(
            r'std::unordered_map\s*<\s*EntityID\s*,\s*EntityID\s*>\s+parentMap_',
            content
        )
        assert has_parent_map is not None, \
            "CollisionWorld must have parentMap_ as unordered_map<EntityID, EntityID>"

    def test_collision_world_set_hierarchy_method(self):
        """
        Confirms CollisionWorld has a setHierarchy method that updates the
        parent relationship in parentMap_ for a given entity.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'void\s+CollisionWorld::setHierarchy\s*\(\s*EntityID[^,]*,\s*EntityID[^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "setHierarchy method not found"
        
        function_body = function_match.group(1)
        updates_map = 'parentMap_' in function_body
        assert updates_map, \
            "setHierarchy must update parentMap_ with the parent relationship"

    def test_collision_world_get_parent_method(self):
        """
        Verifies CollisionWorld has a getParent method that looks up and
        returns the parent EntityID from parentMap_.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'EntityID\s+CollisionWorld::getParent\s*\(\s*EntityID[^)]*\)\s*const[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "getParent method not found"
        
        function_body = function_match.group(1)
        uses_parent_map = 'parentMap_' in function_body
        assert uses_parent_map, \
            "getParent must query parentMap_ to find parent"

    def test_collision_world_get_world_position_traverses(self):
        """
        Ensures getWorldPosition method traverses up the hierarchy chain,
        accumulating position offsets from each parent entity.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'CollisionWorld::getWorldPosition\s*\([^)]*\)[^{]*\{(.*?)^\}',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert function_match is not None, "getWorldPosition method not found"
        
        function_body = function_match.group(1)
        traverses_hierarchy = ('while' in function_body or 'for' in function_body) and 'parent' in function_body.lower()
        assert traverses_hierarchy, \
            "getWorldPosition must traverse hierarchy using a loop to accumulate positions"

    def test_collision_world_get_world_position_accumulates(self):
        """
        Validates that getWorldPosition accumulates x and y positions from
        each collider as it walks up the parent chain.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        function_match = re.search(
            r'CollisionWorld::getWorldPosition\s*\([^)]*\)[^{]*\{(.*?)^\}',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert function_match is not None, "getWorldPosition method not found"
        
        function_body = function_match.group(1)
        accumulates_position = ('+=' in function_body or ('x' in function_body and 'y' in function_body and 'pos' in function_body.lower()))
        assert accumulates_position, \
            "getWorldPosition must accumulate x and y positions from hierarchy"
