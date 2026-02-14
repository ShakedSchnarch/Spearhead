from typing import List, Type, Dict
from spearhead.logic.analyzers import Analyzer, IntegrityAnalyzer, ErosionAnalyzer, LogisticsAnalyzer
import logging

logger = logging.getLogger(__name__)

class AnalyzerRegistry:
    """
    Registry for Iron-Intelligence Analyzers.
    Decouples the main loop from specific analyzer implementations.
    """
    _analyzers: Dict[str, Type[Analyzer]] = {}

    @classmethod
    def register(cls, analyzer_cls: Type[Analyzer]):
        cls._analyzers[analyzer_cls.name] = analyzer_cls
        logger.debug(f"Registered analyzer: {analyzer_cls.name}")

    @classmethod
    def get_all(cls) -> List[Type[Analyzer]]:
        return list(cls._analyzers.values())

    @classmethod
    def initialize_active(cls, config: dict = None) -> List[Analyzer]:
        """
        Instantiates all registered analyzers.
        Config currently supports threshold values for analyzers that require runtime tuning.
        """
        instances = []
        for name, cls in cls._analyzers.items():
            try:
                # Handle special inits (Dependency Injection could be added here)
                if name == "erosion":
                    threshold = config.get("thresholds", {}).get("erosion_alert", 0.5) if config else 0.5
                    instances.append(cls(threshold=threshold))
                else:
                    instances.append(cls())
            except Exception as e:
                logger.error(f"Failed to initialize analyzer {name}: {e}")
        
        return instances

from spearhead.logic.ai_inference import RuleBasedAI

# Auto-register core analyzers
AnalyzerRegistry.register(IntegrityAnalyzer)
AnalyzerRegistry.register(ErosionAnalyzer)
AnalyzerRegistry.register(LogisticsAnalyzer)
AnalyzerRegistry.register(RuleBasedAI)
