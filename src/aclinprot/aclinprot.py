import datetime
import io
import os
import re
import pandas as pd
import xml.etree.ElementTree as ET
import pydicom as dcm
from textdistance import ratcliff_obershelp
from numpy import isnan

def parseDose(strDose):
    '''
    Function: parseDose
        Parse the string specifying a dose and retrieve its numerical value in n Gy

    Arguments:
        srtDose: String
            The string specifying the dose in Gy

    Returns:
        Dose: Float
            The dose numerical value
    '''
    dose_rx_dict = {
        'Dose' : re.compile(r'(?P<Dose>(\d+)?\.?(\d+)?) Gy')
    }

    for key, rx in dose_rx_dict.items():
        match = rx.search(strDose)

    Dose = float(match.group('Dose'))
    return Dose

def parseDosimPar(strDosimPar):
    '''
    Function: parseDosimPar
        Parse the string specifying a a dosimetric parameter 

    Arguments:
        srtDosimPar: String
            The string specifying the dosimetric parameter

    Returns:
    '''
    dosimPar_rx_dict = {
        'Vxx%': re.compile(r'V(\s+)?(?P<Dose>\d+\.?(\d+)?)\s*?(Gy)?\$(?P<VolumeRelative>\d+\.?(\d+)?)(\s+)?(\%)?$'),
        'Vxxcc': re.compile(r'V(\s+)?(?P<Dose>\d+\.?(\d+)?)\s*?(Gy)?\$(?P<VolumeAbsolute>\d+\.?(\d+)?)(\s+)?cc$'),
        'Dxxcc': re.compile(r'D(\s+)?(?P<Volume>\d+\.?(\d+)?)cc\$(?P<DoseRelative>\d+\.?(\d+)?)(\s+)?\%?'),
        'Dxx%': re.compile(r'D(\s+)?(?P<VolumeRelative>\d+\.?(\d+)?)\%\$(?P<DoseRelative>\d+\.?(\d+)?)(\s+)?\%?'),
        'Dxx_Gy': re.compile(r'D(\s+)?(?P<Volume>\d+\.?(\d+)?)\$(?P<DoseGy>\d+\.?(\d+)?)(\s+)?(Gy)?'),
        'Dxxcc_Gy': re.compile(r'D(\s+)?(?P<Volume>\d+\.?(\d+)?).*?cc\$(?P<DoseGy>\d+\.?(\d+)?)(\s+)?(Gy)?'),
        'Dxx%_Gy': re.compile(r'D(\s+)?(?P<VolumeRelative>\d+\.?(\d+)?)\%\$(?P<DoseGy>\d+\.?(\d+)?)(\s+)?(Gy)?'),
    }

    matches = {}
    for key, rx in dosimPar_rx_dict.items():
        match = rx.search(strDosimPar)
        if match:
            if key == 'Vxx%':
                VolumeRelative = float(match.group('VolumeRelative'))
                Dose = float(match.group('Dose'))
                matches[key] = {'VolumeRelative': VolumeRelative, 'DoseGy': Dose}
            if key == 'Vxxcc':
                VolumeAbsolute = float(match.group('VolumeAbsolute'))
                Dose = float(match.group('Dose'))
                matches[key] = {'VolumeAbsolute': VolumeAbsolute, 'DoseGy': Dose}
            if key == 'Dxxcc':
                Volume = float(match.group('Volume'))
                Dose = float(match.group('DoseRelative'))
                matches[key] = {'VolumeAbsolute': Volume, 'DoseRelative': Dose}
            if key == 'Dxx%':
                Volume = float(match.group('VolumeRelative'))
                Dose = float(match.group('DoseRelative'))
                matches[key] = {'VolumeRelative': Volume, 'DoseRelative': Dose}
            if key == 'Dxx_Gy':
                Volume = float(match.group('Volume'))
                Dose = float(match.group('DoseGy'))
                matches[key] = {'VolumeAbsolute': Volume, 'DoseGy': Dose}
            if key == 'Dxxcc_Gy':
                Volume = float(match.group('Volume'))
                Dose = float(match.group('DoseGy'))
                matches[key] = {'VolumeAbsolute': Volume, 'DoseGy': Dose}
            if key == 'Dxx%_Gy':
                Volume = float(match.group('VolumeRelative'))
                Dose = float(match.group('DoseGy'))
                matches[key] = {'VolumeRelative': Volume, 'DoseGy': Dose}
        
    return matches        


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
                matches[key] = match.group(key).strip()
            
        return matches

    # Read the prescription file
    prdf = read_prescription(file)

    # Split the fields with the prescription volumes, covarage constraints and the organ at risk
    pv_lines = prdf.PrescribedTo.values[0].split('|')
    cc_lines = prdf.CoverageConstraints.values[0].split('|')
    if isinstance(prdf.OrgansAtRisk.values[0], str):
        oar_lines = prdf.OrgansAtRisk.values[0].split('\n')
    else:
        oar_lines = []
    
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
            oar.append(oar_line.strip())
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
def parseProt(protin = 'ClinicalProtocol.xml'):
    '''
    Function: Parse a clinical protocol

    Arguments:
    protin: String
        File name of the clinical protocal (XML formt)

    Returns:
    An ElementTree instance
    '''
    # Leer el protocolo clínico de entrada
    cpet = ET.parse(protin)
    return cpet

