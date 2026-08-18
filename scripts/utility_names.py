"""Territory name -> tariff-book name. ENUMERATED, not fuzzy-matched at runtime.

The map console resolves a parcel's serving utility by point-in-polygon against
`in_territories`, which publishes names like "CITY OF AUBURN - (IN)" and "DUKE ENERGY INDIANA,
LLC". The tariff books are keyed by IURC names - "City of Auburn, Indiana (Utility Company)",
"Duke Energy Indiana Inc". Measured: of 145 territory names and 74 tariff names, **ZERO match
exactly**, so without this map the dossier can never price the utility it just named.

⛔ WHY THIS IS A LIST AND NOT A FUNCTION. The same rule that governs the EIA-861 benchmark applies
here, and for the same reason: *"Mapped EXPLICITLY rather than fuzzy-matched: a wrong benchmark
silently validates a wrong bill, which is worse than none."* A runtime normaliser would keep
matching new names nobody reviewed. This list was DERIVED by normalisation once, reviewed pair by
pair, and committed - so a wrong pair is visible in a diff rather than invented on load.

HOW IT WAS DERIVED, and what was checked
----------------------------------------
Uppercase, strip the publisher's suffixes ("- (IN)", "(Utility Company)", ", Indiana"), drop
corporate-form words (CO/INC/LLC/CORP) and the leading "City of"/"Town of", and normalise the
IURC's abbreviations (ELEC->ELECTRIC, PUB->PUBLIC, SERV->SERVICE, EMC/REC->REMC). Then keep only
the pairs whose normalised keys match **exactly one** candidate on each side.

  68 unambiguous pairs, **0 ambiguous** - including all five IOUs.
  +1 added by hand: "CRAWFORDSVILLE ELEC, LGT & PWR" -> "City of Crawfordsville, Indiana (Utility
    Company)". The territory publishes a trade name and the IURC a municipal one; no normalisation
    could bridge that, and inventing one that could would be exactly the fuzzy matching this file
    exists to avoid.

⚠ SIX tariff utilities are reached by no territory, and that is CORRECT for five of them:
  Hoosier Energy REC, Wabash Valley Power and Indiana Municipal Power Agency are WHOLESALE
  suppliers with no retail service territory; Indiana Michigan Power Co (Michigan) is out of
  state. Only "Town of Crane" is a genuine gap - a tiny municipal whose territory polygon we do
  not hold.

⚠ The reverse gap is larger and matters more: **77 of the 145 territories have no tariff book at
  all**, including out-of-state utilities that clip into Indiana (Consumers Energy, ComEd,
  Kentucky Utilities, Ohio Power). A parcel there must read "no tariff held", never a neighbour's.

RE-DERIVE: python scripts/build_utility_name_map.py
"""

