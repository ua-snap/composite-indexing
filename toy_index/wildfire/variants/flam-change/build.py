"""Absolute change in ALFRESCO relative flammability: 2040-2069 (5modelAvg, RCP 4.5) minus 1980-2008 (MODEL-SPINUP,
historical), both from the same Rasdaman coverage. Absolute, not %, because a third of burnable land is 0 at the start."""
from common import data as D
from common import sources as S


def build():
    return dict(values=D.flam(S.FLAM) - D.flam(S.FLAM_HIST))