def modPreview(cpet, ID, ApprovalStatus='Unapproved', TreatmentSite='', AssignedUsers=r'salud\50724293R'):
    '''
    Function: Modify the Preview section of a clinical protocol

    Arguments:
    cpet: An element tree instance
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
    Preview = cpet.find('Preview')
    Preview.set('ID', ID)
    Preview.set('ApprovalStatus', ApprovalStatus)
    Preview.set('TreatmentSite', TreatmentSite)
    Preview.set('AssignedUsers', AssignedUsers)
    creationdatetime = datetime.datetime.strftime(datetime.datetime.now(), ' %B %d %Y %H:%M:%S:%f')[:-3]
    Preview.set('LastModified', creationdatetime)
    ApprovalHistory = AssignedUsers + ' Created [' + creationdatetime + ' ]'
    Preview.set('ApprovalHistory', ApprovalHistory)

def addStructure(cpet, structureName, stColourAndStyle='Countour - Brown', searchCT=1000, vDVHLineColor=-16777216):
    '''
    Function: Add a new structure to the Structures section of a clinical protocol

    Arguments:
    cpet: An element tree instance
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
    StructureTemplate = cpet.find('StructureTemplate')
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

def modPhase(cpet, ID, vFractionCount):
    '''
    Function: modify the Phase section

    Arguments:
    cpet: An element tree instance
    ID: String
        The Phase identification
    vFractionCount: Int
        The treatment fraction count
    '''
    Phases = cpet.find('Phases')
    Phase = Phases.find('Phase')
    Phase.set('ID', ID)
    FractionCount = Phase.find('FractionCount')
    FractionCount.text = str(vFractionCount)

def addPlanObjetive(cpet, ID, vParameter, vDose, vTotalDose, vPrimary='false', vModifier=1):
    '''
    Function: Add a Plan Objetive
    
    Arguments:
    cpet: An element tree instance
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
    Phases = cpet.find('Phases')
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
    Parameter.text = f'{float(vParameter):g}'
    Dose = ET.SubElement(Item, 'Dose')
    Dose.text = f'{float(vDose):g}'
    TotalDose = ET.SubElement(Item, 'TotalDose')
    TotalDose.text = f'{float(vTotalDose):g}'

def addQualityIndex(cpet, ID, vType, vModifier, vValue, vTypeSpecifier, vReportDQPValueInAbsoluteUnits):
    '''
    Function: Add a Quality Index
    
    Arguments:
    cpet: An element tree instance
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
    Phases = cpet.find('Phases')
    Phase = Phases.find('Phase')
    Prescription = Phase.find('Prescription')
    MeasureItem = ET.SubElement(Prescription, 'MeasureItem')
    MeasureItem.set('ID', ID)
    Type = ET.SubElement(MeasureItem, 'Type')
    Type.text = str(vType)
    Modifier = ET.SubElement(MeasureItem, 'Modifier')
    Modifier.text = str(vModifier)
    Value = ET.SubElement(MeasureItem, 'Value')
    Value.text = f'{float(vValue):g}' 
    TypeSpecifier = ET.SubElement(MeasureItem, 'TypeSpecifier')
    TypeSpecifier.text = f'{float(vTypeSpecifier):g}' 
    ReportDQPValueInAbsoluteUnits = ET.SubElement(MeasureItem, 'ReportDQPValueInAbsoluteUnits')
    ReportDQPValueInAbsoluteUnits.text = vReportDQPValueInAbsoluteUnits

