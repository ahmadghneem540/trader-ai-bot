import math
from typing import List


def calculate_sma(data: List[float], period: int) -> List[float]:
    sma = []
    for i in range(len(data)):
        if i < period - 1:
            sma.append(None)
        else:
            sma.append(sum(data[i - period + 1: i + 1]) / period)
    return sma


def calculate_ema(data: List[float], period: int) -> List[float]:
    if not data:
        return []
    ema = []
    multiplier = 2 / (period + 1)
    sma = calculate_sma(data, period)
    ema = [None] * (period - 1)
    if len(data) >= period:
        ema.append(sma[period - 1])
        for i in range(period, len(data)):
            ema.append((data[i] * multiplier) + (ema[-1] * (1 - multiplier)))
    return ema


def calculate_rsi(data: List[float], period: int = 14) -> List[float]:
    if not data or len(data) < period + 1:
        return [None] * len(data)
    rsi = [None] * (period + 1)
    gains = []
    losses = []
    for i in range(1, len(data)):
        change = data[i] - data[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    if avg_loss == 0:
        rsi[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi[period] = 100 - (100 / (1 + rs))
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        if avg_loss == 0:
            rsi[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi[i + 1] = 100 - (100 / (1 + rs))
    return rsi


def calculate_macd(data: List[float], fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
    ema_fast = calculate_ema(data, fast_period)
    ema_slow = calculate_ema(data, slow_period)
    macd_line = []
    for i in range(len(data)):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line.append(ema_fast[i] - ema_slow[i])
        else:
            macd_line.append(None)
    signal_line = calculate_ema([x for x in macd_line if x is not None], signal_period)
    padded_signal = [None] * (len(macd_line) - len([x for x in macd_line if x is not None])) + signal_line
    histogram = []
    for i in range(len(macd_line)):
        if macd_line[i] is not None and padded_signal[i] is not None:
            histogram.append(macd_line[i] - padded_signal[i])
        else:
            histogram.append(None)
    return macd_line, padded_signal, histogram


def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14):
    if len(highs) != len(lows) or len(highs) != len(closes):
        return [None] * len(highs)
    tr = []
    for i in range(len(highs)):
        if i == 0:
            tr.append(highs[i] - lows[i])
        else:
            tr1 = highs[i] - lows[i]
            tr2 = abs(highs[i] - closes[i - 1])
            tr3 = abs(lows[i] - closes[i - 1])
            tr.append(max(tr1, tr2, tr3))
    atr = calculate_sma(tr, period)
    return atr
