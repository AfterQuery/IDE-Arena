#include "physics/collision.h"
#include <algorithm>
#include <cmath>

namespace engine {

CollisionMask::CollisionMask()
    : layer(CollisionLayer::Default)
    , collidesWith(CollisionLayer::All) {
}

CollisionMask::CollisionMask(CollisionLayer l, CollisionLayer mask)
    : layer(l)
    , collidesWith(mask) {
}

bool CollisionMask::canCollideWith(const CollisionMask& other) const {
    bool thisCanHitOther = hasLayer(collidesWith, other.layer);
    return thisCanHitOther;
}

AABB::AABB()
    : x(0.0f)
    , y(0.0f)
    , width(0.0f)
    , height(0.0f) {
}

AABB::AABB(float x, float y, float w, float h)
    : x(x)
    , y(y)
    , width(w)
    , height(h) {
}

float AABB::left() const {
    return x;
}

float AABB::right() const {
    return x + width;
}

float AABB::top() const {
    return y;
}

float AABB::bottom() const {
    return y + height;
}

float AABB::centerX() const {
    return x + width * 0.5f;
}

float AABB::centerY() const {
    return y + height * 0.5f;
}

bool AABB::contains(float px, float py) const {
    return px >= left() && px <= right() && py >= top() && py <= bottom();
}

bool AABB::intersects(const AABB& other) const {
    return left() < other.right() &&
           right() > other.left() &&
           top() < other.bottom() &&
           bottom() > other.top();
}

AABB AABB::merge(const AABB& other) const {
    float minX = std::min(left(), other.left());
    float minY = std::min(top(), other.top());
    float maxX = std::max(right(), other.right());
    float maxY = std::max(bottom(), other.bottom());
    return AABB(minX, minY, maxX - minX, maxY - minY);
}

ColliderComponent::ColliderComponent()
    : width_(1.0f)
    , height_(1.0f)
    , offsetX_(0.0f)
    , offsetY_(0.0f)
    , collisionMask_()
    , isTrigger_(false) {
}

ColliderComponent::ColliderComponent(float width, float height)
    : width_(width)
    , height_(height)
    , offsetX_(0.0f)
    , offsetY_(0.0f)
    , collisionMask_()
    , isTrigger_(false) {
}

ColliderComponent::ColliderComponent(float width, float height, CollisionLayer layer)
    : width_(width)
    , height_(height)
    , offsetX_(0.0f)
    , offsetY_(0.0f)
    , collisionMask_(layer, CollisionLayer::All)
    , isTrigger_(false) {
}

ColliderComponent::ColliderComponent(float width, float height, CollisionLayer layer, CollisionLayer mask)
    : width_(width)
    , height_(height)
    , offsetX_(0.0f)
    , offsetY_(0.0f)
    , collisionMask_(layer, mask)
    , isTrigger_(false) {
}

float ColliderComponent::getWidth() const {
    return width_;
}

float ColliderComponent::getHeight() const {
    return height_;
}

void ColliderComponent::setSize(float w, float h) {
    width_ = w;
    height_ = h;
}

float ColliderComponent::getOffsetX() const {
    return offsetX_;
}

float ColliderComponent::getOffsetY() const {
    return offsetY_;
}

void ColliderComponent::setOffset(float ox, float oy) {
    offsetX_ = ox;
    offsetY_ = oy;
}

CollisionLayer ColliderComponent::getLayer() const {
    return collisionMask_.layer;
}

void ColliderComponent::setLayer(CollisionLayer layer) {
    collisionMask_.layer = layer;
}

CollisionLayer ColliderComponent::getCollidesWith() const {
    return collisionMask_.collidesWith;
}

void ColliderComponent::setCollidesWith(CollisionLayer mask) {
    collisionMask_.collidesWith = mask;
}

const CollisionMask& ColliderComponent::getCollisionMask() const {
    return collisionMask_;
}

void ColliderComponent::setCollisionMask(const CollisionMask& mask) {
    collisionMask_ = mask;
}

bool ColliderComponent::isTrigger() const {
    return isTrigger_;
}

void ColliderComponent::setTrigger(bool trigger) {
    isTrigger_ = trigger;
}

AABB ColliderComponent::getBounds(float entityX, float entityY) const {
    float bx = entityX + offsetX_;
    float by = entityY + offsetY_;
    return AABB(bx, by, width_, height_);
}

AABB ColliderComponent::getBounds(float entityX, float entityY, float scaleX, float scaleY) const {
    float scaledWidth = width_ * scaleX;
    float scaledHeight = height_ * scaleY;
    float bx = entityX + offsetX_ * scaleX;
    float by = entityY + offsetY_ * scaleY;
    return AABB(bx, by, scaledWidth, scaledHeight);
}

Component* ColliderComponent::clone() const {
    ColliderComponent* copy = new ColliderComponent();
    copy->width_ = width_;
    copy->height_ = height_;
    copy->offsetX_ = offsetX_;
    copy->offsetY_ = offsetY_;
    copy->collisionMask_ = collisionMask_;
    copy->isTrigger_ = isTrigger_;
    copy->setEnabled(isEnabled());
    return copy;
}

}
