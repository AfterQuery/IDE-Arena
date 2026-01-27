#ifndef TIME_MANAGER_H
#define TIME_MANAGER_H

#include <chrono>
#include <vector>
#include <functional>
#include <string>
#include <unordered_map>

namespace engine {

using TimePoint = std::chrono::high_resolution_clock::time_point;
using Duration = std::chrono::duration<double>;

enum class EasingType {
    Linear,
    EaseIn,
    EaseOut,
    EaseInOut
};

float applyEasing(EasingType type, float t);

struct Timer {
    std::string name;
    double duration;
    double elapsed;
    bool repeating;
    bool active;
    std::function<void()> callback;
};

class TimeManager {
public:
    TimeManager();
    ~TimeManager();

    void update();
    void reset();

    double getDeltaTime() const;
    double getTotalTime() const;
    double getUnscaledDeltaTime() const;

    void setTimeScale(double scale);
    double getTimeScale() const;

    int createTimer(const std::string& name, double duration, 
                    std::function<void()> callback, bool repeating = false);
    void cancelTimer(int timerId);
    void pauseTimer(int timerId);
    void resumeTimer(int timerId);
    Timer* getTimer(int timerId);

    void pauseAllTimers();
    void resumeAllTimers();

    int getFPS() const;
    double getAverageFPS() const;

    void setTargetFrameTime(double frameTime);
    double getTargetFrameTime() const;
    double getFrameTimeDeviation() const;

private:
    void updateTimers(double dt);
    void calculateFPS();

    TimePoint startTime_;
    TimePoint lastFrameTime_;
    TimePoint currentFrameTime_;

    double deltaTime_;
    double unscaledDeltaTime_;
    double totalTime_;
    double timeScale_;

    double targetFrameTime_;

    std::vector<Timer> timers_;
    std::unordered_map<std::string, int> timerNameMap_;
    int nextTimerId_;

    std::vector<double> frameTimes_;
    int frameCount_;
    int currentFPS_;
    double fpsUpdateInterval_;
    double fpsAccumulator_;
};

}

#endif
