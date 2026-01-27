import re
import pytest


def read_file_content(filepath: str) -> str:
    with open(filepath, 'r') as f:
        return f.read()


class TestSpriteBatchDeclarations:

    def test_sprite_batch_struct_declared(self):
        """
        Checks that SpriteBatch struct is declared in sprite.h.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'struct\s+SpriteBatch\s*\{', content) is not None, \
            "SpriteBatch struct must be declared"

    def test_sprite_batch_has_default_constructor(self):
        """
        Checks SpriteBatch declares default constructor.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'SpriteBatch\s*\(\s*\)\s*;', content) is not None, \
            "SpriteBatch must declare default constructor"

    def test_sprite_batch_has_texture_id_constructor(self):
        """
        Checks SpriteBatch declares constructor taking texture ID.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'explicit\s+SpriteBatch\s*\(\s*const\s+std::string\s*&', content) is not None, \
            "SpriteBatch must declare explicit constructor with const std::string&"

    def test_sprite_batch_has_texture_id_member(self):
        """
        Validates SpriteBatch has textureId string member.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'std::string\s+textureId\s*;', content) is not None, \
            "SpriteBatch must have textureId member"

    def test_sprite_batch_has_sprites_vector_member(self):
        """
        Validates SpriteBatch has sprites vector member.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'std::vector<Sprite>\s+sprites\s*;', content) is not None, \
            "SpriteBatch must have sprites vector member"

    def test_sprite_batch_has_max_batch_size_member(self):
        """
        Validates SpriteBatch has maxBatchSize size_t member.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'size_t\s+maxBatchSize\s*;', content) is not None, \
            "SpriteBatch must have maxBatchSize member"

    def test_sprite_batch_has_auto_flush_member(self):
        """
        Validates SpriteBatch has autoFlush bool member.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'bool\s+autoFlush\s*;', content) is not None, \
            "SpriteBatch must have autoFlush member"

    def test_sprite_batch_has_add_method(self):
        """
        Checks SpriteBatch declares add method taking const Sprite reference.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'void\s+add\s*\(\s*const\s+Sprite\s*&', content) is not None, \
            "SpriteBatch must declare add(const Sprite&) method"

    def test_sprite_batch_has_flush_method(self):
        """
        Checks SpriteBatch declares flush method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'void\s+flush\s*\(\s*\)', content) is not None, \
            "SpriteBatch must declare flush() method"

    def test_sprite_batch_has_clear_method(self):
        """
        Checks SpriteBatch declares clear method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'void\s+clear\s*\(\s*\)', content) is not None, \
            "SpriteBatch must declare clear() method"

    def test_sprite_batch_has_get_count_method(self):
        """
        Checks SpriteBatch declares getCount method returning size_t.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'size_t\s+getCount\s*\(\s*\)\s*const', content) is not None, \
            "SpriteBatch must declare getCount() const method"

    def test_sprite_batch_has_get_texture_id_method(self):
        """
        Checks SpriteBatch declares getTextureId method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'const\s+std::string\s*&\s+getTextureId\s*\(\s*\)\s*const', content) is not None, \
            "SpriteBatch must declare getTextureId() const method"

    def test_sprite_batch_has_is_empty_method(self):
        """
        Checks SpriteBatch declares isEmpty method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'bool\s+isEmpty\s*\(\s*\)\s*const', content) is not None, \
            "SpriteBatch must declare isEmpty() const method"

    def test_sprite_batch_has_is_full_method(self):
        """
        Checks SpriteBatch declares isFull method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'bool\s+isFull\s*\(\s*\)\s*const', content) is not None, \
            "SpriteBatch must declare isFull() const method"


