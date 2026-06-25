import runpy
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: isoftdev_requirements_runner.py <reagent_root> [main.py args...]")

    reagent_root = Path(sys.argv[1]).resolve()
    reagent_src = reagent_root / "src" / "reagent"
    main_py = reagent_src / "main.py"

    sys.path.insert(0, str(reagent_root))
    sys.path.insert(0, str(reagent_src))

    import util
    import util.util

    def auto_no_feedback(*_args, **_kwargs):
        return "no"

    util.multiline_input = auto_no_feedback
    util.util.multiline_input = auto_no_feedback

    sys.argv = [str(main_py), *sys.argv[2:]]
    runpy.run_path(str(main_py), run_name="__main__")


if __name__ == "__main__":
    main()
