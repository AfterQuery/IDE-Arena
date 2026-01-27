
import os
import pytest

PROJECT_DIR = "/app/project"
SRC_DIR = os.path.join(PROJECT_DIR, "src")
INCLUDE_DIR = os.path.join(PROJECT_DIR, "include")


def read_file(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "r") as f:
        return f.read()


def test_easeout_uses_multiplication():
    """Verifies EaseOut case has a multiplication operator in the return statement."""
    src_path = os.path.join(SRC_DIR, "core", "time_manager.cpp")
    content = read_file(src_path)
    lines = content.split('\n')
    in_easeout = False
    for line in lines:
        if 'EaseOut' in line and 'case' in line:
            in_easeout = True
            continue
        if in_easeout and 'return' in line:
            code_part = line.split('//')[0].strip()
            assert '*' in code_part
            break
        if in_easeout and 'case' in line:
            break


def test_easeout_uses_two_minus_formula():
    """Verifies EaseOut return contains 2 and subtraction for the (2-t) formula."""
    src_path = os.path.join(SRC_DIR, "core", "time_manager.cpp")
    content = read_file(src_path)
    lines = content.split('\n')
    in_easeout = False
    for line in lines:
        if 'EaseOut' in line and 'case' in line:
            in_easeout = True
            continue
        if in_easeout and 'return' in line:
            code_part = line.split('//')[0]
            assert ('2' in code_part and '-' in code_part)
            break
        if in_easeout and 'case' in line:
            break


def test_easeout_not_linear():
    """Verifies EaseOut doesnt just return t which would make it linear."""
    src_path = os.path.join(SRC_DIR, "core", "time_manager.cpp")
    content = read_file(src_path)
    lines = content.split('\n')
    in_easeout = False
    for line in lines:
        if 'EaseOut' in line and 'case' in line:
            in_easeout = True
            continue
        if in_easeout and 'return' in line:
            code_part = line.split('//')[0].strip()
            assert code_part != "return t;"
            break
        if in_easeout and 'case' in line:
            break


def test_easeout_complete_quadratic_formula():
    """Verifies EaseOut has all parts of t*(2-t) formula: multiply, 2, and subtract."""
    src_path = os.path.join(SRC_DIR, "core", "time_manager.cpp")
    content = read_file(src_path)
    lines = content.split('\n')
    in_easeout = False
    for line in lines:
        if 'EaseOut' in line and 'case' in line:
            in_easeout = True
            continue
        if in_easeout and 'return' in line:
            code_part = line.split('//')[0].strip()
            has_mult = '*' in code_part
            has_two = '2' in code_part
            has_minus = '-' in code_part
            assert has_mult and has_two and has_minus
            break
        if in_easeout and 'case' in line:
            break


def test_rotation_checks_positive_boundary():
    """Verifies rotation interpolation checks if angular diff exceeds 180 degrees."""
    src_path = os.path.join(SRC_DIR, "ecs", "component.cpp")
    content = read_file(src_path)
    assert "diff > 180" in content or "diff>180" in content


def test_rotation_checks_negative_boundary():
    """Verifies rotation interpolation checks if angular diff is below -180 degrees."""
    src_path = os.path.join(SRC_DIR, "ecs", "component.cpp")
    content = read_file(src_path)
    assert "diff < -180" in content or "diff<-180" in content


def test_rotation_subtracts_full_circle():
    """Verifies rotation subtracts 360 when diff is too large positive."""
    src_path = os.path.join(SRC_DIR, "ecs", "component.cpp")
    content = read_file(src_path)
    assert "diff -= 360" in content or "diff-=360" in content


def test_rotation_adds_full_circle():
    """Verifies rotation adds 360 when diff is too large negative."""
    src_path = os.path.join(SRC_DIR, "ecs", "component.cpp")
    content = read_file(src_path)
    assert "diff += 360" in content or "diff+=360" in content


def test_rotation_uses_loop_for_normalization():
    """Verifies rotation uses while loop to handle angles that need multiple wraps."""
    src_path = os.path.join(SRC_DIR, "ecs", "component.cpp")
    content = read_file(src_path)
    assert "while" in content and "diff > 180" in content


def test_blend_weight_calls_easing_function():
    """Verifies animation blending code calls the applyEasing function."""
    src_path = os.path.join(SRC_DIR, "rendering", "animation.cpp")
    content = read_file(src_path)
    assert "applyEasing" in content


def test_blend_weight_not_using_raw_time():
    """Verifies blend weight assignment uses easing not just raw time value."""
    src_path = os.path.join(SRC_DIR, "rendering", "animation.cpp")
    content = read_file(src_path)
    lines = content.split('\n')
    for line in lines:
        if 'blendWeight' in line and '=' in line and 'rawT' in line:
            code_part = line.split('//')[0]
            if 'rawT' in code_part and 'applyEasing' not in code_part:
                pytest.fail("Blend weight assigned raw time without easing")


def test_blend_weight_assignment_applies_easing():
    """Verifies the line that sets blendWeight includes applyEasing call."""
    src_path = os.path.join(SRC_DIR, "rendering", "animation.cpp")
    content = read_file(src_path)
    lines = content.split('\n')
    found_correct = False
    for line in lines:
        if 'blendWeight' in line and '=' in line:
            code_part = line.split('//')[0]
            if 'applyEasing' in code_part:
                found_correct = True
                break
    assert found_correct


def test_easing_type_enum_defined():
    """Verifies EasingType enum is declared in the time_manager header."""
    header_path = os.path.join(INCLUDE_DIR, "core", "time_manager.h")
    content = read_file(header_path)
    assert "EasingType" in content


def test_apply_easing_function_declared():
    """Verifies applyEasing function is declared in the time_manager header."""
    header_path = os.path.join(INCLUDE_DIR, "core", "time_manager.h")
    content = read_file(header_path)
    assert "applyEasing" in content