class TestBatchRendererDeclarations:

    def test_batch_renderer_class_declared(self):
        """
        Validates BatchRenderer class is declared in sprite.h.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'class\s+BatchRenderer\s*\{', content) is not None, \
            "BatchRenderer class must be declared"

    def test_batch_renderer_has_batch_size_constructor(self):
        """
        Checks BatchRenderer declares constructor taking batch size.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'explicit\s+BatchRenderer\s*\(\s*size_t', content) is not None, \
            "BatchRenderer must declare explicit constructor with size_t parameter"

    def test_batch_renderer_has_batches_member(self):
        """
        Checks BatchRenderer has batches_ vector member.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'std::vector<SpriteBatch>\s+batches_\s*;', content) is not None, \
            "BatchRenderer must have batches_ vector member"

    def test_batch_renderer_has_batch_indices_member(self):
        """
        Checks BatchRenderer has batchIndices_ map member.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'std::unordered_map<std::string,\s*size_t>\s+batchIndices_\s*;', content) is not None, \
            "BatchRenderer must have batchIndices_ map member"

    def test_batch_renderer_has_default_batch_size_member(self):
        """
        Checks BatchRenderer has defaultBatchSize_ size_t member.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'size_t\s+defaultBatchSize_\s*;', content) is not None, \
            "BatchRenderer must have defaultBatchSize_ member"

    def test_batch_renderer_has_submit_method(self):
        """
        Validates BatchRenderer declares submit method taking const Sprite reference.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'void\s+submit\s*\(\s*const\s+Sprite\s*&', content) is not None, \
            "BatchRenderer must declare submit(const Sprite&) method"

    def test_batch_renderer_has_flush_method(self):
        """
        Validates BatchRenderer declares flush method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'void\s+flush\s*\(\s*\)', content) is not None, \
            "BatchRenderer must declare flush() method"

    def test_batch_renderer_has_flush_batch_method(self):
        """
        Validates BatchRenderer declares flushBatch method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'void\s+flushBatch\s*\(\s*const\s+std::string\s*&', content) is not None, \
            "BatchRenderer must declare flushBatch(const std::string&) method"

    def test_batch_renderer_has_get_batch_count_method(self):
        """
        Validates BatchRenderer declares getBatchCount method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'size_t\s+getBatchCount\s*\(\s*\)', content) is not None, \
            "BatchRenderer must declare getBatchCount() method"

    def test_batch_renderer_has_get_total_sprite_count_method(self):
        """
        Validates BatchRenderer declares getTotalSpriteCount method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'size_t\s+getTotalSpriteCount\s*\(\s*\)', content) is not None, \
            "BatchRenderer must declare getTotalSpriteCount() method"

    def test_batch_renderer_has_set_default_batch_size_method(self):
        """
        Validates BatchRenderer declares setDefaultBatchSize method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'void\s+setDefaultBatchSize\s*\(\s*size_t', content) is not None, \
            "BatchRenderer must declare setDefaultBatchSize(size_t) method"

    def test_batch_renderer_has_get_default_batch_size_method(self):
        """
        Validates BatchRenderer declares getDefaultBatchSize method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'size_t\s+getDefaultBatchSize\s*\(\s*\)', content) is not None, \
            "BatchRenderer must declare getDefaultBatchSize() method"

    def test_batch_renderer_has_clear_method(self):
        """
        Validates BatchRenderer declares clear method.
        """
        content = read_file_content('project/include/rendering/sprite.h')
        assert re.search(r'void\s+clear\s*\(\s*\)', content) is not None, \
            "BatchRenderer must declare clear() method"


class TestAnimationFrameBatchId:

    def test_animation_frame_has_batch_id_member(self):
        """
        Validates AnimationFrame struct has batchId int member.
        """
        content = read_file_content('project/include/rendering/animation.h')
        assert re.search(r'int\s+batchId\s*;', content) is not None, \
            "AnimationFrame must have batchId int member"


class TestAnimationTextureAtlas:

    def test_animation_has_texture_atlas_id_member(self):
        """
        Validates Animation class has textureAtlasId_ string member.
        """
        content = read_file_content('project/include/rendering/animation.h')
        assert re.search(r'std::string\s+textureAtlasId_\s*;', content) is not None, \
            "Animation must have textureAtlasId_ member"

    def test_animation_has_set_texture_atlas_id_method(self):
        """
        Checks Animation declares setTextureAtlasId method.
        """
        content = read_file_content('project/include/rendering/animation.h')
        assert re.search(r'void\s+setTextureAtlasId\s*\(\s*const\s+std::string\s*&', content) is not None, \
            "Animation must declare setTextureAtlasId method"

    def test_animation_has_get_texture_atlas_id_method(self):
        """
        Checks Animation declares getTextureAtlasId method.
        """
        content = read_file_content('project/include/rendering/animation.h')
        assert re.search(r'const\s+std::string\s*&\s+getTextureAtlasId\s*\(\s*\)', content) is not None, \
            "Animation must declare getTextureAtlasId method"


class TestAnimationImplementations:

    def test_animation_default_constructor_initializes_texture_atlas_id(self):
        """
        Validates Animation default constructor initializes textureAtlasId_ in initializer list.
        """
        content = read_file_content('project/src/rendering/animation.cpp')
        ctor_match = re.search(
            r'Animation::Animation\s*\(\s*\)\s*:([^{]+)\{',
            content,
            re.DOTALL
        )
        assert ctor_match is not None, "Default constructor not found"
        init_list = ctor_match.group(1)
        assert 'textureAtlasId_' in init_list, \
            "Default constructor must initialize textureAtlasId_ in initializer list"

    def test_animation_name_constructor_initializes_texture_atlas_id(self):
        """
        Validates Animation(name) constructor initializes textureAtlasId_ in initializer list.
        """
        content = read_file_content('project/src/rendering/animation.cpp')
        ctor_match = re.search(
            r'Animation::Animation\s*\(\s*const\s+std::string\s*&[^)]*\)\s*:([^{]+)\{',
            content,
            re.DOTALL
        )
        assert ctor_match is not None, "Constructor with name parameter not found"
        init_list = ctor_match.group(1)
        assert 'textureAtlasId_' in init_list, \
            "Constructor must initialize textureAtlasId_ in initializer list"

    def test_set_texture_atlas_id_implementation_exists(self):
        """
        Checks setTextureAtlasId implementation exists in animation.cpp.
        """
        content = read_file_content('project/src/rendering/animation.cpp')
        assert re.search(r'void\s+Animation::setTextureAtlasId', content) is not None, \
            "setTextureAtlasId implementation must exist"

    def test_get_texture_atlas_id_implementation_exists(self):
        """
        Checks getTextureAtlasId implementation exists in animation.cpp.
        """
        content = read_file_content('project/src/rendering/animation.cpp')
        assert re.search(r'const\s+std::string\s*&\s+Animation::getTextureAtlasId', content) is not None, \
            "getTextureAtlasId implementation must exist"