def writeProt(cpet, protout):
    '''
    Function: write a clinical protocol

    Arguments:
    cpet: An element tree instance
        The xml document to be written
    protout: String
        File name of the clinical protocal (XML formt) to be written
    '''
    ET.indent(cpet)
    cpet.write(protout, encoding='utf-8', xml_declaration=True)

def indentProt(prot):
    '''
    Function: indent a clinical protocol xml file
    Overwrite the xml file indenting its elements

    Arguments:
    prot: String
        File name of the clinical protocal (XML formt)
    '''
    # Leer el protocolo clínico de entrada
    cpet = ET.parse(prot)
    writeProt(cpet, prot)

def convertPrescriptionIntoClinicalProtocol(prescription, ProtocolID, TreatmentSite, PlanID, ProtTemplate='BareBone.xml', ProtOut='ClinicalProtocol.xml'):
    '''
    Function: Convert a prescription into a clinical protocol

    Arguments:
    prescription: String
        Prescription file name
    ProtocolID: String
        The identification of the clinical protocol in ARIA
    TreatmetSite: String
        The treatment anatomial region
    PlanID: String
        The plan identification
    ProtTemplate: String
        The xml document used as a clinical protocol template
    ProtOut: String
        Name of the xml file describing the clinical protocol
        
    '''
    # Read the prescriptiop
    pvdf, ccdf, oardf = parse_prescription(prescription)
    # Read protocol template
    cpet = parseProt(os.path.dirname(__file__) + '/' + ProtTemplate)
    # Preview
    modPreview(cpet, ID=ProtocolID, TreatmentSite=TreatmentSite)
    # Phases
    FractionCount = int(float(pvdf.Dose[0])/float(pvdf.FxDose[0]))
    modPhase(cpet, ID=PlanID, vFractionCount=FractionCount)
    # Structutures
    for pv in pvdf.itertuples():
        addStructure(cpet, structureName=pv.Volume)
    for oar in oardf.itertuples():
        addStructure(cpet, structureName=oar.Organ)
    
    # Plan objetives
    for pv in pvdf.itertuples():
        ccVolumedf = ccdf[ccdf.Volume == pv.Volume]
        if ccVolumedf.AtLeast.values[0] and isinstance(ccVolumedf.AtLeast.values[0], list):
            atLeastlst = ccVolumedf.AtLeast.values[0]
            VolumePercentage =  atLeastlst[0]
            DosePercentage = float(atLeastlst[1])/100
            FxDoseGy = float(pv.FxDose) * DosePercentage
            DoseGy = float(pv.Dose) * DosePercentage
            addPlanObjetive(cpet, ID=pv.Volume, vParameter=VolumePercentage,
                                vDose=FxDoseGy, vTotalDose=DoseGy, vModifier=0)
        if ccVolumedf.NoMore.values[0] and isinstance(ccVolumedf.NoMore.values[0], list):
            noMorelst = ccVolumedf.NoMore.values[0]
            VolumePercentage =  noMorelst[0]
            DosePercentage = float(noMorelst[1])/100
            FxDoseGy = float(pv.FxDose) * DosePercentage
            DoseGy = float(pv.Dose) * DosePercentage
            addPlanObjetive(cpet, ID=pv.Volume, vParameter=VolumePercentage,
                                vDose=FxDoseGy, vTotalDose=DoseGy)
    for oar in oardf.itertuples():
        if oar.Dmean:
            ID = oar.Organ
            Parameter = 0
            Fxs = float(pvdf.Dose.values[0]) / float(pvdf.FxDose.values[0])
            TotalDose = parseDose(oar.Dmean)
            Dose = f'{TotalDose / Fxs:g}'
            addPlanObjetive(cpet, ID=ID, vParameter=Parameter, vDose=Dose, vTotalDose=TotalDose,
                                vModifier=8)
        if oar.Dmax:
            ID = oar.Organ
            Parameter = 0
            Fxs = float(pvdf.Dose.values[0]) / float(pvdf.FxDose.values[0])
            TotalDose = parseDose(oar.Dmax)
            Dose = f'{TotalDose / Fxs:g}'
            addPlanObjetive(cpet, ID=ID, vParameter=Parameter, vDose=Dose, vTotalDose=TotalDose,
                                vModifier=10)
        if oar.DosimPars:
            ID = oar.Organ
            for DosimPar in oar.DosimPars:
                constraint_dict = parseDosimPar(DosimPar)
                for key, constraint in constraint_dict.items():
                    if key == 'Vxx%':
                        VolumePercentage = constraint['VolumeRelative']
                        Fxs = float(pvdf.Dose.values[0]) / float(pvdf.FxDose.values[0])
                        TotalDose = constraint['DoseGy']
                        Dose = f'{TotalDose / Fxs:g}'
                        addPlanObjetive(cpet, ID=ID, vParameter=VolumePercentage, vDose=Dose, vTotalDose=TotalDose,
                                            vModifier=1)
                        
    # Quality Indexes
    for pv in pvdf.itertuples():
        ccVolumedf = ccdf[ccdf.Volume == pv.Volume]
        if ccVolumedf.AtLeast.values[0] and isinstance(ccVolumedf.AtLeast.values[0], list):
            TreatmentDosePrescription = getTreatmentDosePrescription(pvdf)
            atLeastlst = ccVolumedf.AtLeast.values[0]
            VolumePercentage =  atLeastlst[0]
            DosePercentage = float(atLeastlst[1])/100
            structureAbsoluteDose = float(pv.Dose) * DosePercentage
            StructureRelativeDose = structureAbsoluteDose / TreatmentDosePrescription * 100
            addQualityIndex(cpet, ID=pv.Volume, vType=3, vModifier=0, 
                                vValue=VolumePercentage, vTypeSpecifier=structureAbsoluteDose, 
                                vReportDQPValueInAbsoluteUnits='false')
        if ccVolumedf.NoMore.values[0] and isinstance(ccVolumedf.NoMore.values[0], list):
            TreatmentDosePrescription = getTreatmentDosePrescription(pvdf)
            noMorelst = ccVolumedf.NoMore.values[0]
            VolumePercentage = noMorelst[0]
            DosePercentage = float(noMorelst[1])/100
            structureAbsoluteDose = float(pv.Dose) * DosePercentage
            StructureRelativeDose = structureAbsoluteDose / TreatmentDosePrescription * 100
            addQualityIndex(cpet, ID=pv.Volume, vType=3, vModifier=1, 
                                vValue=VolumePercentage, vTypeSpecifier=structureAbsoluteDose, 
                                vReportDQPValueInAbsoluteUnits='false')
    
    for oar in oardf.itertuples():
        if oar.DosimPars:
            ID = oar.Organ
            for DosimPar in oar.DosimPars:
                constraint_dict = parseDosimPar(DosimPar)
                for key, constraint in constraint_dict.items():
                    if key == 'Vxx%':
                        VolumePercentage = constraint['VolumeRelative']
                        PrescriptionDoseGy = pvdf.Dose.astype('float').max()
                        ConstraintDoseGy = constraint['DoseGy']
                        StructureRelativeDose = f'{ConstraintDoseGy / PrescriptionDoseGy * 100:g}'
                        addQualityIndex(cpet, ID=ID, vType=3, vModifier=1, 
                                            vValue=VolumePercentage, vTypeSpecifier=ConstraintDoseGy, 
                                            vReportDQPValueInAbsoluteUnits='false')
                    if key == 'Vxxcc':
                        VolumeAbsolute = constraint['VolumeAbsolute']*1000
                        PrescriptionDoseGy = pvdf.Dose.astype('float').max()
                        ConstraintDoseGy = constraint['DoseGy']
                        StructureRelativeDose = f'{ConstraintDoseGy / PrescriptionDoseGy * 100:g}'
                        addQualityIndex(cpet, ID=ID, vType=3, vModifier=1, 
                                            vValue=VolumeAbsolute, vTypeSpecifier=ConstraintDoseGy, 
                                            vReportDQPValueInAbsoluteUnits='true')
                    if key == 'Dxx_Gy':
                        VolumeAbsolute = constraint['VolumeAbsolute']
                        print(VolumeAbsolute)
                        StructureAbsoluteDose = constraint['DoseGy']
                        addQualityIndex(cpet, ID=ID, vType=5, vModifier=1, 
                                            vValue=StructureAbsoluteDose, vTypeSpecifier=VolumeAbsolute, 
                                            vReportDQPValueInAbsoluteUnits='true')
                    if key == 'Dxxcc_Gy':
                        VolumeAbsolute = constraint['VolumeAbsolute']
                        StructureAbsoluteDose = constraint['DoseGy']
                        addQualityIndex(cpet, ID=ID, vType=5, vModifier=1, 
                                            vValue=StructureAbsoluteDose, vTypeSpecifier=VolumeAbsolute, 
                                            vReportDQPValueInAbsoluteUnits='true')
    
                    if key == 'Dxx%_Gy':
                        VolumePercentage = constraint['VolumeRelative']
                        StructureAbsoluteDose = constraint['DoseGy']
                        addQualityIndex(cpet, ID=ID, vType=4, vModifier=1, 
                                            vValue=StructureAbsoluteDose, vTypeSpecifier=VolumePercentage, 
                                            vReportDQPValueInAbsoluteUnits='true')

    # Write clincial protocol
    clinprotpath = '../protocolos/clinicos/'
    if os.path.exists(clinprotpath):
        writeProt(cpet, clinprotpath + ProtOut)
        print('Creado protocolo ' + clinprotpath + ProtOut)
    else:
        writeProt(cpet, ProtOut)


