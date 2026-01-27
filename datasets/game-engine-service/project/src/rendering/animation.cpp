#include "rendering/animation.h"
#include <algorithm>
#include "core/time_manager.h"

namespace engine {

Animation::Animation()
    : name_("")
    , textureId_("")
    , playMode_(AnimationPlayMode::Loop)
    , speed_(1.0f)
    , frameWidth_(32.0f)
    , frameHeight_(32.0f)
    , columns_(1)
    , rows_(1) {
}

Animation::Animation(const std::string& name)
    : name_(name)
    , textureId_("")
    , playMode_(AnimationPlayMode::Loop)
    , speed_(1.0f)
    , frameWidth_(32.0f)
    , frameHeight_(32.0f)
    , columns_(1)
    , rows_(1) {
}

Animation::~Animation() {}

void Animation::setName(const std::string& name) {
    name_ = name;
}

const std::string& Animation::getName() const {
    return name_;
}

void Animation::addFrame(const AnimationFrame& frame) {
    frames_.push_back(frame);
}

void Animation::addFrame(int frameIndex, float duration) {
    AnimationFrame frame;
    frame.frameIndex = frameIndex;
    frame.duration = duration;
    frame.sourceRect = getFrameRect(frameIndex);
    frame.offset = Vector2(0.0f, 0.0f);
    frame.callback = nullptr;
    frames_.push_back(frame);
}

void Animation::addFrameRange(int startIndex, int endIndex, float frameDuration) {
    int step = (startIndex <= endIndex) ? 1 : -1;
    for (int i = startIndex; i != endIndex + step; i += step) {
        addFrame(i, frameDuration);
    }
}

void Animation::setFrameDuration(int index, float duration) {
    if (index >= 0 && static_cast<size_t>(index) < frames_.size()) {
        frames_[index].duration = duration;
    }
}

void Animation::setAllFramesDuration(float duration) {
    for (auto& frame : frames_) {
        frame.duration = duration;
    }
}

int Animation::getFrameCount() const {
    return static_cast<int>(frames_.size());
}

const AnimationFrame& Animation::getFrame(int index) const {
    return frames_[index];
}

AnimationFrame& Animation::getFrame(int index) {
    return frames_[index];
}

void Animation::setPlayMode(AnimationPlayMode mode) {
    playMode_ = mode;
}

AnimationPlayMode Animation::getPlayMode() const {
    return playMode_;
}

void Animation::setSpeed(float speed) {
    speed_ = std::max(0.0f, speed);
}

float Animation::getSpeed() const {
    return speed_;
}

float Animation::getTotalDuration() const {
    float total = 0.0f;
    for (const auto& frame : frames_) {
        total += frame.duration;
    }
    return total / speed_;
}

void Animation::setTextureId(const std::string& textureId) {
    textureId_ = textureId;
}

const std::string& Animation::getTextureId() const {
    return textureId_;
}

void Animation::setFrameSize(float width, float height) {
    frameWidth_ = width;
    frameHeight_ = height;
}

float Animation::getFrameWidth() const {
    return frameWidth_;
}

float Animation::getFrameHeight() const {
    return frameHeight_;
}

void Animation::setGridSize(int columns, int rows) {
    columns_ = std::max(1, columns);
    rows_ = std::max(1, rows);
}

int Animation::getColumns() const {
    return columns_;
}

int Animation::getRows() const {
    return rows_;
}

Rect Animation::getFrameRect(int frameIndex) const {
    int col = frameIndex % columns_;
    int row = frameIndex / columns_;
    return Rect(col * frameWidth_, row * frameHeight_, frameWidth_, frameHeight_);
}

AnimationController::AnimationController()
    : currentAnimation_("")
    , isPlaying_(false)
    , isPaused_(false)
    , currentFrameIndex_(0)
    , frameTimer_(0.0f)
    , isReversing_(false)
    , onAnimationEnd_(nullptr)
    , onFrameChange_(nullptr)
    , blendEasingType_(0) {
}

AnimationController::~AnimationController() {}

void AnimationController::addAnimation(const std::string& name, const Animation& animation) {
    animations_[name] = animation;
}

void AnimationController::removeAnimation(const std::string& name) {
    animations_.erase(name);
    if (currentAnimation_ == name) {
        stop();
    }
}

Animation* AnimationController::getAnimation(const std::string& name) {
    auto it = animations_.find(name);
    return (it != animations_.end()) ? &it->second : nullptr;
}

bool AnimationController::hasAnimation(const std::string& name) const {
    return animations_.find(name) != animations_.end();
}

void AnimationController::play(const std::string& name, bool restart) {
    auto it = animations_.find(name);
    if (it == animations_.end()) {
        return;
    }

    if (currentAnimation_ == name && isPlaying_ && !restart) {
        return;
    }

    currentAnimation_ = name;
    isPlaying_ = true;
    isPaused_ = false;

    if (restart || currentAnimation_ != name) {
        currentFrameIndex_ = 0;
        frameTimer_ = 0.0f;
        isReversing_ = false;
    }
}

void AnimationController::pause() {
    isPaused_ = true;
}

void AnimationController::resume() {
    isPaused_ = false;
}

void AnimationController::stop() {
    isPlaying_ = false;
    isPaused_ = false;
    currentFrameIndex_ = 0;
    frameTimer_ = 0.0f;
    isReversing_ = false;
}

void AnimationController::transitionTo(const std::string& animationName, float duration) {
    if (animationName == currentAnimation_) {
        return;
    }
    if (animations_.find(animationName) == animations_.end()) {
        return;
    }
    if (duration <= 0.0f) {
        play(animationName, true);
        return;
    }
    blendState_.sourceAnimation = currentAnimation_;
    blendState_.targetAnimation = animationName;
    blendState_.blendDuration = duration;
    blendState_.blendTimer = 0.0f;
    blendState_.blendWeight = 0.0f;
    blendState_.isBlending = true;
}

void AnimationController::setBlendEasing(int easingType) { blendEasingType_ = easingType; }

float AnimationController::getBlendWeight() const { return blendState_.blendWeight; }
bool AnimationController::isBlending() const { return blendState_.isBlending; }
const BlendState& AnimationController::getBlendState() const { return blendState_; }

bool AnimationController::isPlaying() const {
    return isPlaying_ && !isPaused_;
}

bool AnimationController::isPaused() const {
    return isPaused_;
}

const std::string& AnimationController::getCurrentAnimationName() const {
    return currentAnimation_;
}

void AnimationController::update(float deltaTime) {
    if (!isPlaying_ || isPaused_ || currentAnimation_.empty()) {
        return;
    }

    if (blendState_.isBlending) {
        blendState_.blendTimer += deltaTime;
        float rawT = blendState_.blendTimer / blendState_.blendDuration;
        rawT = std::max(0.0f, std::min(1.0f, rawT));

        EasingType easing = static_cast<EasingType>(blendEasingType_);
        blendState_.blendWeight = rawT;

        if (blendState_.blendTimer >= blendState_.blendDuration) {
            currentAnimation_ = blendState_.targetAnimation;
            blendState_.isBlending = false;
            blendState_.blendWeight = 0.0f;
            currentFrameIndex_ = 0;
            frameTimer_ = 0.0f;
        }
    }

    auto it = animations_.find(currentAnimation_);
    if (it == animations_.end() || it->second.getFrameCount() == 0) {
        return;
    }

    Animation& anim = it->second;
    const AnimationFrame& frame = anim.getFrame(currentFrameIndex_);

    frameTimer_ += deltaTime * anim.getSpeed();

    if (frameTimer_ >= frame.duration) {
        frameTimer_ -= frame.duration;

        if (frame.callback) {
            frame.callback();
        }

        advanceFrame();
    }
}

int AnimationController::getCurrentFrameIndex() const {
    return currentFrameIndex_;
}

const AnimationFrame* AnimationController::getCurrentFrame() const {
    if (currentAnimation_.empty()) {
        return nullptr;
    }

    auto it = animations_.find(currentAnimation_);
    if (it == animations_.end() || it->second.getFrameCount() == 0) {
        return nullptr;
    }

    return &it->second.getFrame(currentFrameIndex_);
}

float AnimationController::getNormalizedTime() const {
    if (currentAnimation_.empty()) {
        return 0.0f;
    }

    auto it = animations_.find(currentAnimation_);
    if (it == animations_.end() || it->second.getFrameCount() == 0) {
        return 0.0f;
    }

    const Animation& anim = it->second;
    float total = anim.getTotalDuration();
    if (total <= 0.0f) {
        return 0.0f;
    }

    float elapsed = 0.0f;
    for (int i = 0; i < currentFrameIndex_; i++) {
        elapsed += anim.getFrame(i).duration;
    }
    elapsed += frameTimer_;

    return elapsed / total;
}

void AnimationController::setOnAnimationEnd(std::function<void(const std::string&)> callback) {
    onAnimationEnd_ = callback;
}

void AnimationController::setOnFrameChange(std::function<void(int, int)> callback) {
    onFrameChange_ = callback;
}

Rect AnimationController::getCurrentSourceRect() const {
    const AnimationFrame* frame = getCurrentFrame();
    if (frame) {
        return frame->sourceRect;
    }
    return Rect(0, 0, 0, 0);
}

Vector2 AnimationController::getCurrentOffset() const {
    const AnimationFrame* frame = getCurrentFrame();
    if (frame) {
        return frame->offset;
    }
    return Vector2(0.0f, 0.0f);
}

void AnimationController::advanceFrame() {
    auto it = animations_.find(currentAnimation_);
    if (it == animations_.end()) {
        return;
    }

    Animation& anim = it->second;
    int frameCount = anim.getFrameCount();
    int oldFrame = currentFrameIndex_;

    switch (anim.getPlayMode()) {
        case AnimationPlayMode::Once:
            if (currentFrameIndex_ < frameCount - 1) {
                currentFrameIndex_++;
            } else {
                isPlaying_ = false;
                if (onAnimationEnd_) {
                    onAnimationEnd_(currentAnimation_);
                }
            }
            break;

        case AnimationPlayMode::Loop:
            currentFrameIndex_ = (currentFrameIndex_ + 1) % frameCount;
            if (currentFrameIndex_ == 0 && onAnimationEnd_) {
                onAnimationEnd_(currentAnimation_);
            }
            break;

        case AnimationPlayMode::PingPong:
            if (isReversing_) {
                if (currentFrameIndex_ > 0) {
                    currentFrameIndex_--;
                } else {
                    isReversing_ = false;
                    currentFrameIndex_ = 1;
                    if (onAnimationEnd_) {
                        onAnimationEnd_(currentAnimation_);
                    }
                }
            } else {
                if (currentFrameIndex_ < frameCount - 1) {
                    currentFrameIndex_++;
                } else {
                    isReversing_ = true;
                    currentFrameIndex_ = frameCount - 2;
                }
            }
            break;
    }

    if (onFrameChange_ && oldFrame != currentFrameIndex_) {
        onFrameChange_(oldFrame, currentFrameIndex_);
    }
}

AnimationComponent::AnimationComponent() {}

AnimationComponent::~AnimationComponent() {}

AnimationController* AnimationComponent::getController() {
    return &controller_;
}

const AnimationController* AnimationComponent::getController() const {
    return &controller_;
}

void AnimationComponent::addAnimation(const std::string& name, const Animation& animation) {
    controller_.addAnimation(name, animation);
}

void AnimationComponent::play(const std::string& name, bool restart) {
    controller_.play(name, restart);
}

void AnimationComponent::pause() {
    controller_.pause();
}

void AnimationComponent::resume() {
    controller_.resume();
}

void AnimationComponent::stop() {
    controller_.stop();
}

void AnimationComponent::update(float deltaTime) {
    controller_.update(deltaTime);
}

Component* AnimationComponent::clone() const {
    auto* copy = new AnimationComponent();
    return copy;
}

AnimationBuilder::AnimationBuilder(const std::string& name)
    : animation_(name) {
}

AnimationBuilder& AnimationBuilder::setTexture(const std::string& textureId) {
    animation_.setTextureId(textureId);
    return *this;
}

AnimationBuilder& AnimationBuilder::setFrameSize(float width, float height) {
    animation_.setFrameSize(width, height);
    return *this;
}

AnimationBuilder& AnimationBuilder::setGridSize(int columns, int rows) {
    animation_.setGridSize(columns, rows);
    return *this;
}

AnimationBuilder& AnimationBuilder::setSpeed(float speed) {
    animation_.setSpeed(speed);
    return *this;
}

AnimationBuilder& AnimationBuilder::setPlayMode(AnimationPlayMode mode) {
    animation_.setPlayMode(mode);
    return *this;
}

AnimationBuilder& AnimationBuilder::addFrame(int index, float duration) {
    animation_.addFrame(index, duration);
    return *this;
}

AnimationBuilder& AnimationBuilder::addFrameRange(int start, int end, float duration) {
    animation_.addFrameRange(start, end, duration);
    return *this;
}

AnimationBuilder& AnimationBuilder::addFrameCallback(int frameIndex, std::function<void()> callback) {
    frameCallbacks_.push_back({frameIndex, callback});
    return *this;
}

Animation AnimationBuilder::build() {
    for (const auto& cb : frameCallbacks_) {
        if (cb.first >= 0 && cb.first < animation_.getFrameCount()) {
            animation_.getFrame(cb.first).callback = cb.second;
        }
    }
    return animation_;
}

}
