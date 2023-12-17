import datetime
import io
import re
import pandas as pd
import xml.etree.ElementTree as ET

'''
    Prescriptions
'''
def read_prescription(file):
    '''
    Function: read_prescription
    Arguments:
    file: Path file
    File containing the prescription. Exported from ARIA in csv format
    
    Returns:
    prdf: Pandas DataFrame
    Dataframe with the prescription data
    '''
    prdf = pd.read_csv(file)
    return prdf

def parse_prescription(file):
    '''
    Function: parse_prescription
    Arguments:
    file: Path file
    File containing the prescription. Exported from ARIA in csv format

    Returns: a tuple comtaining three dataframes pvdf, ccdf, oardf
    pvdf: Pandas DataFrame
    Dataframe with the prescription volumes
    ccdf: Pandas DataFrame
    Dataframe with the covarage constraints
    oardf: Pandas DataFrame
    Dataframe with oars restriction
    '''

    # Regular expession dictionary to filter the prescription volumes (PrescribedTo field)
    pv_rx_dict = {
        'Volume': re.compile(r'Volume (?P<Volume>.+)  \d+\.\d+ Gy '),
        'Dose': re.compile(r'  (?P<Dose>\d+\.\d+) Gy'),
        'FxDose' : re.compile(r'  (?P<FxDose>\d+\.\d+) Gy/Frac'),
    }

    # Regular expession dictionary to filter the CovarageConstraints
    cc_rx_dict = {
        'Volume': re.compile(r'Volume / Structure :(?P<Volume>.*) Min Dose'),
        'Min': re.compile(r'Min Dose:(?P<Min>.*) Gy Max'),
        'Max': re.compile(r'Max Dose:(?P<Max>.*) Gy At'),
        'AtLeast': re.compile(r'At Least (?P<AtLeast>.*) % of (?P<Volume>.*) at (?P<Percentage>.*) % (?P<Dose>.*) Gy No More Than'),
        'NoMore': re.compile(r'No More Than (?P<NoMore>.*) % of (?P<Volume>.*) at (?P<Percentage>.*) % (?P<Dose>.*) Gy'),
    }

    # Regular expession dictionary to filter the OAR constraints
    oar_rx_dict = {
        'Organ': re.compile(r'Organ :(?P<Organ>.*) Mean'),
        'Dmean': re.compile(r'Mean :(?P<Dmean>.*) Max Dose'),
        'Dmax' : re.compile(r'Max Dose :(?P<Dmax>.*)$'),
    }
   
    # Define parsing functions
    def _parse_prescription_volume(line):
        """
        Do a regex search against all defined regexes and
        return a dictionary the key and match result
    
        """
    
        matches = {}
        for key, rx in pv_rx_dict.items():
            match = rx.search(line)
            if match:
                matches[key] = match.group(key)
            
        return matches

    def _parse_volume(line):
        """
        Do a regex search against all defined CovarageConstraints regexes and
        return a dictionary the key and match result
    
        """
    
        matches = {}
        for key, rx in cc_rx_dict.items():
            match = rx.search(line)
            if match:
                if key == 'Volume':
                    volume = match.group(key)
                    matches[key] = match.group(key)
                elif key == 'AtLeast' and match.group('Volume') == volume:
                    constraint = [match.group('AtLeast'), match.group('Percentage'), match.group('Dose')]
                    matches[key] = constraint
                elif key == 'NoMore' and match.group('Volume') == volume:
                    constraint = [match.group('NoMore'), match.group('Percentage'), match.group('Dose')]
                    matches[key] = constraint
                else:
                    matches[key] = match.group(key)
            
        return matches
    
    def _parse_line(line):
        """
        Do a regex search against all defined OAR regexes and
        return the key and match result of the first matching regex
    
        """
    
        for key, rx in oar_rx_dict.items():
            match = rx.search(line)
            if match:
                return key, match
        # if there are no matches
        return None, None
        
    def _parse_organ(line):
        """
        Do a regex search against all defined OAR regexes and
        return a dictionary the key and match result
    
        """
    
        matches = {}
        for key, rx in oar_rx_dict.items():
            match = rx.search(line)
            if match:
                matches[key] = match.group(key)
            
        return matches

    # Read the prescription file
    prdf = read_prescription(file)

    # Split the fields with the prescription volumes, covarage constraints and the organ at risk
    pv_lines = prdf.PrescribedTo.values[0].split('|')
    cc_lines = prdf.CoverageConstraints.values[0].split('|')
    oar_lines = prdf.OrgansAtRisk.values[0].split('\n')
    
    # Parse the prescription volume lines and create the pvdf dataframe
    pvdf = pd.DataFrame([_parse_prescription_volume(pv_line) for pv_line in pv_lines])
    
    # Parse the covarage constraint lines and create the ccdf dataframe
    ccdf = pd.DataFrame([_parse_volume(cc_line) for cc_line in cc_lines])

    # Parse the oar lines and create a list, each element with the lines corresponding a specific oar 
    oars, oar = [], None
    for oar_line in oar_lines:
        oar_key, oar_name = _parse_line(oar_line)
        if oar_key:
            oars.append(oar)
            oar = [oar_line]
        else:
            oar.append(oar_line)
    oars.append(oar)
    oars.pop(0)
    oars
    # Parse each organ and create a list of dcitionaries with Dmin, Dmax and Dosimetric Parameters
    oars_list = []
    for oar in oars:
        oar_dict = _parse_organ(oar[0])
        oar_dict['DosimPars'] = oar[2:]
        oars_list.append(oar_dict)

    # Create the oardf dataframe
    oardf = pd.DataFrame(oars_list)

    return pvdf, ccdf, oardf

