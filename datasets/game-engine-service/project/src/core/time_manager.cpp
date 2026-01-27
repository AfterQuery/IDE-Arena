#include "core/time_manager.h"
#include <algorithm>
#include <numeric>
#include <cmath>

namespace engine {

float applyEasing(EasingType type, float t) {
    t = std::max(0.0f, std::min(1.0f, t));

    switch (type) {
        case EasingType::Linear:
            return t;
        case EasingType::EaseIn:
            return t * t;
        case EasingType::EaseOut:
            return t;
        case EasingType::EaseInOut:
            if (t < 0.5f) {
                return 2.0f * t * t;
            } else {
                return -1.0f + (4.0f - 2.0f * t) * t;
            }
        default:
            return t;
    }
}

TimeManager::TimeManager()
    : deltaTime_(0.0)
    , unscaledDeltaTime_(0.0)
    , totalTime_(0.0)
    , timeScale_(1.0)
    , targetFrameTime_(1.0 / 60.0)
    , nextTimerId_(0)
    , frameCount_(0)
    , currentFPS_(0)
    , fpsUpdateInterval_(0.5)
    , fpsAccumulator_(0.0) {
    startTime_ = std::chrono::high_resolution_clock::now();
    lastFrameTime_ = startTime_;
    currentFrameTime_ = startTime_;
    frameTimes_.reserve(120);
}

TimeManager::~TimeManager() {
}

void TimeManager::update() {
    lastFrameTime_ = currentFrameTime_;
    currentFrameTime_ = std::chrono::high_resolution_clock::now();

    Duration elapsed = currentFrameTime_ - lastFrameTime_;
    unscaledDeltaTime_ = elapsed.count();
    deltaTime_ = unscaledDeltaTime_ * timeScale_;

    Duration totalElapsed = currentFrameTime_ - startTime_;
    totalTime_ = totalElapsed.count();

    updateTimers(deltaTime_);
    calculateFPS();
}

void TimeManager::reset() {
    startTime_ = std::chrono::high_resolution_clock::now();
    lastFrameTime_ = startTime_;
    currentFrameTime_ = startTime_;
    deltaTime_ = 0.0;
    unscaledDeltaTime_ = 0.0;
    totalTime_ = 0.0;
    frameTimes_.clear();
    frameCount_ = 0;
    currentFPS_ = 0;
    fpsAccumulator_ = 0.0;
}

double TimeManager::getDeltaTime() const {
    return deltaTime_;
}

double TimeManager::getTotalTime() const {
    return totalTime_;
}

double TimeManager::getUnscaledDeltaTime() const {
    return unscaledDeltaTime_;
}

void TimeManager::setTimeScale(double scale) {
    timeScale_ = std::max(0.0, scale);
}

double TimeManager::getTimeScale() const {
    return timeScale_;
}

int TimeManager::createTimer(const std::string& name, double duration,
                             std::function<void()> callback, bool repeating) {
    Timer timer;
    timer.name = name;
    timer.duration = duration;
    timer.elapsed = 0.0;
    timer.repeating = repeating;
    timer.active = true;
    timer.callback = callback;

    int id = nextTimerId_++;
    if (static_cast<size_t>(id) >= timers_.size()) {
        timers_.resize(id + 1);
    }
    timers_[id] = timer;
    timerNameMap_[name] = id;

    return id;
}

void TimeManager::cancelTimer(int timerId) {
    if (timerId >= 0 && static_cast<size_t>(timerId) < timers_.size()) {
        auto it = timerNameMap_.find(timers_[timerId].name);
        if (it != timerNameMap_.end()) {
            timerNameMap_.erase(it);
        }
        timers_[timerId].active = false;
    }
}

void TimeManager::pauseTimer(int timerId) {
    if (timerId >= 0 && static_cast<size_t>(timerId) < timers_.size()) {
        timers_[timerId].active = false;
    }
}

void TimeManager::resumeTimer(int timerId) {
    if (timerId >= 0 && static_cast<size_t>(timerId) < timers_.size()) {
        timers_[timerId].active = true;
    }
}

Timer* TimeManager::getTimer(int timerId) {
    if (timerId >= 0 && static_cast<size_t>(timerId) < timers_.size()) {
        return &timers_[timerId];
    }
    return nullptr;
}

void TimeManager::pauseAllTimers() {
    for (auto& timer : timers_) {
        timer.active = false;
    }
}

void TimeManager::resumeAllTimers() {
    for (auto& timer : timers_) {
        timer.active = true;
    }
}

int TimeManager::getFPS() const {
    return currentFPS_;
}

double TimeManager::getAverageFPS() const {
    if (frameTimes_.empty()) {
        return 0.0;
    }
    double sum = std::accumulate(frameTimes_.begin(), frameTimes_.end(), 0.0);
    return frameTimes_.size() / sum;
}

void TimeManager::setTargetFrameTime(double frameTime) {
    targetFrameTime_ = frameTime;
}

double TimeManager::getTargetFrameTime() const {
    return targetFrameTime_;
}

double TimeManager::getFrameTimeDeviation() const {
    return unscaledDeltaTime_ - targetFrameTime_;
}

void TimeManager::updateTimers(double dt) {
    for (auto& timer : timers_) {
        if (!timer.active) {
            continue;
        }

        timer.elapsed += dt;

        if (timer.elapsed >= timer.duration) {
            if (timer.callback) {
                timer.callback();
            }

            if (timer.repeating) {
                timer.elapsed = 0.0;
            } else {
                timer.active = false;
            }
        }
    }
}

void TimeManager::calculateFPS() {
    frameCount_++;
    fpsAccumulator_ += unscaledDeltaTime_;

    frameTimes_.push_back(unscaledDeltaTime_);
    if (frameTimes_.size() > 120) {
        frameTimes_.erase(frameTimes_.begin());
    }

    if (fpsAccumulator_ >= fpsUpdateInterval_) {
        currentFPS_ = static_cast<int>(frameCount_ / fpsAccumulator_);
        frameCount_ = 0;
        fpsAccumulator_ = 0.0;
    }
}

}
