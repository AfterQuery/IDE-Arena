"""
Event System Task Tests
"""

import re
import pytest


def read_file_content(filepath: str) -> str:
    """Read and return the contents of a source file."""
    with open(filepath, 'r') as f:
        return f.read()


class TestTimeManagerEventDeclarations:
    """Tests for event system declarations in TimeManager header."""

    def test_event_listeners_map_declared(self):
        """
        Validates that TimeManager declares an eventListeners_ member as an
        unordered_map with string keys and vector of function callbacks.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_map = re.search(
            r'std::unordered_map\s*<\s*std::string\s*,\s*std::vector\s*<\s*std::function',
            content
        )
        assert has_map is not None, \
            "TimeManager must have eventListeners_ as unordered_map<string, vector<function>>"

    def test_add_event_listener_declared(self):
        """
        Confirms TimeManager declares an addEventListener method that takes
        a string event name and a callback function.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_method = re.search(
            r'void\s+addEventListener\s*\(\s*(const\s+)?std::string',
            content
        )
        assert has_method is not None, \
            "TimeManager must declare addEventListener(string, callback) method"

    def test_dispatch_event_declared(self):
        """
        Verifies TimeManager declares a dispatchEvent method that takes
        a string event name parameter.
        """
        content = read_file_content('project/include/core/time_manager.h')
        
        has_method = re.search(
            r'void\s+dispatchEvent\s*\(\s*(const\s+)?std::string',
            content
        )
        assert has_method is not None, \
            "TimeManager must declare dispatchEvent(string) method"


class TestTimeManagerEventImplementations:
    """Tests for event method implementations in TimeManager source."""

    def test_add_event_listener_adds_to_map(self):
        """
        Ensures addEventListener implementation adds the callback to the
        eventListeners_ map for the given event name.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        function_match = re.search(
            r'void\s+TimeManager::addEventListener\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "addEventListener method not found"
        
        function_body = function_match.group(1)
        uses_map = 'eventListeners_' in function_body
        uses_push = 'push_back' in function_body or 'emplace_back' in function_body
        assert uses_map and uses_push, \
            "addEventListener must add callback to eventListeners_ using push_back"

    def test_dispatch_event_iterates_callbacks(self):
        """
        Validates that dispatchEvent implementation iterates through the
        callbacks registered for the event name and calls each one.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        function_match = re.search(
            r'void\s+TimeManager::dispatchEvent\s*\([^)]+\)[^{]*\{(.*?)^\}',
            content,
            re.DOTALL | re.MULTILINE
        )
        assert function_match is not None, "dispatchEvent method not found"
        
        function_body = function_match.group(1)
        has_loop = 'for' in function_body or 'while' in function_body
        uses_map = 'eventListeners_' in function_body
        assert has_loop and uses_map, \
            "dispatchEvent must iterate through eventListeners_ callbacks"

    def test_remove_event_listener_erases(self):
        """
        Confirms removeEventListener implementation erases the entry
        from eventListeners_ for the given event name.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        function_match = re.search(
            r'void\s+TimeManager::removeEventListener\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "removeEventListener method not found"
        
        function_body = function_match.group(1)
        uses_erase = 'erase' in function_body
        uses_map = 'eventListeners_' in function_body
        assert uses_erase and uses_map, \
            "removeEventListener must erase from eventListeners_"

    def test_has_event_listeners_checks_map(self):
        """
        Verifies hasEventListeners implementation checks if any callbacks
        exist in eventListeners_ for the given event name.
        """
        content = read_file_content('project/src/core/time_manager.cpp')
        
        function_match = re.search(
            r'bool\s+TimeManager::hasEventListeners\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "hasEventListeners method not found"
        
        function_body = function_match.group(1)
        uses_map = 'eventListeners_' in function_body
        checks_find = 'find' in function_body or 'count' in function_body or 'end()' in function_body
        assert uses_map and checks_find, \
            "hasEventListeners must check eventListeners_ using find or count"


class TestEventListenerComponentDeclaration:
    """Tests for EventListenerComponent class declaration."""

    def test_event_listener_component_class_declared(self):
        """
        Validates that EventListenerComponent class is declared in the header
        inheriting from ComponentBase<EventListenerComponent>.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        has_class = re.search(
            r'class\s+EventListenerComponent\s*:\s*public\s+ComponentBase\s*<\s*EventListenerComponent\s*>',
            content
        )
        assert has_class is not None, \
            "EventListenerComponent must be declared inheriting from ComponentBase"

    def test_event_names_vector_declared(self):
        """
        Confirms EventListenerComponent has an eventNames_ member declared
        as a vector of strings to store subscribed event names.
        """
        content = read_file_content('project/include/ecs/component.h')
        
        class_match = re.search(
            r'class\s+EventListenerComponent[^{]*\{(.*?)\};',
            content,
            re.DOTALL
        )
        assert class_match is not None, "EventListenerComponent class not found"
        
        class_body = class_match.group(1)
        has_vector = re.search(r'std::vector\s*<\s*std::string\s*>\s+eventNames_', class_body)
        assert has_vector is not None, \
            "EventListenerComponent must have eventNames_ as vector<string>"


class TestEventListenerComponentMethods:
    """Tests for EventListenerComponent method implementations."""

    def test_add_event_name_uses_push_back(self):
        """
        Ensures addEventName implementation uses push_back to append
        the event name to the eventNames_ vector.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'void\s+EventListenerComponent::addEventName\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "addEventName method not found"
        
        function_body = function_match.group(1)
        uses_push = 'push_back' in function_body or 'emplace_back' in function_body
        assert uses_push, \
            "addEventName must use push_back to add name to eventNames_"

    def test_remove_event_name_uses_erase(self):
        """
        Validates that removeEventName implementation uses remove/erase
        to take the event name out of the eventNames_ vector.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'void\s+EventListenerComponent::removeEventName\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "removeEventName method not found"
        
        function_body = function_match.group(1)
        uses_remove = 'remove' in function_body or 'erase' in function_body
        assert uses_remove, \
            "removeEventName must use remove or erase on eventNames_"

    def test_has_event_name_uses_find(self):
        """
        Confirms hasEventName implementation uses find to check whether
        the given event name exists in the eventNames_ vector.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'bool\s+EventListenerComponent::hasEventName\s*\([^)]+\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "hasEventName method not found"
        
        function_body = function_match.group(1)
        uses_find = 'find' in function_body
        assert uses_find, \
            "hasEventName must use find to check eventNames_"

    def test_clear_event_names_uses_clear(self):
        """
        Verifies that clearEventNames implementation calls clear on the
        eventNames_ vector to remove all entries.
        """
        content = read_file_content('project/src/ecs/component.cpp')
        
        function_match = re.search(
            r'void\s+EventListenerComponent::clearEventNames\s*\([^)]*\)[^{]*\{([^}]+)\}',
            content,
            re.DOTALL
        )
        assert function_match is not None, "clearEventNames method not found"
        
        function_body = function_match.group(1)
        uses_clear = 'clear' in function_body
        assert uses_clear, \
            "clearEventNames must call clear on eventNames_"
