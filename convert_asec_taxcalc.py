import numpy as np
import pandas as pd

ASEC_TAXCALC_RENAMES = {
    'incunemp': 'e02300',
    'inccapg': 'p23250',
    'incdivid': 'e00650',
    'incretir': 'e01700',
    'incss': 'e02400',
    'incint': 'e00300'
}


def convert_asec_person_taxcalc(ipum):
    """ Add taxcalc columns to ASEC person record, which can be summed by
        tax unit to create a dataset that can act as a taxcalc Records object.

    Args:
        ipums: DataFrame representing ASEC persons as retrieved through IPUMS.

    Returns:
        DataFrame with taxcalc columns.
    """
    # Start by renaming 1:1 mapped columns.
    res = ipum.rename(columns=ASEC_TAXCALC_RENAMES)
    # Add simple count of people.
    res['XTOT'] = 1
    # Add dependent features.
    res['nu06'] = (res.age < 6) & res.is_dep
    res['nu13'] = (res.age < 13) & res.is_dep
    res['f2441'] = (res.age < 13) & res.is_dep
    res['n24'] = (res.age < 17) & res.is_dep
    res['num_eitc_qualified_kids'] = (res.age < 18) & res.is_dep
    res['elderly_dependents'] = (res.age > 65) & res.is_dep
    # Add age groups.
    res['nu18'] = res.age < 18
    res['n1820'] = res.age.between(18, 20)
    res['n21'] = res.age > 20
    # Summed income categories for calculating primary and spouse values.
    # May differ from e00200, which is calculated post hoc as e00200p+e00200s.
    res['_e00200'] = res[['incwage', 'incbus', 'incfarm']].sum(axis=1)
    # Treat all qualified dividends as ordinary dividends.
    res['e00600'] = res.e00650
    # Assume taxable pensions and annuities = total pensions and annuities.
    res['e01500'] = res.e01700
    # Add ages and wages for heads and spouses.
    res['is_filer_head'] = res.pernum == res.filer_pernum
    res['is_filer_spouse'] = res.sploc == res.filer_pernum
    res['age_head'] = np.where(res.is_filer_head, res.age, 0)
    res['age_spouse'] = np.where(res.is_filer_spouse, res.age, 0)
    res['e00200p'] = np.where(res.is_filer_head, res._e00200, 0)
    res['e00200s'] = np.where(res.is_filer_spouse, res._e00200, 0)
    res['e00200'] = res.e00200p + res.e00200s
    res['blind_head'] = res.is_filer_head & (res.diffeye == 1)
    res['blind_spouse'] = res.is_filer_spouse & (res.diffeye == 1)
    return res


def create_tax_unit(tp):
    """ Creates tax unit based on a taxcalc-prepared person file.

    Args:
        tp: DataFrame representing taxcalc person file.

    Returns:
        DataFrame with one record per tax unit.
    """
    SUMCOLS = (
        list(ASEC_TAXCALC_RENAMES.values()) +
        ['XTOT', 'nu06', 'nu13', 'f2441', 'n24', 'num_eitc_qualified_kids',
         'elderly_dependents', 'is_dep', 'nu18', 'n1820', 'n21',
         'e00200', 'e00200p', 'e00200s', 'e00600', 'e01500',
         'age_head', 'age_spouse',
         'blind_head', 'blind_spouse'
         ])
    TAX_UNIT_IDS = ['FLPDYR', 'filer_pernum', 'taxid', 'serial']
    tu = tp.groupby(TAX_UNIT_IDS)[SUMCOLS].sum().reset_index()
    tu['EIC'] = np.minimum(tu.num_eitc_qualified_kids, 3)
    # Define marital status:
    # 1=single (no spouse or dependents)
    # 2=joint (married)
    # 3=separate (not identified in CPS)
    # 4=household-head (no spouse, but with dependents)
    # 5=widow(er) (not identified in CPS)
    tu['MARS'] = np.where(tu.age_spouse == 0,  # i.e., spouse exists.
                          np.where(tu.is_dep > 0, 4, 1), 2)
    # Calculate unique RECID (required for taxcalc) based on year and taxid.
    tu['RECID'] = tu.FLPDYR * 1e9 + tu.taxid
    return tu.reset_index()
