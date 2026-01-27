#ifndef ENGINE_COLLISION_WORLD_H
#define ENGINE_COLLISION_WORLD_H

#include "physics/collision.h"
#include <vector>
#include <functional>
#include <unordered_map>

namespace engine {

using EntityID = uint32_t;

struct ColliderEntry {
    EntityID entityId;
    float posX;
    float posY;
    float scaleX;
    float scaleY;
    ColliderComponent collider;
    
    ColliderEntry();
    ColliderEntry(EntityID id, float x, float y, const ColliderComponent& col);
    ColliderEntry(EntityID id, float x, float y, float sx, float sy, const ColliderComponent& col);
    
    AABB getBounds() const;
};

using CollisionCallback = std::function<void(const CollisionInfo&)>;
using TriggerCallback = std::function<void(EntityID, EntityID)>;

class CollisionWorld {
public:
    CollisionWorld();
    ~CollisionWorld();
    
    void addCollider(EntityID entityId, float x, float y, const ColliderComponent& collider);
    void addCollider(EntityID entityId, float x, float y, float scaleX, float scaleY, const ColliderComponent& collider);
    void removeCollider(EntityID entityId);
    void updatePosition(EntityID entityId, float x, float y);
    void updateScale(EntityID entityId, float scaleX, float scaleY);
    void clear();
    
    bool hasCollider(EntityID entityId) const;
    const ColliderEntry* getCollider(EntityID entityId) const;
    size_t getColliderCount() const;
    
    std::vector<CollisionInfo> detectCollisions() const;
    std::vector<CollisionInfo> detectCollisionsForEntity(EntityID entityId) const;
    
    std::vector<EntityID> queryPoint(float x, float y) const;
    std::vector<EntityID> queryPoint(float x, float y, CollisionLayer layerFilter) const;
    std::vector<EntityID> queryAABB(const AABB& bounds) const;
    std::vector<EntityID> queryAABB(const AABB& bounds, CollisionLayer layerFilter) const;
    
    bool checkCollision(EntityID a, EntityID b) const;
    bool checkCollision(EntityID a, EntityID b, CollisionInfo& outInfo) const;
    
    void setCollisionCallback(CollisionCallback callback);
    void setTriggerEnterCallback(TriggerCallback callback);
    void setTriggerExitCallback(TriggerCallback callback);
    
    void processCollisions();
    
    void setLayerCollisionEnabled(CollisionLayer layer1, CollisionLayer layer2, bool enabled);
    bool isLayerCollisionEnabled(CollisionLayer layer1, CollisionLayer layer2) const;

private:
    std::vector<ColliderEntry> colliders_;
    std::unordered_map<EntityID, size_t> entityIndexMap_;
    
    CollisionCallback onCollision_;
    TriggerCallback onTriggerEnter_;
    TriggerCallback onTriggerExit_;
    
    uint32_t layerMatrix_[8];
    
    bool shouldCollideLayers(CollisionLayer a, CollisionLayer b) const;
    void rebuildIndexMap();
};

}

#endif
