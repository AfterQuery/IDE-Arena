"""
Component Serialization Task Tests
"""

import re
import pytest


def read_file_content(filepath: str) -> str:
    """Read and return the contents of a source file."""
    with open(filepath, 'r') as f:
        return f.read()


class TestTransformComponentSerialization:
    """Tests for TransformComponent serialize and deserialize methods."""

    def test_transform_has_serialize_method(self):
        """
        Verifies TransformComponent declares a serialize method that returns
        a string containing the position and scale fields.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        has_serialize = re.search(
            r'std::string\s+TransformComponent::serialize\s*\(\s*\)',
            content
        )
        assert has_serialize is not None, \
            "TransformComponent must have serialize() method returning std::string"

    def test_transform_has_deserialize_method(self):
        """
        Verifies TransformComponent declares a static deserialize method
        that accepts a const string reference parameter.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        has_deserialize = re.search(
            r'TransformComponent\s+TransformComponent::deserialize\s*\(\s*const\s+std::string\s*&',
            content
        )
        assert has_deserialize is not None, \
            "TransformComponent must have static deserialize(const std::string&) method"

    def test_transform_serialize_includes_scale_fields(self):
        """
        Confirms TransformComponent serialize output contains both scaleX
        and scaleY field identifiers in the serialized string.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'std::string\s+TransformComponent::serialize\s*\(\s*\)[^{]*\{(.*?)\n\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "serialize method not found"
        
        function_body = function_match.group(1)
        has_scale_x = 'scaleX' in function_body
        has_scale_y = 'scaleY' in function_body
        assert has_scale_x and has_scale_y, \
            "TransformComponent serialize must include scaleX and scaleY fields"

    def test_transform_serialize_includes_rotation(self):
        """
        Validates that TransformComponent serialize method includes the
        rotation field in its serialized output.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'std::string\s+TransformComponent::serialize\s*\(\s*\)[^{]*\{(.*?)\n\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "serialize method not found"
        
        function_body = function_match.group(1)
        has_rotation = 'rotation' in function_body
        assert has_rotation, \
            "TransformComponent serialize must include rotation field"

    def test_transform_deserialize_uses_stringstream(self):
        """
        Confirms TransformComponent deserialize uses stringstream for
        parsing the serialized data.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'TransformComponent\s+TransformComponent::deserialize\s*\([^)]+\)[^{]*\{(.*?)\n\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "deserialize method not found"
        
        function_body = function_match.group(1)
        has_stringstream = 'istringstream' in function_body or 'stringstream' in function_body
        assert has_stringstream, \
            "TransformComponent deserialize should use stringstream for parsing"


class TestTagComponentSerialization:
    """Tests for TagComponent serialize and deserialize methods."""

    def test_tag_has_serialize_method(self):
        """
        Verifies TagComponent has a serialize method that includes the tag
        field identifier in its output.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'std::string\s+TagComponent::serialize\s*\(\s*\)[^{]*\{(.*?)\n\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, \
            "TagComponent must have serialize() method"
        
        function_body = function_match.group(1)
        has_tag = 'tag' in function_body.lower()
        assert has_tag, "TagComponent serialize must include tag field"

    def test_tag_has_deserialize_method(self):
        """
        Confirms TagComponent has a static deserialize method that accepts
        a const string reference and returns a TagComponent.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        has_deserialize = re.search(
            r'TagComponent\s+TagComponent::deserialize\s*\(\s*const\s+std::string\s*&',
            content
        )
        assert has_deserialize is not None, \
            "TagComponent must have static deserialize(const std::string&) method"

    def test_tag_serialize_declaration_in_header(self):
        """
        Confirms TagComponent serialize method is declared in the header
        file with correct return type.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        tag_class_match = re.search(
            r'class\s+TagComponent[^{]*\{(.*?)\};',
            content,
            re.DOTALL
        )
        assert tag_class_match is not None, "TagComponent class not found"
        
        class_body = tag_class_match.group(1)
        has_serialize_decl = 'serialize' in class_body
        assert has_serialize_decl, \
            "TagComponent must declare serialize() in header file"


class TestSpriteSerialization:
    """Tests for Sprite serialize and deserialize methods."""

    def test_sprite_has_serialize_method(self):
        """
        Verifies Sprite class has a serialize method that returns a string.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        
        has_serialize = re.search(
            r'std::string\s+serialize\s*\(\s*\)',
            content
        )
        assert has_serialize is not None, \
            "Sprite must have serialize() method returning std::string"

    def test_sprite_has_deserialize_method(self):
        """
        Confirms Sprite class has a static deserialize method accepting
        a const string reference.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        
        has_deserialize = re.search(
            r'static\s+Sprite\s+deserialize\s*\(\s*const\s+std::string\s*&',
            content
        )
        assert has_deserialize is not None, \
            "Sprite must have static deserialize(const std::string&) method"

    def test_sprite_serialize_includes_rect_dimensions(self):
        """
        Validates that Sprite serialize method includes the sourceRect
        dimensions by checking for width and height references.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        
        function_match = re.search(
            r'std::string\s+serialize\s*\(\s*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "serialize method not found"
        
        function_body = function_match.group(1)
        has_width = 'width' in function_body.lower() or 'sourceRect_' in function_body
        has_height = 'height' in function_body.lower() or 'sourceRect_' in function_body
        assert has_width and has_height, \
            "Sprite serialize must include sourceRect dimensions"

    def test_sprite_serialize_uses_stringstream(self):
        """
        Confirms Sprite serialize uses ostringstream for building the
        serialized output string.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        
        has_ostringstream = 'ostringstream' in content
        assert has_ostringstream, \
            "Sprite serialize should use ostringstream for building output"
