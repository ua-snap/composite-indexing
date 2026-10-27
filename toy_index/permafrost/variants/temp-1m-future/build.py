"""GIPL magt1m, 5ModelAvg RCP 4.5, mean of climate years 2040-2069; stuck cells and their 2 km border masked."""
from common import data as D


def build():
    return dict(values=D.gipl_mean(range(2040, 2070)))
