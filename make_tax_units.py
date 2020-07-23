""" Makes tax units from the ASEC.

Based on Sam Portnow's code at 
https://users.nber.org/~taxsim/to-taxsim/cps/cps-portnow/TaxSimRScriptForDan.R
"""
import numpy as np

# https://cps.ipums.org/cps-action/variables/RELATE#codes_section
RELATE_COHABITORS_NOT_MARRIED_CODE = 1114


def tax_unit_id(ipum):
    """ Create a tax unit identifier for each person record in an IPUMS ASEC.

    Args:
        ipum: DataFrame representing the ASEC file from IPUMS.

    Returns:
        Series with a tax unit ID for each row in ipum.
        This is the minimum of the pernum or sploc, so spouses will get the
        same id. For children, it is the minimum of the momloc or poploc.
        Other relatives are made dependent on the household head (which may be
        incorrect) and non-relatives are separate tax units. 
    """
    # Set to lower case
    ipum.columns = ipum.columns.str.lower()
    ipum.loc[ipum.relate == RELATE_COHABITORS_NOT_MARRIED_CODE,
             'sploc'] = np.nan
    # hnum is used for x.
    ipum['hnum'] = np.where(ipum.relate == RELATE_HEAD_OF_HOUSEHOLD_CODE,
                            ipum.pernum, np.nan)
    # If someone is a dependent of their spouse, set dependent pointer to 0.
    ipum.loc[~ipum.sploc.isna() & (ipum.depstat > 0) & 
             (ipum.depstat == ipum.sploc), 'depstat'] = 0
    # Someone is a dependent if they have a depstat.
    ipum['is_dep'] = ipum.depstat > 0
    # Dependent children must be dependents with a parent who is below age 18,
    # or below age 24 if in school.
    ipum['depchild'] = np.where(
        ipum.is_dep &
        (~ipum.momloc.isna() | ~ipum.poploc.isna()) &
        ((ipum.age < 18) | ((ipum.age < 24) & (ipum.schlcoll > 0))),
        1, 0)
    # Dependent relatives are dependents who are not dependent children.
    ipum['deprel'] = np.where(ipum.is_dep & (ipum.depchild == 0), 1, 0)
    # Define identifier as 100 * serial (household) + tax unit sub-identifier
    tax_id = (100 * ipum.serial +
              # Dependents
              np.where(ipum.depchild, np.fmin(deps.momloc, deps.poploc),
                       np.where(deps.deprel, deps.hnum,
                                # Taxpayers.
                                np.fmin(txpyrs.pernum, txpyrs.sploc))))
    return tax_id