def structureElementByID(cpet, ID):
    '''
    Function: Retrieve the structure element with the specified ID in the clinical protocol element tree

    Arguments:
    cpet: Element Tree
        Clinical protocol element tree

    ID: String
        Structure element ID
        
    Returns:
    structureElement: Elment
        Structure Element in the clinical protocol element tree
    '''
    for structureElement in cpet.find('StructureTemplate').find('Structures').findall('Structure'):
        if structureElement.get('ID') == ID:
            return structureElement
    return None

def prescriptionItemsByID(cpet, ID):
    '''
    Function: Retrieve the prescription elements with the specified ID in the clinical protocol element tree

    Arguments:
    cpet: Element Tree
        Clinical protocol element tree

    ID: String
        Structure element ID
        
    Returns:
    prescriptionItems: List
        Prescription Item Element List in the clinical protocol element tree
    '''
    prescriptionItems = []
    for prescriptionItem in cpet.find('Phases').find('Phase').find('Prescription').findall('Item'):
        if prescriptionItem.get('ID') == ID:
            prescriptionItems.append(prescriptionItem)
    return prescriptionItems

def measureItemsByID(cpet, ID):
    '''
    Function: Retrieve the MeasureItem elements with the specified ID in the clinical protocol element tree

    Arguments:
    cpet: Element Tree
        Clinical protocol element tree

    ID: String
        Structure element ID
        
    Returns:
    measureItems: List
        Measure Item Element List in the clinical protocol element tree
    '''
    measureItems = []
    for measureItem in cpet.find('Phases').find('Phase').find('Prescription').findall('MeasureItem'):
        if measureItem.get('ID') == ID:
            measureItems.append(measureItem)
    return measureItems

