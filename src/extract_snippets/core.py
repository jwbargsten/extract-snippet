import logging
import pystache
import re
from itertools import dropwhile
import extract_snippets.util as util

logger = logging.getLogger(__name__)

DEFAULT = {
    "output_template": "```{{lang}}\n{{snippet}}\n```\n",
    "output_dir": "extracted",
    "comment_prefix": "# ",
    "comment_suffix": "",
    "snippet_start": ":snippet",
    "snippet_end": ":endsnippet",
    "cloak_start": ":cloak",
    "cloak_end": ":endcloak",
}


class Snippet:
    @classmethod
    def from_raw_data(cls, params, data):
        (head,) = data[:1]
        (tail,) = data[-1:]
        body = data[1:-1]

        idlvl = util.det_indent_lvl(body)

        body = (line[idlvl:] for line in body)
        body = dropwhile(util.is_empty, body)
        body = util.dropwhile_right(util.is_empty, list(body))

        return cls(params=params, head=head.lstrip(), body=list(body), tail=tail.lstrip())

    def __init__(self, params=None, head=None, body=None, tail=None):
        self.params = params
        self.head = head
        self.body = body
        self.tail = tail

    def __repr__(self):
        return f"Snippet({self.params!r}, {self.head!r}, {self.body!r}, {self.tail!r})"


def render_snippet(template, params, body):
    return pystache.render(template, {**params, **{"snippet": "\n".join(body)}})


def get_configs(conf):
    configs = conf["config"]
    default = configs["default"] if "default" in configs else None
    for name in [n for n in configs if not n == "default"]:
        c = util.merge_with_default_conf(configs[name], default, global_default=DEFAULT)
        yield c


def extract_from_file(f, conf):
    comment_prefix = re.escape(conf["comment_prefix"])
    comment_suffix = re.escape(conf["comment_suffix"])

    cloak_start = re.escape(conf["cloak_start"])
    cloak_end = re.escape(conf["cloak_end"])
    cloak_start_re = f"^\\s*{comment_prefix}{cloak_start}{comment_suffix}$"
    cloak_end_re = f"^\\s*{comment_prefix}{cloak_end}{comment_suffix}$"

    snippet_start = re.escape(conf["snippet_start"])
    snippet_end = re.escape(conf["snippet_end"])
    snippet_start_re = f"^\\s*{comment_prefix}{snippet_start} (.*){comment_suffix}$"
    snippet_end_re = f"^\\s*{comment_prefix}{snippet_end}{comment_suffix}$"

    snippets = []

    in_snippet = False
    cloaked = False
    data = []
    params = {}

    with open(f, "r") as fd:
        for line in fd:
            if re.search(cloak_end_re, line):
                cloaked = False
                continue
            if re.search(cloak_start_re, line):
                cloaked = True
            if cloaked:
                continue

            if match := re.search(snippet_start_re, line):
                params = util.to_dict(match.group(1).strip())
                if not params["name"]:
                    raise KeyError("name key not set")
                in_snippet = True
            if not in_snippet:
                continue

            data.append(line.rstrip("\n"))
            if re.search(snippet_end_re, line):
                in_snippet = False
                snippets.append(Snippet.from_raw_data(params, data))
                data = []
                params = {}
    return snippets
