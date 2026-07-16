import logging


logger = logging.getLogger(__name__)


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

    def _clean_text(self, text):
        return " ".join(
            str(text).strip().split()
        )


    def normalize_category(self, category):
        cleaned = self._clean_text(category)
        normalized = CATEGORY_ALIASES.get(
            cleaned.casefold(),
            cleaned
        )

        if normalized != cleaned:
            logger.info(
                "Normalized category %r -> %r",
                cleaned,
                normalized
            )

        return normalized


    def normalize_key(self, key):
        cleaned = self._clean_text(key)
        normalized = KEY_ALIASES.get(
            cleaned.casefold(),
            cleaned
        )

        if normalized != cleaned:
            logger.info(
                "Normalized key %r -> %r",
                cleaned,
                normalized
            )

        return normalized


    def normalize_value(self, value):
        if not isinstance(value, str):
            return value

        cleaned = self._clean_text(value)

        if cleaned != value:
            logger.info(
                "Normalized value %r -> %r",
                value,
                cleaned
            )

        return cleaned


    def normalize_topic(self, topic):
        if topic is None:
            return topic

        cleaned = self._clean_text(topic)
        normalized = KEY_ALIASES.get(
            cleaned.casefold(),
            cleaned
        )

        if normalized != cleaned:
            logger.info(
                "Normalized topic %r -> %r",
                cleaned,
                normalized
            )

        return normalized


    def normalize_fact(self, fact):
        fact = fact.copy()

        fact["category"] = self.normalize_category(
            fact["category"]
        )
        fact["key"] = self.normalize_key(
            fact["key"]
        )

        if "value" in fact:
            fact["value"] = self.normalize_value(
                fact["value"]
            )

        return fact


    def normalize_summary(self, summary):
        summary = summary.copy()

        if "topic" in summary:
            summary["topic"] = self.normalize_topic(
                summary["topic"]
            )

        if "summary" in summary:
            summary["summary"] = self.normalize_value(
                summary["summary"]
            )

        return summary


    def normalize(self, fact):
        return self.normalize_fact(
            fact
        )
