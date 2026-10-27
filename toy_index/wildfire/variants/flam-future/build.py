"""ALFRESCO relative flammability 2040-2069, 5modelAvg, RCP 4.5 (Rasdaman); raw pixels, NaN = not burnable."""
from common import data as D


def build():
    return dict(values=D.flam())
