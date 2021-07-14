__version__ = "2021.3.22"

import logging
from pyhocon import ConfigFactory
import snex.core as core
import snex.util as util
from pathlib import Path

logger = logging.getLogger(__name__)


def extract(base_path=None, out_path=None, config_file=None):
    if base_path is None:
        base_path = Path()

    if config_file is None:
        config_file = base_path / "snex.conf"

    processed_snippets = []
    logger.info(f"using config file {str(config_file)}")
    conf_root = ConfigFactory.parse_file(config_file)
    no_snippets = True
    for conf_name, conf in core.get_configs(conf_root):
        logger.info(f"processing config {conf_name}")

        if out_path is None:
            out_path = base_path / Path(conf["output_path"])
        logger.info(f"working dir: {str(base_path)}")
        logger.info(f"output dir: {str(out_path)}")
        out_path.mkdir(exist_ok=True, parents=True)

        out_ext = conf["output_ext"]

        snippets = (
            snippet
            for f in util.list_paths(conf, base_path)
            for snippet in core.extract_from_path(f, conf)
        )
        for snippet in snippets:
            no_snippets = False
            dst = out_path / f"{conf_name}-{snippet.name}{out_ext}"
            origin = str(Path(snippet.origin).relative_to(base_path))
            logger.info(f"{origin}:{snippet.name} -> {dst}")
            processed_snippets.append((dst, snippet.name, origin, snippet.line_number))
            res = core.render_snippet(conf["output_template"], {**conf, **snippet.params}, snippet.body)
            dst.write_text(res)
    if no_snippets:
        logger.info("no snippets found")
    return processed_snippets