def amendClinicalProtocol(amendedcpet, modelcpet, ID):
    '''
    Function: Amend a clinical protocolo element tree using the element tree of other clinical protocol as a model

    Arguments:
    amendedcpet: Element Tree
        Clinical protocol element tree to be amended

    modelcpet: Element Tree
        Clinical protocol element tree to be used as a model

    ID: String
        Structure element ID
        
    Returns:
    amendedcpet: Element Tree
        Amended clinical protocol element tree
    '''
    # Structures
    structureElement = structureElementByID(cpet=modelcpet, ID=ID)
    amendedcpet.find('StructureTemplate').find('Structures').append(structureElement)
    # Prescriptions
    prescriptionItems = prescriptionItemsByID(cpet=modelcpet, ID=ID)
    for prescriptionItem in prescriptionItems:
        indexInsertedItem = len([element for element in amendedcpet.find('Phases').find('Phase').find('Prescription').iter(tag='Item')])
        amendedcpet.find('Phases').find('Phase').find('Prescription').insert(indexInsertedItem, prescriptionItem)
    # MeasureItems
    measureItems = measureItemsByID(cpet=modelcpet, ID=ID)
    for measureItem in measureItems:
        amendedcpet.find('Phases').find('Phase').find('Prescription').append(measureItem)    
     
    return amendedcpet

'''
    Validation
'''

