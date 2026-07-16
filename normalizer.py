CATEGORY_ALIASES = {

    "interesse": "Interessen",
    "interessen": "Interessen",
    "interest": "Interessen",
    "interests": "Interessen",

    "präferenz": "Präferenzen",
    "präferenzen": "Präferenzen",
    "preference": "Präferenzen",
    "preferences": "Präferenzen",

    "fähigkeiten": "Fähigkeiten",
    "fähigkeit": "Fähigkeiten",

    "skill": "Fähigkeiten",
    "skills": "Fähigkeiten",

    "experience": "Erfahrung",
    "erfahrung": "Erfahrung",

    "hobby": "Hobbys",
    "hobbys": "Hobbys",
    "hobbies": "Hobbys"
}


KEY_ALIASES = {

    "musik": "Lieblingsband",
    "music": "Lieblingsband",
    "musik_band": "Lieblingsband",
    "musik_bands": "Lieblingsband",
    "music_band": "Lieblingsband",
    "music_bands": "Lieblingsband",
    "favorite_band": "Lieblingsband",
    "favourite_band": "Lieblingsband",
    "favorite band": "Lieblingsband",
    "favourite band": "Lieblingsband",
    "favorite music": "Lieblingsband",
    "favourite music": "Lieblingsband",
    "favorite artist": "Lieblingsband",
    "favourite artist": "Lieblingsband",
    "band": "Lieblingsband",
    "lieblingsband": "Lieblingsband",

    "vorbilder": "Vorbild",
    "inspiration": "Vorbild",

    "programming_language": "Programmiersprache",
    "programming language": "Programmiersprache",

    "musical_instrument": "Instrument",
    "musical instrument": "Instrument",

    "favorite_book": "Lieblingsbuch",
    "favorite book": "Lieblingsbuch",
    "favourite_book": "Lieblingsbuch",
    "favourite book": "Lieblingsbuch"
}


class Normalizer:

    def normalize_category(self, category):

        category = category.strip()

        return CATEGORY_ALIASES.get(
            category.lower(),
            category
        )


    def normalize_key(self, key):

        key = key.strip()

        return KEY_ALIASES.get(
            key.lower(),
            key
        )


    def normalize_fact(self, fact):

        fact = fact.copy()

        fact["category"] = self.normalize_category(
            fact["category"]
        )

        fact["key"] = self.normalize_key(
            fact["key"]
        )

        if "value" in fact and isinstance(fact["value"], str):
            fact["value"] = fact["value"].strip()

        return fact


    def normalize(self, fact):

        return self.normalize_fact(
            fact
        )
