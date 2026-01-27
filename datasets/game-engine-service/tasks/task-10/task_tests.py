"""
Fixed Timestep Task Tests
"""

import re
import pytest


def read_file_content(filepath: str) -> str:
    """Read and return the contents of a source file."""
    with open(filepath, 'r') as f:
        return f.read()


class TestTimeManagerFixedTimestepDeclarations:
    """Tests for fixed timestep declarations in TimeManager header."""

    def test_fixed_delta_time_member_declared(self):
        """
        Validates that TimeManager declares a fixedDeltaTime_ member
        as a double to store the fixed physics timestep.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_member = re.search(r'double\s+fixedDeltaTime_\s*;', content)
        assert has_member is not None, \
            "TimeManager must have fixedDeltaTime_ as double member"

    def test_fixed_time_accumulator_member_declared(self):
        """
        Confirms that TimeManager declares a fixedTimeAccumulator_ member
        as a double to track accumulated time for fixed updates.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_member = re.search(r'double\s+fixedTimeAccumulator_\s*;', content)
        assert has_member is not None, \
            "TimeManager must have fixedTimeAccumulator_ as double member"

    def test_set_fixed_delta_time_declared(self):
        """
        Verifies that TimeManager declares a setFixedDeltaTime method
        taking a double parameter.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_method = re.search(r'void\s+setFixedDeltaTime\s*\(\s*double', content)
        assert has_method is not None, \
            "TimeManager must declare setFixedDeltaTime(double) method"

    def test_get_fixed_delta_time_declared(self):
        """
        Confirms that TimeManager declares a getFixedDeltaTime method
        returning a double.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_method = re.search(r'double\s+getFixedDeltaTime\s*\(\s*\)', content)
        assert has_method is not None, \
            "TimeManager must declare getFixedDeltaTime() method"

    def test_consume_fixed_time_step_declared(self):
        """
        Validates that TimeManager declares a consumeFixedTimeStep method
        returning a bool.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_method = re.search(r'bool\s+consumeFixedTimeStep\s*\(\s*\)', content)
        assert has_method is not None, \
            "TimeManager must declare consumeFixedTimeStep() method"

    def test_get_fixed_update_alpha_declared(self):
        """
        Confirms that TimeManager declares a getFixedUpdateAlpha method
        returning a double for interpolation.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_method = re.search(r'double\s+getFixedUpdateAlpha\s*\(\s*\)', content)
        assert has_method is not None, \
            "TimeManager must declare getFixedUpdateAlpha() method"