def coverageConstraintCounting(prescriptionFile, prescriptionIndex=0):
    '''
    Function: covareageConstraintCounting
    Arguments:
    prescriptionFile: Path file
    File containing the prescription. Exported from ARIA in csv format
    
    prescriptionIndex: Integer
    Index of the prescription to be considered. Defaut: 0, the first prescription in the file
    
    Returns:
    coverageConstraintCount: Integer
    Number of coverage constraints in the prescription
    '''
    prdf = read_prescription(prescriptionFile)
    pres = prdf.iloc[prescriptionIndex]
    coverageConstraints = pres.CoverageConstraints.split('|')
    
    targetVolume_rx_dict = {
    #    'targetVolume': re.compile(r'Volume / Structure :(?P<targetVolume>.*?) M'),
        'Dmean': re.compile(r'Mean :(?P<Dmean>.*?) c?Gy'),
        'Dmax': re.compile(r'Max Dose:(?P<Dmax>.*?) c?Gy'),
        'Dmin': re.compile(r'Min Dose:(?P<Dmin>.*?) c?Gy'),
        'atLeast': re.compile(r'At Least(?P<atLeast>.*?) No More Than'),
        'noMoreThan': re.compile(r'No More Than(?P<noMoreThan>.*?)$'),
    }
    
    coverageConstraintList = []
    for coverageConstraint in coverageConstraints:
        for key, rx in targetVolume_rx_dict.items():
            match = rx.search(coverageConstraint)
            if match:
                if match.group(key).strip():
                    coverageConstraintList.append(match.group(key))
    
    coverageConstraintCount = len(coverageConstraintList)
    return coverageConstraintCount

def OARConstraintCounting(prescriptionFile, prescriptionIndex=0):
    '''
    Function: OARConstraintCounting
    Arguments:
    prescriptionFile: Path file
    File containing the prescription. Exported from ARIA in csv format
    
    prescriptionIndex: Integer
    Index of the prescription to be considered. Defaut: 0, the first prescription in the file
    
    Returns:
    OARConstraintCount: Integer
    Number of OAR constraints in the prescription
    '''
    prdf = read_prescription(prescriptionFile)
    prescription = prdf.iloc[prescriptionIndex]
    
    OARs = prescription.OrgansAtRisk.split('Organ :')[1:]
    
    MeanMax_rx_dict = {
    #    'targetVolume': re.compile(r'Volume / Structure :(?P<targetVolume>.*?) M'),
        'Mean': re.compile(r'Mean :(?P<Mean>.*?) Max Dose :'),
        'Max': re.compile(r'Max Dose :(?P<Max>.*?c?Gy)$'),
    }
    
    OARConstraints = []
    for OAR in OARs:
        MeanMax, Constraints = re.split(r'Constraints : \r?\n', OAR)
        for key, rx in MeanMax_rx_dict.items():
            match = rx.search(MeanMax)
            if match:
                if match.group(key).strip():
                    OARConstraints.append(match.group(key))
        
        OARConstraints = OARConstraints + Constraints.splitlines()
    
    OARConstraints = list(filter(None, OARConstraints))
    OARConstraintCount = len(OARConstraints)
    return OARConstraintCount

def prescriptionPlanObjetiveCounting(prescriptionFile, prescriptionIndex=0):
    '''
    Function: prescriptionPlanObjetiveCounting
    Arguments:
    prescriptionFile: Path file
    File containing the prescription. Exported from ARIA in csv format
    
    prescriptionIndex: Integer
    Index of the prescription to be considered. Defaut: 0, the first prescription in the file
    
    Returns:
    prescriptionPlanObjetiveCount: Integer
    Number of constraints in the prescription writable as plan objetive in the clinical protocol
    '''
    prdf = read_prescription(prescriptionFile)
    prescription = prdf.iloc[0]
    
    OARs = prescription.OrgansAtRisk.split('Organ :')[1:]

    MeanMax_rx_dict = {
    #    'targetVolume': re.compile(r'Volume / Structure :(?P<targetVolume>.*?) M'),
        'Mean': re.compile(r'Mean :(?P<Mean>.*?) Max Dose :'),
        'Max': re.compile(r'Max Dose :(?P<Max>.*?c?Gy)$'),
    }

    rxVxx = re.compile(r'V.*?\$')
    rxVxxGy = re.compile(r'V.*?Gy.*?\$')
    
    MeanMaxConstraints, VxxConstraints, VxxGyConstraints = [], [], []
    for OAR in OARs:
        MeanMax, Constraints = re.split(r'Constraints : \r?\n', OAR)
        for key, rx in MeanMax_rx_dict.items():
            match = rx.search(MeanMax)
            if match:
                if match.group(key).strip():
                    MeanMaxConstraints.append(match.group(key))
        constraintList = Constraints.splitlines()
        for constraint in constraintList:
            matchVxx = rxVxx.search(constraint)
            if matchVxx:
                VxxConstraints.append(matchVxx.string)
    
            matchVxxGy = rxVxxGy.search(constraint)
            if matchVxxGy:
                VxxGyConstraints.append(matchVxxGy.string)
    
    coverageConstraintCount = coverageConstraintCounting(prescriptionFile)
    prescriptionPlanObjetiveCount = len(MeanMaxConstraints) + len(VxxConstraints) - len(VxxGyConstraints) + coverageConstraintCount
    return prescriptionPlanObjetiveCount
    
