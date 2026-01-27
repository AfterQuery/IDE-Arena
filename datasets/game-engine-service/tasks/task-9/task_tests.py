import pytest
import os
import re

COMPONENT_H = "project/include/ecs/component.h"
COMPONENT_CPP = "project/src/ecs/component.cpp"
TIME_MANAGER_H = "project/include/core/time_manager.h"
TIME_MANAGER_CPP = "project/src/core/time_manager.cpp"

def read_file(path):
    """Read file content from the project directory."""
    base = os.environ.get("PROJECT_ROOT", "/app")
    full_path = os.path.join(base, path)
    with open(full_path, "r") as f:
        return f.read()


class TestMemoryPoolDeclarations:
    """Tests for MemoryPool template class declarations in component.h"""

    def test_memorypool_template_class_declared(self):
        """MemoryPool template class is declared with template<typename T>"""
        content = read_file(COMPONENT_H)
        assert re.search(r'template\s*<\s*typename\s+T\s*>\s*class\s+MemoryPool', content), \
            "MemoryPool template class declaration not found"

    def test_memorypool_has_pool_vector_member(self):
        """MemoryPool has pool_ member as vector of T pointers"""
        content = read_file(COMPONENT_H)
        assert re.search(r'std::vector\s*<\s*T\s*\*\s*>\s+pool_', content), \
            "pool_ vector member not found in MemoryPool"

    def test_memorypool_has_freelist_vector_member(self):
        """MemoryPool has freeList_ member as vector of T pointers"""
        content = read_file(COMPONENT_H)
        assert re.search(r'std::vector\s*<\s*T\s*\*\s*>\s+freeList_', content), \
            "freeList_ vector member not found in MemoryPool"

    def test_memorypool_has_allocatedcount_member(self):
        """MemoryPool has allocatedCount_ member of type size_t"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+allocatedCount_', content), \
            "allocatedCount_ member not found in MemoryPool"

    def test_memorypool_allocate_method_declared(self):
        """MemoryPool has allocate method returning T pointer"""
        content = read_file(COMPONENT_H)
        assert re.search(r'T\s*\*\s*allocate\s*\(\s*\)', content), \
            "allocate() method not declared in MemoryPool"

    def test_memorypool_deallocate_method_declared(self):
        """MemoryPool has deallocate method taking T pointer"""
        content = read_file(COMPONENT_H)
        assert re.search(r'void\s+deallocate\s*\(\s*T\s*\*', content), \
            "deallocate(T*) method not declared in MemoryPool"

    def test_memorypool_clear_method_declared(self):
        """MemoryPool has clear method"""
        content = read_file(COMPONENT_H)
        assert re.search(r'void\s+clear\s*\(\s*\)', content), \
            "clear() method not declared in MemoryPool"

    def test_memorypool_reserve_method_declared(self):
        """MemoryPool has reserve method taking size_t"""
        content = read_file(COMPONENT_H)
        assert re.search(r'void\s+reserve\s*\(\s*size_t', content), \
            "reserve(size_t) method not declared in MemoryPool"

    def test_memorypool_getcapacity_method_declared(self):
        """MemoryPool has getCapacity method returning size_t"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+getCapacity\s*\(\s*\)\s*const', content), \
            "getCapacity() method not declared in MemoryPool"

    def test_memorypool_getallocatedcount_method_declared(self):
        """MemoryPool has getAllocatedCount method returning size_t"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+getAllocatedCount\s*\(\s*\)\s*const', content), \
            "getAllocatedCount() method not declared in MemoryPool"

    def test_memorypool_getfreecount_method_declared(self):
        """MemoryPool has getFreeCount method returning size_t"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+getFreeCount\s*\(\s*\)\s*const', content), \
            "getFreeCount() method not declared in MemoryPool"

    def test_memorypool_contains_method_declared(self):
        """MemoryPool has contains method returning bool"""
        content = read_file(COMPONENT_H)
        assert re.search(r'bool\s+contains\s*\(\s*T\s*\*', content), \
            "contains(T*) method not declared in MemoryPool"


