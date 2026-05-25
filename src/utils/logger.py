from loguru import logger

def setup_logger(level: str = "INFO") -> None:
    logger.remove()
    
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level=level.upper(),
        backtrace=True,
        diagnose=True,
    )
    
    logger.add(
        sink="logs/app_{time:YYYY-MM-DD}.log",
        rotation="10 MB",      
        retention="7 days",    
        level=level.upper(),
        backtrace=True,
        diagnose=True,
    )

__all__ = ["logger", "setup_logger"]