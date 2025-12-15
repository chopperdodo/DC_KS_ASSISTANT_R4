class EventConfig:
    # Default Fallback
    DEFAULT_COLOR = 0x3498db # Blue
    DEFAULT_ICON = "https://img.icons8.com/color/96/calendar--v1.png"

    # Event Definitions
    # Key = Bifurcated Name (Stored in DB)
    # Value = Metadata
    EVENTS = {
        "KvK & Castle / KvK & 王城戰": {
            "color": 0xe74c3c, # Red
            "icon": "https://img.icons8.com/color/96/sword.png",
            "desc": "War Event",
            "legacy_keys": ["KvK & Castle"],
            "duration": 360
        },
        "Bear / 熊": {
            "color": 0xe67e22, # Orange
            "icon": "https://img.icons8.com/color/96/bear.png",
            "desc": "Bear Trap",
            "legacy_keys": ["Bear"],
            "duration": 30
        },
        "Swordland / 聖劍": {
            "color": 0xe74c3c, 
            "icon": "https://img.icons8.com/color/96/sword.png",
            "desc": "Battle",
            "legacy_keys": ["Swordland"],
            "duration": 60
        },
        "Tri-Alliance / 三盟": {
            "color": 0xe74c3c,
            "icon": "https://img.icons8.com/color/96/sword.png",
            "desc": "Alliance Battle",
            "legacy_keys": ["Tri-Alliance"],
            "duration": 60
        },
        "Sanctuary / 遺跡": {
            "color": 0x9b59b6, # Purple
            "icon": "https://img.icons8.com/color/96/ruins.png",
            "desc": "Ruins",
            "legacy_keys": ["Sanctuary"],
            "duration": 35
        },
        "Viking / 維京": {
            "color": 0xf1c40f, # Yellow
            "icon": "https://img.icons8.com/color/96/viking-helmet.png",
            "desc": "PVE",
            "legacy_keys": ["Viking"],
            "duration": 40
        },
        "Arena / 競技場": {
            "color": 0xe74c3c,
            "icon": "https://img.icons8.com/color/96/boxing.png",
            "desc": "PVP Event",
            "legacy_keys": ["Arena"],
            "duration": 0
        },
        "Fishing / 釣魚": {
            "color": 0x2ecc71, # Green
            "icon": "https://img.icons8.com/color/96/fishing-pole.png",
            "desc": "Social",
            "legacy_keys": ["Fishing"],
            "duration": 0
        },
        "Shield / 護盾": {
            "color": 0xe74c3c,
            "icon": "https://img.icons8.com/color/96/shield.png",
            "desc": "Urgent Alert",
            "legacy_keys": ["Shield"],
            "duration": 0
        },
        "Farm / 採集": {
            "color": 0x2ecc71,
            "icon": "https://img.icons8.com/color/96/field.png",
            "desc": "Resources",
            "legacy_keys": ["Farm"],
            "duration": 0
        },
        "General / 一般": {
            "color": 0x3498db, 
            "icon": "https://img.icons8.com/color/96/calendar--v1.png",
            "desc": "Custom Event",
            "legacy_keys": ["General"],
            "duration": 0
        }
    }

    @classmethod
    def get_event_duration(cls, event_name):
        """Returns default duration (int) for a given event name."""
        if event_name in cls.EVENTS:
            return cls.EVENTS[event_name].get("duration", 0)
        
        for name, data in cls.EVENTS.items():
            if event_name in data["legacy_keys"]:
                 return data.get("duration", 0)
        return 0

    @classmethod
    def get_event_metadata(cls, event_name):
        """Returns (color, icon) for a given event name (or legacy name)."""
        # 1. Exact Match
        if event_name in cls.EVENTS:
            data = cls.EVENTS[event_name]
            return data["color"], data["icon"]
        
        # 2. Partial Match (e.g. "Shield" in "Shield / 護盾")
        # Reverse lookup: Check if any key contains the event_name, OR if event_name contains the key.
        # Actually, our keys are the "Official Names". 
        
        # 3. Legacy Keys Map
        for name, data in cls.EVENTS.items():
            if event_name in data["legacy_keys"]:
                 return data["color"], data["icon"]
            
            # 4. Keyword Match (simulating the old if/else logic)
            # Old logic: if "Shield" in name...
            # We can iterate and check if the English part is in provided name
            # The keys are like "Bear / 熊". 
            
            # Simple heuristic: Check if the key starts with the legacy key?
            # Or just rely on the fact we modernized everything.
            
            # Let's trust the exact match + legacy usage for now.
            # If we fall back, we use defaults.
        
        # Replicate the old "contains" logic more dynamically if needed?
        # The old logic was: if "Shield" in name: ...
        # We can iterate our config events and check if ANY key subset matches?
        
        for name, data in cls.EVENTS.items():
             # Basic check: if "Shield" in "Shield / ..."
             # We want input "Shield" to match "Shield / ..." key?
             # No, standard input is "Shield / ...".
             # If input is "Shield", it hits legacy key.
             pass
        
        return cls.DEFAULT_COLOR, cls.DEFAULT_ICON

    @classmethod
    def get_legacy_mapping(cls):
        """Returns a dict mapping legacy keys to new full keys."""
        mapping = {}
        for name, data in cls.EVENTS.items():
            for legacy in data.get("legacy_keys", []):
                mapping[legacy] = name
        return mapping
