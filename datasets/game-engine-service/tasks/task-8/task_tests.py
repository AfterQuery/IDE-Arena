import re
import pytest


def read_file_content(filepath: str) -> str:
    with open(filepath, 'r') as f:
        return f.read()


class TestTimeManagerInterpolationDeclarations:
    """Tests for interpolation declarations in TimeManager header."""

    def test_interpolation_alpha_member_declared(self):
        """
        Validates that TimeManager declares an interpolationAlpha_ member
        as a double to store the current interpolation factor.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_member = re.search(r'double\s+interpolationAlpha_\s*;', content)
        assert has_member is not None, \
            "TimeManager must have interpolationAlpha_ as double member"

    def test_set_interpolation_alpha_declared(self):
        """
        Verifies that TimeManager declares a setInterpolationAlpha method
        taking a double parameter.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_method = re.search(r'void\s+setInterpolationAlpha\s*\(\s*double', content)
        assert has_method is not None, \
            "TimeManager must declare setInterpolationAlpha(double) method"

    def test_get_interpolation_alpha_declared(self):
        """
        Confirms that TimeManager declares a getInterpolationAlpha method
        returning a double.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_method = re.search(r'double\s+getInterpolationAlpha\s*\(\s*\)', content)
        assert has_method is not None, \
            "TimeManager must declare getInterpolationAlpha() method"

    def test_calculate_interpolation_alpha_declared(self):
        """
        Validates that TimeManager declares a calculateInterpolationAlpha method
        taking accumulator and fixedDt parameters.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_method = re.search(
            r'double\s+calculateInterpolationAlpha\s*\([^)]*double[^)]*double',
            content
        )
        assert has_method is not None, \
            "TimeManager must declare calculateInterpolationAlpha(double, double) method"


