from kivy.event import EventDispatcher
from kivy.animation import Animation
from kivy.properties import ListProperty, NumericProperty, StringProperty

class OnPropertyAnimationMixin(EventDispatcher):  
    """
    Animates particular properties on it's assignment
    """
    # point animation properties list
    animate_properties = ListProperty([])
    duration = NumericProperty(1)
    transition = StringProperty('linear')

    def generate_handler(self, prop):
        def handler(instance, value):
            last_animation = self.animations.get(prop)
            if last_animation:
                last_animation.cancel(self)

            last_value = self.last_values.get(prop, self.property(prop).defaultvalue)
            self.unbind(**{prop: self.handlers[prop]})
            setattr(instance, prop, last_value)
            animation = Animation(**{prop: value,
                                     "duration": self.duration,
                                     'transition': self.transition})

            animation.bind(on_complete=lambda x, instance: instance.bind(**{prop: self.handlers[prop]}))
            animation.start(self)
            self.animations[prop] = animation
            self.last_values[prop] = value
            return True

        return handler

    def on_animate_properties(self, instance, value):
        for prop in value:
            handler = self.generate_handler(prop)
            self.handlers[prop] = handler
            self.bind(**{prop: handler})

    def __init__(self, **kwargs):
        super(OnPropertyAnimationMixin, self).__init__(**kwargs)
        self.handlers = {}
        self.last_values = {}
        self.animations = {}
        #self.transition = 'linear'