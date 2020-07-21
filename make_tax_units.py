""" Makes tax units from the ASEC.

Based on Sam Portnow's code at 
https://users.nber.org/~taxsim/to-taxsim/cps/cps-portnow/TaxSimRScriptForDan.R
"""
import numpy as np
import pandas as pd

# personal exemptions

pexemp = pd.DataFrame({
  'year': np.arange(1960, 2014),
  'pexemp': [600,600,600,600,600,600,600,600,600,600,625,675,750,750,750,750,
             750,750,750, 1000,1000,1000,1000,1000,1000,1040,1080,1900,1950,
             2000,2050,2150,2300,2350,2450,2500,2550,2650,2700,2750,2800,2900,
             3000,3050,3100,3200,3300,3400,3500,3650,3750,3750,3750,3750]})

# gotta get 1999 thru 2009
pexemp = pexemp[pexemp.year.between(1998, 2010)]


ipum = pd.read_csv('~/MaxGhenis/datarepo/pppub19.csv.gz')
# set to lower case
ipum.columns = ipum.columns.str.lower()

# /* Set missing income items to zero so that non-filers etc will get zeroes.*/
# find out what statatax is and get it
VARS1 = ['eitcred', 'fedretir']
VARS2 = ['fedtax', 'statetax', 'adjginc', 'taxinc', 'fedtaxac', 'fica',
         'caploss', 'stataxac', 'incdivid', 'incint', 'incrent', 'incother',
         'incalim', 'incasist', 'incss', 'incwelfr', 'incwkcom', 'incvet',
         'incchild', 'incunemp', 'inceduc', 'gotveduc', 'gotvothe', 'gotvpens',
         'gotvsurv', 'incssi']
VARS3 = ['incwage', 'incbus', 'incfarm', 'incsurv', 'incdisab', 'incretir']
vars = VARS1 + VARS2 + VARS3


# these are the missing codes
MISSING_CODES = [9999, 99999, 999999, 9999999,
                 -9999, -99999, -999999, -9999999,
                 9997, 99997, 999997, 9999997]

for var in vars:
    ipum[var] = np.where(ipum[var].isna() or ipum[var].isin(MISSING_CODES), 0,
                         ipum[var])

# set 0's to NA for location
COLS_ZERO_TO_NA = ['momloc', 'poploc', 'sploc']
for col in COLS_ZERO_TO_NA:
    ipum[col] = np.where(ipum[col] == 0, np.nan, ipum[col])


# year before tax returns
ipum['x2'] = ipum.year - 1

# set x3 to  fips code
ipum['x3'] = ipum.statefip

# convert to soi - TODO
# source('FIPStoSOI.R')

# /* Marital status will be sum of spouse's x4 values */
ipum['x4'] = 1

# if age > 65, x6 is 1
ipum['x6'] = np.where(ipum.age > 65, 1, 0)

# primary wage or spouse wage
ipum['incwagebusfarm'] = ipum[['incwage', 'incbus', 'incfarm']].sum(axis=1)
ipum['x7'] = np.where(ipum.sex == 1, ipum.incwagebusfarm, 0)
ipum['x8'] = np.where(ipum.sex == 2, ipum.incwagebusfarm, 0)


ipum['x9'] = ipum.incdivid
ipum['x10'] = ipum[['incint', 'incrent', 'incother', 'incalim']].sum(axis=1)
ipum['x11'] = ipum.incretir
ipum['x12'] = ipum.incss

# /* Commented out got* items below because they are an error - 
# hope to fix soon. drf, 
# Nov18, 2015
# */
ipum['x13'] = ipum[['incwelfr', 'incwkcom', 'incvet', 'incsurv', 'incdisab',
                     'incchild', 'inceduc', 'incssi', 'incasist']].sum(axis=1)
  # /*gotveduc+gotvothe+gotvpens+gotvsurv+*/ 

ipum['x14'] = 0
ipum['x15'] = 0


# /* use Census imputation of itemized deductions where available.*/
# first have to join the exemption table
pexemp.rename(columns={'year': 'x2'}, inplace=True)
ipum = ipum.merge(pexemp, on='x2')

