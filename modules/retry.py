"""
=============================================================
MODULO: RETRY COM BACKOFF EXPONENCIAL
=============================================================
Decorator e presets para retry com backoff exponencial.
Uso em chamadas de API (Apify, Groq, Gemini).
"""

import time
import functools
from typing import Callable


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    retryable_exceptions: tuple = (Exception,),
    on_retry: Callable | None = None,
):
    """
    Decorator para retry com backoff exponencial.

    Args:
        max_retries: Numero maximo de tentativas (alem da primeira)
        base_delay: Delay base em segundos
        max_delay: Delay maximo em segundos
        exponential_base: Base da exponenciacao
        retryable_exceptions: Tupla de exceptions que disparam retry
        on_retry: Callback opcional chamado a cada retry (attempt, exception, delay)
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    delay = min(
                        base_delay * (exponential_base ** attempt),
                        max_delay
                    )

                    if on_retry:
                        on_retry(attempt + 1, e, delay)
                    else:
                        print(f"    Retry {attempt + 1}/{max_retries}: {type(e).__name__}: {e}")
                        print(f"    Aguardando {delay:.1f}s...")

                    time.sleep(delay)

            raise last_exception

        return wrapper
    return decorator


def _default_retry_log(attempt, exception, delay):
    """Log padrao para retries."""
    print(f"    Retry {attempt}: {type(exception).__name__}: {exception}")
    print(f"    Aguardando {delay:.1f}s...")


# -----------------------------------------
# PRESETS
# -----------------------------------------

def api_retry(func):
    """Preset para chamadas de API genericas (3 retries, 2s base)."""
    return retry_with_backoff(
        max_retries=3,
        base_delay=2.0,
        max_delay=30.0,
        retryable_exceptions=(Exception,),
    )(func)


def apify_retry(func):
    """Preset para Apify API (3 retries, 5s base — actors demoram)."""
    return retry_with_backoff(
        max_retries=3,
        base_delay=5.0,
        max_delay=60.0,
        retryable_exceptions=(Exception,),
    )(func)


def groq_retry(func):
    """Preset para Groq Whisper API (3 retries, 3s base)."""
    return retry_with_backoff(
        max_retries=3,
        base_delay=3.0,
        max_delay=30.0,
        retryable_exceptions=(Exception,),
    )(func)


def gemini_retry(func):
    """Preset para Gemini API (3 retries, 5s base — rate limit)."""
    return retry_with_backoff(
        max_retries=3,
        base_delay=5.0,
        max_delay=60.0,
        retryable_exceptions=(Exception,),
    )(func)
