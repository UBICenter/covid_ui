""" Makes tax units from the ASEC.

Based on Sam Portnow's code at 
https://users.nber.org/~taxsim/to-taxsim/cps/cps-portnow/TaxSimRScriptForDan.R
"""
import numpy as np

"""
TODO:
1) Verify that heads of household (relate=101) always have pernum = 1.
   True for 2018.
2) Verify that sploc is always null for cohabitors not married (relate=1114).
   True for 2018.
"""


def tax_unit_id(ipum):
    """ Create a tax unit identifier for each person record in an IPUMS ASEC.

    Args:
        ipum: DataFrame representing the ASEC file from IPUMS.

    Returns:
        Nothing. Adds the following columns:
        - is_dep: Dependent of someone other than their spouse.
        - depchild: Dependent whose parent is in their household and is either
            under 18 or under 24 and in school.
        - deprel: Dependent who is not a dependent child.
        - filer_pernum: Person number of the filer.
            This is the minimum of the pernum or sploc, so spouses will get the
            same id. For children, it is the minimum of the momloc or poploc.
            Other dependent relatives are assigned to the household head.
            (TODO: Assign them to their claimant, or their claimant's filer
            head). Non-relatives and relative non-dependents are separate tax
            units.
        - taxid: Unique identifier for the filer, calculated as:
            100 * serial (household identifier) + filer_pernum.
    """
    # Set to lower case
    ipum.columns = ipum.columns.str.lower()
    # Someone is a dependent if they have a depstat that isn't their spouse.
    ipum['is_dep'] = (ipum.depstat > 0) & (ipum.depstat != ipum.sploc)
    # Dependent children must be dependents with a parent who is below age 18,
    # or below age 24 if in school.
    ipum['depchild'] = np.where(
        ipum.is_dep &
        (~ipum.momloc.isna() | ~ipum.poploc.isna()) &
        ((ipum.age < 18) | ((ipum.age < 24) & (ipum.schlcoll > 0))),
        1, 0)
    # Dependent relatives are dependents who are not dependent children.
    ipum['deprel'] = np.where(ipum.is_dep & (ipum.depchild == 0), 1, 0)
    # Calculate line number within household of the filer.
    ipum['filer_pernum'] = np.where(
        # Dependent children go to their parent.
        ipum.depchild, np.fmin(ipum.momloc, ipum.poploc),
        # Dependent relatives go to the head of household.
        np.where(ipum.deprel, 1,
            # Taxpayers.
            np.fmin(ipum.pernum, ipum.sploc)))
    # Define identifier as 100 * serial (household) + tax unit sub-identifier
    ipum['taxid'] = 100 * ipum.serial + ipum.filer_pernum