# adjusted gross - taxes + exemptions
ipum['x16'] = (ipum.adjginc - 
    ipum[['pexemp', 'proptax', 'statetax', 'taxinc']].sum(axis=1))
# no values less than 0
ipum['x16'] = np.where(ipum.x16 < 0, 0, ipum.x16)

ipum['x17'] = 0
ipum['x18'] = ipum.incunemp
ipum['x19'] = 0
ipum['x20'] = 0
ipum['x21'] = 0

# * Assume capgain and caploss are long term;
ipum['x22'] = np.where(ipum.capgain != -999, ipum.capgain - ipum.caploss, 0)
ipum.capgain = np.where(ipum.capgain == -999, 0)


# Here we output a record for each person, so that tax units can be formed 
# later by summing over person records. The taxunit id is the minimum of
# the pernum or sploc, so spouses will get the same id. For children
# it is the minimum of the momloc or poploc. Other relatives are made
# dependent on the household head (which may be incorrect) and non-relatives
# are separate tax units. 
# */

ipum['hnum'] = 0
ipum.hnum = np.where(ipum.relate==101, ipum.pernum, ipum.hnum)
ipum.hnum.replace(0, np.nan)

# if claiming > personal exemption than they're their own filer
ipum['sum'] = ipum[['x7', 'x8', 'x9', 'x10', 'x11', 'x12', 'x13',
                    'x22']].sum(axis=1)
ipum['notself'] = np.where(ipum.sum <= ipum.pexemp, 1, 0)


ipum['deprel'] = np.where((ipum.notself == 1) & (ipum.relate >= 303) & 
                          (ipum.relate <= 901), 1, 0)
ipum['depchild'] = np.where(
    (ipum.notself == 1) & 
    (ipum[['momloc', 'poploc']].sum(axis=1) > 0) &
    ((ipum.age < 18) | (ipum.age < 24 & ipum.schlcoll > 0)),
    1, 0)

# set dependents and taxpayers
dpndnts = ipum[(ipum.depchild == 1) | (ipum.deprel == 1)]
dpndnts['x1'] = np.where(dpndnts.depchild == 1,
    100 * dpndnts.serial + np.minimum(dpndnts.momloc, dpndnts.poploc), 0)
dpndnts.x1 = np.where(dpndnts.deprel == 1,
    100 * dpndnts.serial + dpndnts.hnum, dpndnts.x1)

dpndnts['x4'] = np.nan
dpndnts['x5'] = 1
dpndnts['x6'] = np.nan
dpndnts['x19'] = np.nan

txpyrs = ipum[(ipum.depchild == 0) & (ipum.deprel == 0)]
txpyrs.x1 = 100 * txpyrs.serial + np.minimum(txpyrs.pernum, txpyrs.sploc)
txpyrs.x5 = 0


# set whats not x1, x2, or x5 in deps to NA
vars = ['x' + str(i) for i in [3, 4] + range(6, 23)]
dpndnts[vars] = np.nan

# put them back together
ipum = pd.concat([txpyrs, dpndnts])


# sum value over tax #
ipum['n'] = 1
concat = ipum.group_by(['x2', 'x1'])[['n', 'deprel', 'depchild'] +
                                     ['x' + str(i) for i in range(5, 23)]].sum()
concat['x3'] = concat.x3 / concat.n
concat['x4'] = concat.deprel + concat.depchild

concat.x4 = np.where(~concat.x4.isna() & (concat.x4 == 1) & (concat.x5 > 0), 3,
                     concat.x4)

concat = concat[(concat.x19 > 0) & (concat.x4) > 0]

concat = concat[['x' + str(i) for i in range(1, 23)]]

concat.columns = ['id', 'year', 'state', 'mstat', 'depx', 'agex', 'pwages',
                  'swages', 'dividends', 'otherprop', 'pensions', 'gssi',
                  'transfers', 'rentpaid', 'proptax', 'otheritem', 'childcare',
                  'ui', 'depchild', 'mortgage', 'stcg', 'ltcg']