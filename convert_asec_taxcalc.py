# personal exemptions

pexemp = pd.DataFrame({
    'year': [2018],
    'pexemp': [0]})


# Set missing income items to zero so that non-filers etc will get zeroes.
VARS_MISSING_ZERO = [
    'eitcred', 'fedretir', 'fedtax', 'statetax', 'adjginc', 'taxinc',
    'fedtaxac', 'fica', 'stataxac', 'incdivid', 'incint', 'incrent',
    'incother', 'incasist', 'incss', 'incwelfr', 'incwkcom', 'incvet',
    'incchild', 'incunemp', 'inceduc', 'gotveduc', 'gotvothe', 'gotvpens',
    'gotvsurv', 'incssi', 'incwage', 'incbus', 'incfarm', 'incsurv',
    'incdisab', 'incretir', 'inccapg']


# these are the missing codes
MISSING_CODES = [9999, 99999, 999999, 9999999,
                 -9999, -99999, -999999, -9999999,
                 9997, 99997, 999997, 9999997]

COLS_ZERO_TO_NA = ['momloc', 'poploc', 'sploc']

ASEC_TAXCALC_RENAMES = {
    'incunemp': 'e02300',
    'inccapg': 'p23250',
    'proptax': 'e18500',
    'incdivid': 'e00650',
    'incretir': 'e01700',
    'incss': 'e02400',
    'incint': 'e00300'
}


def convert_asec_person_taxcalc(ipums):
    """ Add taxcalc columns to ASEC person record, which can be summed by
        tax unit to create a dataset that can act as a taxcalc Records object.

    Args:
        ipums: DataFrame representing ASEC persons as retrieved through IPUMS.

    Returns:
        DataFrame with taxcalc columns.
    """
    # Start by renaming 1:1 mapped columns.
    res = ipums.rename(columns=ASEC_TAXCALC_RENAMES)
    # Add simple count of people.
    res['XTOT'] = 1
    # Add dependent features.
    res['nu06'] = (res.age < 6) & res.is_dep
    res['nu13'] = (res.age < 13) & res.is_dep
    res['f2441'] = (res.age < 13) & res.is_dep
    res['n24'] = (res.age < 17) & res.is_dep
    res['elderly_dependents'] = (res.age > 65) & res.is_dep
    # Add age groups.
    res['nu18'] = res.age < 18
    res['n1820'] = res.age.between(18, 20)
    res['n21'] = res.age > 20
    # Summed income categories.
    res['e00200'] = ipum[['incwage', 'incbus', 'incfarm']].sum(axis=1)
    # Treat all qualified dividends as ordinary dividends.
    res['e00600'] = res.e00650
    # Assume taxable pensions and annuities = total pensions and annuities.
    res['e01500'] = res.e01700
    # Add ages and wages for heads and spouses.
    res['is_filer_head'] = res.pernum == res.filer_pernum
    res['is_filer_spouse'] = res.sploc == res.filer_pernum
    res['age_head'] = np.where(is_filer_head, res.age, 0)
    res['age_spouse'] = np.where(is_filer_spouse, res.age, 0)
    res['e00200p'] = np.where(is_filer_head, res.e00200, 0)
    res['e00200s'] = np.where(is_filer_spouse, res.e00200, 0)
    # 