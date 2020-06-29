# __init__.py

from typing import Dict, Any
import logging
import os
import sys
from traceback import print_tb

log = logging.getLogger('server')

def exception_to_dict(exception: Exception, log_error=False) -> Dict[str,Any]:
    """Convert an exception into a dict for JSON response."""
    if log_err:
        log.error(f'converting exception: {str(exception)}')
        if os.environ.get('PRINT_TB'):
            print_tb(sys.exc_info()[2])
    return {'error_type': type(exception).__name__, 'message': str(exception)}
