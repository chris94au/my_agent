from pathlib import Path


WORKSPACE = Path("./workspace")



def read_file(filename):

    try:

        file_path = WORKSPACE / filename


        if not file_path.exists():

            return f"Datei {filename} existiert nicht."


        return file_path.read_text(
            encoding="utf-8"
        )


    except Exception as e:

        return f"Fehler beim Lesen: {e}"




def write_file(data):

    try:

        WORKSPACE.mkdir(
            exist_ok=True
        )


        filename = data["filename"]

        content = data["content"]


        file_path = WORKSPACE / filename


        file_path.write_text(
            content,
            encoding="utf-8"
        )


        return (
            f"Datei {filename} wurde erfolgreich gespeichert."
        )


    except Exception as e:

        return f"Fehler beim Schreiben: {e}"