def getTreatmentDosePrescription(pvdf):
    '''
    Function: Retrieve the treatment dose prescription. 

    Arguments:
    pvdf: Pandas DataFrame
        Dataframe with the prescription volumes

    Returns:
    TreatmentDosePrescription: Float
        The PTV prescription with the highest dose 
    '''
    TreatmentDosePrescription = pvdf.Dose.astype('float').max()
    return TreatmentDosePrescription
    
'''
    Clinical protocols
'''
def parseProt(protin = 'BareBone.xml'):
    '''
    Function: Parse a clinical protocol

    Arguments:
    protin: String
        File name of the clinical protocal (XML formt)

    Returns:
    An ElementTree instance
    '''
    # Leer el protocolo clínico de entrada
    bbx = ET.parse(protin)
    return bbx

def modPreview(bbx, ID, ApprovalStatus='Unapproved', TreatmentSite='', AssignedUsers='salud\\50724293r'):
    '''
    Function: Modify the Preview section of a clinical protocol

    Arguments:
    bbx: An element tree instance
        The xml document to be modified
    ID: String
        The identification of the clinical protocol
    ApprovalStatus: String ('Unapproved' [Default], 'Approved', 'Reviewed', 'Retired')
        Clinical protocol approval status
    TreatmentSite:  String
        Clinical protocol treatment site
    AssignedUsers: String
        Aria User(s) writing the clinical protocol. It defaults to 'salud\50724293r'
    '''
    Preview = bbx.find('Preview')
    Preview.set('ID', ID)
    Preview.set('ApprovalStatus', ApprovalStatus)
    Preview.set('TreatmentSite', TreatmentSite)
    Preview.set('AssignedUsers', AssignedUsers)
    creationdatetime = datetime.datetime.strftime(datetime.datetime.now(), ' %B %d %Y %H:%M:%S:%f')[:-3]
    Preview.set('LastModified', creationdatetime)
    ApprovalHistory = AssignedUsers + ' Created [' + creationdatetime + ' ]'
    Preview.set('ApprovalHistory', ApprovalHistory)

