# sdwan_tunnel/utils/logging_utils.py
"""
Structured logging utility for tracing operations.
"""
import logging
import uuid
 
logger = logging.getLogger('sdwan_tunnel')
 
 
def structured_log(event, level='info', correlation_id=None, **fields):
    """
    Emit a structured log entry with an event name, optional correlation_id, and key/value fields.
    Returns a generated correlation_id if not provided.
    """
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())
    log_data = {'event': event, 'correlation_id': correlation_id}
    log_data.update(fields)
    message = f"{event} | " + " | ".join(f"{k}={v}" for k, v in fields.items())
    log_method = getattr(logger, level, logger.info)
    log_method(message)
    return correlation_id