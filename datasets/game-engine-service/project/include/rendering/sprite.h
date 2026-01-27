#ifndef ENGINE_SPRITE_H
#define ENGINE_SPRITE_H

#include <string>

namespace engine {

struct Rect {
    int x;
    int y;
    int width;
    int height;
    
    Rect() : x(0), y(0), width(0), height(0) {}
    Rect(int x, int y, int w, int h) : x(x), y(y), width(w), height(h) {}
};

class Sprite {
public:
    Sprite();
    Sprite(const std::string& texturePath);
    Sprite(const std::string& texturePath, const Rect& sourceRect);
    
    const std::string& getTexturePath() const { return texturePath_; }
    const Rect& getSourceRect() const { return sourceRect_; }
    
    void setTexturePath(const std::string& path) { texturePath_ = path; }
    void setSourceRect(const Rect& rect) { sourceRect_ = rect; }

private:
    std::string texturePath_;
    Rect sourceRect_;
};

} // namespace engine

#endif // ENGINE_SPRITE_H