def addStructure(bbx, structureName, stColourAndStyle='Countour - Brown', searchCT=1000, vDVHLineColor=-16777216):
    '''
    Function: Add a new structure to the Structures section of a clinical protocol

    Arguments:
    bbx: An element tree instance
        The xml document to be modified
    structureName: String
        The name of the structure to be added
    stColourAndStyle: String
        A string specifying the color and style of the structure. It defaults to 'Countour - Brown'
    searchCT: Int 
        An integer to set the SearchCTLow and SearchCTHigh fields
    vDVHLineColor:  Int
        A signed integer coding the DVH line color of the structure
    '''
    StructureTemplate = bbx.find('StructureTemplate')
    Structures = StructureTemplate.find('Structures')
    Structure = ET.SubElement(Structures, 'Structure')
    Structure.set('ID', structureName)
    Structure.set('Name', structureName)
    Identification = ET.SubElement(Structure, 'Identification')
    VolumeID = ET.SubElement(Identification, 'VolumeID')
    VolumeCode = ET.SubElement(Identification, 'VolumeCode')
    VolumeType = ET.SubElement(Identification, 'VolumeType')
    VolumeType.text = 'Organ'
    VolumeCodeTable = ET.SubElement(Identification, 'VolumeCodeTable')
    StructureCode = ET.SubElement(Identification, 'StructureCode')
    TypeIndex = ET.SubElement(Structure, 'TypeIndex')
    TypeIndex.text = str(2)
    ColorAndStyle = ET.SubElement(Structure, 'ColorAndStyle')
    ColorAndStyle.text = stColourAndStyle
    SearchCTLow = ET.SubElement(Structure, 'SearchCTLow')
    SearchCTLow.text = str(searchCT)
    SearchCTHigh = ET.SubElement(Structure, 'SearchCTHigh')
    SearchCTHigh.text = str(searchCT)
    DVHLineStyle = ET.SubElement(Structure, 'DVHLineStyle')
    DVHLineStyle.text = str(0)
    DVHLineColor = ET.SubElement(Structure, 'DVHLineColor')
    DVHLineColor.text = str(vDVHLineColor)
    DVHLineWidth = ET.SubElement(Structure, 'DVHLineWidth')
    DVHLineWidth.text = str(1)
    EUDAlpha = ET.SubElement(Structure, 'EUDAlpha')
    EUDAlpha.set('xsi:nil', 'true')
    TCPAlpha = ET.SubElement(Structure, 'TCPAlpha')
    TCPAlpha.set('xsi:nil', 'true')
    TCPBeta = ET.SubElement(Structure, 'TCPBeta')
    TCPBeta.set('xsi:nil', 'true')
    TCPGamma = ET.SubElement(Structure, 'TCPGamma')
    TCPGamma.set('xsi:nil', 'true')

def modPhase(bbx, ID, vFractionCount):
    '''
    Function: modify the Phase section

    Arguments:
    bbx: An element tree instance
    ID: String
        The Phase identification
    vFractionCount: Int
        The treatment fraction count
    '''
    Phases = bbx.find('Phases')
    Phase = Phases.find('Phase')
    Phase.set('ID', ID)
    FractionCount = Phase.find('FractionCount')
    FractionCount.text = str(vFractionCount)