# territory name (in_territories.utility) -> tariff name (in_utility_tariff_riders.utility)
TERRITORY_TO_TARIFF = {
    'CITY OF ANDERSON - (IN)':
        'City of Anderson, Indiana (Utility Company)',
    'CITY OF AUBURN - (IN)':
        'City of Auburn, Indiana (Utility Company)',
    'CITY OF BLUFFTON - (IN)':
        'City of Bluffton, Indiana (Utility Company)',
    'CITY OF COLUMBIA CITY - (IN)':
        'City of Columbia City, Indiana (Utility Company)',
    'CITY OF COVINGTON - (IN)':
        'City of Covington, Indiana (Utility Company)',
    'CITY OF FRANKFORT - (IN)':
        'City of Frankfort, Indiana (Utility Company)',
    'CITY OF GARRETT':
        'City of Garrett, Indiana (Utility Company)',
    'CITY OF GAS CITY - (IN)':
        'City of Gas City, Indiana (Utility Company)',
    'CITY OF GREENDALE':
        'City of Greendale, Indiana (Utility Company)',
    'CITY OF GREENFIELD - (IN)':
        'City of Greenfield, Indiana (Utility Company)',
    'CITY OF HAGERSTOWN - (IN)':
        'City of Hagerstown, Indiana (Utility Company)',
    'CITY OF HUNTINGBURG - (IN)':
        'City of Huntingburg, Indiana (Utility Company)',
    'CITY OF JASPER - (IN)':
        'City of Jasper, Indiana (Utility Company)',
    'CITY OF LEBANON - (IN)':
        'City of Lebanon, Indiana (Utility Company)',
    'CITY OF LEWISVILLE - (IN)':
        'City of Lewisville, Indiana (Utility Company)',
    'CITY OF LINTON - (IN)':
        'City of Linton, Indiana (Utility Company)',
    'CITY OF LOGANSPORT - (IN)':
        'City of Logansport, Indiana (Utility Company)',
    'CITY OF MISHAWAKA':
        'City of Mishawaka, Indiana (Utility Company)',
    'CITY OF PERU - (IN)':
        'City of Peru, Indiana (Utility Company)',
    'CITY OF RENSSELAER - (IN)':
        'City of Rensselaer, Indiana (Utility Company)',
    'CITY OF RICHMOND - (IN)':
        'City of Richmond, Indiana (Utility Company)',
    'CITY OF RISING SUN - (IN)':
        'City of Rising Sun, Indiana (Utility Company)',
    'CITY OF SCOTTSBURG - (IN)':
        'City of Scottsburg, Indiana (Utility Company)',
    'CITY OF TELL CITY - (IN)':
        'City of Tell City, Indiana (Utility Company)',
    'CITY OF THORNTOWN - (IN)':
        'City of Thorntown, Indiana (Utility Company)',
    'CITY OF TROY - (IN)':
        'City of Troy, Indiana (Utility Company)',
    'CITY OF WASHINGTON - (IN)':
        'City of Washington, Indiana (Utility Company)',
    'CITY OF WAYNETOWN - (IN)':
        'City of Waynetown, Indiana (Utility Company)',
    'CITY OF WILLIAMSPORT - (IN)':
        'City of Williamsport, Indiana (Utility Company)',
    'CRAWFORDSVILLE ELEC, LGT & PWR':
        'City of Crawfordsville, Indiana (Utility Company)',
    'DUKE ENERGY INDIANA, LLC':
        'Duke Energy Indiana Inc',
    'INDIANA MICHIGAN POWER CO':
        'Indiana Michigan Power Co (Indiana)',
    'INDIANAPOLIS POWER & LIGHT CO':
        'Indianapolis Power & Light Co',
    'NORTHERN INDIANA PUB SERV CO':
        'Northern Indiana Pub Serv Co',
    'PAULDING-PUTMAN ELEC COOP, INC':
        'Paulding-Putman Elec Coop, Inc (Indiana)',
    'SOUTH CENTRAL INDIANA REMC':
        'South Central Indiana REMC',
    'SOUTHEASTERN INDIANA R E M C':
        'Southeastern Indiana R E M C',
    'SOUTHERN INDIANA GAS & ELEC CO':
        'Southern Indiana Gas & Elec Co',
    'SOUTHERN INDIANA R E C, INC':
        'Southern Indiana R E C, Inc',
    'TOWN OF ARGOS':
        'Town of Argos, Indiana (Utility Company)',
    'TOWN OF AVILLA - (IN)':
        'Town of Avilla, Indiana (Utility Company)',
    'TOWN OF BAINBRIDGE - (IN)':
        'Town of Bainbridge, Indiana (Utility Company)',
    'TOWN OF BARGERSVILLE - (IN)':
        'Town of Bargersville, Indiana (Utility Company)',
    'TOWN OF BROOKLYN':
        'Town of Brooklyn, Indiana (Utility Company)',
    'TOWN OF BROOKSTON - (IN)':
        'Town of Brookston, Indiana (Utility Company)',
    'TOWN OF CENTERVILLE - (IN)':
        'Town of Centerville, Indiana (Utility Company)',
    'TOWN OF CHALMERS - (IN)':
        'Town of Chalmers, Indiana (Utility Company)',
    'TOWN OF COATESVILLE - (IN)':
        'Town of Coatesville, Indiana (Utility Company)',
    'TOWN OF ETNA GREEN':
        'Town of Etna Green, Indiana (Utility Company)',
    'TOWN OF FERDINAND - (IN)':
        'Town of Ferdinand, Indiana (Utility Company)',
    'TOWN OF FRANKTON - (IN)':
        'Town of Frankton, Indiana (Utility Company)',
    'TOWN OF JAMESTOWN - (IN)':
        'Town of Jamestown, Indiana (Utility Company)',
    'TOWN OF KINGSFORD HEIGHTS':
        'Town of Kingsford Heights, Indiana (Utility Company)',
    'TOWN OF KNIGHTSTOWN - (IN)':
        'Town of Knightstown, Indiana (Utility Company)',
    'TOWN OF LADOGA - (IN)':
        'Town of Ladoga, Indiana (Utility Company)',
    'TOWN OF MIDDLETOWN - (IN)':
        'Town of Middletown, Indiana (Utility Company)',
    'TOWN OF MONTEZUMA - (IN)':
        'Town of Montezuma, Indiana (Utility Company)',
    'TOWN OF NEW CARLISLE- (IN)':
        'Town of New Carlisle, Indiana (Utility Company)',
    'TOWN OF PAOLI':
        'Town of Paoli, Indiana (Utility Company)',
    'TOWN OF PENDLETON - (IN)':
        'Town of Pendleton, Indiana (Utility Company)',
    'TOWN OF PITTSBORO - (IN)':
        'Town of Pittsboro, Indiana (Utility Company)',
    'TOWN OF ROCKVILLE - (IN)':
        'Town of Rockville, Indiana (Utility Company)',
    'TOWN OF SOUTH WHITLEY - (IN)':
        'Town of South Whitley, Indiana (Utility Company)',
    'TOWN OF SPICELAND - (IN)':
        'Town of Spiceland, Indiana (Utility Company)',
    'TOWN OF STRAUGHN - (IN)':
        'Town of Straughn, Indiana (Utility Company)',
    'TOWN OF VEEDERSBURG - (IN)':
        'Town of Veedersburg, Indiana (Utility Company)',
    'TOWN OF WALKERTON - (IN)':
        'Town of Walkerton, Indiana (Utility Company)',
    'TOWN OF WARREN - (IN)':
        'Town of Warren, Indiana (Utility Company)',
    'TOWN OF WINAMAC - (IN)':
        'Town of Winamac, Indiana (Utility Company)',
}


def tariff_name(territory_utility):
    """The tariff-book name for a territory name, or None if we hold no book for it."""
    return TERRITORY_TO_TARIFF.get((territory_utility or "").strip())


assert tariff_name("DUKE ENERGY INDIANA, LLC") == "Duke Energy Indiana Inc"
assert tariff_name("CITY OF AUBURN - (IN)") == "City of Auburn, Indiana (Utility Company)"
assert tariff_name("CONSUMERS ENERGY CO") is None       # out of state, no Indiana book
assert tariff_name(None) is None
