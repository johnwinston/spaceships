from src.auto_ntzfind import AUTO_NTZFIND
from src.rle2apgcode import RLE2APGCODE
from src.cleanup import CLEANUP
from src.combine import COMBINE
from submodules import lifelib

import argparse
from typing import Optional, List


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Automons runner (non-interactive or interactive)")
    sub = parser.add_subparsers(dest="command")

    # auto-ntzfind: clear files, run ntzfind, then rle2apgcode
    p_auto = sub.add_parser("auto-ntzfind", help="Run ntzfind search and convert results")
    p_auto.add_argument("period", type=str, help="Period, e.g. 4")
    p_auto.add_argument("iterations", type=int, help="Number of spaceships to find")
    p_auto.add_argument("--no-clear", action="store_true", help="Do not clear existing Golly files first")

    # rle2apgcode only
    p_rle = sub.add_parser("rle2apgcode", help="Convert RLEs to APGcode and generate GIFs/QRs")
    p_rle.add_argument("period", type=str, help="Period, e.g. 4")

    # clear files inside Golly dirs
    p_clear = sub.add_parser("clear-files", help="Clear generated RLEs and ntzfind patterns from Golly dirs")
    p_clear.add_argument("period", type=str, help="Period, e.g. 4")

    # interactive selection GUI (Tk)
    p_select = sub.add_parser("select", help="Open selection UI to keep/delete generated GIFs/QRs")
    p_select.add_argument("period", type=str, help="Period, e.g. 4")

    # combine cards
    p_combine = sub.add_parser("combine", help="Render cards for a given period")
    p_combine.add_argument("period", type=str, help="Period, e.g. 4")

    # one-shot end-to-end (clear -> ntzfind -> rle2apgcode -> combine)
    p_all = sub.add_parser("all", help="Run the full flow non-interactively")
    p_all.add_argument("period", type=str, help="Period, e.g. 4")
    p_all.add_argument("iterations", type=int, help="Number of spaceships to find")
    p_all.add_argument("--no-clear", action="store_true", help="Do not clear existing Golly files first")

    args = parser.parse_args(argv)

    # Non-interactive CLI path
    if args.command == "auto-ntzfind":
        if not args.no_clear:
            print("Clearing golly files...")
            CLEANUP(args.period).clear_files()
        print("Searching for spaceships...")
        AUTO_NTZFIND(args.iterations, args.period).run()
        RLE2APGCODE(lifelib, args.period).run()
        return 0

    if args.command == "rle2apgcode":
        RLE2APGCODE(lifelib, args.period).run()
        return 0

    if args.command == "clear-files":
        CLEANUP(args.period).clear_files()
        return 0

    if args.command == "select":
        CLEANUP(args.period).select_patterns()
        return 0

    if args.command == "combine":
        COMBINE(args.period).run()
        return 0

    if args.command == "all":
        if not args.no_clear:
            print("Clearing golly files...")
            CLEANUP(args.period).clear_files()
        print("Searching for spaceships...")
        AUTO_NTZFIND(args.iterations, args.period).run()
        RLE2APGCODE(lifelib, args.period).run()
        COMBINE(args.period).run()
        return 0

    # Interactive fallback if no command provided
    period: object = 0
    user_input = input('Run auto-ntzfind? (y/n): ')
    if user_input.lower() == 'y':
        period = int(input('Period: '))
        iterations = int(input('Number of spaceships: '))
        print('Clearing golly files...')
        CLEANUP(period).clear_files()
        print('Searching for spaceships...')
        AUTO_NTZFIND(iterations, period).run()
        RLE2APGCODE(lifelib, period).run()

    user_input = input('Run rle2apgcode? (y/n): ')
    if user_input.lower() == 'y':
        if period == 0:
            period = input('Period: ')
        RLE2APGCODE(lifelib, period).run()

    user_input = input('Run cleanup? (y/n): ')
    if user_input.lower() == 'y':
        if period == 0:
            period = input('Period: ')
        CLEANUP(period).select_patterns()

    user_input = input('Combine cards? (y/n): ')
    if user_input.lower() == 'y':
        if period == 0:
            period = input('Period: ')
        COMBINE(period).run()

    return 0


if __name__ == '__main__':
    raise SystemExit(main())