class TestPoolStatisticsDeclarations:
    """Tests for PoolStatistics class declarations in component.h"""

    def test_poolstatistics_class_declared(self):
        """PoolStatistics class is declared"""
        content = read_file(COMPONENT_H)
        assert re.search(r'class\s+PoolStatistics', content), \
            "PoolStatistics class declaration not found"

    def test_poolstatistics_has_totalallocs_member(self):
        """PoolStatistics has totalAllocations_ member"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+totalAllocations_', content), \
            "totalAllocations_ member not found in PoolStatistics"

    def test_poolstatistics_has_totaldeallocs_member(self):
        """PoolStatistics has totalDeallocations_ member"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+totalDeallocations_', content), \
            "totalDeallocations_ member not found in PoolStatistics"

    def test_poolstatistics_has_currentusage_member(self):
        """PoolStatistics has currentUsage_ member"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+currentUsage_', content), \
            "currentUsage_ member not found in PoolStatistics"

    def test_poolstatistics_has_peakusage_member(self):
        """PoolStatistics has peakUsage_ member"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+peakUsage_', content), \
            "peakUsage_ member not found in PoolStatistics"

    def test_poolstatistics_recordallocation_declared(self):
        """PoolStatistics has recordAllocation method"""
        content = read_file(COMPONENT_H)
        assert re.search(r'void\s+recordAllocation\s*\(\s*size_t', content), \
            "recordAllocation() method not declared"

    def test_poolstatistics_recorddeallocation_declared(self):
        """PoolStatistics has recordDeallocation method"""
        content = read_file(COMPONENT_H)
        assert re.search(r'void\s+recordDeallocation\s*\(\s*size_t', content), \
            "recordDeallocation() method not declared"

    def test_poolstatistics_gettotalallocations_declared(self):
        """PoolStatistics has getTotalAllocations method"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+getTotalAllocations\s*\(\s*\)\s*const', content), \
            "getTotalAllocations() method not declared"

    def test_poolstatistics_getcurrentusage_declared(self):
        """PoolStatistics has getCurrentUsage method"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+getCurrentUsage\s*\(\s*\)\s*const', content), \
            "getCurrentUsage() method not declared"

    def test_poolstatistics_getpeakusage_declared(self):
        """PoolStatistics has getPeakUsage method"""
        content = read_file(COMPONENT_H)
        assert re.search(r'size_t\s+getPeakUsage\s*\(\s*\)\s*const', content), \
            "getPeakUsage() method not declared"


class TestMemoryPoolImplementations:
    """Tests for MemoryPool implementations in component.cpp"""

    def test_memorypool_allocate_checks_freelist_empty(self):
        """allocate() checks if freeList is empty"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'freeList_\.empty\s*\(\s*\)', content), \
            "allocate() should check freeList_.empty()"

    def test_memorypool_allocate_uses_new(self):
        """allocate() creates new objects with new T()"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'new\s+T\s*\(\s*\)', content), \
            "allocate() should use new T()"

    def test_memorypool_allocate_pushes_to_pool(self):
        """allocate() pushes new objects to pool_"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'pool_\.push_back', content), \
            "allocate() should push to pool_"

    def test_memorypool_allocate_pops_from_freelist(self):
        """allocate() pops from freeList when available"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'freeList_\.pop_back\s*\(\s*\)', content), \
            "allocate() should pop from freeList_"

    def test_memorypool_deallocate_pushes_to_freelist(self):
        """deallocate() pushes pointer back to freeList"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'freeList_\.push_back', content), \
            "deallocate() should push to freeList_"

    def test_memorypool_clear_deletes_objects(self):
        """clear() deletes all objects in pool"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'delete\s+ptr', content), \
            "clear() should delete objects"

    def test_memorypool_template_instantiated_for_transform(self):
        """MemoryPool is explicitly instantiated for TransformComponent"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'template\s+class\s+MemoryPool\s*<\s*TransformComponent\s*>', content), \
            "MemoryPool should be instantiated for TransformComponent"

    def test_memorypool_template_instantiated_for_tag(self):
        """MemoryPool is explicitly instantiated for TagComponent"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'template\s+class\s+MemoryPool\s*<\s*TagComponent\s*>', content), \
            "MemoryPool should be instantiated for TagComponent"


class TestPoolStatisticsImplementations:
    """Tests for PoolStatistics implementations in component.cpp"""

    def test_poolstatistics_recordallocation_increments_counter(self):
        """recordAllocation increments totalAllocations_"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'totalAllocations_\s*\+\+', content), \
            "recordAllocation should increment totalAllocations_"

    def test_poolstatistics_recordallocation_adds_to_currentusage(self):
        """recordAllocation adds bytes to currentUsage_"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'currentUsage_\s*\+=', content), \
            "recordAllocation should add to currentUsage_"

    def test_poolstatistics_recordallocation_updates_peak(self):
        """recordAllocation updates peakUsage_ when current exceeds peak"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'peakUsage_\s*=\s*currentUsage_', content), \
            "recordAllocation should update peakUsage_"

    def test_poolstatistics_recorddeallocation_increments_counter(self):
        """recordDeallocation increments totalDeallocations_"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'totalDeallocations_\s*\+\+', content), \
            "recordDeallocation should increment totalDeallocations_"

    def test_poolstatistics_reset_zeros_allocations(self):
        """reset() sets totalAllocations_ to 0"""
        content = read_file(COMPONENT_CPP)
        assert re.search(r'totalAllocations_\s*=\s*0', content), \
            "reset() should zero totalAllocations_"