class TestTimeManagerInterpolationImplementations:
    """Tests for interpolation implementations in TimeManager source."""

    def test_constructor_initializes_interpolation_alpha(self):
        """
        Ensures the TimeManager constructor initializes interpolationAlpha_
        to 0.0 in the initializer list.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        has_init = re.search(r'interpolationAlpha_\s*\(\s*0\.0\s*\)', content)
        assert has_init is not None, \
            "Constructor must initialize interpolationAlpha_ to 0.0"

    def test_reset_clears_interpolation_alpha(self):
        """
        Verifies that the reset method sets interpolationAlpha_ to 0.0.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        reset_match = re.search(
            r'void\s+TimeManager::reset\s*\([^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert reset_match is not None, "reset method not found"
        
        reset_body = reset_match.group(1)
        has_reset = 'interpolationAlpha_' in reset_body and '0.0' in reset_body
        assert has_reset, \
            "reset must set interpolationAlpha_ to 0.0"

    def test_set_interpolation_alpha_clamps_value(self):
        """
        Confirms that setInterpolationAlpha clamps values between 0.0 and 1.0
        using std::max and std::min.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        method_match = re.search(
            r'void\s+TimeManager::setInterpolationAlpha\s*\([^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert method_match is not None, "setInterpolationAlpha method not found"
        
        method_body = method_match.group(1)
        has_clamp = 'max' in method_body and 'min' in method_body
        assert has_clamp, \
            "setInterpolationAlpha must clamp value using max and min"

    def test_calculate_interpolation_alpha_handles_zero_fixed_dt(self):
        """
        Validates that calculateInterpolationAlpha returns 0.0 when
        fixedDt is zero or negative to avoid division by zero.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        method_match = re.search(
            r'double\s+TimeManager::calculateInterpolationAlpha\s*\([^)]*\)[^{]*\{([\s\S]*?)^\}',
            content,
            re.MULTILINE
        )
        assert method_match is not None, "calculateInterpolationAlpha method not found"
        
        method_body = method_match.group(1)
        has_zero_check = '<= 0.0' in method_body or '<= 0' in method_body
        assert has_zero_check, \
            "calculateInterpolationAlpha must check for zero or negative fixedDt"


class TestInterpolatedPositionDeclarations:
    """Tests for InterpolatedPosition struct declarations in collision.h."""

    def test_interpolated_position_struct_declared(self):
        """
        Validates that collision.h declares the InterpolatedPosition struct.
        """
        content = read_file_content('project/include/physics/collision.h')
        
        has_struct = re.search(r'struct\s+InterpolatedPosition\s*\{', content)
        assert has_struct is not None, \
            "collision.h must declare InterpolatedPosition struct"

    def test_interpolated_position_has_previous_x_member(self):
        """
        Confirms that InterpolatedPosition has a previousX float member.
        """
        content = read_file_content('project/include/physics/collision.h')
        
        has_member = re.search(r'float\s+previousX\s*;', content)
        assert has_member is not None, \
            "InterpolatedPosition must have previousX float member"

    def test_interpolated_position_has_previous_y_member(self):
        """
        Confirms that InterpolatedPosition has a previousY float member.
        """
        content = read_file_content('project/include/physics/collision.h')
        
        has_member = re.search(r'float\s+previousY\s*;', content)
        assert has_member is not None, \
            "InterpolatedPosition must have previousY float member"

    def test_interpolated_position_has_current_x_member(self):
        """
        Confirms that InterpolatedPosition has a currentX float member.
        """
        content = read_file_content('project/include/physics/collision.h')
        
        has_member = re.search(r'float\s+currentX\s*;', content)
        assert has_member is not None, \
            "InterpolatedPosition must have currentX float member"

    def test_interpolated_position_has_current_y_member(self):
        """
        Confirms that InterpolatedPosition has a currentY float member.
        """
        content = read_file_content('project/include/physics/collision.h')
        
        has_member = re.search(r'float\s+currentY\s*;', content)
        assert has_member is not None, \
            "InterpolatedPosition must have currentY float member"

    def test_save_current_method_declared(self):
        """
        Validates that InterpolatedPosition declares saveCurrent method.
        """
        content = read_file_content('project/include/physics/collision.h')
        
        has_method = re.search(r'void\s+saveCurrent\s*\(\s*float\s+\w+\s*,\s*float', content)
        assert has_method is not None, \
            "InterpolatedPosition must declare saveCurrent(float, float) method"

    def test_get_interpolated_method_declared(self):
        """
        Confirms that InterpolatedPosition declares getInterpolated method
        with alpha, outX, and outY parameters.
        """
        content = read_file_content('project/include/physics/collision.h')
        
        has_method = re.search(
            r'void\s+getInterpolated\s*\(\s*float\s+\w+\s*,\s*float\s*&',
            content
        )
        assert has_method is not None, \
            "InterpolatedPosition must declare getInterpolated method"


class TestInterpolatedPositionImplementations:
    """Tests for InterpolatedPosition implementations in collision.cpp."""

    def test_default_constructor_initializes_to_zero(self):
        """
        Validates that InterpolatedPosition default constructor initializes
        all members to 0.0f.
        """
        content = read_file_content('project/src/physics/collision.cpp')
        
        ctor_match = re.search(
            r'InterpolatedPosition::InterpolatedPosition\s*\(\s*\)\s*:\s*([^{]+)\{',
            content,
            re.DOTALL
        )
        assert ctor_match is not None, "Default constructor not found"
        
        init_list = ctor_match.group(1)
        has_prev_x_init = 'previousX' in init_list and '0.0f' in init_list
        assert has_prev_x_init, \
            "Default constructor must initialize previousX to 0.0f"

    def test_save_current_updates_previous(self):
        """
        Confirms that saveCurrent updates previousX/Y from currentX/Y
        before setting new current values.
        """
        content = read_file_content('project/src/physics/collision.cpp')
        
        method_match = re.search(
            r'void\s+InterpolatedPosition::saveCurrent\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert method_match is not None, "saveCurrent method not found"
        
        method_body = method_match.group(1)
        has_prev_update = 'previousX' in method_body and 'currentX' in method_body
        assert has_prev_update, \
            "saveCurrent must update previousX from currentX"

    def test_get_interpolated_performs_lerp(self):
        """
        Validates that getInterpolated performs linear interpolation
        using the alpha parameter.
        """
        content = read_file_content('project/src/physics/collision.cpp')
        
        method_match = re.search(
            r'void\s+InterpolatedPosition::getInterpolated\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert method_match is not None, "getInterpolated method not found"
        
        method_body = method_match.group(1)
        has_lerp = 'previousX' in method_body and 'currentX' in method_body and 'alpha' in method_body
        assert has_lerp, \
            "getInterpolated must interpolate between previous and current"


class TestColliderEntryInterpolation:
    """Tests for ColliderEntry interpolation member in collision_world.h."""

    def test_collider_entry_has_interpolation_member(self):
        """
        Validates that ColliderEntry struct has an interpolation member
        of type InterpolatedPosition.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        
        has_member = re.search(r'InterpolatedPosition\s+interpolation\s*;', content)
        assert has_member is not None, \
            "ColliderEntry must have interpolation member of type InterpolatedPosition"


class TestCollisionWorldInterpolation:
    """Tests for CollisionWorld interpolation methods."""

    def test_save_positions_for_interpolation_declared(self):
        """
        Validates that CollisionWorld declares savePositionsForInterpolation method.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        
        has_method = re.search(r'void\s+savePositionsForInterpolation\s*\(\s*\)', content)
        assert has_method is not None, \
            "CollisionWorld must declare savePositionsForInterpolation() method"

    def test_get_interpolated_position_declared(self):
        """
        Confirms that CollisionWorld declares getInterpolatedPosition method
        with entityId, alpha, outX, and outY parameters.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        
        has_method = re.search(
            r'bool\s+getInterpolatedPosition\s*\(\s*EntityID',
            content
        )
        assert has_method is not None, \
            "CollisionWorld must declare getInterpolatedPosition method"

    def test_set_interpolation_enabled_declared(self):
        """
        Validates that CollisionWorld declares setInterpolationEnabled method.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        
        has_method = re.search(r'void\s+setInterpolationEnabled\s*\(\s*bool', content)
        assert has_method is not None, \
            "CollisionWorld must declare setInterpolationEnabled(bool) method"

    def test_is_interpolation_enabled_declared(self):
        """
        Confirms that CollisionWorld declares isInterpolationEnabled method.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        
        has_method = re.search(r'bool\s+isInterpolationEnabled\s*\(\s*\)', content)
        assert has_method is not None, \
            "CollisionWorld must declare isInterpolationEnabled() method"

    def test_interpolation_enabled_member_declared(self):
        """
        Validates that CollisionWorld has interpolationEnabled_ bool member.
        """
        content = read_file_content('project/include/physics/collision_world.h')
        
        has_member = re.search(r'bool\s+interpolationEnabled_\s*;', content)
        assert has_member is not None, \
            "CollisionWorld must have interpolationEnabled_ bool member"


class TestCollisionWorldInterpolationImplementations:
    """Tests for CollisionWorld interpolation implementations in collision_world.cpp."""

    def test_constructor_initializes_interpolation_enabled(self):
        """
        Ensures CollisionWorld constructor initializes interpolationEnabled_
        to false in the initializer list.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        has_init = re.search(r'interpolationEnabled_\s*\(\s*false\s*\)', content)
        assert has_init is not None, \
            "Constructor must initialize interpolationEnabled_ to false"

    def test_save_positions_iterates_colliders(self):
        """
        Validates that savePositionsForInterpolation iterates over colliders
        and calls saveCurrent on each.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        method_match = re.search(
            r'void\s+CollisionWorld::savePositionsForInterpolation\s*\(\s*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert method_match is not None, "savePositionsForInterpolation method not found"
        
        method_body = method_match.group(1)
        has_iteration = 'colliders_' in method_body and 'interpolation' in method_body
        assert has_iteration, \
            "savePositionsForInterpolation must iterate colliders and update interpolation"

    def test_get_interpolated_position_returns_false_for_invalid_entity(self):
        """
        Confirms that getInterpolatedPosition returns false when entity
        is not found in the collision world.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        method_match = re.search(
            r'bool\s+CollisionWorld::getInterpolatedPosition\s*\([^)]+\)[^{]*\{([\s\S]*?)^\}',
            content,
            re.MULTILINE
        )
        assert method_match is not None, "getInterpolatedPosition method not found"
        
        method_body = method_match.group(1)
        has_check = 'entityIndexMap_' in method_body and 'return false' in method_body
        assert has_check, \
            "getInterpolatedPosition must return false for invalid entity"

    def test_collider_entry_constructors_initialize_interpolation(self):
        """
        Validates that ColliderEntry constructors initialize the interpolation
        member with position values.
        """
        content = read_file_content('project/src/physics/collision_world.cpp')
        
        ctor_match = re.search(
            r'ColliderEntry::ColliderEntry\s*\(\s*EntityID\s+id\s*,\s*float\s+x\s*,\s*float\s+y\s*,\s*const[^)]+\)[^:]*:\s*([^{]+)\{',
            content,
            re.DOTALL
        )
        assert ctor_match is not None, "ColliderEntry constructor not found"
        
        init_list = ctor_match.group(1)
        has_interp_init = 'interpolation' in init_list
        assert has_interp_init, \
            "ColliderEntry constructor must initialize interpolation member"
