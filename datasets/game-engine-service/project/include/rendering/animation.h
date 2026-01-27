#ifndef ANIMATION_H
#define ANIMATION_H

#include "ecs/component.h"
#include "rendering/sprite.h"
#include <string>
#include <vector>
#include <unordered_map>
#include <functional>

namespace engine {

enum class AnimationPlayMode {
    Once,
    Loop,
    PingPong
};

struct BlendState {
    std::string sourceAnimation;
    std::string targetAnimation;
    float blendDuration;
    float blendTimer;
    float blendWeight;
    bool isBlending;

    BlendState() : blendDuration(0.0f), blendTimer(0.0f), blendWeight(0.0f), isBlending(false) {}
};

struct AnimationFrame {
    int frameIndex;
    float duration;
    Rect sourceRect;
    Vector2 offset;
    std::function<void()> callback;
};

class Animation {
public:
    Animation();
    Animation(const std::string& name);
    ~Animation();

    void setName(const std::string& name);
    const std::string& getName() const;

    void addFrame(const AnimationFrame& frame);
    void addFrame(int frameIndex, float duration);
    void addFrameRange(int startIndex, int endIndex, float frameDuration);

    void setFrameDuration(int index, float duration);
    void setAllFramesDuration(float duration);

    int getFrameCount() const;
    const AnimationFrame& getFrame(int index) const;
    AnimationFrame& getFrame(int index);

    void setPlayMode(AnimationPlayMode mode);
    AnimationPlayMode getPlayMode() const;

    void setSpeed(float speed);
    float getSpeed() const;

    float getTotalDuration() const;

    void setTextureId(const std::string& textureId);
    const std::string& getTextureId() const;

    void setFrameSize(float width, float height);
    float getFrameWidth() const;
    float getFrameHeight() const;

    void setGridSize(int columns, int rows);
    int getColumns() const;
    int getRows() const;

    Rect getFrameRect(int frameIndex) const;

private:
    std::string name_;
    std::string textureId_;
    std::vector<AnimationFrame> frames_;
    AnimationPlayMode playMode_;
    float speed_;

    float frameWidth_;
    float frameHeight_;
    int columns_;
    int rows_;
};

class AnimationController {
public:
    AnimationController();
    ~AnimationController();

    void addAnimation(const std::string& name, const Animation& animation);
    void removeAnimation(const std::string& name);
    Animation* getAnimation(const std::string& name);
    bool hasAnimation(const std::string& name) const;

    void play(const std::string& name, bool restart = false);
    void pause();
    void resume();
    void stop();

    bool isPlaying() const;
    bool isPaused() const;
    const std::string& getCurrentAnimationName() const;

    void update(float deltaTime);

    int getCurrentFrameIndex() const;
    const AnimationFrame* getCurrentFrame() const;
    float getNormalizedTime() const;

    void setOnAnimationEnd(std::function<void(const std::string&)> callback);
    void setOnFrameChange(std::function<void(int, int)> callback);

    Rect getCurrentSourceRect() const;
    Vector2 getCurrentOffset() const;

    void transitionTo(const std::string& animationName, float duration);
    void setBlendEasing(int easingType);
    float getBlendWeight() const;
    bool isBlending() const;
    const BlendState& getBlendState() const;

private:
    void advanceFrame();

    std::unordered_map<std::string, Animation> animations_;
    std::string currentAnimation_;
    bool isPlaying_;
    bool isPaused_;

    int currentFrameIndex_;
    float frameTimer_;
    bool isReversing_;

    std::function<void(const std::string&)> onAnimationEnd_;
    std::function<void(int, int)> onFrameChange_;

    BlendState blendState_;
    int blendEasingType_;
};

class AnimationComponent : public ComponentBase<AnimationComponent> {
public:
    AnimationComponent();
    ~AnimationComponent() override;

    AnimationController* getController();
    const AnimationController* getController() const;

    void addAnimation(const std::string& name, const Animation& animation);
    void play(const std::string& name, bool restart = false);
    void pause();
    void resume();
    void stop();

    void update(float deltaTime);

    Component* clone() const override;

private:
    AnimationController controller_;
};

class AnimationBuilder {
public:
    AnimationBuilder(const std::string& name);

    AnimationBuilder& setTexture(const std::string& textureId);
    AnimationBuilder& setFrameSize(float width, float height);
    AnimationBuilder& setGridSize(int columns, int rows);
    AnimationBuilder& setSpeed(float speed);
    AnimationBuilder& setPlayMode(AnimationPlayMode mode);
    AnimationBuilder& addFrame(int index, float duration = 0.1f);
    AnimationBuilder& addFrameRange(int start, int end, float duration = 0.1f);
    AnimationBuilder& addFrameCallback(int frameIndex, std::function<void()> callback);

    Animation build();

private:
    Animation animation_;
    std::vector<std::pair<int, std::function<void()>>> frameCallbacks_;
};

}

#endif
