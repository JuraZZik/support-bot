import json
import os
from typing import Dict, Any

# Global state for current locale and locales data
_current_locale = None
_locales_data: Dict[str, Dict[str, Any]] = {}
_user_locales: Dict[int, str] = {}  # user_id -> locale mapping


def load_locales():
    """Load all locale files"""
    global _locales_data
    
    locales_dir = os.path.dirname(__file__)
    
    for locale_file in ["ru.json", "en.json"]:
        file_path = os.path.join(locales_dir, locale_file)
        locale_code = locale_file.replace(".json", "")
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                _locales_data[locale_code] = json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Locale file not found: {file_path}")
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing {locale_file}: {e}")


def set_locale(locale_code: str) -> bool:
    """Set global locale"""
    global _current_locale
    
    if locale_code not in _locales_data:
        print(f"⚠️ Locale '{locale_code}' not found. Available: {list(_locales_data.keys())}")
        return False
    
    _current_locale = locale_code
    return True


def set_user_locale(user_id: int, locale_code: str) -> bool:
    """Set locale for specific user"""
    if locale_code not in _locales_data:
        print(f"⚠️ Locale '{locale_code}' not found. Available: {list(_locales_data.keys())}")
        return False
    
    _user_locales[user_id] = locale_code
    return True


def get_user_locale(user_id: int) -> str:
    """Get locale for specific user, or global if not set"""
    return _user_locales.get(user_id, _current_locale)


def get_locale() -> str:
    """Get current global locale"""
    return _current_locale


def get_text(key: str, user_id: int = None, **kwargs) -> str:
    """
    Get translated text from current locale
    
    Args:
        key: Dot-separated path (e.g., "alerts.bot_started")
        user_id: Optional user ID to get user-specific locale
        **kwargs: Format parameters
    
    Returns:
        Translated text with applied formatting
    """
    try:
        # Get locale for user or use global
        locale = get_user_locale(user_id) if user_id else _current_locale
        
        # Navigate through nested dict using dot notation
        keys = key.split(".")
        value = _locales_data[locale]
        
        for k in keys:
            value = value[k]
        
        # Format with provided parameters
        if kwargs:
            return value.format(**kwargs)
        return value
        
    except (KeyError, AttributeError):
        print(f"❌ Translation key not found: {key} (locale: {locale})")
        return key


# Alias for gettext-style usage
_ = get_text
