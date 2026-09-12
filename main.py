from src.auto_ntzfind import AUTO_NTZFIND
from src.lif2rle import convert_period
from src.rle2apgcode import RLE2APGCODE
from src.cleanup import CLEANUP
from src.combine import COMBINE
from submodules import lifelib

def main():
    period = 0
    user_input = input('Run auto-ntzfind? (y/n): ')
    if user_input.lower() == 'y':
        period = int(input('Period: '))
        iterations = int(input('Number of spaceships: '))
        print('Clearing golly files...')
        CLEANUP(period).clear_files()
        print('Searching for spaceships...')
        AUTO_NTZFIND(iterations, period).run()
        convert_period(period)
        RLE2APGCODE(lifelib, period).run()

    user_input = input('Run rle2apgcode? (y/n): ')
    if user_input.lower() == 'y':
        if period == 0:
            period = input('Period: ')
        convert_period(period)
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

if __name__ == '__main__':
    main()
