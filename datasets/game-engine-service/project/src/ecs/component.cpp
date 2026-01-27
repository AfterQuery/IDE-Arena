#include "ecs/component.h"
#include "ecs/entity.h"
#include <cmath>

namespace engine {

Component::Component()
    : entity_(nullptr)
    , enabled_(true) {
}

Component::~Component() {
}

void Component::onAttach(Entity* entity) {
    entity_ = entity;
}

void Component::onDetach() {
    entity_ = nullptr;
}

void Component::onActivate() {
}

void Component::onDeactivate() {
}

Entity* Component::getEntity() {
    return entity_;
}

const Entity* Component::getEntity() const {
    return entity_;
}

bool Component::isEnabled() const {
    return enabled_;
}

void Component::setEnabled(bool enabled) {
    if (enabled_ != enabled) {
        enabled_ = enabled;
        if (enabled_) {
            onActivate();
        } else {
            onDeactivate();
        }
    }
}

TransformComponent::TransformComponent()
    : x(0.0f)
    , y(0.0f)
    , rotation(0.0f)
    , scaleX(1.0f)
    , scaleY(1.0f) {
}

TransformComponent::TransformComponent(float x, float y)
    : x(x)
    , y(y)
    , rotation(0.0f)
    , scaleX(1.0f)
    , scaleY(1.0f) {
}

TransformComponent::~TransformComponent() {
}

void TransformComponent::setPosition(float px, float py) {
    x = px;
    y = py;
}

void TransformComponent::translate(float dx, float dy) {
    x += dx;
    y += dy;
}

void TransformComponent::rotate(float angle) {
    rotation += angle;
    while (rotation >= 360.0f) rotation -= 360.0f;
    while (rotation < 0.0f) rotation += 360.0f;
}

void TransformComponent::setScale(float sx, float sy) {
    scaleX = sx;
    scaleY = sy;
}

float TransformComponent::getWorldX() const {
    float worldX = x;
    if (entity_) {
        Entity* parent = const_cast<Entity*>(entity_)->getParent();
        if (parent) {
            auto parentComponents = parent->getAllComponents();
            for (auto* comp : parentComponents) {
                auto* parentTransform = dynamic_cast<TransformComponent*>(comp);
                if (parentTransform) {
                    float cosR = std::cos(parentTransform->rotation * 3.14159265f / 180.0f);
                    float sinR = std::sin(parentTransform->rotation * 3.14159265f / 180.0f);
                    worldX = parentTransform->getWorldX() + (x * cosR - y * sinR) * parentTransform->scaleX;
                    break;
                }
            }
        }
    }
    return worldX;
}

float TransformComponent::getWorldY() const {
    float worldY = y;
    if (entity_) {
        Entity* parent = const_cast<Entity*>(entity_)->getParent();
        if (parent) {
            auto parentComponents = parent->getAllComponents();
            for (auto* comp : parentComponents) {
                auto* parentTransform = dynamic_cast<TransformComponent*>(comp);
                if (parentTransform) {
                    float cosR = std::cos(parentTransform->rotation * 3.14159265f / 180.0f);
                    float sinR = std::sin(parentTransform->rotation * 3.14159265f / 180.0f);
                    worldY = parentTransform->getWorldY() + (x * sinR + y * cosR) * parentTransform->scaleY;
                    break;
                }
            }
        }
    }
    return worldY;
}

float TransformComponent::getWorldRotation() const {
    float worldRotation = rotation;
    if (entity_) {
        Entity* parent = const_cast<Entity*>(entity_)->getParent();
        if (parent) {
            auto parentComponents = parent->getAllComponents();
            for (auto* comp : parentComponents) {
                auto* parentTransform = dynamic_cast<TransformComponent*>(comp);
                if (parentTransform) {
                    worldRotation += parentTransform->getWorldRotation();
                    break;
                }
            }
        }
    }
    return worldRotation;
}

Component* TransformComponent::clone() const {
    auto* copy = new TransformComponent();
    copy->x = x;
    copy->y = y;
    copy->rotation = rotation;
    copy->scaleX = scaleX;
    copy->scaleY = scaleY;
    return copy;
}

TransformComponent interpolateTransform(const TransformComponent& a, const TransformComponent& b, float t) {
    t = std::max(0.0f, std::min(1.0f, t));

    TransformComponent result;
    result.x = a.x + (b.x - a.x) * t;
    result.y = a.y + (b.y - a.y) * t;
    result.scaleX = a.scaleX + (b.scaleX - a.scaleX) * t;
    result.scaleY = a.scaleY + (b.scaleY - a.scaleY) * t;

    float rotA = a.rotation;
    float rotB = b.rotation;

    float diff = rotB - rotA;

    result.rotation = rotA + diff * t;
    while (result.rotation >= 360.0f) result.rotation -= 360.0f;
    while (result.rotation < 0.0f) result.rotation += 360.0f;

    return result;
}

TagComponent::TagComponent()
    : tag("") {
}

TagComponent::TagComponent(const std::string& tag)
    : tag(tag) {
}

TagComponent::~TagComponent() {
}

Component* TagComponent::clone() const {
    return new TagComponent(tag);
}

}
