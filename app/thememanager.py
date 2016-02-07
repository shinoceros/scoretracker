from soundmanager import SoundManager
from persistentdict import PersistentDict
import settings

class ThemeManagerBase(object):
    
    KEY = 'theme'

    def __init__(self):
        with PersistentDict(settings.THEME_FILE, 'c', format='json') as dictionary:
            self.theme = dictionary.get(self.KEY, 'default')
            self._load_theme()

    def set_theme(self, theme):
        self.theme = theme
        with PersistentDict(settings.THEME_FILE, 'c', format='json') as dictionary:
            dictionary[self.KEY] = self.theme

        self._load_theme()

    def get_theme(self):
        return self.theme
        
    def _load_theme(self):
        SoundManager.init(self.theme)

                    
ThemeManager = ThemeManagerBase()

if __name__ == "__main__":
    ThemeManager.set_theme('test')
    print ThemeManager.get_theme()
