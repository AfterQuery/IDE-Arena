#include "physics/collision_world.h"
#include <algorithm>
#include <cmath>

namespace engine {

ColliderEntry::ColliderEntry()
    : entityId(0)
    , posX(0.0f)
    , posY(0.0f)
    , scaleX(1.0f)
    , scaleY(1.0f)
    , collider() {
}

ColliderEntry::ColliderEntry(EntityID id, float x, float y, const ColliderComponent& col)
    : entityId(id)
    , posX(x)
    , posY(y)
    , scaleX(1.0f)
    , scaleY(1.0f)
    , collider(col) {
}

ColliderEntry::ColliderEntry(EntityID id, float x, float y, float sx, float sy, const ColliderComponent& col)
    : entityId(id)
    , posX(x)
    , posY(y)
    , scaleX(sx)
    , scaleY(sy)
    , collider(col) {
}

AABB ColliderEntry::getBounds() const {
    return collider.getBounds(posX, posY, scaleX, scaleY);
}

CollisionWorld::CollisionWorld()
    : onCollision_(nullptr)
    , onTriggerEnter_(nullptr)
    , onTriggerExit_(nullptr) {
    for (int i = 0; i < 8; i++) {
        layerMatrix_[i] = 0xFFFFFFFF;
    }
}

CollisionWorld::~CollisionWorld() {
    clear();
}

void CollisionWorld::addCollider(EntityID entityId, float x, float y, const ColliderComponent& collider) {
    addCollider(entityId, x, y, 1.0f, 1.0f, collider);
}

void CollisionWorld::addCollider(EntityID entityId, float x, float y, float scaleX, float scaleY, const ColliderComponent& collider) {
    if (entityIndexMap_.find(entityId) != entityIndexMap_.end()) {
        removeCollider(entityId);
    }
    
    colliders_.emplace_back(entityId, x, y, scaleX, scaleY, collider);
    entityIndexMap_[entityId] = colliders_.size() - 1;
}

void CollisionWorld::removeCollider(EntityID entityId) {
    auto it = entityIndexMap_.find(entityId);
    if (it == entityIndexMap_.end()) {
        return;
    }
    
    size_t index = it->second;
    if (index < colliders_.size() - 1) {
        colliders_[index] = colliders_.back();
        entityIndexMap_[colliders_[index].entityId] = index;
    }
    colliders_.pop_back();
    entityIndexMap_.erase(it);
}

void CollisionWorld::updatePosition(EntityID entityId, float x, float y) {
    auto it = entityIndexMap_.find(entityId);
    if (it != entityIndexMap_.end()) {
        colliders_[it->second].posX = x;
        colliders_[it->second].posY = y;
    }
}

void CollisionWorld::updateScale(EntityID entityId, float scaleX, float scaleY) {
    auto it = entityIndexMap_.find(entityId);
    if (it != entityIndexMap_.end()) {
        colliders_[it->second].scaleX = scaleX;
        colliders_[it->second].scaleY = scaleY;
    }
}

void CollisionWorld::clear() {
    colliders_.clear();
    entityIndexMap_.clear();
}

bool CollisionWorld::hasCollider(EntityID entityId) const {
    return entityIndexMap_.find(entityId) != entityIndexMap_.end();
}

const ColliderEntry* CollisionWorld::getCollider(EntityID entityId) const {
    auto it = entityIndexMap_.find(entityId);
    if (it != entityIndexMap_.end()) {
        return &colliders_[it->second];
    }
    return nullptr;
}

size_t CollisionWorld::getColliderCount() const {
    return colliders_.size();
}

std::vector<CollisionInfo> CollisionWorld::detectCollisions() const {
    std::vector<CollisionInfo> results;
    
    for (size_t i = 0; i < colliders_.size(); i++) {
        const ColliderEntry& a = colliders_[i];
        AABB boundsA = a.getBounds();
        
        for (size_t j = i + 1; j < colliders_.size(); j++) {
            const ColliderEntry& b = colliders_[j];
            AABB boundsB = b.getBounds();
            
            if (boundsA.intersects(boundsB)) {
                CollisionInfo info;
                info.entityA = a.entityId;
                info.entityB = b.entityId;
                info.boundsA = boundsA;
                info.boundsB = boundsB;
                info.isTrigger = a.collider.isTrigger() || b.collider.isTrigger();
                
                float overlapLeft = boundsA.right() - boundsB.left();
                float overlapRight = boundsB.right() - boundsA.left();
                float overlapTop = boundsA.bottom() - boundsB.top();
                float overlapBottom = boundsB.bottom() - boundsA.top();
                
                info.overlapX = std::min(overlapLeft, overlapRight);
                info.overlapY = std::min(overlapTop, overlapBottom);
                
                results.push_back(info);
            }
        }
    }
    
    return results;
}

std::vector<CollisionInfo> CollisionWorld::detectCollisionsForEntity(EntityID entityId) const {
    std::vector<CollisionInfo> results;
    
    auto it = entityIndexMap_.find(entityId);
    if (it == entityIndexMap_.end()) {
        return results;
    }
    
    const ColliderEntry& target = colliders_[it->second];
    AABB targetBounds = target.getBounds();
    
    for (size_t i = 0; i < colliders_.size(); i++) {
        if (colliders_[i].entityId == entityId) {
            continue;
        }
        
        const ColliderEntry& other = colliders_[i];
        AABB otherBounds = other.getBounds();
        
        if (targetBounds.intersects(otherBounds)) {
            const CollisionMask& maskA = target.collider.getCollisionMask();
            const CollisionMask& maskB = other.collider.getCollisionMask();
            
            if (!maskA.canCollideWith(maskB)) {
                continue;
            }
            
            CollisionInfo info;
            info.entityA = target.entityId;
            info.entityB = other.entityId;
            info.boundsA = targetBounds;
            info.boundsB = otherBounds;
            info.isTrigger = target.collider.isTrigger() || other.collider.isTrigger();
            
            float overlapLeft = targetBounds.right() - otherBounds.left();
            float overlapRight = otherBounds.right() - targetBounds.left();
            float overlapTop = targetBounds.bottom() - otherBounds.top();
            float overlapBottom = otherBounds.bottom() - targetBounds.top();
            
            info.overlapX = std::min(overlapLeft, overlapRight);
            info.overlapY = std::min(overlapTop, overlapBottom);
            
            results.push_back(info);
        }
    }
    
    return results;
}

std::vector<EntityID> CollisionWorld::queryPoint(float x, float y) const {
    return queryPoint(x, y, CollisionLayer::All);
}

std::vector<EntityID> CollisionWorld::queryPoint(float x, float y, CollisionLayer layerFilter) const {
    std::vector<EntityID> results;
    
    for (const auto& entry : colliders_) {
        AABB bounds = entry.getBounds();
        if (bounds.contains(x, y)) {
            if (hasLayer(layerFilter, entry.collider.getLayer())) {
                results.push_back(entry.entityId);
            }
        }
    }
    
    return results;
}

std::vector<EntityID> CollisionWorld::queryAABB(const AABB& bounds) const {
    return queryAABB(bounds, CollisionLayer::All);
}

std::vector<EntityID> CollisionWorld::queryAABB(const AABB& bounds, CollisionLayer layerFilter) const {
    std::vector<EntityID> results;
    
    for (const auto& entry : colliders_) {
        AABB entryBounds = entry.getBounds();
        if (bounds.intersects(entryBounds)) {
            results.push_back(entry.entityId);
        }
    }
    
    return results;
}

bool CollisionWorld::checkCollision(EntityID a, EntityID b) const {
    CollisionInfo info;
    return checkCollision(a, b, info);
}

bool CollisionWorld::checkCollision(EntityID a, EntityID b, CollisionInfo& outInfo) const {
    auto itA = entityIndexMap_.find(a);
    auto itB = entityIndexMap_.find(b);
    
    if (itA == entityIndexMap_.end() || itB == entityIndexMap_.end()) {
        return false;
    }
    
    const ColliderEntry& entryA = colliders_[itA->second];
    const ColliderEntry& entryB = colliders_[itB->second];
    
    AABB boundsA = entryA.getBounds();
    AABB boundsB = entryB.getBounds();
    
    if (!boundsA.intersects(boundsB)) {
        return false;
    }
    
    const CollisionMask& maskA = entryA.collider.getCollisionMask();
    const CollisionMask& maskB = entryB.collider.getCollisionMask();
    
    if (!maskA.canCollideWith(maskB)) {
        return false;
    }
    
    outInfo.entityA = a;
    outInfo.entityB = b;
    outInfo.boundsA = boundsA;
    outInfo.boundsB = boundsB;
    outInfo.isTrigger = entryA.collider.isTrigger() || entryB.collider.isTrigger();
    
    float overlapLeft = boundsA.right() - boundsB.left();
    float overlapRight = boundsB.right() - boundsA.left();
    float overlapTop = boundsA.bottom() - boundsB.top();
    float overlapBottom = boundsB.bottom() - boundsA.top();
    
    outInfo.overlapX = std::min(overlapLeft, overlapRight);
    outInfo.overlapY = std::min(overlapTop, overlapBottom);
    
    return true;
}

void CollisionWorld::setCollisionCallback(CollisionCallback callback) {
    onCollision_ = callback;
}

void CollisionWorld::setTriggerEnterCallback(TriggerCallback callback) {
    onTriggerEnter_ = callback;
}

void CollisionWorld::setTriggerExitCallback(TriggerCallback callback) {
    onTriggerExit_ = callback;
}

void CollisionWorld::processCollisions() {
    auto collisions = detectCollisions();
    
    for (const auto& info : collisions) {
        if (info.isTrigger) {
            if (onTriggerEnter_) {
                onTriggerEnter_(info.entityA, info.entityB);
            }
        } else {
            if (onCollision_) {
                onCollision_(info);
            }
        }
    }
}

void CollisionWorld::setLayerCollisionEnabled(CollisionLayer layer1, CollisionLayer layer2, bool enabled) {
    uint32_t l1 = static_cast<uint32_t>(layer1);
    uint32_t l2 = static_cast<uint32_t>(layer2);
    
    for (int i = 0; i < 8; i++) {
        if (l1 & (1 << i)) {
            if (enabled) {
                layerMatrix_[i] |= l2;
            } else {
                layerMatrix_[i] &= ~l2;
            }
        }
        if (l2 & (1 << i)) {
            if (enabled) {
                layerMatrix_[i] |= l1;
            } else {
                layerMatrix_[i] &= ~l1;
            }
        }
    }
}

bool CollisionWorld::isLayerCollisionEnabled(CollisionLayer layer1, CollisionLayer layer2) const {
    uint32_t l1 = static_cast<uint32_t>(layer1);
    uint32_t l2 = static_cast<uint32_t>(layer2);
    
    for (int i = 0; i < 8; i++) {
        if (l1 & (1 << i)) {
            if (!(layerMatrix_[i] & l2)) {
                return false;
            }
        }
    }
    return true;
}

bool CollisionWorld::shouldCollideLayers(CollisionLayer a, CollisionLayer b) const {
    return isLayerCollisionEnabled(a, b);
}

void CollisionWorld::rebuildIndexMap() {
    entityIndexMap_.clear();
    for (size_t i = 0; i < colliders_.size(); i++) {
        entityIndexMap_[colliders_[i].entityId] = i;
    }
}

}