class TestTimeManagerFixedTimestepImplementations:
    """Tests for fixed timestep implementations in TimeManager source."""

    def test_constructor_initializes_fixed_delta_time(self):
        """
        Ensures the TimeManager constructor initializes fixedDeltaTime_
        in the initializer list.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        has_init = re.search(r'fixedDeltaTime_\s*\(', content)
        assert has_init is not None, \
            "Constructor must initialize fixedDeltaTime_ in initializer list"

    def test_constructor_initializes_fixed_time_accumulator(self):
        """
        Validates that the TimeManager constructor initializes 
        fixedTimeAccumulator_ to 0.0 in the initializer list.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        has_init = re.search(r'fixedTimeAccumulator_\s*\(\s*0\.0\s*\)', content)
        assert has_init is not None, \
            "Constructor must initialize fixedTimeAccumulator_ to 0.0"

    def test_update_accumulates_fixed_time(self):
        """
        Confirms that the update method adds deltaTime_ to 
        fixedTimeAccumulator_ using the += operator.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        update_match = re.search(
            r'void\s+TimeManager::update\s*\([^)]*\)[^{]*\{(.*?)^void\s+TimeManager::',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert update_match is not None, "update method not found"
        
        update_body = update_match.group(1)
        has_accumulate = 'fixedTimeAccumulator_' in update_body and '+=' in update_body
        assert has_accumulate, \
            "update must accumulate deltaTime_ into fixedTimeAccumulator_"

    def test_reset_clears_fixed_time_accumulator(self):
        """
        Verifies that the reset method sets fixedTimeAccumulator_ to 0.0.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        reset_match = re.search(
            r'void\s+TimeManager::reset\s*\([^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert reset_match is not None, "reset method not found"
        
        reset_body = reset_match.group(1)
        has_reset = 'fixedTimeAccumulator_' in reset_body and '0.0' in reset_body
        assert has_reset, \
            "reset must set fixedTimeAccumulator_ to 0.0"

    def test_consume_fixed_time_step_subtracts(self):
        """
        Ensures consumeFixedTimeStep subtracts fixedDeltaTime_ from
        fixedTimeAccumulator_ when enough time has accumulated.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        func_match = re.search(
            r'bool\s+TimeManager::consumeFixedTimeStep\s*\([^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert func_match is not None, "consumeFixedTimeStep method not found"
        
        func_body = func_match.group(1)
        has_subtract = '-=' in func_body and 'fixedDeltaTime_' in func_body
        assert has_subtract, \
            "consumeFixedTimeStep must subtract fixedDeltaTime_ from accumulator"

    def test_get_fixed_update_alpha_divides(self):
        """
        Validates that getFixedUpdateAlpha divides fixedTimeAccumulator_
        by fixedDeltaTime_ to compute the interpolation factor.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        func_match = re.search(
            r'double\s+TimeManager::getFixedUpdateAlpha\s*\([^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert func_match is not None, "getFixedUpdateAlpha method not found"
        
        func_body = func_match.group(1)
        has_divide = '/' in func_body and 'fixedDeltaTime_' in func_body
        assert has_divide, \
            "getFixedUpdateAlpha must divide accumulator by fixedDeltaTime_"


class TestPhysicsStateComponentDeclaration:
    """Tests for PhysicsStateComponent class declaration."""

    def test_physics_state_component_class_declared(self):
        """
        Validates that PhysicsStateComponent class is declared in the header
        inheriting from ComponentBase<PhysicsStateComponent>.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        has_class = re.search(
            r'class\s+PhysicsStateComponent\s*:\s*public\s+ComponentBase\s*<\s*PhysicsStateComponent\s*>',
            content
        )
        assert has_class is not None, \
            "PhysicsStateComponent must be declared inheriting from ComponentBase"

    def test_previous_position_members_declared(self):
        """
        Confirms PhysicsStateComponent has previousX_ and previousY_ members
        declared as floats to store the previous physics state.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        class_match = re.search(
            r'class\s+PhysicsStateComponent[^{]*\{(.*?)\};',
            content,
            re.DOTALL
        )
        assert class_match is not None, "PhysicsStateComponent class not found"
        
        class_body = class_match.group(1)
        has_prev_x = re.search(r'float\s+previousX_\s*;', class_body)
        has_prev_y = re.search(r'float\s+previousY_\s*;', class_body)
        assert has_prev_x and has_prev_y, \
            "PhysicsStateComponent must have previousX_ and previousY_ as float members"

    def test_save_state_method_declared(self):
        """
        Verifies that PhysicsStateComponent declares a saveState method
        taking x and y float parameters.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        has_method = re.search(
            r'void\s+saveState\s*\(\s*float\s+\w+\s*,\s*float',
            content
        )
        assert has_method is not None, \
            "PhysicsStateComponent must declare saveState(float, float) method"

    def test_get_interpolated_position_declared(self):
        """
        Confirms that PhysicsStateComponent declares a getInterpolatedPosition
        method taking alpha and position parameters with output references.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        has_method = re.search(
            r'void\s+getInterpolatedPosition\s*\(',
            content
        )
        assert has_method is not None, \
            "PhysicsStateComponent must declare getInterpolatedPosition method"


class TestPhysicsStateComponentMethods:
    """Tests for PhysicsStateComponent method implementations."""

    def test_save_state_assigns_previous_values(self):
        """
        Ensures saveState implementation assigns the x and y parameters
        to previousX_ and previousY_ members.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        func_match = re.search(
            r'void\s+PhysicsStateComponent::saveState\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert func_match is not None, "saveState method not found"
        
        func_body = func_match.group(1)
        assigns_x = 'previousX_' in func_body and '=' in func_body
        assigns_y = 'previousY_' in func_body
        assert assigns_x and assigns_y, \
            "saveState must assign parameters to previousX_ and previousY_"

    def test_get_interpolated_position_uses_alpha(self):
        """
        Validates that getInterpolatedPosition uses the alpha parameter
        to interpolate between previous and current positions.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        func_match = re.search(
            r'void\s+PhysicsStateComponent::getInterpolatedPosition\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert func_match is not None, "getInterpolatedPosition method not found"
        
        func_body = func_match.group(1)
        uses_alpha = 'alpha' in func_body
        uses_previous = 'previousX_' in func_body or 'previousY_' in func_body
        assert uses_alpha and uses_previous, \
            "getInterpolatedPosition must use alpha and previous position values"

    def test_get_previous_x_returns_member(self):
        """
        Confirms getPreviousX returns the previousX_ member value.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        func_match = re.search(
            r'float\s+PhysicsStateComponent::getPreviousX\s*\([^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert func_match is not None, "getPreviousX method not found"
        
        func_body = func_match.group(1)
        returns_member = 'previousX_' in func_body and 'return' in func_body
        assert returns_member, \
            "getPreviousX must return previousX_ member"

    def test_get_previous_y_returns_member(self):
        """
        Confirms getPreviousY returns the previousY_ member value.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        func_match = re.search(
            r'float\s+PhysicsStateComponent::getPreviousY\s*\([^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert func_match is not None, "getPreviousY method not found"
        
        func_body = func_match.group(1)
        returns_member = 'previousY_' in func_body and 'return' in func_body
        assert returns_member, \
            "getPreviousY must return previousY_ member"