def addPlanObjetive(bbx, ID, vParameter, vDose, vTotalDose, vPrimary='false', vModifier=1):
    '''
    Function: Add a Plan Objetive
    
    Arguments:
    bbx: An element tree instance
        The xml document to be modified
    ID: String
        Structure name which the plan objetive applies to
    VModifier: Int
        An index specifying the comparison operator to be used in Plan Objetive evaluation
             0: At Least (% receives more than)
             1: At Most (% receives more than). Default
             2: Minimum dose (is)
             3: Maximum dose (is)
             4: Mean dose (is)
             5: Reference point (receives)
             6: EUD (receives)
             7: Mean dose (is more than)
             8: Mean dose (is less than)
             9: Minimum dose (is more than)
            10: Maximum dose (is less than)
    vParameter: Float
        Volume percentage. Meaningless if vModifier is >= 2
    vDose: Float
        Fraction dose in Gy
    vTotalDose: Float
        Total dose in Gy
    '''
    Phases = bbx.find('Phases')
    Phase = Phases.find('Phase')
    Prescription = Phase.find('Prescription')
    Item = ET.SubElement(Prescription, 'Item')
    Item.set('ID', ID)
    Item.set('Primary', vPrimary)
    Type = ET.SubElement(Item, 'Type')
    Type.text = str(0) # hardcoded. It seems always default to zero
    Modifier = ET.SubElement(Item, 'Modifier')
    Modifier.text = str(vModifier)
    Parameter = ET.SubElement(Item, 'Parameter')
    Parameter.text = str(vParameter)
    Dose = ET.SubElement(Item, 'Dose')
    Dose.text = str(vDose)
    TotalDose = ET.SubElement(Item, 'TotalDose')
    TotalDose.text = str(vTotalDose)

def addQualityIndex(bbx, ID, vType, vModifier, vValue, vTypeSpecifier, vReportDQPValueInAbsoluteUnits):
    '''
    Function: Add a Quality Index
    
    Arguments:
    bbx: An element tree instance
        The xml document to be modified
    ID: String
        Structure name which the quality index applies to
    vType: Int
        An index specifying the Quality Index Type
            0: ConformityIndex
            1: GradientMeasure [cm]
            2: Vxx [%/cc of volume] where xx, dose percentage, is specified by vTypeSpecifier and the %/cc of volume by vValue
            3: Vxx Gy [%/cc of volume] where xx, absolute dose in Gy, is specified by vTypeSpecifier and the %/cc of volume by vValue
            4: Dxx [%/Gy] where xx, volume percentage, is specified by vTypeSpecifier and the %/Gy of volume by vValue
            5: Dxx cc [%/Gy] where xx, absolute volume in cc, is specified by vTypeSpecifier and the %/Gy of volume by vValue
    VModifier: Int
        An index specifying the comparison operator to be used in quality index evaluation
            0: is more than
            1: is less than
            2: is
    vValue: Float
        The constrain in %, Gy o cc
    vTypeSpecifier: Float
        The dose or volume in Vdose or Dvolume in %, Gy or cc
    vReportDQPValueInAbsoluteUnits: string {'true', 'false'}
        If the constrain is specified in absolute units
    '''
    Phases = bbx.find('Phases')
    Phase = Phases.find('Phase')
    Prescription = Phase.find('Prescription')
    MeasureItem = ET.SubElement(Prescription, 'MeasureItem')
    MeasureItem.set('ID', ID)
    Type = ET.SubElement(MeasureItem, 'Type')
    Type.text = str(vType)
    Modifier = ET.SubElement(MeasureItem, 'Modifier')
    Modifier.text = str(vModifier)
    Value = ET.SubElement(MeasureItem, 'Value')
    Value.text = str(vValue)
    TypeSpecifier = ET.SubElement(MeasureItem, 'TypeSpecifier')
    TypeSpecifier.text = str(vTypeSpecifier)
    ReportDQPValueInAbsoluteUnits = ET.SubElement(MeasureItem, 'ReportDQPValueInAbsoluteUnits')
    ReportDQPValueInAbsoluteUnits.text = vReportDQPValueInAbsoluteUnits

def writeProt(bbx, protout = 'TestSalida.xml'):
    '''
    Function: write a clinical protocol

    Arguments:
    bbx: An element tree instance
        The xml document to be written
    protout: String
        File name of the clinical protocal (XML formt) to be written
    '''
    ET.indent(bbx)
    bbx.write(protout, encoding='utf-8', xml_declaration=True)