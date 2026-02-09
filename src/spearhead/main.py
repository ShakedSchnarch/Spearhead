from __future__ import annotations

import typer
import uvicorn

from spearhead.config import settings
from spearhead.v1.reconcile import main as reconcile_main

cli = typer.Typer(help="Spearhead CLI (responses-only runtime)")


@cli.command()
def version() -> None:
    """Print runtime version."""
    typer.echo(f"Spearhead {settings.app.version}")


@cli.command()
def serve(
    host: str = typer.Option("127.0.0.1", help="Host to bind"),
    port: int = typer.Option(8000, help="Port to bind"),
    reload: bool = typer.Option(False, help="Enable autoreload for local development"),
) -> None:
    """Run the Spearhead API server."""
    uvicorn.run(
        "spearhead.api.main:app",
        host=host,
        port=port,
        reload=reload,
        app_dir="src",
    )


@cli.command()
def reconcile() -> None:
    """Rebuild v1 read-model snapshots from normalized responses."""
    raise SystemExit(reconcile_main())


if __name__ == "__main__":
    cli()