def prescriptionConstraintsToQualityIndexesCounting(prescriptionFile, prescriptionIndex=0):
    '''
    Function: prescriptionConstraintsToQualityIndexesCounting
    Count the number of prescriptions items convertible into quality indexes
    
    Arguments:
    prescriptionFile: Path file
    File containing the prescription. Exported from ARIA in csv format
    
    prescriptionIndex: Integer
    Index of the prescription to be considered. Defaut: 0, the first prescription in the file
    
    Returns:
    prescriptionConstraintsToQualityIndexesCount: Integer
    Number of constraints in the prescription writable as quality indexes in the clinical protocol
    '''
    prdf = read_prescription(prescriptionFile)
    prescription = prdf.iloc[0]
    
    OARs = prescription.OrgansAtRisk.split('Organ :')[1:]

    rxVxx = re.compile(r'V.*?\$')
    rxDxx = re.compile(r'D.*?\$')
    
    VxxConstraints, DxxConstraints = [], []
    for OAR in OARs:
        MeanMax, Constraints = re.split(r'Constraints : \r?\n', OAR)
        constraintList = Constraints.splitlines()
        for constraint in constraintList:
            matchVxx = rxVxx.search(constraint)
            if matchVxx:
                VxxConstraints.append(matchVxx.string)
    
            matchDxx = rxDxx.search(constraint)
            if matchDxx:
                DxxConstraints.append(matchDxx.string)
    

    prescriptionConstraintsToQualityIndexesCount = len(VxxConstraints + DxxConstraints)
    return prescriptionConstraintsToQualityIndexesCount

def prescriptionQualityIndexCounting(prescriptionFile, prescriptionIndex=0):
    '''
    Function: prescriptionQualityIndexCounting
    Count the number of items convertible into quality indexes
    
    Arguments:
    prescriptionFile: Path file
    File containing the prescription. Exported from ARIA in csv format
    
    prescriptionIndex: Integer
    Index of the prescription to be considered. Defaut: 0, the first prescription in the file
    
    Returns:
    prescriptionQualityIndexCount: Integer
    Number of quality indexes to be written in the clinical protocol
    '''

    prescriptionConstraintsToQualityIndexesCount = prescriptionConstraintsToQualityIndexesCounting(prescriptionFile)
    coverageConstraintCount = coverageConstraintCounting(prescriptionFile)
    prescriptionQualityIndexCount = prescriptionConstraintsToQualityIndexesCount + coverageConstraintCount
    return prescriptionQualityIndexCount

def clinicalProtocolPrescriptionItemCounting(clinicalProtocol='ClinicalProtocol.xml'):
    '''
    Function: clinicalProtocolPrescriptionItemCounting
    Arguments:
    clinicalProtocol: Path file
    File containing the Clinical Protocol in XML formal
       
    Returns:
    clinicalProtocolPrescriptionItemCount: Integer
    Number of Items in the prescription section of the clinical protocol
    '''
    cpet = parseProt(clinicalProtocol)
    clinicalProtocolPrescriptionItemCount = len(cpet.find('Phases').find('Phase').find('Prescription').findall('Item'))
    return clinicalProtocolPrescriptionItemCount


def clinicalProtocolPrescriptionQualityIndexCounting(clinicalProtocol='ClinicalProtocol.xml'):
    '''
    Function: clinicalProtocolPrescriptionItemCounting
    Arguments:
    clinicalProtocol: Path file
    File containing the Clinical Protocol in XML formal
       
    Returns:
    clinicalProtocolPrescriptionQualityIndexCount: Integer
    Number of Quality Indexes (Measure Items) in the prescription section of the clinical protocol
    '''
    cpet = parseProt(clinicalProtocol)
    clinicalProtocolPrescriptionQualityIndexCount = len(cpet.find('Phases').find('Phase').find('Prescription').findall('MeasureItem'))
    return clinicalProtocolPrescriptionQualityIndexCount

'''
    Contouring
'''

