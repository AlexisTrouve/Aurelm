"""Standalone profiler run — profiles all entities missing description/tags."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from pipeline.entity_profiler import build_entity_profiles
from pipeline.llm_provider import OpenRouterProvider, load_llm_config

DB = "aurelm_t01t08_fresh.db"
cfg = load_llm_config("pipeline_llm_config.json")
provider = OpenRouterProvider()

profiles = build_entity_profiles(
    DB,
    model=cfg.get_model("profiling"),
    use_llm=True,
    incremental=True,
    run_id=None,
    provider=provider,
)
usage = provider.get_usage()
print(f"Profiled: {len(profiles)} entities | Cost: ${usage['total_cost']:.4f}")
