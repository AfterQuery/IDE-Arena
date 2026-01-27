import re
import pytest


def read_file_content(filepath: str) -> str:
    with open(filepath, 'r') as f:
        return f.read()


class TestQuadTreeNodeDeclarations:

    def test_quadtree_node_struct_declared(self):
        """
        Validates QuadTreeNode struct is declared in collision.h.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'struct\s+QuadTreeNode\s*\{', content) is not None, \
            "QuadTreeNode struct must be declared"

    def test_quadtree_node_has_bounds_member(self):
        """
        Checks QuadTreeNode has bounds AABB member.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'AABB\s+bounds\s*;', content) is not None, \
            "QuadTreeNode must have bounds member"

    def test_quadtree_node_has_entities_member(self):
        """
        Checks QuadTreeNode has entities vector member.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'std::vector<EntityID>\s+entities\s*;', content) is not None, \
            "QuadTreeNode must have entities vector member"

    def test_quadtree_node_has_children_member(self):
        """
        Checks QuadTreeNode has children vector of pointers member.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'std::vector<QuadTreeNode\s*\*>\s+children\s*;', content) is not None, \
            "QuadTreeNode must have children vector member"

    def test_quadtree_node_has_depth_member(self):
        """
        Checks QuadTreeNode has depth int member.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'int\s+depth\s*;', content) is not None, \
            "QuadTreeNode must have depth member"

    def test_quadtree_node_has_max_entities_member(self):
        """
        Checks QuadTreeNode has maxEntities size_t member.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'size_t\s+maxEntities\s*;', content) is not None, \
            "QuadTreeNode must have maxEntities member"

    def test_quadtree_node_has_constructor(self):
        """
        Validates QuadTreeNode has constructor taking AABB reference and depth.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'QuadTreeNode\s*\(\s*const\s+AABB\s*&[^)]*,\s*int\s+depth\s*=\s*0\s*\)', content) is not None, \
            "QuadTreeNode must have constructor with AABB& and int depth=0"

    def test_quadtree_node_has_insert_method(self):
        """
        Checks QuadTreeNode declares insert method.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'void\s+insert\s*\(\s*EntityID\s+entityId\s*,\s*const\s+AABB\s*&\s+entityBounds\s*\)', content) is not None, \
            "QuadTreeNode must declare insert method"

    def test_quadtree_node_has_subdivide_method(self):
        """
        Checks QuadTreeNode declares subdivide method.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'void\s+subdivide\s*\(\s*\)', content) is not None, \
            "QuadTreeNode must declare subdivide method"

    def test_quadtree_node_has_clear_method(self):
        """
        Checks QuadTreeNode declares clear method.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'void\s+clear\s*\(\s*\)', content) is not None, \
            "QuadTreeNode must declare clear method"

    def test_quadtree_node_has_query_method(self):
        """
        Checks QuadTreeNode declares query method returning vector of EntityID.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'std::vector<EntityID>\s+query\s*\(\s*const\s+AABB\s*&\s+queryBounds\s*\)\s*const', content) is not None, \
            "QuadTreeNode must declare query method"

    def test_quadtree_node_has_is_leaf_method(self):
        """
        Checks QuadTreeNode declares isLeaf method.
        """
        content = read_file_content('project/include/physics/collision.h')
        assert re.search(r'bool\s+isLeaf\s*\(\s*\)\s*const', content) is not None, \
            "QuadTreeNode must declare isLeaf method"


class TestCollisionWorldSpatialPartition:

    def test_collision_world_has_spatial_partition_member(self):
        """
        Validates CollisionWorld has spatialPartition_ pointer member.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        assert re.search(r'QuadTreeNode\s*\*\s*spatialPartition_\s*;', content) is not None, \
            "CollisionWorld must have spatialPartition_ member"

    def test_collision_world_has_world_bounds_member(self):
        """
        Checks CollisionWorld has worldBounds_ AABB member.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        assert re.search(r'AABB\s+worldBounds_\s*;', content) is not None, \
            "CollisionWorld must have worldBounds_ member"

    def test_collision_world_has_use_spatial_partition_member(self):
        """
        Checks CollisionWorld has useSpatialPartition_ bool member.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        assert re.search(r'bool\s+useSpatialPartition_\s*;', content) is not None, \
            "CollisionWorld must have useSpatialPartition_ member"

    def test_collision_world_has_set_spatial_partition_bounds_method(self):
        """
        Validates CollisionWorld declares setSpatialPartitionBounds method.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        assert re.search(r'void\s+setSpatialPartitionBounds\s*\(\s*const\s+AABB\s*&\s+bounds\s*\)', content) is not None, \
            "CollisionWorld must declare setSpatialPartitionBounds method"

    def test_collision_world_has_enable_spatial_partition_method(self):
        """
        Validates CollisionWorld declares enableSpatialPartition method.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        assert re.search(r'void\s+enableSpatialPartition\s*\(\s*bool\s+enable\s*\)', content) is not None, \
            "CollisionWorld must declare enableSpatialPartition method"

    def test_collision_world_has_is_spatial_partition_enabled_method(self):
        """
        Checks CollisionWorld declares isSpatialPartitionEnabled method.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        assert re.search(r'bool\s+isSpatialPartitionEnabled\s*\(\s*\)\s*const', content) is not None, \
            "CollisionWorld must declare isSpatialPartitionEnabled method"

    def test_collision_world_has_rebuild_spatial_partition_method(self):
        """
        Checks CollisionWorld declares rebuildSpatialPartition method.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        assert re.search(r'void\s+rebuildSpatialPartition\s*\(\s*\)', content) is not None, \
            "CollisionWorld must declare rebuildSpatialPartition method"


