import logging
import sys
from pathlib import Path

import typer
import yaml

from iron_view.etl.loader import load_data
from iron_view.renderer.builder import ReportBuilder
from iron_view.domain.models import BattalionData
from iron_view.config import settings

app = typer.Typer(help="Iron-View Battalion Readiness System")

def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
@app.command()
def version():
    """
    Prints the version of Iron-View.
    """
    print("Iron-View v1.0.0")

@app.command()
def build(
    input_path: Path = typer.Option(..., "--input", "-i", help="Path to input CSV file"),
    output_path: Path = typer.Option(..., "--output", "-o", help="Path to output HTML report"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """
    Builds the readiness report from raw data.
    """
    setup_logging(verbose)
    logger = logging.getLogger("iron_view")
    
    logger.info(f"Starting Iron-View build. Input: {input_path}")
    
    try:
        # 1. Load Data
        data = load_data(input_path)
    except Exception as e:
        logger.critical(f"Failed to load data: {e}")
        raise typer.Exit(code=1)
        
    logger.info(f"Loaded {len(data.reports)} reports.")

    if not data.reports:
        logger.warning("No data loaded. Report might be empty.")

    # 2. Logic / AI Analysis
    from iron_view.logic.engine import AnalysisEngine
    from iron_view.logic.registry import AnalyzerRegistry
    
    # Initialize Engine via Registry (Decoupled)
    analyzers = AnalyzerRegistry.initialize_active(
        config={"thresholds": {"erosion_alert": settings.thresholds.erosion_alert}}
    )
    engine = AnalysisEngine(analyzers)
    
    engine.run(data)
    
    # 3. Render Report
    # Use paths from config
    templates_dir = settings.paths.templates_dir
    assets_dir = settings.paths.assets_dir
    
    if not templates_dir.exists():
        logger.warning(f"Templates dir not found at {templates_dir}. Checks config/settings.yaml or CWD.")

    builder = ReportBuilder(template_dir=templates_dir, assets_dir=assets_dir, settings=settings)
    html_content = builder.build_artifact(data)
    
    # 4. Write Output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    
    logger.info(f"Report generated successfully at: {output_path}")

if __name__ == "__main__":
    app()