class TestTimeManagerPoolTracking:
    """Tests for frame allocation tracking in TimeManager"""

    def test_timemanager_has_frameallocations_member(self):
        """TimeManager has frameAllocations_ member"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'size_t\s+frameAllocations_', content), \
            "frameAllocations_ member not found in TimeManager"

    def test_timemanager_has_framedeallocations_member(self):
        """TimeManager has frameDeallocations_ member"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'size_t\s+frameDeallocations_', content), \
            "frameDeallocations_ member not found in TimeManager"

    def test_timemanager_recordpoolallocation_declared(self):
        """TimeManager has recordPoolAllocation method"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'void\s+recordPoolAllocation\s*\(\s*size_t', content), \
            "recordPoolAllocation() method not declared"

    def test_timemanager_recordpooldeallocation_declared(self):
        """TimeManager has recordPoolDeallocation method"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'void\s+recordPoolDeallocation\s*\(\s*size_t', content), \
            "recordPoolDeallocation() method not declared"

    def test_timemanager_getframeallocations_declared(self):
        """TimeManager has getFrameAllocations method"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'size_t\s+getFrameAllocations\s*\(\s*\)\s*const', content), \
            "getFrameAllocations() method not declared"

    def test_timemanager_getframedeallocations_declared(self):
        """TimeManager has getFrameDeallocations method"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'size_t\s+getFrameDeallocations\s*\(\s*\)\s*const', content), \
            "getFrameDeallocations() method not declared"

    def test_timemanager_resetframestats_declared(self):
        """TimeManager has resetFrameStats method"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'void\s+resetFrameStats\s*\(\s*\)', content), \
            "resetFrameStats() method not declared"


class TestTimeManagerPoolImplementations:
    """Tests for pool tracking implementations in time_manager.cpp"""

    def test_timemanager_constructor_inits_frameallocations(self):
        """TimeManager constructor initializes frameAllocations_ to 0"""
        content = read_file(TIME_MANAGER_CPP)
        assert re.search(r'frameAllocations_\s*\(\s*0\s*\)', content), \
            "Constructor should initialize frameAllocations_ to 0"

    def test_timemanager_constructor_inits_framedeallocations(self):
        """TimeManager constructor initializes frameDeallocations_ to 0"""
        content = read_file(TIME_MANAGER_CPP)
        assert re.search(r'frameDeallocations_\s*\(\s*0\s*\)', content), \
            "Constructor should initialize frameDeallocations_ to 0"

    def test_timemanager_reset_zeros_frameallocations(self):
        """reset() sets frameAllocations_ to 0"""
        content = read_file(TIME_MANAGER_CPP)
        assert re.search(r'frameAllocations_\s*=\s*0', content), \
            "reset() should zero frameAllocations_"

    def test_timemanager_reset_zeros_framedeallocations(self):
        """reset() sets frameDeallocations_ to 0"""
        content = read_file(TIME_MANAGER_CPP)
        assert re.search(r'frameDeallocations_\s*=\s*0', content), \
            "reset() should zero frameDeallocations_"

    def test_timemanager_recordpoolallocation_adds_bytes(self):
        """recordPoolAllocation adds bytes to frameAllocations_"""
        content = read_file(TIME_MANAGER_CPP)
        assert re.search(r'frameAllocations_\s*\+=', content), \
            "recordPoolAllocation should add to frameAllocations_"

    def test_timemanager_recordpooldeallocation_adds_bytes(self):
        """recordPoolDeallocation adds bytes to frameDeallocations_"""
        content = read_file(TIME_MANAGER_CPP)
        assert re.search(r'frameDeallocations_\s*\+=', content), \
            "recordPoolDeallocation should add to frameDeallocations_"


class TestPoolMemoryStatsStruct:
    """Tests for PoolMemoryStats struct"""

    def test_poolmemorystats_struct_declared(self):
        """PoolMemoryStats struct is declared in time_manager.h"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'struct\s+PoolMemoryStats', content), \
            "PoolMemoryStats struct not declared"

    def test_poolmemorystats_has_poolcount(self):
        """PoolMemoryStats has poolCount member"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'size_t\s+poolCount', content), \
            "poolCount member not found in PoolMemoryStats"

    def test_poolmemorystats_has_totalcapacity(self):
        """PoolMemoryStats has totalCapacity member"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'size_t\s+totalCapacity', content), \
            "totalCapacity member not found in PoolMemoryStats"

    def test_poolmemorystats_has_totalallocated(self):
        """PoolMemoryStats has totalAllocated member"""
        content = read_file(TIME_MANAGER_H)
        assert re.search(r'size_t\s+totalAllocated', content), \
            "totalAllocated member not found in PoolMemoryStats"

    def test_poolmemorystats_constructor_implemented(self):
        """PoolMemoryStats constructor is implemented"""
        content = read_file(TIME_MANAGER_CPP)
        assert re.search(r'PoolMemoryStats::PoolMemoryStats\s*\(\s*\)', content), \
            "PoolMemoryStats constructor not implemented"