class TestCollisionWorldImplementations:

    def test_constructor_initializes_spatial_partition_to_nullptr(self):
        """
        Validates CollisionWorld constructor initializes spatialPartition_ to nullptr.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        ctor_match = re.search(
            r'CollisionWorld::CollisionWorld\s*\(\s*\)\s*:([^{]+)\{',
            content,
            re.DOTALL
        )
        assert ctor_match is not None, "CollisionWorld constructor not found"
        init_list = ctor_match.group(1)
        assert 'spatialPartition_' in init_list and 'nullptr' in init_list, \
            "Constructor must initialize spatialPartition_ to nullptr"

    def test_constructor_initializes_use_spatial_partition_to_false(self):
        """
        Validates CollisionWorld constructor initializes useSpatialPartition_ to false.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        ctor_match = re.search(
            r'CollisionWorld::CollisionWorld\s*\(\s*\)\s*:([^{]+)\{',
            content,
            re.DOTALL
        )
        assert ctor_match is not None, "CollisionWorld constructor not found"
        init_list = ctor_match.group(1)
        assert 'useSpatialPartition_' in init_list and 'false' in init_list, \
            "Constructor must initialize useSpatialPartition_ to false"

    def test_constructor_initializes_world_bounds(self):
        """
        Validates CollisionWorld constructor initializes worldBounds_ with default values.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        ctor_match = re.search(
            r'CollisionWorld::CollisionWorld\s*\(\s*\)\s*:([^{]+)\{',
            content,
            re.DOTALL
        )
        assert ctor_match is not None, "CollisionWorld constructor not found"
        init_list = ctor_match.group(1)
        assert 'worldBounds_' in init_list, \
            "Constructor must initialize worldBounds_"

    def test_destructor_deletes_spatial_partition(self):
        """
        Validates CollisionWorld destructor deletes spatialPartition_.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        dtor_match = re.search(
            r'CollisionWorld::~CollisionWorld\s*\(\s*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert dtor_match is not None, "CollisionWorld destructor not found"
        dtor_body = dtor_match.group(1)
        assert 'delete' in dtor_body and 'spatialPartition_' in dtor_body, \
            "Destructor must delete spatialPartition_"

    def test_set_spatial_partition_bounds_implementation_exists(self):
        """
        Checks setSpatialPartitionBounds implementation exists.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        assert re.search(r'void\s+CollisionWorld::setSpatialPartitionBounds', content) is not None, \
            "setSpatialPartitionBounds implementation must exist"

    def test_enable_spatial_partition_implementation_exists(self):
        """
        Checks enableSpatialPartition implementation exists.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        assert re.search(r'void\s+CollisionWorld::enableSpatialPartition', content) is not None, \
            "enableSpatialPartition implementation must exist"

    def test_is_spatial_partition_enabled_implementation_exists(self):
        """
        Checks isSpatialPartitionEnabled implementation exists.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        assert re.search(r'bool\s+CollisionWorld::isSpatialPartitionEnabled', content) is not None, \
            "isSpatialPartitionEnabled implementation must exist"

    def test_rebuild_spatial_partition_implementation_exists(self):
        """
        Checks rebuildSpatialPartition implementation exists.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        assert re.search(r'void\s+CollisionWorld::rebuildSpatialPartition', content) is not None, \
            "rebuildSpatialPartition implementation must exist"