def readContouringStructureNames(rsdicom):
    '''
    Function: Read RT Dicom structure set file and generate a list of structure names

    Arguments:
    rsdicom: String
        File Path to the RT Dicom structure set

    Return:
        constrnames: list
        A list of the structure names given in ARIA
    '''
    dcmds = dcm.read_file(rsdicom)
    strsetsq = dcmds.StructureSetROISequence
    contstrnames = [structure.ROIName for structure in strsetsq]
    return contstrnames

def readClinProtStructureNames(clinprot):
    '''
    Function: Read the structure names in the clinical protocol xml file

    Arguments:
    clinprot: String
        File Path to the clinical protocol xml file

    Return:
        protstrnames: list
        A list of the structure names given in the clinical protocol xml file
    '''
    tree = ET.parse(clinprot)
    root = tree.getroot()
    structures = root.find('StructureTemplate').find('Structures')
    protstrnames = [structure.get('ID') for structure in structures.findall('Structure')]
    return protstrnames

def checkStructureNameLength(strnames):
    '''
    Function: Check if the structure name length is less than 16 characters

    Arguments:
    strnames: List
        Structure name list

    Return:
        invalidStrNames: List
        List of contouring structures names with length greater than 16 characters
    '''
    invalidStrNames = []
    for strname in strnames:
        if len(strname) > 16:
            invalidStrNames.append(strname)
    return invalidStrNames

def _suggestStrNames(strlistA, strlistB):
    '''
    Function: Suggest changes in a list of structure names based on the names of the other list 

    Arguments:
    strlistA: List
        Structure name list to be corrected

    strlistB: List
        Structure name list taken as reference

    Return:
        suggestiondf: Pandas DataFrame
        A pandas DataFrame which index is the names of the structures to be corrected and its column is the structure name suggested
    '''
    infstrdf = pd.DataFrame([{strB: ratcliff_obershelp(strA, strB) 
                              for strB in strlistB} 
                                for strA in strlistA], index=strlistA)
    infstrdf['Suggestion'] = infstrdf.idxmax(axis=1)
    suggestiondf = pd.DataFrame(infstrdf['Suggestion'])
    suggestiondf.reset_index(names='Structure', inplace=True)
    return suggestiondf

def suggestStrNames(clinprot, rsdicom):
    '''
    Function: Suggest changes in a list of structure names based on the names of the other list 

    Arguments:
    clinprot: String
        File Path to the clinical protocol xml file containing the structure names to be corrected

    rsdicom: String
        File Path to the RT Dicom containing the reference structure set

    Return:
        suggestiondf: Pandas DataFrame
        A pandas DataFrame which index is the names of the structures to be corrected and its column is the structure name suggested
    '''

    protstrnames = readClinProtStructureNames(clinprot)
    contstrnames = readContouringStructureNames(rsdicom)
    invalidStrNames = checkStructureNameLength(contstrnames)
    sep = ', '
    if invalidStrNames:
        raise NameError('''
        The following structures are more than 16 characters long
        which is not allowed for the clinical protocol definition.\n
        ''' + sep.join(invalidStrNames))
    invalidStrNames = checkStructureNameLength(protstrnames)
    if invalidStrNames:
        raise NameError('''
        The following structures are more than 16 characters long
        which is not allowed for the clinical protocol definition
        ''' + sep.join(invalidStrNames))
    suggestiondf = _suggestStrNames(protstrnames, contstrnames)
    return suggestiondf

def _correctStrNames(filedata, strNameChanges):
    '''
    Function: Correct structure names in a prescrption file following a DataFrame of directions  

    Arguments:
    filedata: String
        The text content of a prescription csv file to be corrected

    strNameChanges: DataFrame
        Pandas datafrmae with the old and new names of each structure to be corrected

    Return:
        filedata: String
        The corrected text of the prescription csv file
    '''
    for index, strName in strNameChanges.iterrows():
        filedata = filedata.replace(strName.Old, strName.New)
    return filedata

def correctStrNames(prescriptionFile, strNameChanges):
    '''
    Function: Correct structure names in a prescrption file following a DataFrame of directions  

    Arguments:
    prescriptionFile: String
        The path to the prescription csv file to be corrected

    strNameChanges: DataFrame
        Pandas datafrmae with the old and new names of each structure to be corrected

    '''
    # Read the prescription file
    with open(prescriptionFile, 'r') as file:
      filedata = file.read()
    # Correct the prescription file
    filedata = _correctStrNames(filedata, strNameChanges)
    # Write the corrected prescription file
    with open(prescriptionFile, 'w') as file:
      file.write(filedata)
