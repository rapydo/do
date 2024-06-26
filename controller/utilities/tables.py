from rich.console import Console
from rich.table import Table


def print_table(headers: list[str], rows: list[list[str]], table_title: str) -> None:
    table = Table(title=table_title)

    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*row)

    console = Console()
    console.print(table)
