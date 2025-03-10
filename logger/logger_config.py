from loguru import logger


logger.level("PROFIT", no=25, color="<green>")
logger.level("BALANCE", no=35, color="<yellow>")
logger.level("PROFIT_ERROR", no=40, color="<red>")

logger.level("MODULE", no=10, color="<blue>")

logger.level("SUMMARY", no=10, color="<blue>")


logger.add('../logger/debug.log',
           format="{time} {level} {message}",
           level='DEBUG',
           rotation='100 MB',
           compression='zip')


logger.add('../logger/profit_search.log',
           format="{time} {level} {message}",
           level='PROFIT',
           rotation='100 MB',
           compression='zip')


logger.add('../logger/profit_search.log',
           format="{time} {level} {message}",
           level='PROFIT_ERROR',
           rotation='100 MB',
           compression='zip')


logger.add('../logger/debug.log',
           format="{time} {level} {message}",
           level='SUMMARY',
           rotation='100 MB',
           compression='zip')




