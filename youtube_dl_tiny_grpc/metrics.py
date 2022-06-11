from prometheus_client import CollectorRegistry
import glob
import os


_REGISTRY = CollectorRegistry()


def prepare_metrics_directory(d: str) -> None:
    os.environ["PROMETHEUS_MULTIPROC_DIR"] = d
    if not os.path.exists(d):
        os.mkdir(d)
    files = glob.glob(d + "/*")
    for f in files:
        os.remove(f)
