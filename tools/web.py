from .internet_research import read_url, web_search
from .registry import Tool, ToolParameter


web_search_tool = Tool(
    name="web_search",
    description="Durchsucht das Internet frei und priorisiert Ergebnisse mit einem dynamischen Glossar informativer Websites.",
    parameters=[
        ToolParameter(
            name="query",
            type="string",
            required=True,
            description="Suchanfrage"
        ),
        ToolParameter(
            name="max_results",
            type="integer",
            required=False,
            description="Maximale Anzahl an Treffern",
            default=5
        )
    ],
    execute_fn=web_search,
    permission="network",
    requires_confirmation=False,
    accepts_scalar=True,
)


read_url_tool = Tool(
    name="read_url",
    description="Öffnet eine URL und liest Textseiten direkt. Nicht-textuelle Inhalte werden nur nach Bestätigung gespeichert.",
    parameters=[
        ToolParameter(
            name="url",
            type="string",
            required=True,
            description="Zu öffnende URL"
        ),
        ToolParameter(
            name="max_chars",
            type="integer",
            required=False,
            description="Maximale Zeichenanzahl",
            default=12000
        ),
        ToolParameter(
            name="confirm_download",
            type="boolean",
            required=False,
            description="Download bestätigen",
            default=False
        )
    ],
    execute_fn=read_url,
    permission="network",
    requires_confirmation=False,
    accepts_scalar=True,
)


tool = web_search_tool
read_tool = read_url_tool
