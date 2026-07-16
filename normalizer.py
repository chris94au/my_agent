CATEGORY_ALIASES = {

    "interesse": "Interessen",
    "interessen": "Interessen",

    "fähigkeiten": "Fähigkeiten",
    "fähigkeit": "Fähigkeiten",

    "skill": "Fähigkeiten",

    "experience": "Erfahrung",
    "erfahrung": "Erfahrung",

    "hobby": "Hobbys",
    "hobbys": "Hobbys"
}


KEY_ALIASES = {

    "musik": "Lieblingsband",
    "musik_band": "Lieblingsband",
    "musik_bands": "Lieblingsband",
    "musik_bewerber": "Lieblingsband",
    "band": "Lieblingsband",

    "vorbilder": "Vorbild",
    "inspiration": "Vorbild",

    "programming_language": "Programmiersprache",

    "musical_instrument": "Instrument",

    "favorite_book": "Lieblingsbuch"
}


class Normalizer:

    def normalize(self, fact):

        fact = fact.copy()

        category = fact["category"].strip().lower()
        key = fact["key"].strip().lower()

        fact["category"] = CATEGORY_ALIASES.get(
            category,
            fact["category"]
        )

        fact["key"] = KEY_ALIASES.get(
            key,
            fact["key"]
        )

        return fact