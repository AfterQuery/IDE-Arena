#ifndef ENGINE_COLLISION_H
#define ENGINE_COLLISION_H

#include <cstdint>
#include <functional>
#include "ecs/component.h"

namespace engine {

enum class CollisionLayer : uint32_t {
    None       = 0,
    Default    = 1 << 0,
    Player     = 1 << 1,
    Enemy      = 1 << 2,
    Projectile = 1 << 3,
    Terrain    = 1 << 4,
    Trigger    = 1 << 5,
    Pickup     = 1 << 6,
    Platform   = 1 << 7,
    All        = 0xFFFFFFFF
};

inline CollisionLayer operator|(CollisionLayer a, CollisionLayer b) {
    return static_cast<CollisionLayer>(static_cast<uint32_t>(a) | static_cast<uint32_t>(b));
}

inline CollisionLayer operator&(CollisionLayer a, CollisionLayer b) {
    return static_cast<CollisionLayer>(static_cast<uint32_t>(a) & static_cast<uint32_t>(b));
}

inline CollisionLayer operator~(CollisionLayer a) {
    return static_cast<CollisionLayer>(~static_cast<uint32_t>(a));
}

inline bool hasLayer(CollisionLayer mask, CollisionLayer layer) {
    return (mask & layer) != CollisionLayer::None;
}

struct CollisionMask {
    CollisionLayer layer;
    CollisionLayer collidesWith;
    
    CollisionMask();
    CollisionMask(CollisionLayer l, CollisionLayer mask);
    
    bool canCollideWith(const CollisionMask& other) const;
};

struct AABB {
    float x;
    float y;
    float width;
    float height;
    
    AABB();
    AABB(float x, float y, float w, float h);
    
    float left() const;
    float right() const;
    float top() const;
    float bottom() const;
    float centerX() const;
    float centerY() const;
    
    bool contains(float px, float py) const;
    bool intersects(const AABB& other) const;
    AABB merge(const AABB& other) const;
};

struct CollisionInfo {
    uint32_t entityA;
    uint32_t entityB;
    AABB boundsA;
    AABB boundsB;
    float overlapX;
    float overlapY;
    bool isTrigger;
};

class ColliderComponent : public ComponentBase<ColliderComponent> {
public:
    ColliderComponent();
    ColliderComponent(float width, float height);
    ColliderComponent(float width, float height, CollisionLayer layer);
    ColliderComponent(float width, float height, CollisionLayer layer, CollisionLayer mask);
    
    float getWidth() const;
    float getHeight() const;
    void setSize(float w, float h);
    
    float getOffsetX() const;
    float getOffsetY() const;
    void setOffset(float ox, float oy);
    
    CollisionLayer getLayer() const;
    void setLayer(CollisionLayer layer);
    
    CollisionLayer getCollidesWith() const;
    void setCollidesWith(CollisionLayer mask);
    
    const CollisionMask& getCollisionMask() const;
    void setCollisionMask(const CollisionMask& mask);
    
    bool isTrigger() const;
    void setTrigger(bool trigger);
    
    AABB getBounds(float entityX, float entityY) const;
    AABB getBounds(float entityX, float entityY, float scaleX, float scaleY) const;
    
    Component* clone() const override;

private:
    float width_;
    float height_;
    float offsetX_;
    float offsetY_;
    CollisionMask collisionMask_;
    bool isTrigger_;
};

}

#endif
