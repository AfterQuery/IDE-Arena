#ifndef COMPONENT_H
#define COMPONENT_H

#include <cstdint>
#include <string>
#include <typeinfo>

namespace engine {

using ComponentTypeId = uint32_t;

class Entity;

class ComponentTypeRegistry {
public:
    template<typename T>
    static ComponentTypeId getTypeId() {
        static ComponentTypeId id = nextId_++;
        return id;
    }

    static ComponentTypeId getTypeCount() { return nextId_; }

private:
    static inline ComponentTypeId nextId_ = 0;
};

class Component {
public:
    Component();
    virtual ~Component();

    virtual void onAttach(Entity* entity);
    virtual void onDetach();
    virtual void onActivate();
    virtual void onDeactivate();

    Entity* getEntity();
    const Entity* getEntity() const;

    bool isEnabled() const;
    void setEnabled(bool enabled);

    virtual ComponentTypeId getTypeId() const = 0;
    virtual std::string getTypeName() const = 0;

    virtual Component* clone() const = 0;

protected:
    Entity* entity_;
    bool enabled_;
};

template<typename T>
class ComponentBase : public Component {
public:
    static ComponentTypeId staticGetTypeId() {
        return ComponentTypeRegistry::getTypeId<T>();
    }

    ComponentTypeId getTypeId() const override {
        return staticGetTypeId();
    }

    std::string getTypeName() const override {
        return typeid(T).name();
    }
};

class TransformComponent : public ComponentBase<TransformComponent> {
public:
    TransformComponent();
    TransformComponent(float x, float y);
    ~TransformComponent() override;

    float x, y;
    float rotation;
    float scaleX, scaleY;

    void setPosition(float px, float py);
    void translate(float dx, float dy);
    void rotate(float angle);
    void setScale(float sx, float sy);

    float getWorldX() const;
    float getWorldY() const;
    float getWorldRotation() const;

    Component* clone() const override;
};

TransformComponent interpolateTransform(const TransformComponent& a, const TransformComponent& b, float t);

class TagComponent : public ComponentBase<TagComponent> {
public:
    TagComponent();
    TagComponent(const std::string& tag);
    ~TagComponent() override;

    std::string tag;

    Component* clone() const override;
};

}

#endif
